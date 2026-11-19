"""Compare recording-time forecasts and frozen controls on the oracle study's common origins."""

import numpy as np

from .metrics import (
    HORIZON, LEAD_INDICES, NLL_EPS, STAGES, _difference, _groups, _mean, _support,
    _target_array, _target_mean, _vector,
)
from .oracle_scores import _nll, _probabilities
from .reporting import _fmt, _table

METHODS = ("stage_prior", "prior_mix", "transition", "oracle", "time_only", "time_transition", "time_oracle")
FROZEN = {"time_only": "stage_prior", "time_transition": "transition", "time_oracle": "oracle"}


def _score_row(target, valid, losses, groups):
    nll = {method: _target_mean(loss, valid, groups) for method, loss in losses.items()}
    return {
        "origins": int(valid.sum()),
        "participants": sum(bool(valid[group].any()) for group in groups),
        "support": _support(target[valid]),
        "nll": nll,
        "minus_time_only": {arm: _difference(nll[arm], nll["time_only"]) for arm in METHODS},
        "minus_frozen": {arm: _difference(nll[arm], nll[baseline]) for arm, baseline in FROZEN.items()},
    }


def _verify_paired_deltas(aggregate, individuals):
    """The equal-person difference must also be the mean of matched person differences."""
    for field in ("minus_time_only", "minus_frozen"):
        for arm, delta in aggregate[field].items():
            observed = _mean([row[field][arm] for row in individuals])
            if (delta is None) != (observed is None) or (
                delta is not None and not np.isclose(observed, delta, rtol=1e-12, atol=1e-12)
            ):
                raise ValueError(f"participant deltas do not reproduce {arm} {field}")


def score_time(val, probs):
    future = _target_array(val.stage)
    n = len(future)
    person = _vector(val.participant, n, "participant", str)
    night = _vector(val.night, n, "night", str)
    origin = _vector(val.origin_time, n, "origin_time", float)
    if not np.isfinite(origin).all() or len(set(zip(person, night, origin))) != n:
        raise ValueError("origins must be unique by participant, night and finite cutoff")
    current = _vector(val.current_stage, n, "current_stage")
    if not np.isin(current, (-1, 0, 1, 2, 3)).all():
        raise ValueError("invalid current reference stage")
    current_known = current >= 0
    if set(probs) != set(METHODS):
        raise ValueError(f"expected forecasts for all methods {METHODS}")
    forecasts = {}
    for name in METHODS:
        arr = np.asarray(probs[name])
        if arr.shape != (n, HORIZON, len(STAGES)):
            raise ValueError(f"{name} predictions have incorrect shape")
        # A diagnostic oracle is undefined before selecting its current-stage row.
        valid_rows = arr[current_known] if name in ("oracle", "time_oracle") else arr
        _probabilities(valid_rows, valid_rows.shape, name)
        forecasts[name] = arr
    groups = _groups(person)
    individuals = {str(person[group[0]]): {} for group in groups}
    result = {
        "total_origins": n, "stage_order": list(STAGES), "nll_probability_floor": NLL_EPS,
        "matched_frozen": FROZEN.copy(), "common_masks": {}, "leads": {}, "per_participant": individuals,
    }
    for minute, index in LEAD_INDICES.items():
        lead = str(minute)
        target = future[:, index]
        target_known = target >= 0
        both = current_known & target_known
        result["common_masks"][lead] = {
            "both_known": int(both.sum()), "both_unknown": int((~current_known & ~target_known).sum()),
            "current_unknown_target_known": int((~current_known & target_known).sum()),
            "current_known_target_unknown": int((current_known & ~target_known).sum()),
        }
        subset = {"overall": both, "same": both & (current == target), "changed": both & (current != target)}
        losses = {name: _nll(both, target, values[:, index]) for name, values in forecasts.items()}
        for group in groups:
            own = {name: loss[group] for name, loss in losses.items()}
            individuals[str(person[group[0]])][lead] = {
                key: _score_row(target[group], valid[group], own, [np.arange(len(group))])
                for key, valid in subset.items()
            }
        result["leads"][lead] = {}
        for key, valid in subset.items():
            aggregate = _score_row(target, valid, losses, groups)
            _verify_paired_deltas(aggregate, [row[lead][key] for row in individuals.values()])
            result["leads"][lead][key] = aggregate
    return result


def render_time(scores):
    """Render compact whole-cohort scores, matched comparisons and per-person differences."""
    alternatives = [m for m in METHODS if m != "time_only"]
    group_rows, nll_rows, primary_rows, matched_rows = [], [], [], []
    for minute, lead in scores["leads"].items():
        for stratum, row in lead.items():
            key = [f"+{minute}", stratum]
            group_rows.append([*key, row["participants"], row["origins"], *(row["support"][s] for s in STAGES)])
            nll_rows.append([*key, *(_fmt(row["nll"][m]) for m in METHODS)])
            primary_rows.append([*key, *(_fmt(row["minus_time_only"][m], True) for m in alternatives)])
            matched_rows.append([*key, *(_fmt(row["minus_frozen"][m], True) for m in FROZEN)])
    person_rows = [
        [name, f"+{minute}", stratum, row["origins"], _fmt(row["nll"]["time_only"]),
         *(_fmt(row["minus_time_only"][m], True) for m in alternatives)]
        for name, leads in scores["per_participant"].items() for minute, lead in leads.items()
        for stratum, row in lead.items()
    ]
    return "\n".join([
        "## Validation coverage", "",
        "All seven forecasts use the same origins with known current and target stages. "
        "Same and changed describe the two endpoints. Class counts refer to the future label.", "",
        _table(["Lead (min)", "Stratum", "People", "Origins", *STAGES], group_rows), "",
        "## Participant-balanced NLL", "",
        _table(["Lead (min)", "Stratum", *METHODS], nll_rows), "",
        "Each difference below subtracts the time_only NLL. Negative values favor the named method.", "",
        _table(["Lead (min)", "Stratum", *alternatives], primary_rows), "",
        "The following paired differences subtract each previously frozen method from its recording-time counterpart. "
        "A negative value favors the recording-time method.", "",
        _table(["Lead (min)", "Stratum", *(f"{m} − {baseline}" for m, baseline in FROZEN.items())], matched_rows), "",
        "## Participant differences relative to time_only", "",
        "Each row gives the baseline NLL followed by method minus baseline NLL on the same origins. "
        "NE denotes empty support. The JSON also contains each person's method scores and matched frozen comparisons.", "",
        _table(["Participant", "Lead (min)", "Stratum", "Origins", "time_only NLL", *alternatives], person_rows), "",
    ])
