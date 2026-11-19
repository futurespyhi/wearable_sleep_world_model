"""Score aligned four-stage forecasts without exposing per-person results."""

from __future__ import annotations

from fractions import Fraction

import numpy as np

from sleep_g3.expanded_analysis import unique_event_scores

STAGES = ("Wake", "Light", "Deep", "REM")
LEAD_INDICES = {5: 9, 15: 29, 30: 59}
HORIZON = 60
EPOCH_SECONDS = 30
NLL_EPS = 1e-12
WAKE_THRESHOLD = 0.5


def _mean(values):
    known = [value for value in values if value is not None]
    return float(np.mean(known)) if known else None


def _target_array(value):
    target = np.asarray(value)
    if target.ndim != 2 or target.shape[1] != HORIZON or not np.isin(target, (-1, 0, 1, 2, 3)).all():
        raise ValueError("stage targets must have shape [N,60] and use -1,0,1,2,3")
    return target.astype(np.intp, copy=False)


def _vector(value, length, name, dtype=None):
    result = np.asarray(value, dtype=dtype)
    if result.shape != (length,):
        raise ValueError(f"{name} must have shape [N]")
    return result


def _groups(participant):
    return [np.flatnonzero(participant == person) for person in np.unique(participant)]


def _support(target):
    return dict(zip(STAGES, np.bincount(target[target >= 0], minlength=len(STAGES)).tolist()))


def _matrix(truth, decision):
    return np.bincount(len(STAGES) * truth + decision, minlength=len(STAGES) ** 2).reshape(4, 4)


def _decision_scores(truth, decision, groups):
    matrices = []
    for indices in groups:
        known = indices[truth[indices] >= 0]
        if len(known):
            matrices.append(_matrix(truth[known], decision[known]))
    if matrices:
        counts = np.asarray(matrices)
        normalized = (counts / counts.sum(axis=(1, 2), keepdims=True)).mean(axis=0)
        pooled = counts.sum(axis=0)
    else:
        normalized = np.zeros((4, 4), dtype=float)
        pooled = np.zeros((4, 4), dtype=int)

    row_sum = normalized.sum(axis=1)
    column_sum = normalized.sum(axis=0)
    f1 = {
        name: float(2 * normalized[i, i] / (row_sum[i] + column_sum[i])) if row_sum[i] else None
        for i, name in enumerate(STAGES)
    }
    n_known = int(pooled.sum())
    return {
        "macro_f1": _mean(f1.values()) if all(value is not None for value in f1.values()) else None,
        "f1": f1,
        "wake_recall": float(normalized[0, 0] / row_sum[0]) if row_sum[0] else None,
        "support": dict(zip(STAGES, pooled.sum(axis=1).tolist())),
        "participants": len(matrices),
        "origins": n_known,
        "unknown": int(len(truth) - n_known),
        "normalized_confusion_matrix": normalized.tolist(),
        "pooled_confusion_matrix": pooled.tolist(),
    }


def _target_mean(values, mask, groups):
    per_person = []
    for indices in groups:
        valid = mask[indices]
        if valid.any():
            per_person.append(float(values[indices][valid].mean()))
    return _mean(per_person)


def _probability_losses(target, probability):
    row, step = np.nonzero(target >= 0)
    label = target[row, step]
    valid_p = probability[row, step].astype(np.float64, copy=False)
    observed = valid_p[np.arange(len(label)), label]
    nll = np.zeros(target.shape)
    brier = np.zeros(target.shape)
    nll[row, step] = -np.log(np.clip(observed, NLL_EPS, 1.0))
    # Equivalent to a sum of squared errors against an unscaled one-hot vector.
    valid_p[np.arange(len(label)), label] -= 1.0
    brier[row, step] = np.square(valid_p).sum(axis=1)
    return nll, brier


def _wake_minutes(predicted, truth, complete, groups):
    error = predicted - truth
    return {
        "mean_expected_minutes": _target_mean(predicted, complete, groups),
        "mean_reference_minutes": _target_mean(truth, complete, groups),
        "mae_minutes": _target_mean(np.abs(error), complete, groups),
        "bias_minutes": _target_mean(error, complete, groups),
        "complete_origins": int(complete.sum()),
        "participants": sum(bool(complete[indices].any()) for indices in groups),
    }


