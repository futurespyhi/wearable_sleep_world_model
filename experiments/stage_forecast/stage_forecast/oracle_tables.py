"""Render the frozen oracle comparison and its common evaluation denominators."""

from .metrics import STAGES


_CONTROLS = ("transition", "prior_mix", "stage_prior")
_ENDPOINTS = (("5", "overall"), ("15", "overall"), ("30", "overall"),
              ("30", "same"), ("30", "changed"))


def _score(value, signed=False):
    if value is None:
        return "NE"
    return f"{value:+.4f}" if signed else f"{value:.4f}"


def _row(*cells):
    return "| " + " | ".join(str(cell) for cell in cells) + " |"


def _support(row):
    return [row["support"][stage] for stage in STAGES]


def _participant_table(scores, stratum):
    rows = [
        _row("Participant", "Origins", "Oracle − transition", "Oracle − prior mixture", "Oracle − stage prior"),
        _row("---", "---:", "---:", "---:", "---:"),
    ]
    for person, strata in sorted(scores["participants_30"].items()):
        data = strata[stratum]
        differences = [_score(data["oracle_minus"][control], signed=True) for control in _CONTROLS]
        rows.append(_row(person, data["origins"], *differences))
    mean = scores["paired_mean_check_30"][stratum]
    per_person_mean = [_score(mean[control], signed=True) for control in _CONTROLS]
    rows.append(_row("**Equal-participant mean**", "—", *per_person_mean))
    return rows


def render_tables(scores):
    """Present the scorer's already matched and participant-weighted estimates."""
    rows = [
        "All four methods use the same origins within each lead and stratum. Both the stage at cutoff "
        "and the endpoint stage must be known. Same and changed compare those two stages.",
        "",
        _row("Lead", "Stratum", "People", "Origins", *STAGES),
        _row("---", "---", "---:", "---:", "---:", "---:", "---:", "---:"),
    ]
    for lead, stratum in _ENDPOINTS:
        data = scores["leads"][lead][stratum]
        rows.append(_row(f"+{lead} min", stratum, data["participants"], data["origins"], *_support(data)))
    rows.extend([
        "",
        "The stage counts above refer to the future endpoint. NLL below averages within each person, "
        "then across people. Lower values are better.",
        "",
        _row("Lead", "Stratum", "Oracle transition", "Estimated-state transition", "Prior mixture", "Stage prior"),
        _row("---", "---", "---:", "---:", "---:", "---:"),
    ])
    for lead, stratum in _ENDPOINTS:
        nll = scores["leads"][lead][stratum]["nll"]
        rows.append(_row(f"+{lead} min", stratum, *[_score(nll[key]) for key in ("oracle", *_CONTROLS)]))
    rows.extend([
        "",
        "**Paired +30-minute NLL differences.** A negative value favors the oracle. Each difference "
        "uses the same origins for the oracle and its comparator. NE indicates no evaluable origins.",
        "",
        *_participant_table(scores, "overall"),
        "",
        "<details><summary>Participant differences for same and changed stages</summary>",
    ])
    for stratum, title in (("same", "Same stage"), ("changed", "Changed stage")):
        rows.extend(["", f"**{title}**", "", *_participant_table(scores, stratum)])
    rows.extend(["", "</details>", ""])
    current = scores["current_stage"]
    rows.extend([
        f"**Current stage at cutoff.** The saved wearable estimate p_t had NLL {_score(current['nll'])} "
        f"and macro-F1 {_score(current['macro_f1'])} on {current['origins']} labeled origins from "
        f"{current['participants']} participants. {current['unknown']} of {scores['total_origins']} "
        "origins had unknown current stage.",
        "",
        _row("Current-stage label", *STAGES),
        _row("---", "---:", "---:", "---:", "---:"),
        _row("Origins", *_support(current)),
    ])
    return "\n".join(rows) + "\n"
