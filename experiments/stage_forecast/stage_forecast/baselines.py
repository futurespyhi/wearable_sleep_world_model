"""Stage frequency and learned persistence controls with NumPy and SciPy only."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import minimize
from scipy.special import logsumexp, softmax


HORIZON = 60
N_STAGES = 4
PERSISTENCE_L2 = 0.01


def stage_prior(train_stage, n_origins):
    """Estimate a separate class prior at each lead from known training labels."""
    if train_stage.ndim != 2 or train_stage.shape[1] != HORIZON:
        raise ValueError("Prior targets must have shape [N,60]")
    if not np.isin(train_stage, [-1, 0, 1, 2, 3]).all():
        raise ValueError("Prior targets must be -1 or a supported class index")
    counts = (train_stage[..., None] == np.arange(N_STAGES)).sum(axis=0)
    known_per_lead = counts.sum(axis=1, keepdims=True)
    if not known_per_lead.sum():
        raise ValueError("Cannot estimate the prior without any known training stage")
    # The pooled training prior covers a lead with no observed training label.
    pooled = counts.sum(axis=0) / known_per_lead.sum()
    prior = np.divide(
        counts,
        known_per_lead,
        out=np.broadcast_to(pooled, counts.shape).copy(),
        where=known_per_lead > 0,
    )
    return np.broadcast_to(prior, (n_origins, HORIZON, N_STAGES))


def _persistence_features(hr, acc):
    if hr.ndim != 3 or acc.ndim != 3 or hr.shape[:2] != acc.shape[:2] or hr.shape[1] != HORIZON:
        raise ValueError("Persistence requires paired 60-epoch HR/ACC histories")
    history = np.concatenate((hr, acc), axis=-1, dtype=np.float64)
    summaries = [history[:, -1, :]]
    for length in (10, 30, HORIZON):
        window = history[:, -length:, :]
        summaries.extend((window.mean(axis=1), window.std(axis=1)))
    return np.column_stack(summaries)


@dataclass(frozen=True)
class Persistence:
    classes: np.ndarray
    coefficients: np.ndarray
    center: np.ndarray
    scale: np.ndarray
    metadata: dict


def fit_persistence(train_hr, train_acc, current_stage):
    """Predict the latest completed stage with a train-only multinomial classifier."""
    features = _persistence_features(train_hr, train_acc)
    if current_stage.shape != (len(features),) or not np.isin(current_stage, [-1, 0, 1, 2, 3]).all():
        raise ValueError("Current-stage targets must match origins and use -1 or a supported class index")
    known = current_stage >= 0
    labels = current_stage[known]
    if not len(labels):
        raise ValueError("Cannot train persistence without known current stages")
    classes, targets = np.unique(labels, return_inverse=True)
    n_classes = len(classes)
    center = features.mean(axis=0)
    scale = features.std(axis=0)
    scale[scale < 1e-8] = 1.0
    design = np.column_stack(((features[known] - center) / scale, np.ones(len(labels))))
    rows = np.arange(len(labels))

    def objective(vector):
        weights = vector.reshape(design.shape[1], n_classes)
        logits = design @ weights
        log_probabilities = logits - logsumexp(logits, axis=1, keepdims=True)
        loss = -log_probabilities[rows, targets].mean() + PERSISTENCE_L2 / 2 * np.square(weights[:-1]).sum()
        residual = np.exp(log_probabilities)
        residual[rows, targets] -= 1
        gradient = design.T @ residual / len(labels)
        gradient[:-1] += PERSISTENCE_L2 * weights[:-1]
        return loss, gradient.ravel()

    result = minimize(
        objective,
        np.zeros(design.shape[1] * n_classes),
        method="L-BFGS-B",
        jac=True,
        options={"maxiter": 500},
    )
    if not result.success:
        raise RuntimeError(f"Persistence optimization failed: {result.message}")
    return Persistence(
        classes,
        result.x.reshape(design.shape[1], n_classes),
        center,
        scale,
        {
            "method": "L2-regularized multinomial logistic regression",
            "l2": PERSISTENCE_L2,
            "parameters": int(result.x.size),
            "optimizer_iterations": int(result.nit),
            "known_current_stages": len(labels),
            "current_stage_support": np.bincount(labels, minlength=N_STAGES).tolist(),
            "history_summary_epochs": [1, 10, 30, HORIZON],
        },
    )


def predict_persistence(fitted, hr, acc):
    """Repeat the estimated current-stage distribution across all 60 leads."""
    features = _persistence_features(hr, acc)
    design = np.column_stack(((features - fitted.center) / fitted.scale, np.ones(len(features))))
    current = np.zeros((len(features), N_STAGES))
    current[:, fitted.classes] = softmax(design @ fitted.coefficients, axis=1)
    return np.broadcast_to(current[:, None, :], (len(features), HORIZON, N_STAGES))