def _training_wake_median(training_target, training_participant):
    complete = (training_target >= 0).all(axis=1)
    if not complete.any():
        return None, "no_complete_training_horizons"
    counts = (training_target == 0).sum(axis=1)
    if training_participant is None:
        return float(np.median(counts[complete]) * EPOCH_SECONDS / 60), "pooled_training_median"

    # Match the historical G3 lower median with exact equal participant weights.
    people = _vector(training_participant, len(counts), "training_participant", str)
    mass = {}
    evaluable_people = 0
    for indices in _groups(people):
        own = counts[indices][complete[indices]]
        if len(own):
            evaluable_people += 1
            values, frequencies = np.unique(own, return_counts=True)
            for value, frequency in zip(values, frequencies):
                mass[value] = mass.get(value, Fraction(0)) + Fraction(int(frequency), len(own))
    cumulative = Fraction(0)
    for count, weight in sorted(mass.items()):
        cumulative += weight
        if cumulative >= Fraction(evaluable_people, 2):
            return float(count * EPOCH_SECONDS / 60), "participant_balanced_lower_weighted_median"
    raise RuntimeError("positive training median mass was expected")


def _short_events(target, decision, participant, night, origin_time):
    raw = unique_event_scores(
        target, {"wake": {"path": decision}}, participant, night, origin_time,
        epoch_seconds=EPOCH_SECONDS, short_max_epochs=2,
    )["arms"]["wake"]
    all_events = raw["events"]
    result = {}
    for duration, name in ((None, "all_short"), (1, "1_epoch"), (2, "2_epoch")):
        events = [event for event in all_events if duration is None or event["duration_epochs"] == duration]
        unique = len(events)
        event_origins = sum(event["evaluable_origins"] for event in events)
        hits = sum(event["hit_origins"] for event in events)
        events_with_hits = sum(event["hit_origins"] > 0 for event in events)
        result[name] = {
            "unique_reference_events": unique,
            "participants": raw["strata"][name]["participants"],
            "evaluable_event_origin_instances": event_origins,
            "hit_event_origin_instances": hits,
            "unique_events_with_a_hit": events_with_hits,
            "unique_event_recall_any_origin": events_with_hits / unique if unique else None,
            "participant_macro_event_origin_hit_rate": raw["strata"][name][
                "event_then_participant_macro_origin_hit_rate"
            ],
            "events_with_multiple_evaluable_origins": sum(event["evaluable_origins"] > 1 for event in events),
            "max_origins_per_event": max((event["evaluable_origins"] for event in events), default=0),
            "mean_origins_per_event": event_origins / unique if unique else None,
        }
    return result


def _hr_scores(target, prediction, mask, groups):
    prediction = np.asarray(prediction, dtype=float)
    if prediction.shape != target.shape:
        raise ValueError("future HR predictions must have shape [N,60]")
    if not np.isfinite(prediction[mask]).all():
        raise ValueError("HR predictions must be finite wherever HR targets are scored")
    count = int(mask.sum())
    error = np.abs(prediction - target)
    return {
        "mae_bpm": _target_mean(error, mask, groups),
        "pooled_mae_bpm": float(error[mask].mean()) if count else None,
        "target_epochs": count,
        "origins": int(mask.any(axis=1).sum()),
        "participants": sum(bool(mask[indices].any()) for indices in groups),
    }


def _difference(first, second):
    return first - second if first is not None and second is not None else None


def _pair_differences(methods, contrasts):
    paired = {}
    for arm, reference in contrasts:
        explicit, other = methods[arm], methods[reference]
        paired[f"{arm}_minus_{reference}"] = {
            "arm": arm,
            "reference": reference,
            "nll": _difference(explicit["nll"], other["nll"]),
            "brier": _difference(explicit["brier"], other["brier"]),
            "leads": {
                minute: {metric: _difference(row[metric], other["leads"][minute][metric])
                         for metric in ("macro_f1", "wake_recall", "nll", "brier")}
                for minute, row in explicit["leads"].items()
            },
        }
    return paired


