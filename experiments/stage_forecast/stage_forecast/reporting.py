"""Pre-specified expanded comparisons from the fitted models' shared validation predictions."""

import hashlib
import json
from pathlib import Path

import numpy as np

from sleep_g3.protocol import write_json
from .data import HISTORY_EPOCHS
from .metrics import (
    LEAD_INDICES, STAGES, _decision_scores, _difference, _groups, _probability_losses,
    _seed_delta_summary, _target_mean,
)


METHODS = ("stage_prior", "persistence", "direct", "hr_only", "fusion", "explicit")
EXPANDED_CONTRASTS = (
    ("explicit", "fusion"), ("explicit", "direct"), ("fusion", "hr_only"), ("fusion", "direct"),
    *((name, "persistence") for name in METHODS if name != "persistence"),
)


def _excluded_histories(keys, audit):
    """Join audited retained cutoffs by participant, night and integer cutoff epoch."""
    coverage = {(str(n["participant"]), str(n["night"])): n["mask_coverage"]
                for n in audit["nights"] if n["partition"] == "validation" and "mask_coverage" in n}
    excluded = {(p, n, int(o)) for (p, n), row in coverage.items() for o in row["retained_origins"]}
    if not excluded.issubset(keys):
        raise ValueError("audited masked-history validation origins missing from predictions")
    by_epoch = {(p, n, o) for p, n, o in keys
                if (p, n) in coverage and any(o - HISTORY_EPOCHS <= e < o for e in coverage[p, n]["epochs"])}
    if by_epoch != excluded:
        raise ValueError("audited mask-affected origins disagree with actual prediction histories")
    return np.array([key in excluded for key in keys], dtype=bool)


def _probabilistic_summary(truth, classes, nll, brier):
    """One person's endpoint decisions and probability losses on their valid targets."""
    group = [np.arange(len(truth))]
    valid = truth >= 0
    leads = {}
    for minute, step in LEAD_INDICES.items():
        row = _decision_scores(truth[:, step], classes[:, step], group)
        row.update(nll=_target_mean(nll[:, step], valid[:, step], group),
                   brier=_target_mean(brier[:, step], valid[:, step], group))
        leads[str(minute)] = row
    return {"leads": leads, "nll": _target_mean(nll, valid, group), "brier": _target_mean(brier, valid, group)}


def score_expanded_seed(val, probabilities, *, audit, participant_output):
    keys = [(str(p), str(n), int(o)) for p, n, o in zip(val.participant, val.night, val.origin)]
    if len(set(keys)) != len(val.stage) or set(probabilities) != set(METHODS):
        raise ValueError("expanded scoring requires all six methods on unique, shared origins")
    excluded = _excluded_histories(keys, audit)
    remaining_people = _groups(val.participant[~excluded])
    step = LEAD_INDICES[30]
    truth = val.stage[~excluded, step]
    restricted = {arm: _decision_scores(truth, probabilities[arm][~excluded, step].argmax(axis=-1), remaining_people)
                  for arm in ("explicit", "fusion")}

    # These participant-level aggregates stay beside predictions on HPG. The
    # public score JSON contains only whole-cohort results and coverage.
    individuals = {str(person): {} for person in np.unique(val.participant)}
    for arm, probability in probabilities.items():
        decisions = np.argmax(probability, axis=-1)
        nll, brier = _probability_losses(val.stage, probability)
        for person, methods in individuals.items():
            idx = val.participant == person
            methods[arm] = _probabilistic_summary(val.stage[idx], decisions[idx], nll[idx], brier[idx])
    write_json(participant_output, individuals)
    return {
        "cache_identity_sha256": audit["cache_identity_sha256"],
        "ordered_validation_keys_sha256": hashlib.sha256(json.dumps(keys, separators=(",", ":")).encode()).hexdigest(),
        "ordered_stage_targets_sha256": hashlib.sha256(np.ascontiguousarray(val.stage, dtype="i1").tobytes()).hexdigest(),
        "excluded_histories": int(excluded.sum()),
        "remaining_origins": int((~excluded).sum()),
        "restricted_at_30": restricted,
        "restricted_primary_delta": _difference(restricted["explicit"]["macro_f1"], restricted["fusion"]["macro_f1"]),
    }


