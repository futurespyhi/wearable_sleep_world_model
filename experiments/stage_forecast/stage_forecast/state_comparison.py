"""CPU follow-up on the frozen 38-night predictions."""

import argparse
import json
import os
import platform
import resource
import sys
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

import numpy as np
import scipy
from sleep_g3.protocol import write_json
from .transition_fit import fit_controls
from .transition_inputs import load_inputs, make_predictions
from .transition_scores import score_comparison, render_scores


def check_reference_scores(scores, published):
    """Reproduce already published reference endpoints before releasing the comparison."""
    largest = 0.0
    for seed in range(3):
        previous = json.loads((published / f"seed-{seed}.json").read_text())["methods"]
        for arm in ("persistence", "stage_prior", "direct"):
            method = f"direct_{seed}" if arm == "direct" else arm
            for minute in ("5", "15", "30"):
                original = previous[arm]["leads"][minute]
                observed = scores["methods"][method]["leads"][minute]
                for key in ("macro_f1", "wake_recall", "nll"):
                    delta = abs(original[key] - observed[key])
                    if not np.isfinite(delta) or delta > 1e-7:
                        raise ValueError(f"Reference score differs for {method}, {minute} min, {key}: {delta}")
                    largest = max(largest, delta)
    return largest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("source_root", "published", "output"):
        parser.add_argument(name, type=Path)
    parser.add_argument("code_commit")
    args = parser.parse_args()
    if args.output.resolve().is_relative_to(args.source_root.resolve()):
        raise ValueError("use a new artifact directory outside the source run")
    args.output.mkdir(parents=True, exist_ok=False)
    started = perf_counter()
    execution = {
        "base_commit": "0e0c0a1127805b7fa1b7cca516ae686638207c12", "code_commit": args.code_commit,
        "run_id": args.output.parent.name, "job_id": os.environ.get("SLURM_JOB_ID"),
        "started_utc": datetime.now(timezone.utc).isoformat(), "host": platform.node(),
        "python": sys.executable, "python_version": platform.python_version(),
        "numpy": np.__version__, "scipy": scipy.__version__,
        "source_root": str(args.source_root), "artifact_path": str(args.output), "test_accessed": False,
    }
    try:
        train, val, current_prob, priors, direct, identities = load_inputs(args.source_root, args.published)
        execution["inputs"] = identities
        weights, matrices, fit = fit_controls(train)
        write_json(args.output / "fit.json", {"prior_weights": weights.tolist(),
                   "transition_matrices": matrices.tolist(), "training": fit})
        probabilities = make_predictions(current_prob, priors, direct, weights, matrices)
        np.savez_compressed(args.output / "control_predictions.npz", participant=val.participant,
                            night=val.night, origin_time=val.origin_time,
                            **{key: probabilities[key] for key in ("persistence", "prior_mix", "transition")})
        scores = score_comparison(val, probabilities)
        execution["max_reference_endpoint_abs_difference"] = check_reference_scores(scores, args.published)
        write_json(args.output / "metrics.json", scores)
        (args.output / "tables.md").write_text(render_scores(scores) + "\n")
        execution["status"] = "completed"
    except Exception as exc:
        execution.update(status="failed", error=f"{type(exc).__name__}: {exc}")
        raise
    finally:
        execution.update(elapsed_seconds=perf_counter() - started,
                         peak_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024)
        write_json(args.output / "execution.json", execution)


if __name__ == "__main__":
    main()