def score_seed(target, participant, night, origin_time, probabilities, *,
               training_target, training_participant=None, future_hr=None,
               future_hr_mask=None, hr_predictions=None, last_hr=None, contrasts=None):
    """Score all methods on shared origins and return JSON-ready aggregates.

    Predictions contain one probability per stage at every future step. All
    HR inputs to this function are in bpm. Stage decisions use argmax. Wake
    events use a separate 0.5 probability threshold and existing G3 matching.
    """
    target = _target_array(target)
    training_target = _target_array(training_target)
    n_origins = len(target)
    participant = _vector(participant, n_origins, "participant", str)
    night = _vector(night, n_origins, "night", str)
    origin_time = _vector(origin_time, n_origins, "origin_time", float)
    if not np.isfinite(origin_time).all():
        raise ValueError("forecast cutoff times must be finite")
    if len(set(zip(participant, night, origin_time))) != n_origins:
        raise ValueError("forecast origins must be unique by participant, night, and cutoff")
    groups = _groups(participant)
    known = target >= 0
    complete = known.all(axis=1)
    true_wake = (target == 0).sum(axis=1) * EPOCH_SECONDS / 60
    event_target = np.where(known, target == 0, -1).astype(np.int8)

    result = {
        "stage_order": list(STAGES),
        "lead_indices_zero_based": {str(key): value for key, value in LEAD_INDICES.items()},
        "aggregation": {
            "confusion": "unit total mass per participant on valid origins, then equal participant mean",
            "nll_and_brier": "mean known target scores within participant, then equal participant mean",
            "nll_probability_floor": NLL_EPS,
            "brier": "sum of squared probability errors over four classes",
            "wake_minutes": "mean over complete horizons within participant, then equal participant mean",
            "short_wake_threshold": WAKE_THRESHOLD,
            "short_wake_deduplication": "participant, night, and absolute reference start and end times",
        },
        "coverage": {
            "participants": len(groups),
            "nights": len(set(zip(participant, night))),
            "origins": n_origins,
            "complete_horizons": int(complete.sum()),
            "complete_horizons_zero_wake": int((complete & (true_wake == 0)).sum()),
            "valid_stage_targets": int(known.sum()),
            "unknown_stage_targets": int((~known).sum()),
            "stage_support": _support(target),
        },
        "methods": {},
        "wake_minute_controls": {},
        "hr_last_observation": None,
        "paired_differences": {},
    }

    hr_predictions = hr_predictions or {}
    if set(hr_predictions) - set(probabilities):
        raise ValueError("HR forecasts must identify a stage forecast method")
    if future_hr is None:
        if future_hr_mask is not None or hr_predictions or last_hr is not None:
            raise ValueError("HR targets are required for HR scoring")
    else:
        future_hr = np.asarray(future_hr, dtype=float)
        hr_mask = np.isfinite(future_hr) if future_hr_mask is None else np.asarray(future_hr_mask, dtype=bool)
        if future_hr.shape != target.shape or hr_mask.shape != target.shape:
            raise ValueError("HR targets and mask must have shape [N,60]")
        if not np.isfinite(future_hr[hr_mask]).all():
            raise ValueError("unmasked HR targets must be finite")
        if last_hr is not None:
            last_hr = _vector(last_hr, n_origins, "last_hr", float)
            hr_available = hr_mask & np.isfinite(last_hr[:, None])
            result["hr_last_observation"] = _hr_scores(
                future_hr, np.broadcast_to(last_hr[:, None], target.shape), hr_available, groups,
            )

    for name, value in probabilities.items():
        probability = np.asarray(value)
        if (probability.shape != (*target.shape, len(STAGES))
                or not np.isfinite(probability).all()
                or (probability < 0).any() or (probability > 1).any()
                or not np.allclose(probability.sum(axis=2), 1.0, rtol=1e-6, atol=1e-6)):
            raise ValueError(f"{name}: probabilities must have shape [N,60,4] and sum to one")
        decision = probability.argmax(axis=2)
        nll, brier = _probability_losses(target, probability)
        lead_rows = {}
        for minute, index in LEAD_INDICES.items():
            lead = _decision_scores(target[:, index], decision[:, index], groups)
            lead["nll"] = _target_mean(nll[:, index], known[:, index], groups)
            lead["brier"] = _target_mean(brier[:, index], known[:, index], groups)
            lead_rows[str(minute)] = lead
        wake_probability = probability[:, :, 0]
        predicted_wake = wake_probability.sum(axis=1, dtype=float) * EPOCH_SECONDS / 60
        result["methods"][name] = {
            "leads": lead_rows,
            "nll": _target_mean(nll, known, groups),
            "brier": _target_mean(brier, known, groups),
            "hr": _hr_scores(future_hr, hr_predictions[name], hr_mask, groups) if name in hr_predictions else None,
            "wake_minutes": _wake_minutes(predicted_wake, true_wake, complete, groups),
            "short_wake_events": _short_events(
                event_target, wake_probability >= WAKE_THRESHOLD, participant, night, origin_time,
            ),
        }

    median, median_fit = _training_wake_median(training_target, training_participant)
    for name, constant, fit in (("training_median", median, median_fit), ("zero_wake", 0.0, "fixed_zero")):
        values = None if constant is None else np.full(n_origins, constant)
        result["wake_minute_controls"][name] = {
            "constant_minutes": constant,
            "fit": fit,
            "score": _wake_minutes(values, true_wake, complete, groups) if values is not None else None,
        }
    result["paired_differences"] = _pair_differences(result["methods"], contrasts or ())
    return result


