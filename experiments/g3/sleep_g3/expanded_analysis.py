"""Frozen coverage, multi-night, and event diagnostics for the expanded pilot."""

import json
import os
import platform
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from .diagnose import reference_summary
from .metrics import _complete_runs, _match_events, _overlap, _runs, evaluate_forecasts, paired_delta
from .protocol import sha256_file, write_json


def _mean(values):
    values = [float(value) for value in values if value is not None]
    return float(np.mean(values)) if values else None


def night_balanced_totals(target, total_minutes, participant, night, epoch_seconds=30):
    complete = (target >= 0).all(axis=1)
    true_minutes = (target == 1).sum(axis=1) * epoch_seconds / 60
    people = {}
    for pid in np.unique(participant):
        nights = {}
        for record_night in np.unique(night[participant == pid]):
            selected = (participant == pid) & (night == record_night)
            valid = selected & complete
            error = total_minutes[valid] - true_minutes[valid]
            nights[str(record_night)] = {
                "candidate_origins": int(selected.sum()), "complete_origins": int(valid.sum()),
                "zero_wake_origins": int((true_minutes[valid] == 0).sum()),
                "mae_minutes": _mean(np.abs(error)), "bias_minutes": _mean(error),
            }
        people[str(pid)] = {"nights": nights,
                            "mae_minutes": _mean([row["mae_minutes"] for row in nights.values()]),
                            "bias_minutes": _mean([row["bias_minutes"] for row in nights.values()])}
    return {"aggregation": "origin_mean_then_equal_nights_within_person_then_equal_participants",
            "mae_minutes": _mean([row["mae_minutes"] for row in people.values()]),
            "bias_minutes": _mean([row["bias_minutes"] for row in people.values()]),
            "per_participant": people}


def unique_event_scores(target, arms, participant, night, origin_time,
                        epoch_seconds=30, short_max_epochs=2):
    """Average hits over evaluable origins, then distinct events, then people.

    A long overlapping prediction may count as a hit. IoU and duration error
    expose that difference from reproducing the reference event's boundaries.
    Matching and censoring are identical to the primary window-event metric.
    """
    output = {}
    for name, arm in arms.items():
        if arm.get("path") is None:
            continue
        events = {}
        for row, path, pid, record_night, origin in zip(
            target, arm["path"], participant, night, origin_time
        ):
            truth = _complete_runs(row)
            censored = [event for event in _runs(row) if event not in set(truth)]
            predicted = [(start, end) for start, end in _complete_runs(path)
                         if not np.any(row[start - 1:end + 1] == -1)
                         and not any(_overlap((start, end), event) for event in censored)]
            matched = {first: second for first, second in _match_events(truth, predicted)}
            for index, (start, end) in enumerate(truth):
                if end - start > short_max_epochs:
                    continue
                key = (str(pid), str(record_night), float(origin + start * epoch_seconds),
                       float(origin + end * epoch_seconds))
                event = events.setdefault(key, {
                    "participant": key[0], "night": key[1], "start_time": key[2], "end_time": key[3],
                    "duration_epochs": end - start, "evaluable_origins": 0, "hit_origins": 0,
                    "matched_iou": [], "matched_duration_error_seconds": [],
                })
                event["evaluable_origins"] += 1
                if index in matched:
                    prediction = predicted[matched[index]]
                    overlap = _overlap((start, end), prediction)
                    event["hit_origins"] += 1
                    event["matched_iou"].append(overlap / (end - start + prediction[1] - prediction[0] - overlap))
                    event["matched_duration_error_seconds"].append(
                        (prediction[1] - prediction[0] - (end - start)) * epoch_seconds)
        rows = []
        for event in events.values():
            event["origin_hit_rate"] = event["hit_origins"] / event["evaluable_origins"]
            event["mean_matched_iou"] = _mean(event.pop("matched_iou"))
            event["mean_matched_duration_error_seconds"] = _mean(event.pop("matched_duration_error_seconds"))
            rows.append(event)
        strata = {}
        for duration in (None, *range(1, short_max_epochs + 1)):
            selected = [row for row in rows if duration is None or row["duration_epochs"] == duration]
            people = {}
            for pid in sorted({row["participant"] for row in selected}):
                own = [row for row in selected if row["participant"] == pid]
                people[pid] = {
                    "unique_reference_events": len(own),
                    "evaluable_event_origins": sum(row["evaluable_origins"] for row in own),
                    "mean_origin_hit_rate_over_events": _mean([row["origin_hit_rate"] for row in own]),
                    "unique_events_by_night": {record_night: sum(row["night"] == record_night for row in own)
                                               for record_night in sorted({row["night"] for row in own})},
                }
            strata["all_short" if duration is None else f"{duration}_epoch"] = {
                "unique_reference_events": len(selected), "participants": len(people),
                "event_then_participant_macro_origin_hit_rate": _mean(
                    [row["mean_origin_hit_rate_over_events"] for row in people.values()]),
                "per_participant": people,
            }
        output[name] = {"strata": strata, "events": rows}
    return {"unit": "distinct_reference_event_with_rate_over_its_evaluable_forecast_origins",
            "aggregation": "origin_hit_rate_then_equal_reference_events_then_equal_participants",
            "matching": "same_positive_overlap_one_to_one_matching_as_primary_metrics",
            "limitation": "a_hit_does_not_imply_correct_event_length_or_exact_boundaries",
            "arms": output}


