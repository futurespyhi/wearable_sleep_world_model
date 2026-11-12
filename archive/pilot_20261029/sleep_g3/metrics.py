"""Participant-balanced metrics for binary future-Wake forecasts.

Labels are sleep=0, Wake=1, and unknown=-1. A short Wake event is an
interior run of at most ``short_max_epochs`` Wake epochs, bounded by known
sleep. These are annotation-defined Wake runs, not clinical arousals.
Overlapping forecast origins produce repeated window-event instances;
this module never interprets those instances as distinct physical events.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np
from scipy.optimize import linear_sum_assignment


_NLL_EPS = 1e-12
_ECE_BINS = 10


def _mean(values: Sequence[float | None]) -> float | None:
    finite = [float(value) for value in values if value is not None]
    return float(np.mean(finite)) if finite else None


def _ratio(numerator: int, denominator: int) -> float | None:
    return float(numerator / denominator) if denominator else None


def _runs(row: np.ndarray) -> list[tuple[int, int]]:
    wake = np.concatenate(([False], row == 1, [False])).astype(np.int8)
    changes = np.diff(wake)
    return list(zip(np.flatnonzero(changes == 1), np.flatnonzero(changes == -1)))


def _complete_runs(row: np.ndarray) -> list[tuple[int, int]]:
    return [
        (int(start), int(end))
        for start, end in _runs(row)
        if start > 0 and end < len(row) and row[start - 1] == 0 and row[end] == 0
    ]


def _overlap(first: tuple[int, int], second: tuple[int, int]) -> int:
    return max(0, min(first[1], second[1]) - max(first[0], second[0]))


def _match_events(
    truth: Sequence[tuple[int, int]], prediction: Sequence[tuple[int, int]]
) -> list[tuple[int, int]]:
    """Return truth/prediction indices, maximizing cardinality before IoU."""
    if not truth or not prediction:
        return []
    scores = np.zeros((len(truth), len(prediction)), dtype=float)
    # The cardinality bonus exceeds the total possible IoU improvement.
    bonus = min(len(truth), len(prediction)) + 1
    for truth_index, true_event in enumerate(truth):
        for prediction_index, predicted_event in enumerate(prediction):
            intersection = _overlap(true_event, predicted_event)
            if intersection:
                union = (
                    true_event[1] - true_event[0]
                    + predicted_event[1] - predicted_event[0]
                    - intersection
                )
                scores[truth_index, prediction_index] = bonus + intersection / union
    truth_indices, prediction_indices = linear_sum_assignment(-scores)
    return [
        (int(truth_index), int(prediction_index))
        for truth_index, prediction_index in zip(truth_indices, prediction_indices)
        if scores[truth_index, prediction_index] > 0
    ]


def _event_counts(
    target: np.ndarray, path: np.ndarray, short_max_epochs: int
) -> dict[str, int]:
    truth = _complete_runs(target)
    truth_set = set(truth)
    censored_truth = [event for event in _runs(target) if event not in truth_set]
    prediction = []
    for start, end in _complete_runs(path):
        if np.any(target[start - 1 : end + 1] == -1):
            continue
        if any(_overlap((start, end), event) for event in censored_truth):
            continue
        prediction.append((start, end))
    matches = _match_events(truth, prediction)
    short = {index for index, (start, end) in enumerate(truth) if end - start <= short_max_epochs}
    valid = target != -1
    return {
        "evaluable_origins": int(np.any(valid[:-2] & valid[1:-1] & valid[2:])),
        "true_event_instances": len(truth),
        "short_event_instances": len(short),
        "predicted_event_instances": len(prediction),
        "matched_event_instances": len(matches),
        "matched_short_event_instances": sum(index in short for index, _ in matches),
        "false_positive_event_instances": len(prediction) - len(matches),
        "censored_true_wake_runs": len(censored_truth),
        "unscored_predicted_wake_runs": len(_runs(path)) - len(prediction),
        "origins_with_short_events": int(bool(short)),
        "origins_with_predicted_events": int(bool(prediction)),
    }


def _event_summary(counts: Sequence[dict[str, int]]) -> dict[str, Any]:
    keys = (
        "evaluable_origins", "true_event_instances", "short_event_instances",
        "predicted_event_instances", "matched_event_instances",
        "matched_short_event_instances", "false_positive_event_instances",
        "censored_true_wake_runs", "unscored_predicted_wake_runs",
        "origins_with_short_events", "origins_with_predicted_events",
    )
    result: dict[str, Any] = {key: sum(row[key] for row in counts) for key in keys}
    result["short_event_recall"] = _ratio(
        result["matched_short_event_instances"], result["short_event_instances"]
    )
    result["event_precision"] = _ratio(
        result["matched_event_instances"], result["predicted_event_instances"]
    )
    result["event_recall"] = _ratio(
        result["matched_event_instances"], result["true_event_instances"]
    )
    return result


def _total_summary(
    prediction: np.ndarray, true_minutes: np.ndarray, complete: np.ndarray
) -> dict[str, Any]:
    errors = prediction[complete] - true_minutes[complete]
    return {
        "evaluable_origins": int(len(errors)),
        "mae_minutes": float(np.mean(np.abs(errors))) if len(errors) else None,
        "bias_minutes": float(np.mean(errors)) if len(errors) else None,
    }


def _aggregate_totals(summaries: Sequence[dict[str, Any]]) -> dict[str, Any]:
    return {
        "aggregation": "mean_over_participants_of_mean_over_complete_origins",
        "evaluable_origins": sum(row["evaluable_origins"] for row in summaries),
        "evaluable_participants": sum(row["evaluable_origins"] > 0 for row in summaries),
        "mae_minutes": _mean([row["mae_minutes"] for row in summaries]),
        "bias_minutes": _mean([row["bias_minutes"] for row in summaries]),
    }


def _probability_by_origin(target: np.ndarray, probability: np.ndarray) -> list[dict[str, Any]]:
    result = []
    for truth, predicted in zip(target, probability):
        valid = truth != -1
        y = truth[valid]
        p = predicted[valid]
        if not len(y):
            result.append({"valid_epochs": 0, "brier": None, "nll": None, "ece": None})
            continue
        clipped = np.clip(p, _NLL_EPS, 1 - _NLL_EPS)
        bins = np.minimum((p * _ECE_BINS).astype(int), _ECE_BINS - 1)
        ece = 0.0
        for bin_index in range(_ECE_BINS):
            inside = bins == bin_index
            if np.any(inside):
                ece += float(np.mean(inside) * abs(np.mean(p[inside]) - np.mean(y[inside])))
        result.append({
            "valid_epochs": int(len(y)),
            "brier": float(np.mean((p - y) ** 2)),
            "nll": float(-np.mean(y * np.log(clipped) + (1 - y) * np.log1p(-clipped))),
            "ece": float(ece),
        })
    return result


def _probability_summary(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    return {
        "evaluable_origins": sum(row["valid_epochs"] > 0 for row in rows),
        "valid_epochs": sum(row["valid_epochs"] for row in rows),
        **{name: _mean([row[name] for row in rows]) for name in ("brier", "nll", "ece")},
    }


def _false_wake_summary(
    target: np.ndarray, path: np.ndarray, epoch_minutes: float
) -> dict[str, Any]:
    sleep = target == 0
    sleep_count = np.sum(sleep, axis=1)
    false_count = np.sum((path == 1) & sleep, axis=1)
    valid = sleep_count > 0
    return {
        "evaluable_origins": int(np.sum(valid)),
        "known_sleep_epochs": int(np.sum(sleep_count)),
        "false_positive_wake_epochs": int(np.sum(false_count)),
        "false_positive_wake_minutes_sum": float(np.sum(false_count) * epoch_minutes),
        "false_positive_wake_minutes": float(np.mean(false_count[valid]) * epoch_minutes) if np.any(valid) else None,
        "false_positive_wake_fraction": float(np.mean(false_count[valid] / sleep_count[valid])) if np.any(valid) else None,
    }


def _numeric_array(value: Any, shape: tuple[int, ...], name: str) -> np.ndarray:
    try:
        result = np.asarray(value, dtype=float)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{name} must be a finite numeric array") from error
    if result.shape != shape:
        raise ValueError(f"{name} has shape {result.shape}; expected {shape}")
    if not np.all(np.isfinite(result)):
        raise ValueError(f"{name} must contain only finite values")
    return result


def evaluate_forecasts(
    target: np.ndarray,
    arms: Mapping[str, Mapping[str, Any]],
    participant: Sequence[Any],
    epoch_seconds: float = 30,
    short_max_epochs: int = 2,
) -> dict[str, Any]:
    """Evaluate forecast arms without fitting, calibration, or threshold choice.

    Each arm provides ``total_minutes[N]`` and optionally
    ``probability[N,T]`` and ``path[N,T]``. A supplied path must be binary;
    no threshold or decoder is inferred here. ``hard_map`` names the metrics
    for that supplied hard path, whose actual decoding method belongs in the
    caller's provenance. Supplied total predictions must be finite and are
    neither clipped nor silently replaced with probability/path sums.

    Total-Wake errors require a fully labeled future. Probabilistic scores
    average valid epochs within each origin, origins within each participant,
    then participants equally. ECE uses ten fixed equal-width probability
    bins separately within each origin. All path events are matched within
    their own origin, one to one, first maximizing positive-overlap matches,
    then their summed IoU. Precision covers all complete Wake events; recall
    for short Wake events uses the short subset of those same matches.

    Predicted runs touching the horizon, unknown labels (including adjacent
    bracketing epochs), or a censored true Wake run are unscored as events.
    Such predictions still contribute to false-Wake minutes on known sleep.
    Event ratios pool instances within each participant before macro
    averaging, and pooled instance ratios are also reported explicitly.
    Zero-denominator scores are None. The result is JSON serializable.
    """
    target = np.asarray(target)
    if target.ndim != 2 or target.shape[1] < 1:
        raise ValueError("target must have shape [N,T] with T >= 1")
    target = _numeric_array(target, target.shape, "target")
    if not np.all(np.isin(target, (-1, 0, 1))):
        raise ValueError("target labels must be -1 (unknown), 0 (sleep), or 1 (Wake)")
    if not np.isfinite(epoch_seconds) or epoch_seconds <= 0:
        raise ValueError("epoch_seconds must be positive and finite")
    if isinstance(short_max_epochs, (bool, np.bool_)) or not isinstance(short_max_epochs, (int, np.integer)) or short_max_epochs < 1:
        raise ValueError("short_max_epochs must be a positive integer")
    identifiers = np.asarray(participant)
    if identifiers.ndim != 1 or len(identifiers) != len(target):
        raise ValueError("participant must have shape [N]")
    for identifier in identifiers:
        if identifier is None or (isinstance(identifier, (float, np.floating)) and not np.isfinite(identifier)):
            raise ValueError("participant identifiers must be nonmissing")
        if not str(identifier).strip():
            raise ValueError("participant identifiers must be nonempty")
    identifiers = identifiers.astype(str)
    groups = {name: np.flatnonzero(identifiers == name) for name in dict.fromkeys(identifiers.tolist())}
    epoch_minutes = float(epoch_seconds) / 60.0
    valid = target != -1
    complete = np.all(valid, axis=1)
    has_labels = np.any(valid, axis=1)
    true_minutes = np.sum(target == 1, axis=1) * epoch_minutes
    if not isinstance(arms, Mapping):
        raise ValueError("arms must map arm names to forecast arrays")
    result: dict[str, Any] = {
        "schema_version": 1,
        "label_encoding": {"sleep": 0, "wake": 1, "unknown": -1},
        "epoch_seconds": float(epoch_seconds),
        "horizon_epochs": int(target.shape[1]),
        "short_max_epochs": int(short_max_epochs),
        "short_event_definition": "interior_complete_Wake_run_bounded_by_known_sleep_not_clinical_arousal",
        "event_count_unit": "window_event_instances_not_unique_physical_events",
        "event_matching": "within_origin_one_to_one_maximum_cardinality_then_summed_IoU_positive_epoch_overlap",
        "coverage": {
            "candidate_origins": int(len(target)),
            "candidate_participants": len(groups),
            "complete_future_origins": int(np.sum(complete)),
            "complete_future_participants": sum(bool(np.any(complete[indices])) for indices in groups.values()),
            "origins_with_valid_labels": int(np.sum(has_labels)),
            "participants_with_valid_labels": sum(bool(np.any(has_labels[indices])) for indices in groups.values()),
            "valid_label_epochs": int(np.sum(valid)),
            "unknown_label_epochs": int(np.sum(~valid)),
        },
        "arms": {},
    }
    for arm_name, arm in arms.items():
        if not isinstance(arm_name, str) or not arm_name:
            raise ValueError("arm names must be nonempty strings")
        if not isinstance(arm, Mapping) or "total_minutes" not in arm:
            raise ValueError(f"arm {arm_name!r} must provide total_minutes")
        total = _numeric_array(arm["total_minutes"], (len(target),), f"{arm_name}.total_minutes")
        probability = arm.get("probability")
        if probability is not None:
            probability = _numeric_array(probability, target.shape, f"{arm_name}.probability")
            if not np.all((probability >= 0) & (probability <= 1)):
                raise ValueError(f"{arm_name}.probability must be in [0,1]")
        path = arm.get("path")
        if path is not None:
            path = _numeric_array(path, target.shape, f"{arm_name}.path")
            if not np.all(np.isin(path, (0, 1))):
                raise ValueError(f"{arm_name}.path must contain only 0 and 1")
        probability_rows = _probability_by_origin(target, probability) if probability is not None else None
        event_rows = [_event_counts(y, p, int(short_max_epochs)) for y, p in zip(target, path)] if path is not None else None
        expected_total = np.sum(probability, axis=1) * epoch_minutes if probability is not None else None
        path_total = np.sum(path, axis=1) * epoch_minutes if path is not None else None
        people: dict[str, Any] = {}
        for name, indices in groups.items():
            person: dict[str, Any] = {
                "coverage": {
                    "candidate_origins": int(len(indices)),
                    "complete_future_origins": int(np.sum(complete[indices])),
                    "origins_with_valid_labels": int(np.sum(has_labels[indices])),
                    "valid_label_epochs": int(np.sum(valid[indices])),
                },
                "total_wake": _total_summary(total[indices], true_minutes[indices], complete[indices]),
                "probability": None,
                "hard_map": None,
            }
            if probability_rows is not None:
                person["probability"] = _probability_summary([probability_rows[index] for index in indices])
                person["probability"]["expected_total_wake"] = _total_summary(expected_total[indices], true_minutes[indices], complete[indices])
            if event_rows is not None:
                person["hard_map"] = {
                    "total_wake": _total_summary(path_total[indices], true_minutes[indices], complete[indices]),
                    "false_wake": _false_wake_summary(target[indices], path[indices], epoch_minutes),
                    "events": _event_summary([event_rows[index] for index in indices]),
                }
            people[name] = person
        people_rows = list(people.values())
        arm_result: dict[str, Any] = {
            "total_wake": _aggregate_totals([person["total_wake"] for person in people_rows]),
            "probability": None,
            "hard_map": None,
            "per_participant": people,
        }
        arm_result["total_wake"]["source"] = "supplied_total_minutes"
        if probability_rows is not None:
            summaries = [person["probability"] for person in people_rows]
            arm_result["probability"] = {
                "aggregation": "mean_over_participants_of_mean_over_origins_of_valid_epoch_score",
                "ece_bins": _ECE_BINS,
                "ece_definition": "per_origin_equal_width_probability_bins_then_origin_and_participant_means",
                "nll_probability_clip": _NLL_EPS,
                "evaluable_origins": sum(row["evaluable_origins"] for row in summaries),
                "evaluable_participants": sum(row["evaluable_origins"] > 0 for row in summaries),
                "valid_epochs": sum(row["valid_epochs"] for row in summaries),
                **{name: _mean([row[name] for row in summaries]) for name in ("brier", "nll", "ece")},
                "expected_total_wake": _aggregate_totals([row["expected_total_wake"] for row in summaries]),
            }
            arm_result["probability"]["expected_total_wake"]["source"] = "sum_Wake_probability_times_epoch_minutes"
        if event_rows is not None:
            summaries = [person["hard_map"] for person in people_rows]
            false_rows = [row["false_wake"] for row in summaries]
            events = _event_summary(event_rows)
            for metric in ("short_event_recall", "event_precision", "event_recall"):
                events[metric + "_pooled"] = events.pop(metric)
                events[metric + "_macro"] = _mean([row["events"][metric] for row in summaries])
            events["participants_with_short_events"] = sum(row["events"]["short_event_instances"] > 0 for row in summaries)
            events["participants_with_predicted_events"] = sum(row["events"]["predicted_event_instances"] > 0 for row in summaries)
            events["aggregation"] = "ratio_of_instance_counts_within_participant_then_participant_macro_or_explicit_pooled_ratio"
            events["count_unit"] = "window_event_instances"
            arm_result["hard_map"] = {
                "total_wake": _aggregate_totals([row["total_wake"] for row in summaries]),
                "false_wake": {
                    "aggregation": "mean_over_participants_of_mean_over_origins_with_known_sleep",
                    "evaluable_origins": sum(row["evaluable_origins"] for row in false_rows),
                    "evaluable_participants": sum(row["evaluable_origins"] > 0 for row in false_rows),
                    "known_sleep_epochs": sum(row["known_sleep_epochs"] for row in false_rows),
                    "false_positive_wake_epochs": sum(row["false_positive_wake_epochs"] for row in false_rows),
                    "false_positive_wake_minutes_sum": sum(row["false_positive_wake_minutes_sum"] for row in false_rows),
                    "false_positive_wake_minutes": _mean([row["false_positive_wake_minutes"] for row in false_rows]),
                    "false_positive_wake_fraction": _mean([row["false_positive_wake_fraction"] for row in false_rows]),
                },
                "events": events,
            }
            arm_result["hard_map"]["total_wake"]["source"] = "sum_supplied_binary_path_times_epoch_minutes"
        result["arms"][arm_name] = arm_result
    return result


def paired_delta(
    receipt: Mapping[str, Any],
    arm: str,
    reference: str,
    metric: str = "total_wake.mae_minutes",
    n_resamples: int = 2000,
    seed: int = 0,
) -> dict[str, Any]:
    """Exploratory paired participant delta; a positive value means arm > reference.

    Bootstrap whole participants, never overlapping windows. With fewer than
    five evaluable participants, report the point estimate and individual
    deltas but omit an interval. Even larger samples remain exploratory.
    """
    if isinstance(n_resamples, bool) or not isinstance(n_resamples, (int, np.integer)) or n_resamples < 1:
        raise ValueError("n_resamples must be a positive integer")
    first = receipt["arms"][arm]["per_participant"]
    second = receipt["arms"][reference]["per_participant"]

    def value(row: Mapping[str, Any]) -> float | None:
        current: Any = row
        for key in metric.split("."):
            if current is None:
                return None
            current = current[key]
        if current is None:
            return None
        result = float(current)
        if not np.isfinite(result):
            raise ValueError("paired metric values must be finite or None")
        return result

    deltas = {}
    for name in sorted(set(first) & set(second)):
        current, baseline = value(first[name]), value(second[name])
        if current is not None and baseline is not None:
            deltas[name] = current - baseline
    result: dict[str, Any] = {
        "arm": arm,
        "reference": reference,
        "metric": metric,
        "direction": "arm_minus_reference",
        "participant_count": len(deltas),
        "mean_delta": _mean(list(deltas.values())),
        "per_participant_delta": deltas,
        "bootstrap_unit": "participant",
        "bootstrap_seed": int(seed),
        "bootstrap_resamples": int(n_resamples),
        "percentile_interval_95": None,
        "interpretation": "exploratory_not_confirmatory",
        "interval_status": "insufficient_participants_minimum_5",
    }
    if len(deltas) >= 5:
        values = np.asarray(list(deltas.values()))
        rng = np.random.default_rng(seed)
        bootstrap = rng.choice(values, size=(n_resamples, len(values)), replace=True).mean(axis=1)
        result["percentile_interval_95"] = np.quantile(bootstrap, [0.025, 0.975]).tolist()
        result["interval_status"] = "exploratory_participant_bootstrap"
    return result