def _with_range(summary):
    measured = [v for v in summary["delta_by_seed"].values() if v is not None]
    return {**summary, "min_delta": min(measured, default=None), "max_delta": max(measured, default=None)}


def expanded_summary(scores, aggregate):
    seeds = sorted(scores)
    details = scores[seeds[0]]["expanded"]
    fields = ("cache_identity_sha256", "ordered_validation_keys_sha256", "ordered_stage_targets_sha256",
              "excluded_histories", "remaining_origins")
    coverage = {key: details[key] for key in fields}
    if any(scores[s]["expanded"][key] != value for s in seeds for key, value in coverage.items()):
        raise ValueError("participant/night/origin identity, targets, cache or sensitivity population changed across seeds")
    pair = aggregate["paired_differences"]["explicit_minus_fusion"]
    primary = _with_range(pair["leads"]["30"]["macro_f1"])
    nll = pair["nll"]
    wake = pair["leads"]["30"]["wake_recall"]
    complete = seeds == [0, 1, 2]
    gates = {
        "positive_primary_every_seed": primary["positive_seeds"] == 3 if complete and primary["seeds_evaluated"] == 3 else None,
        "mean_full_nll_no_higher": nll["mean_delta"] <= 0 if complete and nll["seeds_evaluated"] == 3 else None,
        "mean_30_min_wake_recall_no_lower": wake["mean_delta"] >= 0 if complete and wake["seeds_evaluated"] == 3 else None,
    }
    eligible = None if None in gates.values() else all(gates.values())
    sensitivity = _with_range(_seed_delta_summary({str(s): scores[s]["expanded"]["restricted_primary_delta"] for s in seeds}))
    return {
        **coverage, "primary": primary,
        "mean_full_nll_delta": nll["mean_delta"], "mean_30_min_wake_recall_delta": wake["mean_delta"],
        "gate_components": gates, "advance_explicit": eligible,
        "restricted_primary": sensitivity,
        "restricted_30_min_support": details["restricted_at_30"]["explicit"]["support"],
        "restricted_30_min_evaluable_participants": details["restricted_at_30"]["explicit"]["participants"],
        "restricted_30_min_known": details["restricted_at_30"]["explicit"]["origins"],
        "restricted_30_min_unknown": details["restricted_at_30"]["explicit"]["unknown"],
    }


def _fmt(value, signed=False):
    if value is None:
        return "NE"
    return f"{value:+.4f}" if signed else f"{value:.4f}"


def _table(headers, rows):
    return "\n".join("| " + " | ".join(map(str, row)) + " |" for row in (headers, ["---"] * len(headers), *rows))


