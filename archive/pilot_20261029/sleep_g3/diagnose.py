"""Post-run degeneracy checks, without model fitting or parameter selection."""

import json
import os
import platform
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from .metrics import _complete_runs, evaluate_forecasts
from .protocol import sha256_file, write_json


def reference_summary(target, participant, night, origin_time, epoch_seconds=30, short_max_epochs=2):
    target = np.asarray(target)
    complete = (target >= 0).all(axis=1)
    totals = np.where(complete, np.where(target >= 0, target, 0).sum(axis=1) * epoch_seconds / 60, np.nan)
    people = {}
    for pid in np.unique(participant):
        values = totals[(participant == pid) & complete]
        people[str(pid)] = {"complete_origins": int(len(values)),
                            "zero_wake_origins": int((values == 0).sum()),
                            "mean_wake_minutes": float(values.mean()) if len(values) else None,
                            "median_wake_minutes": float(np.median(values)) if len(values) else None}
    unique_events = set()
    instances = 0
    for y, pid, record_night, origin in zip(target, participant, night, origin_time):
        for start, end in _complete_runs(y):
            if end - start <= short_max_epochs:
                instances += 1
                unique_events.add((str(pid), str(record_night), float(origin + start * epoch_seconds),
                                   float(origin + end * epoch_seconds)))
    return {"complete_origins": int(complete.sum()),
            "zero_wake_origins": int((totals[complete] == 0).sum()),
            "per_participant": people, "short_window_event_instances": instances,
            "unique_short_reference_events_observed_in_windows": len(unique_events),
            "participants_with_unique_short_events": len({event[0] for event in unique_events}),
            "deduplication": "participant, night, absolute reference event start/end; not clinical arousals"}


def diagnose(root):
    if not os.environ.get("SLURM_JOB_ID") or platform.node().startswith("login"):
        raise RuntimeError("diagnostic analysis requires an allocated compute node")
    root = Path(root)
    base = Path(json.loads((root / "latest_run.json").read_text())["path"])
    if not base.resolve().is_relative_to((root / "results").resolve()):
        raise ValueError("run path must remain inside this root")
    metadata = json.loads((base / "run_metadata.json").read_text())
    if metadata["status"] != "scored_diagnostic" or metadata["test_accessed"]:
        raise ValueError("expected a completed validation-only diagnostic")
    config = metadata["protocol"]
    original = json.loads((base / "metrics.json").read_text())
    predictions = base / "validation_predictions.npz"
    with np.load(predictions, allow_pickle=False) as stored:
        y, pid = stored["target"], stored["participant"]
        summary = reference_summary(y, pid, stored["night"], stored["origin_time"],
                                    config["epoch_seconds"], config["short_event_max_epochs"])
        zero = {"probability": np.zeros(y.shape, dtype=float), "path": np.zeros(y.shape, dtype=np.uint8),
                "total_minutes": np.zeros(len(y), dtype=float)}
        evaluated = evaluate_forecasts(y, {"zero_wake": zero}, pid,
                                       config["epoch_seconds"], config["short_event_max_epochs"])
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    output = base / ("supplement_" + stamp)
    output.mkdir(exist_ok=False)
    write_json(output / "reference_summary.json", summary)
    write_json(output / "zero_wake_metrics.json", evaluated)
    receipt = {"status": "scored_diagnostic_supplement", "evidence_class": "diagnostic_only",
               "purpose": "Check constant-sleep degeneracy and deduplicate short events after inspecting sparse pilot outcomes",
               "base_run": str(base), "base_run_metadata_sha256": sha256_file(base / "run_metadata.json"),
               "predictions_sha256": sha256_file(predictions),
               "analysis_sha256": sha256_file(__file__), "test_accessed": False,
               "model_refit": False, "hyperparameters_changed": False,
               "host": platform.node(), "slurm_job_id": os.environ.get("SLURM_JOB_ID"),
               "finished_utc": datetime.now(timezone.utc).isoformat()}
    write_json(output / "metadata.json", receipt)
    write_json(root / "latest_diagnostic_supplement.json", {"path": str(output)})
    return {"output": str(output), "reference": summary,
            "zero_wake_mae_minutes": evaluated["arms"]["zero_wake"]["total_wake"]["mae_minutes"],
            "original_expected_wake_mae": {name: arm["total_wake"]["mae_minutes"]
                                           for name, arm in original["arms"].items()},
            "model_refit": False, "test_accessed": False}
