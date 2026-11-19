"""Endpoint validation scoring for training-only transition and prior-mix controls."""

import numpy as np

from .metrics import (
    HORIZON, LEAD_INDICES, STAGES, _decision_scores, _difference, _groups, _mean_score_rows,
    _probability_losses, _support, _target_array, _target_mean, _vector,
)


DIRECT = tuple(f"direct_{seed}" for seed in (0, 1, 2))
METHODS = ("persistence", "prior_mix", "transition", "stage_prior", *DIRECT)
STEPS = tuple(LEAD_INDICES.values())


def _endpoint_probabilities(values, n, arm):
    prob = np.asarray(values)
    if prob.shape == (n, HORIZON, len(STAGES)):
        prob = prob[:, STEPS, :]
    if (prob.shape != (n, len(STEPS), len(STAGES)) or not np.isfinite(prob).all()
            or (prob < 0).any() or (prob > 1).any()
            or not np.allclose(prob.sum(axis=-1), 1.0, atol=1e-6, rtol=1e-6)):
        raise ValueError(f"{arm}: expected normalized endpoint probabilities in shared origin and stage order")
    return prob


def _coverage(target, selected, groups):
    return {
        "origins": int(selected.sum()),
        "participants": sum(bool(selected[indices].any()) for indices in groups),
        "support": _support(target[selected]),
    }


def score_comparison(val, probs):
    """Compare seven forecasts on common origins, then average direct scores over seeds."""
    if set(probs) != set(METHODS):
        raise ValueError(f"expected predictions for {METHODS}")
    target = _target_array(val.stage)[:, STEPS]
    n = len(target)
    person = _vector(val.participant, n, "participant", str)
    night = _vector(val.night, n, "night", str)
    origin = _vector(val.origin_time, n, "origin_time", float)
    if not np.isfinite(origin).all() or len(set(zip(person, night, origin))) != n:
        raise ValueError("origins must have a unique participant, night, and finite cutoff")
    current = _vector(val.current_stage, n, "current_stage")
    if not np.isin(current, (-1, 0, 1, 2, 3)).all():
        raise ValueError("invalid current reference stage")
    groups = _groups(person)
    known = target >= 0
    last = target[:, -1]
    both_known = (current >= 0) & (last >= 0)
    changed = both_known & (current != last)
    unchanged = both_known & (current == last)
    coverage = {}
    for i, minute in enumerate(LEAD_INDICES):
        row = _coverage(target[:, i], known[:, i], groups)
        row["unknown"] = int((~known[:, i]).sum())
        coverage[str(minute)] = row

    subdivision = {
        **_coverage(last, changed, groups),
        "both_known": int(both_known.sum()),
        "unchanged": int(unchanged.sum()),
        "current_unknown_all": int((current < 0).sum()),
        "current_unknown_target_known": int(((current < 0) & (last >= 0)).sum()),
        "target_unknown": int((last < 0).sum()),
    }
    if (subdivision["origins"] + subdivision["unchanged"] != subdivision["both_known"] or
            subdivision["both_known"] + subdivision["current_unknown_target_known"] != coverage["30"]["origins"]):
        raise ValueError("changed-stratum denominators disagree with endpoint coverage")

    methods = {}
    for arm in METHODS:
        probability = _endpoint_probabilities(probs[arm], n, arm)
        nll, _ = _probability_losses(target, probability)
        decisions = probability.argmax(axis=-1)
        leads = {}
        for i, minute in enumerate(LEAD_INDICES):
            row = _decision_scores(target[:, i], decisions[:, i], groups)
            row["nll"] = _target_mean(nll[:, i], known[:, i], groups)
            leads[str(minute)] = row
        methods[arm] = {"leads": leads, "changed_30_nll": _target_mean(nll[:, -1], changed, groups)}
    methods["direct_mean"] = _mean_score_rows([methods[seed] for seed in DIRECT])

    delta = {
        "transition_minus_prior_mix": _difference(methods["transition"]["leads"]["30"]["nll"],
                                                  methods["prior_mix"]["leads"]["30"]["nll"]),
        "transition_minus_stage_prior": _difference(methods["transition"]["leads"]["30"]["nll"],
                                                     methods["stage_prior"]["leads"]["30"]["nll"]),
        "changed_transition_minus_prior_mix": _difference(methods["transition"]["changed_30_nll"],
                                                          methods["prior_mix"]["changed_30_nll"]),
    }
    return {"total_origins": n, "stage_order": list(STAGES), "coverage": coverage,
            "changed_30": subdivision, "methods": methods, "paired_nll_differences": delta,
            "direct_mean": "arithmetic mean of three separately scored direct seeds",
            "aggregation": "equal participants after averaging known-target NLL or normalizing confusion within person"}


def _fmt(value):
    return "NE" if value is None else f"{value:.4f}"


def render_scores(scores):
    """Markdown tables with forecast scores and the common denominators."""
    changed = scores["changed_30"]
    lines = [
        "| Lead (min) | Participants | Known | Unknown | Wake | Light | Deep | REM |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for lead, row in scores["coverage"].items():
        counts = " | ".join(str(row["support"][stage]) for stage in STAGES)
        lines.append(f"| +{lead} | {row['participants']} | {row['origins']} | {row['unknown']} | {counts} |")
    lines.extend(["", "| Method | Lead (min) | NLL ↓ | Macro-F1 ↑ | Wake recall ↑ |",
                  "| --- | ---: | ---: | ---: | ---: |"])
    for name in ("persistence", "prior_mix", "transition", "stage_prior", "direct_mean"):
        for lead, row in scores["methods"][name]["leads"].items():
            lines.append(f"| {name} | +{lead} | {_fmt(row['nll'])} | {_fmt(row['macro_f1'])} | {_fmt(row['wake_recall'])} |")
    counts = ", ".join(f"{changed['support'][k]} {k}" for k in STAGES)
    lines.extend(["", f"At +30 min, {changed['origins']} of {changed['both_known']} origins with both "
                  f"stages known had a different target stage from the current stage "
                  f"({changed['participants']} participants, target support {counts}). "
                  f"{changed['current_unknown_target_known']} additional known +30 min targets had an unknown current stage.",
                  "", "| Method | +30 min changed-stage NLL ↓ |", "| --- | ---: |"])
    for name in ("persistence", "prior_mix", "transition", "stage_prior", "direct_mean"):
        lines.append(f"| {name} | {_fmt(scores['methods'][name]['changed_30_nll'])} |")
    delta = scores["paired_nll_differences"]
    lines.extend(["", "| +30 min NLL difference | All known targets | Changed stages |",
                  "| --- | ---: | ---: |",
                  f"| Transition − prior mix | {_fmt(delta['transition_minus_prior_mix'])} | "
                  f"{_fmt(delta['changed_transition_minus_prior_mix'])} |",
                  f"| Transition − stage prior | {_fmt(delta['transition_minus_stage_prior'])} | — |",
                  "", "Direct scores average the three independently scored seeds. NE means unavailable support."])
    return "\n".join(lines) + "\n"
