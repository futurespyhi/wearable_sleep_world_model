"""Past wrist summaries and participant-held-out current-stage beliefs for endpoint change."""

import numpy as np

from .baselines import N_STAGES, fit_persistence, predict_persistence
from .data import HISTORY_EPOCHS, HISTORY_FEATURES, _valid_continuous_values, fit_standardizer
from .oracle_scores import _probabilities
from .transition_fit import _oof_predictions


RECENT_FEATURE_NAMES = (
    "hr_mean_last_5min",
    "acc_diff_rms_mean_last_5min",
    "hr_mean_last_5min_minus_prior_25min",
    "acc_diff_rms_mean_last_5min_minus_prior_25min",
)


def _observed_mean(values):
    known = np.isfinite(values)
    count = known.sum(axis=1)
    return np.divide(
        np.where(known, values, 0.).sum(axis=1), count,
        out=np.full(count.shape, np.nan), where=count > 0,
    )


def recent_features(history):
    """Equal-epoch HR and wrist RMS means over the last 5 minutes, and their change from the prior 25."""
    raw = np.asarray(history)
    if raw.ndim != 3 or raw.shape[1:] != (HISTORY_EPOCHS, len(HISTORY_FEATURES)):
        raise ValueError("expected six cached wrist features for each of 60 pre-cutoff epochs")
    values, _, _ = _valid_continuous_values(raw)
    # These are the raw HR mean and ACC adjacent-difference RMS in their original units.
    selected = values[..., [0, 3]]
    recent = _observed_mean(selected[:, -10:])
    previous = _observed_mean(selected[:, :-10])
    return np.column_stack((recent, recent - previous))


def prepare_posteriors(train, val, saved_val_pt):
    """Reuse participant-out-of-fold persistence and check the saved validation predictions."""
    if np.intersect1d(train.participant, val.participant).size:
        raise ValueError("training and validation participants must be disjoint")
    saved = _probabilities(saved_val_pt, (len(val.history), N_STAGES), "saved validation posterior")
    scaler = fit_standardizer(train)
    train_hr, train_acc = scaler.transform(train.history)
    estimator = fit_persistence(train_hr, train_acc, train.current_stage)
    val_hr, val_acc = scaler.transform(val.history)
    reproduced = predict_persistence(estimator, val_hr, val_acc)[:, 0, :]
    delta = float(np.max(np.abs(reproduced - saved)))
    if not np.allclose(reproduced, saved, atol=1e-10, rtol=0.):
        raise ValueError(f"full training refit differs from the frozen validation posterior (max {delta})")
    # The same frozen cross-fit as the previous transition control. The alternate
    # fold-specific stage priors are unused in this endpoint predictor.
    oof_train, _, folds = _oof_predictions(train)
    _probabilities(oof_train, (len(train.history), N_STAGES), "held-out training posterior")
    return oof_train, saved, {
        "oof_folds": folds,
        "validation_pt_max_absolute_error": delta,
        "validation_pt_absolute_tolerance": 1e-10,
        "validation_pt_exact": bool(np.array_equal(reproduced, saved)),
        "recent_feature_names": list(RECENT_FEATURE_NAMES),
    }