def _mean_score_rows(rows):
    """Average numeric leaves of equal-schema score rows over available seeds."""
    first = next((row for row in rows if row is not None), None)
    if isinstance(first, dict):
        return {key: _mean_score_rows([row[key] if row is not None else None for row in rows]) for key in first}
    if isinstance(first, list):
        return [_mean_score_rows([row[i] if row is not None else None for row in rows]) for i in range(len(first))]
    if isinstance(first, (int, float)):
        return _mean(rows)
    return first


def _seed_delta_summary(values):
    measured = [value for value in values.values() if value is not None]
    return {
        "mean_delta": _mean(measured),
        "seeds_evaluated": len(measured),
        "positive_seeds": sum(value > 0 for value in measured),
        "zero_seeds": sum(value == 0 for value in measured),
        "negative_seeds": sum(value < 0 for value in measured),
        "delta_by_seed": values,
    }


def summarize_seeds(scores):
    """Average already scored runs and record the direction of paired deltas."""
    if not scores:
        raise ValueError("at least one seed score is required")
    seeds = sorted(scores)
    first = scores[seeds[0]]
    for seed in seeds[1:]:
        other = scores[seed]
        if (first["coverage"] != other["coverage"]
                or first["methods"].keys() != other["methods"].keys()
                or first["paired_differences"].keys() != other["paired_differences"].keys()):
            raise ValueError("seed score coverage, methods, and contrasts must agree")
    differences = {}
    for key, pair in first["paired_differences"].items():
        rows = {str(seed): scores[seed]["paired_differences"][key] for seed in seeds}
        differences[key] = {
            "arm": pair["arm"],
            "reference": pair["reference"],
            **{metric: _seed_delta_summary({seed: row[metric] for seed, row in rows.items()})
               for metric in ("nll", "brier")},
            "leads": {
                lead: {
                    metric: _seed_delta_summary({seed: row["leads"][lead][metric] for seed, row in rows.items()})
                    for metric in lead_row
                }
                for lead, lead_row in pair["leads"].items()
            },
        }
    return {
        "seeds": seeds,
        "coverage": first["coverage"],
        "aggregation": "unweighted arithmetic mean over seed-specific validation scores",
        "methods": _mean_score_rows([scores[seed]["methods"] for seed in seeds]),
        "hr_last_observation": first["hr_last_observation"],
        "wake_minute_controls": first["wake_minute_controls"],
        "paired_differences": differences,
    }
