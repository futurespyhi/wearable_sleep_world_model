"""Diagnose frozen horizon transitions with a known current reference stage."""

import numpy as np

from .metrics import (
    HORIZON, LEAD_INDICES, NLL_EPS, STAGES, _decision_scores, _difference, _groups,
    _mean, _support, _target_array, _target_mean, _vector,
)

CONTROLS = ("transition", "prior_mix", "stage_prior")


def _probabilities(value, shape, name):
    array = np.asarray(value)
    if (array.shape != shape or not np.isfinite(array).all() or (array < 0).any()
            or (array > 1).any() or not np.allclose(array.sum(axis=-1), 1, atol=1e-6, rtol=1e-6)):
        raise ValueError(f"{name} requires normalized probabilities of shape {shape}")
    return array


def _nll(valid, truth, probability):
    rows = np.flatnonzero(valid)
    losses = np.zeros(len(valid))
    assigned = probability[rows, truth[rows]].astype(np.float64, copy=False)
    losses[rows] = -np.log(np.clip(assigned, NLL_EPS, 1.))
    return losses


def _stratum(target, selected, losses, groups):
    nll = {name: _target_mean(values, selected, groups) for name, values in losses.items()}
    return {
        "origins": int(selected.sum()),
        "participants": sum(bool(selected[indices].any()) for indices in groups),
        "support": _support(target[selected]),
        "nll": nll,
        "oracle_minus": {control: _difference(nll["oracle"], nll[control]) for control in CONTROLS},
    }


def score_oracle(val, p_t, matrices, controls):
    """Evaluate each method on shared rows where both reference stages are known.

    Controls and the current posterior come from the frozen, sensor-only run.
    Only the diagnostic oracle indexes the transition matrix by the observed
    current stage. Same and changed refer to the two endpoint stages.
    """
    future = _target_array(val.stage)
    n = len(future)
    person = _vector(val.participant, n, "participant", str)
    night = _vector(val.night, n, "night", str)
    origin = _vector(val.origin_time, n, "origin_time", float)
    if not np.isfinite(origin).all() or len(set(zip(person, night, origin))) != n:
        raise ValueError("origins must be unique by participant, night and finite cutoff")
    current = _vector(val.current_stage, n, "current_stage")
    if not np.isin(current, (-1, 0, 1, 2, 3)).all():
        raise ValueError("invalid current stage")
    current = current.astype(np.intp, copy=False)
    width = len(STAGES)
    posterior = _probabilities(p_t, (n, width), "p_t")
    matrices = _probabilities(matrices, (HORIZON, width, width), "transition matrices")
    if set(controls) != set(CONTROLS):
        raise ValueError(f"expected frozen forecasts for {CONTROLS}")
    controls = {name: _probabilities(controls[name], (n, HORIZON, width), name) for name in CONTROLS}
    groups = _groups(person)
    current_known = current >= 0
    current_score = _decision_scores(current, posterior.argmax(axis=-1), groups)
    current_score["nll"] = _target_mean(_nll(current_known, current, posterior), current_known, groups)
    result = {
        "total_origins": n, "stage_order": list(STAGES), "nll_probability_floor": NLL_EPS,
        "current_stage": current_score, "leads": {}, "common_masks": {},
        "participants_30": {}, "paired_mean_check_30": {},
    }
    for minute, index in LEAD_INDICES.items():
        truth = future[:, index]
        target_known = truth >= 0
        both = current_known & target_known
        result["common_masks"][str(minute)] = {
            "both_known": int(both.sum()),
            "current_unknown_target_known": int((~current_known & target_known).sum()),
            "current_known_target_unknown": int((current_known & ~target_known).sum()),
            "both_unknown": int((~current_known & ~target_known).sum()),
        }
        selections = {"overall": both, "same": both & (current == truth), "changed": both & (current != truth)}
        oracle = np.zeros((n, width))
        oracle[current_known] = matrices[index, current[current_known]]
        losses = {"oracle": _nll(both, truth, oracle)}
        losses.update({name: _nll(both, truth, values[:, index]) for name, values in controls.items()})
        result["leads"][str(minute)] = {
            stratum: _stratum(truth, mask, losses, groups) for stratum, mask in selections.items()
        }
        if minute == 30:
            for indices in groups:
                own = {name: values[indices] for name, values in losses.items()}
                result["participants_30"][str(person[indices[0]])] = {
                    stratum: _stratum(truth[indices], mask[indices], own, [np.arange(len(indices))])
                    for stratum, mask in selections.items()
                }

    for stratum, aggregate in result["leads"]["30"].items():
        people = [row[stratum] for row in result["participants_30"].values()]
        if sum(row["origins"] for row in people) != aggregate["origins"]:
            raise ValueError("participant origin counts disagree with common +30 min support")
        checked = {}
        for control, delta in aggregate["oracle_minus"].items():
            paired_mean = _mean([row["oracle_minus"][control] for row in people])
            if (paired_mean is None) != (delta is None) or (
                delta is not None and not np.isclose(paired_mean, delta, atol=1e-12, rtol=1e-12)
            ):
                raise ValueError(f"paired mean disagrees for {stratum} oracle minus {control}")
            checked[control] = paired_mean
        result["paired_mean_check_30"][stratum] = checked
    return result
