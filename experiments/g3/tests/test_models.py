"""Leakage and exact-inference checks for the lightweight research baselines."""

import itertools
import unittest

import numpy as np

from sleep_g3.models import BaselineSuite, duration_decode, summarize_history


def enumerate_duration(probability, current_probability, minimum, mode, penalty):
    records = []
    for initial in (0, 1):
        initial_weight = current_probability if initial else 1 - current_probability
        for path in itertools.product((0, 1), repeat=len(probability)):
            weight = initial_weight
            state, age = initial, minimum
            for label, p in zip(path, probability):
                weight *= p if label else 1 - p
                if label != state:
                    if age < minimum:
                        weight *= 0 if mode == "hard" else np.exp(-penalty * (minimum - age))
                    state, age = label, 1
                else:
                    age = min(age + 1, minimum)
            records.append((np.asarray(path), weight))
    normalizer = sum(weight for _, weight in records)
    marginal = sum(path * weight for path, weight in records) / normalizer
    best_path, _ = max(records, key=lambda record: record[1])
    return marginal, best_path


class DurationDecodeTests(unittest.TestCase):
    def test_forward_backward_and_viterbi_match_exhaustive_enumeration(self):
        probabilities = np.array([[0.19, 0.81, 0.27, 0.64], [0.7, 0.2, 0.3, 0.8]])
        current = np.array([0.37, 0.88])
        for minimum in (2, 3):
            for mode in ("soft", "hard"):
                with self.subTest(minimum=minimum, mode=mode):
                    marginal, path = duration_decode(probabilities, current, minimum, mode, 0.7)
                    for row in range(len(probabilities)):
                        expected, expected_path = enumerate_duration(
                            probabilities[row], current[row], minimum, mode, 0.7
                        )
                        np.testing.assert_allclose(marginal[row], expected, atol=1e-12)
                        np.testing.assert_array_equal(path[row], expected_path)

    def test_minimum_one_and_none_preserve_probabilities_exactly(self):
        probability = np.array([[0.0, 0.37, 0.5, 1.0]])
        for mode, minimum in (("hard", 1), ("soft", 1), ("none", 3)):
            marginal, path = duration_decode(probability, np.array([0.01]), minimum, mode)
            np.testing.assert_array_equal(marginal, probability)
            np.testing.assert_array_equal(path, probability >= 0.5)

    def test_zero_soft_penalty_preserves_independent_forecast(self):
        probability = np.array([[0.1, 0.9, 0.2, 0.8]])
        marginal, path = duration_decode(probability, np.array([0.99]), 3, "soft", 0)
        np.testing.assert_array_equal(marginal, probability)
        np.testing.assert_array_equal(path, probability >= 0.5)

    def test_hard_map_has_no_short_interior_runs(self):
        rng = np.random.default_rng(4)
        probability = rng.uniform(0.01, 0.99, (20, 24))
        for minimum in (2, 3, 5):
            _, paths = duration_decode(probability, rng.uniform(size=20), minimum, "hard")
            for path in paths:
                boundaries = np.r_[0, np.flatnonzero(path[1:] != path[:-1]) + 1, len(path)]
                lengths = np.diff(boundaries)
                self.assertTrue(np.all(lengths[1:-1] >= minimum))

    def test_initial_and_final_runs_are_censored(self):
        probability = np.array([[0.01, 0.99, 0.99], [0.01, 0.01, 0.99]])
        _, path = duration_decode(probability, np.zeros(2), 3, "hard")
        np.testing.assert_array_equal(path, [[0, 1, 1], [0, 0, 1]])

    def test_hard_removes_short_interior_burst(self):
        probability = np.array([[0.999, 0.1, 0.999]])
        _, hard = duration_decode(probability, np.ones(1), 3, "hard")
        _, soft = duration_decode(probability, np.ones(1), 3, "soft", 0.1)
        np.testing.assert_array_equal(hard, [[1, 1, 1]])
        np.testing.assert_array_equal(soft, [[1, 0, 1]])

    def test_empty_batch_and_degenerate_probabilities(self):
        probability = np.empty((0, 5))
        marginal, path = duration_decode(probability, np.empty(0))
        self.assertEqual(marginal.shape, (0, 5))
        self.assertEqual(path.dtype, np.uint8)
        marginal, _ = duration_decode(np.array([[0.0, 1.0, 0.0]]), np.zeros(1), 3)
        self.assertTrue(np.isfinite(marginal).all())
        self.assertTrue(((marginal >= 0) & (marginal <= 1)).all())


def synthetic_batch(n_rows=48, history_epochs=12, horizon=6):
    rng = np.random.default_rng(12)
    history = rng.normal(size=(n_rows, history_epochs, 7))
    history[:, :, 0] = 60 + 10 * history[:, :, 0]
    history[:, :, 5:] = rng.integers(1, 40, size=(n_rows, history_epochs, 2))
    current = (history[:, -1, 0] > 60).astype(np.int8)
    target = np.repeat(current[:, None], horizon, axis=1)
    flips = rng.uniform(size=target.shape) < 0.15
    target[flips] = 1 - target[flips]
    return {
        "history": history,
        "target": target,
        "current": current,
        "participant": np.array([f"participant_{row // 12}" for row in range(n_rows)]),
    }


