"""Evaluate time since recording start as a control for stage-transition forecasts."""

import argparse
import json
import os
from pathlib import Path
import platform
import resource
import sys
from time import perf_counter

import numpy as np
from sleep_g3.protocol import sha256_file, write_json

from .recording_time_fit import fit_time, make_time_predictions
from .recording_time_inputs import load_time_inputs
from .recording_time_scores import render_time, score_time


def check_frozen(scores, parent):
    if (scores["common_masks"] != parent["common_masks"]
            or scores["total_origins"] != parent["total_origins"]
            or set(scores["per_participant"]) != set(parent["participants_30"])):
        raise ValueError("validation origins or lead masks differ from the published oracle")
    pairs = [(row, parent["leads"][h][stratum])
             for h, lead in scores["leads"].items() for stratum, row in lead.items()]
    pairs.extend((row, parent["participants_30"][person][stratum])
                 for person, leads in scores["per_participant"].items()
                 for stratum, row in leads["30"].items())
    errors = []
    for row, original in pairs:
        if any(row[key] != original[key] for key in ("support", "origins", "participants")):
            raise ValueError("oracle coverage mismatch")
        for method, nll in original["nll"].items():
            errors.append(abs(row["nll"][method] - nll))
    if not np.allclose(errors, 0.0, atol=1e-12, rtol=0):
        raise ValueError("frozen-method NLL mismatch")
    return {"scores_compared": len(errors), "max_absolute_nll_difference": max(errors)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("expanded", "transition", "oracle", "reports", "output"):
        parser.add_argument(name, type=Path)
    parser.add_argument("code_commit")
    args = parser.parse_args()
    for source in (args.expanded, args.transition, args.oracle):
        if args.output.resolve().is_relative_to(source.resolve()):
            raise ValueError("choose an output outside the parent runs")
    args.output.mkdir(parents=True, exist_ok=False)
    started = perf_counter()
    receipt = {
        "run_id": args.output.parent.name, "base_commit": "2a5cf60b6400068340bc0d8cac3448c62786af6d",
        "code_commit": args.code_commit, "spec_commit": args.code_commit,
        "spec_path": "specs/2026-11-19_recording_time_controls.md",
        "job_id": os.environ["SLURM_JOB_ID"], "host": platform.node(), "device": "cpu",
        "requested_cpus": 2, "requested_memory_gib": 8, "time_limit_minutes": 10,
        "python": sys.executable, "python_version": sys.version, "numpy": np.__version__,
        "artifact_path": str(args.output.resolve()), "test_accessed": False,
    }
    try:
        train, val, pt, prior, matrices, controls, train_bin, val_bin, receipt["inputs"] = load_time_inputs(
            args.expanded, args.transition, args.oracle, args.reports)
        priors, transitions, fit = fit_time(train, train_bin, prior, matrices)
        predictions = make_time_predictions(val_bin, pt, val.current_stage, priors, transitions)
        scores = score_time(val, {**controls, **predictions})
        parent = json.loads((args.reports / "20261119-stage-oracle" / "metrics.json").read_text())
        receipt["frozen_scores_vs_parent"] = check_frozen(scores, parent)
        fit_file = args.output / "fit.npz"
        np.savez_compressed(fit_file, priors=priors, transitions=transitions,
                            future_counts=fit["future_counts"], pair_counts=fit["pair_counts"])
        receipt["fit_sha256"] = sha256_file(fit_file)
        scores["fit"] = {k: v for k, v in fit.items() if k not in ("future_counts", "pair_counts")}
        changed = scores["leads"]["30"]["changed"]["minus_time_only"]
        scores["primary_changed_30"] = {
            "time_transition_beats_time_only": changed["time_transition"] < 0,
            "time_oracle_beats_time_only": changed["time_oracle"] < 0,
        }
        write_json(args.output / "metrics.json", scores)
        (args.output / "tables.md").write_text(render_time(scores).rstrip() + "\n")
        receipt["metrics_sha256"] = sha256_file(args.output / "metrics.json")
        receipt["status"] = "completed"
    except Exception as exc:
        receipt.update(status="failed", error=str(exc))
        raise
    finally:
        receipt.update(elapsed_seconds=perf_counter() - started,
                       peak_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024)
        write_json(args.output / "execution.json", receipt)


if __name__ == "__main__":
    main()