def _report(scores, aggregate, expanded):
    methods = aggregate["methods"]
    primary = expanded["primary"]
    restricted = expanded["restricted_primary"]
    seeds = sorted(scores)
    decision = {True: "Advance the explicit wrist input", False: "Do not advance the explicit wrist input",
                None: "The decision on the explicit wrist input is undetermined"}[expanded["advance_explicit"]]
    lines = [
        "# Fixed 38-night validation results", "",
        f"**{decision} under the prespecified criteria.** "
        f"The +30 min explicit − fusion macro-F1 difference averaged {_fmt(primary['mean_delta'], True)} "
        f"(range {_fmt(primary['min_delta'], True)} to {_fmt(primary['max_delta'], True)}). "
        f"{primary['positive_seeds']}/{len(seeds)} seeds favored explicit. "
        f"Mean full-horizon NLL changed by {_fmt(expanded['mean_full_nll_delta'], True)} (lower is better). "
        f"Mean +30 min Wake recall changed by {_fmt(expanded['mean_30_min_wake_recall_delta'], True)} (higher is better).",
        "", "## Primary comparison and sensitivity", "",
    ]
    if all(methods[arm]["leads"]["30"]["wake_recall"] == 0 for arm in ("explicit", "fusion")):
        lines.extend(["Neither rollout identified a reference Wake target at +30 min in any seed.", ""])
    restricted_support = expanded["restricted_30_min_support"]
    lines.extend([_table(
        ["Seed", "Explicit F1", "Fusion F1", "Explicit − fusion", "Excluding masked histories"],
        [[s, _fmt(scores[s]["methods"]["explicit"]["leads"]["30"]["macro_f1"]),
          _fmt(scores[s]["methods"]["fusion"]["leads"]["30"]["macro_f1"]),
          _fmt(primary["delta_by_seed"][str(s)], True), _fmt(restricted["delta_by_seed"][str(s)], True)] for s in seeds]
    ), "",
        f"The sensitivity analysis used the original fitted predictions and excluded {expanded['excluded_histories']} "
        f"origins with masked historical ACC. Of {expanded['remaining_origins']} remaining origins, "
        f"{expanded['restricted_30_min_known']} had known +30 min labels and {expanded['restricted_30_min_unknown']} did not. "
        f"The {expanded['restricted_30_min_evaluable_participants']} evaluable participants contributed "
        + ", ".join(f"{restricted_support[name]} {name}" for name in STAGES)
        + f" labels. The resulting mean difference was {_fmt(restricted['mean_delta'], True)}.",
        "", "## Endpoint scores", "",
        "Each participant's confusion matrix has unit mass before averaging over participants and computing F1. "
        "Losses are averaged within participant and then across participants. Method scores below average over seeds. "
        "NE indicates unavailable support.", "",
        _table(["Lead (min)", "Participants", "Known origins", "Unknown origins", *STAGES],
               [[lead, row["participants"], row["origins"], row["unknown"], *(row["support"][k] for k in STAGES)]
                for lead, row in scores[seeds[0]]["methods"]["stage_prior"]["leads"].items()]), "",
        _table(["Method", "Lead (min)", "Macro-F1", "Wake recall", "NLL", "Brier", *(f"{s} F1" for s in STAGES)],
               [[arm, lead, *(_fmt(row[k]) for k in ("macro_f1", "wake_recall", "nll", "brier")),
                 *(_fmt(row["f1"][k]) for k in STAGES)]
                for arm in METHODS for lead, row in methods[arm]["leads"].items()]), "",
        "## Paired differences across seeds", "",
        _table(["Arm − reference", "F1 +5", "F1 +15", "F1 +30", "Full NLL", "Full Brier"],
               [[f"{p['arm']} − {p['reference']}", *(_fmt(p["leads"][str(h)]["macro_f1"]["mean_delta"], True)
                                                    for h in LEAD_INDICES),
                 _fmt(p["nll"]["mean_delta"], True), _fmt(p["brier"]["mean_delta"], True)]
                for p in aggregate["paired_differences"].values()]), "",
        "Fusion − HR-only measures the contribution of wrist amplitude, count and availability together. "
        "Direct prediction uses a distinct readout and parameter count.", "",
        "## Full-horizon and auxiliary scores", "",
        _table(["Method", "Parameters¹", "NLL", "Brier", "Wake minutes MAE", "Wake minutes bias",
                "Short Wake recall²", "Short events", "HR MAE (bpm)"],
               [[arm, scores[seeds[0]]["fit"][arm]["parameters"] if arm in scores[seeds[0]]["fit"] else "—",
                 _fmt(row["nll"]), _fmt(row["brier"]), _fmt(row["wake_minutes"]["mae_minutes"]),
                 _fmt(row["wake_minutes"]["bias_minutes"]),
                 _fmt(row["short_wake_events"]["all_short"]["unique_event_recall_any_origin"]),
                 int(row["short_wake_events"]["all_short"]["unique_reference_events"]),
                 _fmt(row["hr"]["mae_bpm"]) if row["hr"] else "—"] for arm, row in methods.items()]), "",
        "¹ Neural trainable parameters. ² Reference events comprise 1–2 Wake epochs and are matched by absolute "
        "participant/night event boundaries. Recall counts each reference event once if any evaluable origin hits it.", "",
        "The seed JSONs include the participant-normalized and pooled confusion matrices, each class F1, "
        "short-event duration strata, event-then-participant macro hit rates, Wake-minute controls, "
        "last-observed HR control, parameter counts and training times. The same validation participants appear "
        "in every seed, and neighboring forecast windows overlap. Differences describe this fixed validation cohort.", "",
    ])
    return "\n".join(lines)


def write_expanded_summary(output, scores, aggregate):
    """Write the reviewer's tables and attach the same numeric decision to aggregate.json."""
    summary = expanded_summary(scores, aggregate)
    aggregate["expanded"] = summary
    (Path(output) / "results.md").write_text(_report(scores, aggregate, summary))