class BaselineSuiteTests(unittest.TestCase):
    def setUp(self):
        self.train = synthetic_batch()
        self.suite = BaselineSuite().fit(self.train)

    def assert_predictions_equal(self, first, second):
        self.assertEqual(first.keys(), second.keys())
        for name in first:
            for key in ("probability", "total_minutes", "path"):
                if first[name][key] is None:
                    self.assertIsNone(second[name][key])
                else:
                    np.testing.assert_array_equal(first[name][key], second[name][key])

    def test_predict_ignores_future_and_current_psg_labels(self):
        baseline = self.suite.predict(self.train)
        poisoned = dict(self.train)
        poisoned["target"] = 1 - self.train["target"]
        poisoned["current"] = 1 - self.train["current"]
        poisoned["participant"] = np.array(["other"] * len(self.train["history"]))
        self.assert_predictions_equal(baseline, self.suite.predict(poisoned))
        self.assert_predictions_equal(baseline, self.suite.predict({"history": self.train["history"]}))

    def test_prediction_never_refits_normalization_or_coefficients(self):
        names = (
            "feature_median_", "feature_mean_", "feature_scale_", "current_coef_",
            "trajectory_coef_", "outcome_coef_", "transition_",
        )
        before = {name: getattr(self.suite, name).copy() for name in names}
        extreme = self.train["history"].copy()
        extreme[:, :, :5] *= 1e5
        extreme[:3, :, :2] = np.nan
        self.suite.predict({"history": extreme})
        for name, expected in before.items():
            np.testing.assert_array_equal(getattr(self.suite, name), expected)

    def test_arm_shapes_ranges_and_expected_totals(self):
        result = self.suite.predict(self.train)
        self.assertEqual(len(result), 7)
        for arm in result.values():
            self.assertEqual(arm["total_minutes"].shape, (48,))
            self.assertTrue(np.isfinite(arm["total_minutes"]).all())
            if arm["probability"] is not None:
                self.assertEqual(arm["probability"].shape, (48, 6))
                self.assertEqual(arm["path"].dtype, np.uint8)
                np.testing.assert_allclose(arm["total_minutes"], 0.5 * arm["probability"].sum(axis=1))
                self.assertTrue(((arm["probability"] >= 0) & (arm["probability"] <= 1)).all())

    def test_all_duration_arms_share_same_fit(self):
        suite = BaselineSuite(min_epochs=1).fit(self.train)
        result = suite.predict(self.train)
        for name in ("direct_trajectory_soft", "direct_trajectory_hard"):
            np.testing.assert_array_equal(
                result[name]["probability"], result["direct_trajectory"]["probability"]
            )

    def test_transition_counts_do_not_bridge_unknown_labels(self):
        episodes = [np.array([0, 0, -1, 1, 1, 0]), np.array([1, 0, 1])]
        suite = BaselineSuite().fit(self.train, episodes)
        np.testing.assert_array_equal(suite.transition_counts_, [[2, 2], [3, 2]])
        self.assertEqual(suite.fit_report_["observed_transition_edges"], 5)
        self.assertEqual(suite.fit_report_["transition_source"], "training_episodes")

    def test_transition_rejects_named_heldout_participant(self):
        with self.assertRaisesRegex(ValueError, "outside training"):
            BaselineSuite().fit(self.train, [{"participant": "heldout", "labels": [0, 1]}])

    def test_unknown_targets_are_not_sleep_or_complete_outcomes(self):
        train = synthetic_batch()
        train["target"][:] = -1
        train["target"][:, :2] = 1
        suite = BaselineSuite().fit(train)
        self.assertEqual(suite.fit_report_["complete_outcome_windows"], 0)
        self.assertEqual(suite.fit_report_["outcome_fit"], "population_fallback_no_complete_targets")
        np.testing.assert_allclose(suite.predict(train)["population_mean"]["total_minutes"], 3.0)
        np.testing.assert_allclose(suite.predict(train)["direct_trajectory"]["probability"], 1.0)

    def test_missing_modalities_are_imputed_without_warnings(self):
        train = synthetic_batch()
        train["history"][:, :, :2] = np.nan
        train["history"][:, :, 5] = 0
        with np.errstate(all="raise"):
            suite = BaselineSuite().fit(train)
            result = suite.predict(train)
        self.assertTrue(np.isfinite(result["direct_trajectory_hard"]["total_minutes"]).all())

    def test_zero_count_masks_unobserved_sensor_values(self):
        history = self.train["history"].copy()
        history[:, :3, 5:] = 0
        first = summarize_history(history)
        history[:, :3, :5] = 1e8
        np.testing.assert_array_equal(first, summarize_history(history))

    def test_predict_rejects_changed_history_length(self):
        with self.assertRaisesRegex(ValueError, "history length"):
            self.suite.predict({"history": self.train["history"][:, :-1]})


if __name__ == "__main__":
    unittest.main()
