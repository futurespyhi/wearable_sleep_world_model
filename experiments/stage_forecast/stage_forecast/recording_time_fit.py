"""Recording-time stage priors and horizon transition estimates for frozen origins."""

import numpy as np

from .metrics import EPOCH_SECONDS, HORIZON, STAGES, _target_array
from .oracle_scores import _probabilities

BIN_EDGES_SECONDS = (7200, 14400, 21600)
BIN_NAMES = ("[0,2)", "[2,4)", "[4,6)", "[6,infinity)")
PSEUDOCOUNT = 20
BINS = len(BIN_NAMES)
CLASSES = len(STAGES)


def recording_bins(windows, starts):
    """Locate the cutoff relative to each night's audited recStart."""
    origin = np.asarray(windows.origin)
    if origin.ndim != 1 or origin.dtype.kind not in "iu" or (origin < 0).any():
        raise ValueError("expect a nonnegative integer cutoff epoch for every origin")
    n = len(origin)
    for field in ("participant", "night", "origin_time"):
        if np.asarray(getattr(windows, field)).shape != (n,):
            raise ValueError(f"misaligned {field} in cached origins")
    try:
        start = np.array([starts[(str(person), str(night))] for person, night
                          in zip(windows.participant, windows.night)], dtype=np.float64)
    except KeyError as error:
        raise ValueError(f"missing audited recording start for {error}") from error
    seconds = origin.astype(np.float64) * EPOCH_SECONDS
    elapsed = np.asarray(windows.origin_time, dtype=np.float64) - start
    if not np.isfinite(elapsed).all() or not np.allclose(elapsed, seconds, atol=1e-6, rtol=0):
        raise ValueError("cached cutoff epoch disagrees with origin_time minus audited recStart")
    return np.searchsorted(BIN_EDGES_SECONDS, seconds, side="right")


def _bins(value, n):
    bins = np.asarray(value)
    if bins.shape != (n,) or bins.dtype.kind not in "iu" or (bins < 0).any() or (bins >= BINS).any():
        raise ValueError("each origin needs one integer recording-time bin in 0..3")
    return bins


def _current(value, n):
    current = np.asarray(value)
    if current.shape != (n,) or not np.isin(current, (-1, 0, 1, 2, 3)).all():
        raise ValueError("each origin needs one current stage in -1..3")
    return current.astype(np.intp, copy=False)


def _shrink(counts, global_distribution):
    support = counts.sum(axis=-1, keepdims=True)
    fitted = (counts + PSEUDOCOUNT * global_distribution) / (support + PSEUDOCOUNT)
    return np.where(support > 0, fitted, global_distribution)


def fit_time(train, train_bin, global_prior, global_T):
    """Fit time-specific multinomials from the training nights using fixed global pseudo-counts."""
    future = _target_array(train.stage)
    current = _current(train.current_stage, len(future))
    bins = _bins(train_bin, len(future))
    global_prior = _probabilities(global_prior, (HORIZON, CLASSES), "global prior")
    global_T = _probabilities(global_T, (HORIZON, CLASSES, CLASSES), "global transitions")
    future_counts = np.zeros((BINS, HORIZON, CLASSES), dtype=np.int64)
    pair_counts = np.zeros((BINS, HORIZON, CLASSES, CLASSES), dtype=np.int64)
    for lead in range(HORIZON):
        target = future[:, lead]
        known = target >= 0
        pair = known & (current >= 0)
        np.add.at(future_counts[:, lead], (bins[known], target[known]), 1)
        np.add.at(pair_counts[:, lead], (bins[pair], current[pair], target[pair]), 1)

    metadata = {
        "bin_hours_since_recStart": list(BIN_NAMES),
        "stage_order": list(STAGES),
        "pseudocount_per_multinomial": PSEUDOCOUNT,
        "training_origins_by_bin": np.bincount(bins, minlength=BINS).tolist(),
        "future_counts_axes": ["bin", "lead", "future_stage"],
        "future_counts": future_counts.tolist(),
        "known_target_support": future_counts.sum(axis=-1).tolist(),
        "pair_counts_axes": ["bin", "lead", "current_stage", "future_stage"],
        "pair_counts": pair_counts.tolist(),
        "known_pair_support_per_row": pair_counts.sum(axis=-1).tolist(),
    }
    return _shrink(future_counts, global_prior), _shrink(pair_counts, global_T), metadata


def make_time_predictions(val_bin, pt, current, priors, T):
    """Only the retrospective oracle indexes a row using the observed cutoff stage."""
    n = len(val_bin)
    bins = _bins(val_bin, n)
    pt = _probabilities(pt, (n, CLASSES), "estimated current-stage distribution")
    current = _current(current, n)
    priors = _probabilities(priors, (BINS, HORIZON, CLASSES), "time priors")
    T = _probabilities(T, (BINS, HORIZON, CLASSES, CLASSES), "time transitions")
    time_only = priors[bins]
    time_transition = np.einsum("ni,nhij->nhj", pt, T[bins])
    # Keep a valid placeholder for the full origin grid. The common oracle mask
    # excludes unknown current stages before scoring any method.
    time_oracle = time_only.copy()
    known = current >= 0
    time_oracle[known] = T[bins[known], :, current[known], :]
    return {"time_only": time_only, "time_transition": time_transition, "time_oracle": time_oracle}
