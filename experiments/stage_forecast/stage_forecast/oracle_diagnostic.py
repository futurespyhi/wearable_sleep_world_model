"""Evaluate a frozen transition model using the observed stage at the cutoff."""

import argparse
import json
import os
from pathlib import Path
import platform
import resource
import sys
from time import perf_counter

import numpy as np

from sleep_g3.protocol import write_json
from .oracle_inputs import load_oracle_inputs
from .oracle_scores import score_oracle
from .oracle_tables import render_tables


def check_parent(scores, original):
    """The changed-stage subset has the identical definition in both reports."""
    prev = original["changed_30"]
    current = scores["leads"]["30"]
    if (current["overall"]["origins"] != prev["both_known"]
            or current["same"]["origins"] != prev["unchanged"]
            or current["changed"]["origins"] != prev["origins"]
            or current["changed"]["support"] != prev["support"]):
        raise ValueError("oracle analysis differs from the source changed-stage cohort")
    return_values = {}
    for arm in ("transition", "prior_mix", "stage_prior"):
        difference = current["changed"]["nll"][arm] - original["methods"][arm]["changed_30_nll"]
        if not np.isclose(difference, 0, rtol=0, atol=1e-12):
            raise ValueError(f"changed-stage {arm} NLL differs from saved scores")
        return_values[arm] = difference
    return return_values


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("expanded_root", "transition_root", "reports_root", "output"):
        parser.add_argument(name, type=Path)
    parser.add_argument("code_commit")
    args = parser.parse_args()
    for source in (args.expanded_root, args.transition_root):
        if args.output.resolve().is_relative_to(source.resolve()):
            raise ValueError("Use a fresh artifact root outside the source runs")
    args.output.mkdir(parents=True, exist_ok=False)
    started = perf_counter()
    receipt = {
        "run_id": args.output.parent.name, "code_commit": args.code_commit,
        "base_commit": "2e15c30318f983b6aec63f0c34859fa46b6ff473",
        "job_id": os.environ["SLURM_JOB_ID"], "host": platform.node(), "device": "cpu",
        "python": sys.executable, "python_version": sys.version, "numpy": np.__version__,
        "artifact_path": str(args.output), "test_accessed": False,
    }
    try:
        val, pt, matrices, controls, receipt["inputs"] = load_oracle_inputs(
            args.expanded_root, args.transition_root, args.reports_root)
        scores = score_oracle(val, pt, matrices, controls)
        original = json.loads((args.reports_root / "20261119-stage-transition" / "metrics.json").read_text())
        receipt["changed_30_difference_from_saved_nll"] = check_parent(scores, original)
        write_json(args.output / "metrics.json", scores)
        (args.output / "tables.md").write_text(render_tables(scores).rstrip() + "\n")
        receipt["status"] = "completed"
    except Exception as error:
        receipt.update(status="failed", error=str(error))
        raise
    finally:
        receipt.update(elapsed_seconds=perf_counter() - started,
                       peak_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024)
        write_json(args.output / "execution.json", receipt)


if __name__ == "__main__":
    main()
