"""Matched binary logistic models for changes in reference stage at three endpoints."""

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit

from .endpoint_features import RECENT_FEATURE_NAMES
from .metrics import LEAD_INDICES, STAGES, _target_array
from .recording_time_fit import BIN_NAMES

L2 = 0.01
ARM_WIDTHS = {"A": 4, "B": 8, "C": 12}


def _features(bins, posterior, sensor):
    bins = np.asarray(bins)
    if bins.ndim != 1 or bins.dtype.kind not in "iu" or not np.isin(bins, np.arange(4)).all():
        raise ValueError("expected integer recording time bin 0..3 for every origin")
    posterior, sensor = np.asarray(posterior, dtype=float), np.asarray(sensor, dtype=float)
    if (posterior.shape != (len(bins), 4) or not np.isfinite(posterior).all()
            or (posterior < 0).any() or (posterior > 1).any()
            or not np.allclose(posterior.sum(axis=-1), 1, atol=1e-6, rtol=1e-6)):
        raise ValueError("expected normalized four-stage wrist posterior for every origin")
    if sensor.shape != (len(bins), 4) or np.isinf(sensor).any():
        raise ValueError("expected four finite or missing recent sensor features per origin")
    return np.column_stack((np.eye(4)[bins], posterior, sensor))


def _transform(training, validation):
    """Train-only available-value means and population SDs for the continuous columns."""
    observed = np.isfinite(training)
    count = observed.sum(axis=0)
    center = np.nansum(training, axis=0) / np.maximum(count, 1)
    residual = np.where(observed, training - center, 0.0)
    scale = np.sqrt(np.sum(residual ** 2, axis=0) / np.maximum(count, 1))
    scale[scale < 1e-8] = 1.
    center[:4] = 0.
    scale[:4] = 1.

    def transform(array):
        return np.where(np.isfinite(array), (array - center) / scale, 0.)

    return transform(training), transform(validation), center, scale, count


def _fit(design, outcome):
    """Minimize mean Bernoulli NLL with L2 on slopes and a free intercept."""
    positives = int(outcome.sum())
    if not 0 < positives < len(outcome):
        raise ValueError("binary logistic regression needs both endpoint outcomes in training")
    def objective(parameters):
        slopes, intercept = parameters[:-1], parameters[-1]
        logits = design @ slopes + intercept
        residual = expit(logits) - outcome
        loss = np.mean(np.logaddexp(0., logits) - outcome * logits) + L2 / 2 * (slopes @ slopes)
        gradient = np.r_[design.T @ residual / len(outcome) + L2 * slopes, residual.mean()]
        return loss, gradient

    initial = np.zeros(design.shape[1] + 1)
    initial[-1] = np.log(positives / (len(outcome) - positives))
    fitted = minimize(objective, initial, method="L-BFGS-B", jac=True,
                      options={"maxiter": 500, "ftol": 1e-13, "gtol": 1e-9})
    if not fitted.success or not np.isfinite(fitted.x).all():
        raise RuntimeError(f"binary logistic optimization failed: {fitted.message}")
    return fitted


def fit_endpoint_models(train, train_bin, val_bin, train_pt, val_pt, train_sensor, val_sensor):
    """Use identical known-endpoint training rows per lead; predict each validation origin."""
    features = _features(train_bin, train_pt, train_sensor)
    validation = _features(val_bin, val_pt, val_sensor)
    current = np.asarray(train.current_stage)
    targets = _target_array(train.stage)
    if (len(targets) != len(features) or current.shape != (len(features),)
            or not np.isin(current, [-1, 0, 1, 2, 3]).all()):
        raise ValueError("training stage labels and origins disagree")
    names = [f"recording_hours_{name}" for name in BIN_NAMES] + [f"p_{stage}" for stage in STAGES]
    names += list(RECENT_FEATURE_NAMES)
    predictions = {arm: np.empty((len(validation), len(LEAD_INDICES))) for arm in ARM_WIDTHS}
    details = {"l2": L2, "lead_minutes": list(LEAD_INDICES), "optimizer": "scipy L-BFGS-B",
               "loss": "mean Bernoulli NLL over all evaluable training origins plus L2/2 * squared slopes",
               "intercept_penalized": False, "leads": {}}
    for column, (minutes, step) in enumerate(LEAD_INDICES.items()):
        known = (current >= 0) & (targets[:, step] >= 0)
        changed = (current[known] != targets[known, step]).astype(float)
        tx, vx, center, scale, count = _transform(features[known], validation)
        fit_rows = {"known": len(changed), "changed": int(changed.sum()), "same": int(len(changed)-changed.sum()),
                    "excluded": int((~known).sum()), "arms": {}}
        for arm, width in ARM_WIDTHS.items():
            fit = _fit(tx[:, :width], changed)
            predictions[arm][:, column] = expit(vx[:, :width] @ fit.x[:-1] + fit.x[-1])
            fit_rows["arms"][arm] = {
                "feature_names": names[:width], "center": center[:width].tolist(), "scale": scale[:width].tolist(),
                "finite_training_counts": count[:width].tolist(), "slopes": fit.x[:-1].tolist(),
                "intercept": float(fit.x[-1]), "iterations": int(fit.nit),
                "gradient_inf_norm": float(np.max(np.abs(fit.jac))),
            }
        details["leads"][str(minutes)] = fit_rows
    return predictions, details
