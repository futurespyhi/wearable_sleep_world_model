"""Can pre-cutoff wearable measurements predict whether two endpoint stages differ?"""

import argparse
import os
from pathlib import Path
import platform
import resource
import sys
from time import perf_counter

import numpy as np
import scipy

from sleep_g3.protocol import sha256_file, write_json
from .endpoint_features import prepare_posteriors, recent_features, RECENT_FEATURE_NAMES
from .endpoint_models import fit_endpoint_models
from .endpoint_scores import score_endpoint, render_endpoint
from .metrics import LEAD_INDICES
from .recording_time_inputs import _partition_bins
from .transition_inputs import _receipt, _require, load_inputs


PARENT = "20261119-recording-time"
BASE = "5af00c4e57456e42bd25939b566c94f8ad7588a4"


def load_parent(artifacts, reports):
    import json
    published = reports / PARENT
    retained = artifacts / PARENT / "results"
    execution, execution_hash = _receipt(retained / "execution.json", published / "execution.json")
    metrics, scores_hash = _receipt(retained / "metrics.json", published / "metrics.json")
    _require(execution["status"] == "completed" and execution["run_id"] == PARENT
             and execution["test_accessed"] is False and execution["metrics_sha256"] == scores_hash,
             "parent recording-time diagnostic identity mismatch")
    expanded = artifacts / "20261119-stage-expanded"
    train, val, saved_pt, _, _, expanded_inputs = load_inputs(expanded, reports / expanded.name)
    _require(all(execution["inputs"][k] == v for k, v in expanded_inputs.items()),
             "expanded inputs differ from those retained by the parent")
    audit = json.loads((expanded / "expanded-cache/audit.json").read_text())
    train_bin = _partition_bins(train, audit, "train")
    val_bin = _partition_bins(val, audit, "validation")
    counts = {k: np.bincount(v, minlength=4).tolist()
              for k, v in (("train", train_bin), ("validation", val_bin))}
    _require(counts == execution["inputs"]["bin_origin_counts"], "recording-time bins differ")
    identity = {**expanded_inputs, "parent_run_id": PARENT, "parent_code_commit": execution["code_commit"],
                "parent_execution_sha256": execution_hash, "parent_metrics_sha256": scores_hash,
                "bin_origin_counts": counts}
    return train, val, saved_pt, train_bin, val_bin, metrics, identity


def score_validation(val, predictions, parent):
    scores = {"target": "endpoint stage differs from cutoff stage", "total_origins": len(val.origin),
              "common_masks": {}, "leads": {}}
    for column, (minute, index) in enumerate(LEAD_INDICES.items()):
        lead = str(minute)
        current = val.current_stage
        future = val.stage[:, index]
        known = current >= 0
        target_known = future >= 0
        mask = known & target_known
        coverage = {"both_known": int(mask.sum()), "both_unknown": int((~known & ~target_known).sum()),
                    "current_known_target_unknown": int((known & ~target_known).sum()),
                    "current_unknown_target_known": int((~known & target_known).sum())}
        _require(coverage == parent["common_masks"][lead], "common mask differs from parent")
        event = current[mask] != future[mask]
        scored = score_endpoint(event.astype(int), val.participant[mask],
                                {arm: prob[mask, column] for arm, prob in predictions.items()})
        for person, row in scored["per_participant"].items():
            reference = parent["per_participant"][person][lead]
            for count, stratum in (("origins", "overall"), ("positive", "changed"), ("negative", "same")):
                _require(row[count] == reference[stratum]["origins"], f"{lead} {person} {count} mismatch")
        scores["common_masks"][lead] = coverage
        scores["leads"][lead] = scored
    return scores


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("artifacts", "reports", "output"):
        parser.add_argument(name, type=Path)
    parser.add_argument("code_commit")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    started = perf_counter()
    receipt = {"run_id": args.output.parent.name, "base_commit": BASE, "code_commit": args.code_commit,
               "spec_commit": args.code_commit, "spec_path": "specs/2026-11-19_endpoint_change.md",
               "job_id": os.environ["SLURM_JOB_ID"], "device": "cpu", "host": platform.node(),
               "python": sys.executable, "python_version": sys.version, "numpy": np.__version__,
               "scipy": scipy.__version__, "requested_cpus": 2, "requested_memory_gib": 8,
               "time_limit_minutes": 10, "artifact_path": str(args.output.resolve()), "test_accessed": False}
    try:
        train, val, saved_pt, tb, vb, parent, receipt["inputs"] = load_parent(args.artifacts, args.reports)
        oof, pt, receipt["posterior"] = prepare_posteriors(train, val, saved_pt)
        recent_train, recent_val = (recent_features(x.history) for x in (train, val))
        predictions, fit = fit_endpoint_models(train, tb, vb, oof, pt, recent_train, recent_val)
        scores = score_validation(val, predictions, parent)
        scores["sensor_features"] = list(RECENT_FEATURE_NAMES)
        scores["missing_summary_counts"] = {k: np.isnan(array).sum(axis=0).tolist() for k, array in
                                           (("train", recent_train), ("validation", recent_val))}
        write_json(args.output / "fit.json", fit)
        np.savez_compressed(args.output / "probabilities.npz", train_oof_pt=oof, participant=val.participant,
                            night=val.night, origin=val.origin, leads=list(LEAD_INDICES), **predictions)
        write_json(args.output / "metrics.json", scores)
        tables = [f"## +{lead} minutes\n\n{render_endpoint(score).strip()}"
                  for lead, score in scores["leads"].items()]
        (args.output / "tables.md").write_text("\n\n".join(tables) + "\n")
        receipt["sha256"] = {name: sha256_file(args.output / name)
                             for name in ("metrics.json", "fit.json", "probabilities.npz")}
        receipt["validation_check"] = "all parent masks and each person's positive and negative counts matched"
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
