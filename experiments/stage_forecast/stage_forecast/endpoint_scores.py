"""Evaluate paired binary forecasts, giving each eligible validation participant equal weight."""

import numpy as np

from .metrics import NLL_EPS, _difference, _mean, _vector
from .reporting import _fmt, _table

ARMS = ("A", "B", "C")
METRICS = ("nll", "brier")
CONTRASTS = (("C", "A"), ("C", "B"), ("B", "A"))


def _contrasts(methods):
    return {
        f"{arm}_minus_{reference}": {
            metric: _difference(methods[arm][metric], methods[reference][metric]) for metric in METRICS
        } for arm, reference in CONTRASTS
    }


def _aggregate(person_rows):
    rows = list(person_rows)
    methods = {
        arm: {metric: _mean([row["methods"][arm][metric] for row in rows]) for metric in METRICS}
        for arm in ARMS
    }
    return {
        "participants": len(rows), "origins": sum(row["origins"] for row in rows),
        "positive": sum(row["positive"] for row in rows), "negative": sum(row["negative"] for row in rows),
        "methods": methods, "paired_differences": _contrasts(methods),
    }


def _strict_gain(row):
    if not row["participants"]:
        return None
    pairs = row["paired_differences"]
    return all(pairs[key][metric] < 0 for key in ("C_minus_A", "C_minus_B") for metric in METRICS)


def score_endpoint(target, participant, probabilities):
    """Score binary targets and positive-class probabilities at jointly eligible origins."""
    target = np.asarray(target)
    if target.ndim != 1 or not np.isin(target, (0, 1)).all():
        raise ValueError("endpoint scores require a 1D vector of known binary targets")
    target = target.astype(np.int8, copy=False)
    people = _vector(participant, len(target), "participant", str)
    if set(probabilities) != set(ARMS):
        raise ValueError("expected forecasts from the three arms A, B and C")
    losses = {}
    for arm in ARMS:
        p = _vector(probabilities[arm], len(target), arm, float)
        if not np.isfinite(p).all() or (p < 0).any() or (p > 1).any():
            raise ValueError(f"{arm} probabilities must be finite and in [0, 1]")
        observed = np.where(target == 1, p, 1 - p)
        losses[arm] = {"nll": -np.log(np.clip(observed, NLL_EPS, 1)), "brier": np.square(p - target)}

    individual = {}
    for person in np.unique(people):
        own = people == person
        methods = {arm: {metric: float(value[own].mean()) for metric, value in arm_losses.items()}
                   for arm, arm_losses in losses.items()}
        positive = int(target[own].sum())
        individual[str(person)] = {
            "participants": 1, "origins": int(own.sum()), "positive": positive,
            "negative": int(own.sum()) - positive, "methods": methods, "paired_differences": _contrasts(methods),
        }
    overall = _aggregate(individual.values())
    omitted = {
        person: _aggregate(row for name, row in individual.items() if name != person) for person in individual
    }
    overall_gain = _strict_gain(overall)
    omission_gain = {person: _strict_gain(row) for person, row in omitted.items()}
    stable = None if len(individual) < 2 else overall_gain and all(omission_gain.values())
    return {
        "aggregation": "mean binary loss over each participant's eligible origins, then equal participant mean",
        "nll_probability_floor": NLL_EPS, "brier_definition": "mean squared error of P(y=1)",
        "overall": overall, "per_participant": individual, "leave_one_out": omitted,
        "decision": {"stable_gain": stable, "overall_gain": overall_gain, "gain_by_omitted_person": omission_gain,
                     "criterion": "C strictly beats A and B on both NLL and Brier, overall and after each omission"},
    }


def render_endpoint(scores):
    row = scores["overall"]
    decision = scores["decision"]
    outcome = {True: "passed", False: "failed", None: "could not be evaluated"}[decision["stable_gain"]]
    metric_cols = [metric.upper() if metric == "nll" else "Brier" for metric in METRICS]
    pair_cols = [f"{arm} − {ref} {metric}" for arm, ref in CONTRASTS for metric in metric_cols]

    def paired_values(row):
        return [_fmt(row["paired_differences"][f"{arm}_minus_{ref}"][metric], True)
                for arm, ref in CONTRASTS for metric in METRICS]

    lines = [
        f"The prespecified stability criterion **{outcome}**. The comparison covered {row['origins']} origins "
        f"from {row['participants']} participants, with {row['positive']} positives and {row['negative']} negatives. "
        "Each participant contributes equally. Lower NLL and Brier are better.", "",
        _table(["Arm", *metric_cols], [[arm, *(_fmt(row["methods"][arm][m]) for m in METRICS)] for arm in ARMS]), "",
        _table(["Validation cohort", *pair_cols], [["All eligible participants", *paired_values(row)]]), "",
        "## Participant scores and paired differences", "",
        _table(["Participant", "Origins", "Positive", "Negative", *(f"{a} {m}" for a in ARMS for m in metric_cols)],
               [[person, item["origins"], item["positive"], item["negative"],
                 *(_fmt(item["methods"][a][m]) for a in ARMS for m in METRICS)]
                for person, item in scores["per_participant"].items()]), "",
        _table(["Participant", *pair_cols],
               [[person, *paired_values(item)] for person, item in scores["per_participant"].items()]), "",
        "## Omit one validation participant", "",
        "Each row reaggregates the original predictions after removing that participant. "
        "Passing requires all four C-versus-A and C-versus-B differences to be strictly negative.", "",
        _table(["Omitted", "Remaining people", "Origins", "Positive", "Negative", *pair_cols, "Pass"],
               [[person, item["participants"], item["origins"], item["positive"], item["negative"], *paired_values(item),
                 {True: "yes", False: "no", None: "NE"}[decision["gain_by_omitted_person"][person]]]
                for person, item in scores["leave_one_out"].items()]), "",
    ]
    return "\n".join(lines)
