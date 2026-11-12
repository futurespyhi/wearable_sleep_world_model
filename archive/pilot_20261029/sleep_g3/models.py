"""CPU baselines for past-sensor-only forecasts of 30-second Wake epochs.

These models are deliberately small reference models, not a reproduction of a
pretrained sensor foundation model. Duration arms share one fitted trajectory
model and differ only in the decoding constraint.
"""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np
from scipy.linalg import solve
from scipy.special import logsumexp


EPOCH_MINUTES = 0.5
_PROBABILITY_EPS = 1e-12


def duration_decode(
    probability: np.ndarray,
    current_probability: np.ndarray,
    min_epochs: int = 2,
    mode: str = "hard",
    soft_penalty: float = 1.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Return posterior Wake marginals and a joint MAP path.

    The state is (Sleep/Wake, run age capped at ``min_epochs``). Forecast
    probabilities supply the only future unary potentials. Allowed edges have
    weight one: they are intentionally not row-normalized, so an unconstrained
    decoder preserves the original independent forecasts. A premature switch
    is forbidden in hard mode or costs ``soft_penalty * (min_epochs - age)``
    in soft mode. Forward-backward and Viterbi use identical potentials.

    The inferred current state has an unknown, left-censored run age, initialized
    at the cap. Every terminal age is allowed, so the final run is right-censored.
    A short first forecast run can continue the current run. With min_epochs=1
    or mode='none', the marginals are exactly the input probabilities. Otherwise
    exact zero/one unary probabilities are clipped to 1e-12 for nonzero support.
    """
    probability = np.asarray(probability, dtype=np.float64)
    current_probability = np.asarray(current_probability, dtype=np.float64)
    if probability.ndim != 2 or probability.shape[1] == 0:
        raise ValueError("probability must have shape [N, T] with T >= 1")
    if current_probability.shape != (probability.shape[0],):
        raise ValueError("current_probability must have shape [N]")
    if not np.isfinite(probability).all() or np.any(
        (probability < 0) | (probability > 1)
    ):
        raise ValueError("probability must contain finite values in [0, 1]")
    if not np.isfinite(current_probability).all() or np.any(
        (current_probability < 0) | (current_probability > 1)
    ):
        raise ValueError("current_probability must contain finite values in [0, 1]")
    if isinstance(min_epochs, bool) or int(min_epochs) != min_epochs or min_epochs < 1:
        raise ValueError("min_epochs must be a positive integer")
    if mode not in {"none", "soft", "hard"}:
        raise ValueError("mode must be 'none', 'soft', or 'hard'")
    if not np.isfinite(soft_penalty) or soft_penalty < 0:
        raise ValueError("soft_penalty must be finite and nonnegative")
    if mode == "none" or min_epochs == 1 or (mode == "soft" and soft_penalty == 0):
        return probability.copy(), (probability >= 0.5).astype(np.uint8)

    n_rows, horizon = probability.shape
    if n_rows == 0:
        return probability.copy(), np.empty(probability.shape, dtype=np.uint8)
    age_cap = int(min_epochs)
    n_states = 2 * age_cap
    state_label = np.repeat(np.arange(2), age_cap)
    transitions = np.full((n_states, n_states), -np.inf)
    for state in range(2):
        for age in range(1, age_cap + 1):
            source = state * age_cap + age - 1
            next_age = min(age + 1, age_cap)
            transitions[source, state * age_cap + next_age - 1] = 0.0
            if age == age_cap:
                transitions[source, (1 - state) * age_cap] = 0.0
            elif mode == "soft":
                transitions[source, (1 - state) * age_cap] = -soft_penalty * (
                    age_cap - age
                )

    p = np.clip(probability, _PROBABILITY_EPS, 1.0 - _PROBABILITY_EPS)
    emissions = np.stack((np.log1p(-p), np.log(p)), axis=-1)
    initial = np.full((n_rows, n_states), -np.inf)
    with np.errstate(divide="ignore"):
        initial[:, age_cap - 1] = np.log1p(-current_probability)
        initial[:, 2 * age_cap - 1] = np.log(current_probability)

    forward = np.empty((n_rows, horizon, n_states), dtype=np.float64)
    parents = np.empty((n_rows, horizon, n_states), dtype=np.int64)
    previous_forward = initial
    previous_viterbi = initial
    for step in range(horizon):
        unary = emissions[:, step, state_label]
        forward[:, step, :] = unary + logsumexp(
            previous_forward[:, :, None] + transitions[None, :, :], axis=1
        )
        candidates = previous_viterbi[:, :, None] + transitions[None, :, :]
        parents[:, step, :] = candidates.argmax(axis=1)
        previous_viterbi = unary + candidates.max(axis=1)
        previous_forward = forward[:, step, :]

    log_normalizer = logsumexp(forward[:, -1, :], axis=1)
    marginals = np.empty_like(probability)
    backward = np.zeros((n_rows, n_states), dtype=np.float64)
    for step in range(horizon - 1, -1, -1):
        posterior = forward[:, step, :] + backward - log_normalizer[:, None]
        marginals[:, step] = np.exp(logsumexp(posterior[:, age_cap:], axis=1))
        if step:
            backward = logsumexp(
                transitions[None, :, :]
                + emissions[:, step, state_label][:, None, :]
                + backward[:, None, :],
                axis=2,
            )

    path = np.empty(probability.shape, dtype=np.uint8)
    state = previous_viterbi.argmax(axis=1)
    rows = np.arange(n_rows)
    for step in range(horizon - 1, -1, -1):
        path[:, step] = state_label[state]
        state = parents[rows, step, state]
    return np.clip(marginals, 0.0, 1.0), path


def summarize_history(history: np.ndarray) -> np.ndarray:
    """Fixed past-only summaries, retaining missingness and sensor coverage.

    Channels are hr_mean, hr_std, acc_norm_mean, acc_norm_std, acc_diff_rms,
    hr_count, acc_count. Windows contain 1, 10, 30, 60, and all history epochs.
    Each contributes mean, standard deviation, per-epoch slope, and valid
    fraction. Last valid values and their ages complete the feature vector.
    """
    history = np.asarray(history, dtype=np.float64)
    if history.ndim != 3 or history.shape[2] != 7 or history.shape[1] < 1:
        raise ValueError("history must have shape [N, H, 7] with H >= 1")
    values = history.copy()
    values[~np.isfinite(values)] = np.nan
    counts = values[:, :, 5:7]
    counts[counts < 0] = np.nan
    hr_valid = np.isfinite(values[:, :, 5]) & (values[:, :, 5] > 0)
    acc_valid = np.isfinite(values[:, :, 6]) & (values[:, :, 6] > 0)
    values[:, :, :2] = np.where(hr_valid[:, :, None], values[:, :, :2], np.nan)
    values[:, :, 2:5] = np.where(acc_valid[:, :, None], values[:, :, 2:5], np.nan)
    horizon = values.shape[1]
    pieces = []
    for requested in (1, 10, 30, 60, horizon):
        window = values[:, -min(requested, horizon) :, :]
        valid = np.isfinite(window)
        count = valid.sum(axis=1)
        denominator = np.maximum(count, 1)
        filled = np.where(valid, window, 0.0)
        mean = filled.sum(axis=1) / denominator
        variance = np.where(valid, window - mean[:, None, :], 0.0) ** 2
        std = np.sqrt(variance.sum(axis=1) / denominator)
        time = np.arange(window.shape[1], dtype=np.float64)[None, :, None]
        time_sum = (valid * time).sum(axis=1)
        time_squared_sum = (valid * time**2).sum(axis=1)
        covariance = (filled * time).sum(axis=1) - time_sum * mean
        time_variance = time_squared_sum - time_sum**2 / denominator
        slope = np.divide(
            covariance,
            time_variance,
            out=np.zeros_like(covariance),
            where=time_variance > 0,
        )
        for summary in (mean, std, slope):
            summary[count == 0] = np.nan
            pieces.append(summary)
        pieces.append(count / float(window.shape[1]))

    valid = np.isfinite(values)
    indices = np.arange(horizon)[None, :, None]
    last_index = np.where(valid, indices, -1).max(axis=1)
    last_value = np.take_along_axis(
        values, np.maximum(last_index, 0)[:, None, :], axis=1
    )[:, 0, :]
    last_value[last_index < 0] = np.nan
    age = (horizon - 1 - last_index).astype(np.float64)
    age[last_index < 0] = np.nan
    pieces.extend((last_value, age))
    return np.concatenate(pieces, axis=1)


def _fit_ridge(
    features: np.ndarray, target: np.ndarray, alpha: float, fallback: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Fit unpenalized intercepts, grouping columns with equal label masks."""
    target = np.asarray(target, dtype=np.float64)
    if target.ndim == 1:
        target = target[:, None]
    fallback = np.broadcast_to(np.asarray(fallback, dtype=float), (target.shape[1],))
    coefficients = np.zeros((features.shape[1], target.shape[1]))
    intercept = fallback.copy()
    groups = {}
    for column in range(target.shape[1]):
        mask = np.isfinite(target[:, column])
        key = np.packbits(mask).tobytes()
        groups.setdefault(key, (mask, []))[1].append(column)
    for mask, columns in groups.values():
        if not mask.any():
            continue
        x = features[mask]
        y = target[np.ix_(mask, columns)]
        x_mean = x.mean(axis=0)
        y_mean = y.mean(axis=0)
        x_centered = x - x_mean
        y_centered = y - y_mean
        gram = x_centered.T @ x_centered
        gram.flat[:: gram.shape[0] + 1] += alpha
        if alpha:
            weight = solve(gram, x_centered.T @ y_centered, assume_a="pos")
        else:
            weight = np.linalg.lstsq(x_centered, y_centered, rcond=None)[0]
        coefficients[:, columns] = weight
        intercept[columns] = y_mean - x_mean @ weight
    return coefficients, intercept


def _label_sequence(episode) -> np.ndarray:
    if isinstance(episode, Mapping):
        for key in ("labels", "label", "wake", "target", "y"):
            if key in episode:
                return np.asarray(episode[key])
        raise ValueError("training episode must provide a one-dimensional label sequence")
    for key in ("labels", "label", "wake", "target", "y"):
        if hasattr(episode, key):
            return np.asarray(getattr(episode, key))
    return np.asarray(episode)


class BaselineSuite:
    """Fit all baseline arms on training participants, then use sensors only.

    ``fit`` accepts history[N,H,7], target[N,T] with labels {-1,0,1}, and
    current[N] with labels {-1,0,1}. ``predict`` only reads history; participant,
    current, and target fields have no effect. Optional ``train_episodes`` are
    chronological one-dimensional label arrays or records exposing labels,
    label, wake, target, or y. They must belong exclusively to training subjects.

    With no complete training forecast windows, the outcome arms use an explicit
    population fallback recorded in ``fit_report_``. Unknown future epochs are
    never treated as Sleep or bridged when counting transitions.
    """

    def __init__(
        self,
        seed: int = 40,
        ridge_alpha: float = 10.0,
        min_epochs: int = 2,
        soft_penalty: float = 1.0,
    ):
        if not np.isfinite(ridge_alpha) or ridge_alpha < 0:
            raise ValueError("ridge_alpha must be finite and nonnegative")
        if isinstance(min_epochs, bool) or int(min_epochs) != min_epochs or min_epochs < 1:
            raise ValueError("min_epochs must be a positive integer")
        if not np.isfinite(soft_penalty) or soft_penalty < 0:
            raise ValueError("soft_penalty must be finite and nonnegative")
        self.seed = int(seed)
        self.ridge_alpha = float(ridge_alpha)
        self.min_epochs = int(min_epochs)
        self.soft_penalty = float(soft_penalty)

    def fit(self, train: dict, train_episodes=None) -> "BaselineSuite":
        history = np.asarray(train["history"])
        raw_features = summarize_history(history)
        target = np.asarray(train["target"], dtype=np.float64)
        current = np.asarray(train["current"], dtype=np.float64)
        if target.ndim != 2 or target.shape[0] != history.shape[0] or target.shape[1] < 1:
            raise ValueError("target must have shape [N, T] with T >= 1")
        if current.shape != (history.shape[0],):
            raise ValueError("current must have shape [N]")
        if not np.isin(target, (-1, 0, 1)).all() or not np.isin(current, (-1, 0, 1)).all():
            raise ValueError("training labels must use -1 for unknown, 0 for Sleep, 1 for Wake")
        known_target = target >= 0
        if not known_target.any():
            raise ValueError("at least one training future label is required")

        self.history_epochs_ = history.shape[1]
        self.horizon_ = target.shape[1]
        self.feature_median_ = np.array(
            [
                np.median(column[np.isfinite(column)]) if np.isfinite(column).any() else 0.0
                for column in raw_features.T
            ]
        )
        imputed = np.where(np.isfinite(raw_features), raw_features, self.feature_median_)
        self.feature_mean_ = imputed.mean(axis=0)
        self.feature_scale_ = imputed.std(axis=0)
        self.feature_scale_[self.feature_scale_ < 1e-8] = 1.0
        features = (imputed - self.feature_mean_) / self.feature_scale_

        prevalence = float(target[known_target].mean())
        per_horizon_count = known_target.sum(axis=0)
        per_horizon_mean = np.divide(
            np.where(known_target, target, 0.0).sum(axis=0),
            per_horizon_count,
            out=np.full(self.horizon_, prevalence),
            where=per_horizon_count > 0,
        )
        complete = known_target.all(axis=1)
        total = np.where(complete, EPOCH_MINUTES * target.sum(axis=1), np.nan)
        self.population_total_ = (
            float(total[complete].mean())
            if complete.any()
            else float(EPOCH_MINUTES * per_horizon_mean.sum())
        )
        self.current_coef_, self.current_intercept_ = _fit_ridge(
            features,
            np.where(current >= 0, current, np.nan),
            self.ridge_alpha,
            np.array([prevalence]),
        )
        self.outcome_coef_, self.outcome_intercept_ = _fit_ridge(
            features, total, self.ridge_alpha, np.array([self.population_total_])
        )
        self.trajectory_coef_, self.trajectory_intercept_ = _fit_ridge(
            features,
            np.where(known_target, target, np.nan),
            self.ridge_alpha,
            per_horizon_mean,
        )

        transition_counts = np.ones((2, 2), dtype=np.float64)
        transition_source = "training_episodes" if train_episodes is not None else "training_windows"
        sequences = (
            train_episodes
            if train_episodes is not None
            else np.concatenate((current[:, None], target), axis=1)
        )
        training_participants = set(np.asarray(train.get("participant", [])).tolist())
        observed_edges = 0
        for episode in sequences:
            participant = (
                episode.get("participant")
                if isinstance(episode, Mapping)
                else getattr(episode, "participant", None)
            )
            if participant is not None and training_participants and participant not in training_participants:
                raise ValueError("transition episode includes a participant outside training")
            labels = _label_sequence(episode)
            if labels.ndim != 1 or not np.isin(labels, (-1, 0, 1)).all():
                raise ValueError("episode labels must be a one-dimensional {-1,0,1} sequence")
            valid_edge = (labels[:-1] >= 0) & (labels[1:] >= 0)
            source = labels[:-1][valid_edge].astype(np.int64)
            destination = labels[1:][valid_edge].astype(np.int64)
            np.add.at(transition_counts, (source, destination), 1.0)
            observed_edges += int(valid_edge.sum())
        self.transition_counts_ = transition_counts
        self.transition_ = transition_counts / transition_counts.sum(axis=1, keepdims=True)
        self.fit_report_ = {
            "seed": self.seed,
            "model": "train-standardized sensor-summary ridge reference baselines",
            "training_windows": int(history.shape[0]),
            "feature_count": int(features.shape[1]),
            "current_labels": int((current >= 0).sum()),
            "future_labels_per_horizon": per_horizon_count.tolist(),
            "complete_outcome_windows": int(complete.sum()),
            "outcome_fit": "complete_windows" if complete.any() else "population_fallback_no_complete_targets",
            "transition_source": transition_source,
            "observed_transition_edges": observed_edges,
            "transition_pseudocount_per_edge": 1.0,
            "duration_min_epochs": self.min_epochs,
            "duration_soft_penalty_per_missing_epoch": self.soft_penalty,
        }
        return self

    def _features(self, batch: dict) -> np.ndarray:
        if not hasattr(self, "feature_median_"):
            raise RuntimeError("fit must be called before predict")
        history = np.asarray(batch["history"])
        raw = summarize_history(history)
        if history.shape[1] != self.history_epochs_:
            raise ValueError("prediction history length must match the training history length")
        imputed = np.where(np.isfinite(raw), raw, self.feature_median_)
        return (imputed - self.feature_mean_) / self.feature_scale_

    def predict(self, batch: dict) -> dict:
        features = self._features(batch)
        n_rows = features.shape[0]
        current_probability = np.clip(
            (features @ self.current_coef_ + self.current_intercept_)[:, 0], 0.0, 1.0
        )
        trajectory = np.clip(
            features @ self.trajectory_coef_ + self.trajectory_intercept_, 0.0, 1.0
        )
        persistence = np.repeat(current_probability[:, None], self.horizon_, axis=1)
        transition = np.empty((n_rows, self.horizon_), dtype=np.float64)
        state_distribution = np.column_stack((1.0 - current_probability, current_probability))
        for step in range(self.horizon_):
            state_distribution = state_distribution @ self.transition_
            transition[:, step] = state_distribution[:, 1]

        def trajectory_result(probability, path=None):
            return {
                "probability": probability,
                "total_minutes": EPOCH_MINUTES * probability.sum(axis=1),
                "path": (probability >= 0.5).astype(np.uint8) if path is None else path,
            }

        result = {
            "population_mean": {
                "probability": None,
                "total_minutes": np.full(n_rows, self.population_total_),
                "path": None,
            },
            "learned_current_persistence": trajectory_result(persistence),
            "transition_matrix": trajectory_result(transition),
            "direct_outcome": {
                "probability": None,
                "total_minutes": np.clip(
                    (features @ self.outcome_coef_ + self.outcome_intercept_)[:, 0],
                    0.0,
                    EPOCH_MINUTES * self.horizon_,
                ),
                "path": None,
            },
            "direct_trajectory": trajectory_result(trajectory),
        }
        for mode in ("soft", "hard"):
            marginal, path = duration_decode(
                trajectory,
                current_probability,
                min_epochs=self.min_epochs,
                mode=mode,
                soft_penalty=self.soft_penalty,
            )
            result[f"direct_trajectory_{mode}"] = trajectory_result(marginal, path)
        return result
