"""Training-only fixed controls for participant-balanced Wake evaluation."""

from fractions import Fraction

import numpy as np

from .models import EPOCH_MINUTES


class FixedControls:
    """Fit fixed constants; prediction reads only the history array's shape.

    Complete training windows have equal weight within each participant for
    the lower weighted median. For each forecast horizon, the probability
    control averages known labels within a participant, then participants.
    A horizon without any known label uses the pooled known training-label
    prevalence. With no complete training window, the unidentifiable median
    explicitly falls back to the probability control's expected total.
    """

    @staticmethod
    def _history_shape(batch):
        history = np.asarray(batch["history"])
        if history.ndim != 3 or history.shape[1] < 1 or history.shape[2] != 7:
            raise ValueError("history must have shape [N, H, 7] with H >= 1")
        return history.shape

    def fit(self, train):
        n_rows, history_epochs, _ = self._history_shape(train)
        target = np.asarray(train["target"], dtype=float)
        if target.ndim != 2 or target.shape[0] != n_rows or target.shape[1] < 1:
            raise ValueError("target must have shape [N, T] with T >= 1")
        if not np.isin(target, (-1, 0, 1)).all():
            raise ValueError("training labels must use -1, 0, or 1")
        participant = np.asarray(train["participant"])
        if participant.ndim != 1 or len(participant) != n_rows:
            raise ValueError("participant must have shape [N]")
        for value in participant:
            if value is None or (
                isinstance(value, (float, np.floating)) and not np.isfinite(value)
            ) or not str(value).strip():
                raise ValueError("training participant identifiers must be nonmissing")
        participant = participant.astype(str)
        known = target >= 0
        if not known.any():
            raise ValueError("at least one known training target label is required")

        complete = known.all(axis=1)
        wake_counts = np.sum(target == 1, axis=1)
        horizon = target.shape[1]
        prevalence = float(target[known].mean())
        probability_sum = np.zeros(horizon, dtype=float)
        probability_people = np.zeros(horizon, dtype=np.int64)
        median_mass = {}
        median_people = 0
        people_report = {}
        for pid in np.unique(participant):
            selected = participant == pid
            counts = known[selected].sum(axis=0)
            observed = counts > 0
            probability_sum += np.divide(
                np.where(known[selected], target[selected], 0.0).sum(axis=0),
                counts,
                out=np.zeros(horizon, dtype=float),
                where=observed,
            )
            probability_people += observed
            person_complete = selected & complete
            n_complete = int(person_complete.sum())
            if n_complete:
                median_people += 1
                values, frequencies = np.unique(
                    wake_counts[person_complete], return_counts=True
                )
                for value, frequency in zip(values, frequencies):
                    value = int(value)
                    median_mass[value] = median_mass.get(value, Fraction(0)) + Fraction(
                        int(frequency), n_complete
                    )
            people_report[str(pid)] = {
                "training_windows": int(selected.sum()),
                "complete_training_windows": n_complete,
                "known_target_counts_per_horizon": counts.tolist(),
            }

        probability = np.divide(
            probability_sum,
            probability_people,
            out=np.full(horizon, prevalence),
            where=probability_people > 0,
        )
        expected_total = float(EPOCH_MINUTES * probability.sum())
        median_total = expected_total
        median_fit = "expected_total_fallback_no_complete_training_windows"
        if median_people:
            # Exact rational masses keep a 50% tie at the lower valid median.
            cumulative = Fraction(0)
            for value, mass in sorted(median_mass.items()):
                cumulative += mass
                if cumulative >= Fraction(median_people, 2):
                    median_total = float(EPOCH_MINUTES * value)
                    break
            median_fit = "participant_balanced_lower_weighted_median"

        self.history_epochs_ = history_epochs
        self.horizon_ = horizon
        self.population_median_ = median_total
        self.population_probability_ = probability
        self.fit_report_ = {
            "model": "training-only fixed reference controls",
            "training_windows": n_rows,
            "training_participants": len(people_report),
            "epoch_minutes": EPOCH_MINUTES,
            "probability_threshold": 0.5,
            "zero_wake": {"fit": "none", "total_minutes": 0.0},
            "population_median": {
                "fit": median_fit,
                "weighting": "equal_participants_then_equal_complete_windows",
                "complete_training_windows": int(complete.sum()),
                "evaluable_training_participants": median_people,
                "total_minutes": median_total,
            },
            "population_probability": {
                "fit": "per_horizon_participant_mean_of_known_training_labels",
                "weighting": "equal_participants_with_labels_at_each_horizon",
                "evaluable_training_participants_per_horizon": probability_people.tolist(),
                "probability": probability.tolist(),
                "expected_total_minutes": expected_total,
                "missing_horizon_fallback": "pooled_known_training_target_prevalence",
                "fallback_prevalence": prevalence,
                "fallback_horizon_indices": np.flatnonzero(probability_people == 0).tolist(),
            },
            "per_participant": people_report,
        }
        return self

    def predict(self, batch):
        if not hasattr(self, "population_probability_"):
            raise RuntimeError("fit must be called before predict")
        n_rows, history_epochs, _ = self._history_shape(batch)
        if history_epochs != self.history_epochs_:
            raise ValueError("prediction history length must match the training history length")
        probability = np.broadcast_to(
            self.population_probability_, (n_rows, self.horizon_)
        ).copy()
        return {
            "zero_wake": {
                "probability": np.zeros((n_rows, self.horizon_), dtype=float),
                "total_minutes": np.zeros(n_rows, dtype=float),
                "path": np.zeros((n_rows, self.horizon_), dtype=np.uint8),
            },
            "population_median": {
                "probability": None,
                "total_minutes": np.full(n_rows, self.population_median_),
                "path": None,
            },
            "population_probability": {
                "probability": probability,
                "total_minutes": EPOCH_MINUTES * probability.sum(axis=1),
                "path": (probability >= 0.5).astype(np.uint8),
            },
        }
