"""Train-only estimation of the horizon prior mixture and empirical transition controls."""

from __future__ import annotations

from dataclasses import fields

import numpy as np
from scipy.optimize import minimize_scalar

from .baselines import HORIZON, N_STAGES, fit_persistence, predict_persistence, stage_prior
from .data import STAGES, StageWindows, fit_standardizer
from .metrics import NLL_EPS


def _slice_train(train, mask):
    return StageWindows(**{field.name: getattr(train, field.name)[mask] for field in fields(train)})


def _oof_predictions(train):
    """Refit all three training estimates each time a person and their nights are held out."""
    people = np.unique(train.participant)
    if len(people) < 2:
        raise ValueError("Cross-fitting requires at least two training participants")
    posterior = np.full((len(train.stage), N_STAGES), np.nan)
    priors = np.full((len(train.stage), HORIZON, N_STAGES), np.nan)
    folds = []
    for person in people:
        held = train.participant == person
        fold_train = _slice_train(train, ~held)
        scaler = fit_standardizer(fold_train)
        training_hr, training_acc = scaler.transform(fold_train.history)
        estimator = fit_persistence(training_hr, training_acc, fold_train.current_stage)
        held_hr, held_acc = scaler.transform(train.history[held])
        posterior[held] = predict_persistence(estimator, held_hr, held_acc)[:, 0, :]
        priors[held] = stage_prior(fold_train.stage, int(held.sum()))
        folds.append({
            "held_out_participant": str(person),
            "held_out_origins": int(held.sum()),
            "fit_origins": int((~held).sum()),
            "fit_participants": len(people) - 1,
            "known_current_training_stages": int(estimator.metadata["known_current_stages"]),
        })
    return posterior, priors, folds


def _minimum_mixture(posterior, prior, sample_weights):
    """Minimize clipped NLL over [0,1], including both pure-component endpoints."""
    difference = prior - posterior

    def loss(alpha):
        prob = (1.0 - alpha) * posterior + alpha * prior
        return float(-sample_weights @ np.log(np.clip(prob, NLL_EPS, 1.0)))

    # Clipping makes NLL piecewise convex. Include each floor crossing as an
    # interval endpoint, so zero-probability components are handled exactly.
    changes = difference != 0
    if not changes.any():
        return 0.0, loss(0.0)
    crossing = (NLL_EPS - posterior[changes]) / difference[changes]
    bounds = np.unique(np.r_[0., crossing[(crossing > 0.) & (crossing < 1.)], 1.])
    candidates = [(loss(value), float(value)) for value in bounds]
    for left, right in zip(bounds[:-1], bounds[1:]):
        result = minimize_scalar(loss, method="bounded", bounds=(left, right), options={"xatol": 1e-12})
        if not result.success:
            raise RuntimeError(f"mixture fit failed: {result.message}")
        candidates.append((float(result.fun), float(result.x)))
    # Same objective value at both endpoints (including flat fits) favors alpha=0.
    best_loss, alpha = min(candidates)
    return alpha, best_loss


def _fit_weights(stage, participant, posterior, priors):
    alpha = np.zeros(HORIZON)
    nll, people_per_lead, known_per_lead = [], [], []
    for lead in range(HORIZON):
        rows = np.flatnonzero(stage[:, lead] >= 0)
        known_per_lead.append(len(rows))
        people, person, support = np.unique(participant[rows], return_inverse=True, return_counts=True)
        people_per_lead.append(len(people))
        if not len(rows):
            nll.append(None)
            continue
        sample_weights = 1.0 / (len(people) * support[person])
        labels = stage[rows, lead]
        weight, fitted_nll = _minimum_mixture(
            posterior[rows, labels], priors[rows, lead, labels], sample_weights,
        )
        alpha[lead] = weight
        nll.append(fitted_nll)
    return alpha, {
        "alpha_definition": "weight of per-lead prior, (1 - alpha) * persistence + alpha * prior",
        "loss": "known future stages, mean NLL within each held-out person then across people per lead",
        "probability_floor": NLL_EPS,
        "zero_support_or_equal_loss_tie": "choose smallest alpha",
        "alpha": alpha.tolist(), "fitted_oof_nll": nll,
        "known_targets": known_per_lead, "participants": people_per_lead,
    }


def _fit_transition(current, future):
    """Count observed origin pairs separately for each future lead."""
    prior = stage_prior(future, 1)[0]
    counts = np.zeros((HORIZON, N_STAGES, N_STAGES), dtype=np.int64)
    for lead in range(HORIZON):
        known = (current >= 0) & (future[:, lead] >= 0)
        np.add.at(counts[lead], (current[known], future[known, lead]), 1)
    support = counts.sum(axis=2, keepdims=True)
    matrices = np.broadcast_to(prior[:, None, :], counts.shape).copy()
    np.divide(counts, support, out=matrices, where=support > 0)
    return matrices, {
        "axes": ["lead", "current_stage", "future_stage"],
        "stage_order": list(STAGES),
        "estimator": "empirical conditional frequencies of retained, known training origin pairs",
        "zero_support_row": "full training stage prior at that lead",
        "pair_counts": counts.tolist(), "current_support": support[..., 0].tolist(),
        "prior_fallback_rows": int(np.count_nonzero(support == 0)),
    }


def fit_controls(train: StageWindows):
    """Estimate the mixture weight and horizon transition matrix for every lead."""
    posterior, priors, folds = _oof_predictions(train)
    weights, mixture = _fit_weights(train.stage, train.participant, posterior, priors)
    matrices, transition = _fit_transition(train.current_stage, train.stage)
    return weights, matrices, {"folds": folds, "mixture": mixture, "transition": transition}