def analyze(root):
    if not os.environ.get("SLURM_JOB_ID") or platform.node().startswith("login"):
        raise RuntimeError("analysis requires an allocated compute node")
    root = Path(root)
    base = Path(json.loads((root / "latest_run.json").read_text())["path"])
    if not base.resolve().is_relative_to((root / "results").resolve()):
        raise ValueError("result path leaves run root")
    receipt = json.loads((base / "run_metadata.json").read_text())
    if receipt["status"] != "scored_diagnostic" or receipt["test_accessed"]:
        raise ValueError("a completed validation-only run is required")
    config = receipt["protocol"]
    metrics = json.loads((base / "metrics.json").read_text())
    with np.load(base / "validation_predictions.npz", allow_pickle=False) as stored:
        y, pid, night, origin = (stored[key] for key in ("target", "participant", "night", "origin_time"))
        arms = {name: {key: stored[name + "__" + key] if name + "__" + key in stored else None
                       for key in ("total_minutes", "probability", "path")}
                for name in metrics["arms"]}
        reference = reference_summary(y, pid, night, origin, config["epoch_seconds"], config["short_event_max_epochs"])
        night_scores = {name: night_balanced_totals(y, arm["total_minutes"], pid, night, config["epoch_seconds"])
                        for name, arm in arms.items()}
        complete = (y >= 0).all(axis=1)
        zero = (y == 1).sum(axis=1) == 0
        conditional = {}
        for label, mask in (("zero_wake_complete", complete & zero), ("nonzero_wake_complete", complete & ~zero)):
            conditional[label] = evaluate_forecasts(
                y[mask], {name: {key: value[mask] if value is not None else None for key, value in arm.items()}
                          for name, arm in arms.items()}, pid[mask],
                config["epoch_seconds"], config["short_event_max_epochs"])
        events = unique_event_scores(y, arms, pid, night, origin,
                                     config["epoch_seconds"], config["short_event_max_epochs"])
    deltas = []
    for arm in ("direct_trajectory_soft", "direct_trajectory_hard"):
        for control in ("direct_trajectory", "zero_wake", "population_median", "population_probability", "direct_outcome", "transition_matrix"):
            if control not in arms:
                continue
            deltas.append(paired_delta(metrics, arm, control, seed=config["split_seed"]))
        for metric in ("probability.brier", "probability.nll", "hard_map.events.short_event_recall",
                       "hard_map.false_wake.false_positive_wake_minutes"):
            deltas.append(paired_delta(metrics, arm, "direct_trajectory", metric, seed=config["split_seed"]))
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    output = base / ("expanded_analysis_" + stamp)
    output.mkdir(exist_ok=False)
    for name, value in (("reference_summary", reference), ("night_balanced_totals", night_scores),
                        ("conditional_metrics", conditional), ("unique_event_scores", events),
                        ("paired_deltas", deltas)):
        write_json(output / (name + ".json"), value)
    write_json(output / "metadata.json", {
        "status": "completed_diagnostic_analysis", "evidence_class": "diagnostic_only", "base_run": str(base),
        "test_accessed": False, "model_refit": False, "hyperparameters_changed": False,
        "protocol_sha256": receipt["protocol_sha256"], "analysis_sha256": sha256_file(__file__),
        "predictions_sha256": sha256_file(base / "validation_predictions.npz"),
        "host": platform.node(), "slurm_job_id": os.environ.get("SLURM_JOB_ID"),
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "conditional_scope": "reference-defined scoring strata only; never used for input/participant/origin selection",
    })
    write_json(root / "latest_expanded_analysis.json", {"path": str(output)})
    return {"output": str(output), "reference": reference, "status": "completed_diagnostic_analysis"}
