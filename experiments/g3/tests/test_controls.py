"""Check training weights, missing-label policy, and prediction isolation."""

import copy
import json
import unittest

import numpy as np

from sleep_g3.controls import FixedControls
from sleep_g3.metrics import evaluate_forecasts


def batch(target, participant):
    target = np.asarray(target, dtype=np.int8)
    return {
        "history": np.zeros((len(target), 4, 7), dtype=float),
        "target": target,
        "participant": np.asarray(participant),
    }


class FixedControlTests(unittest.TestCase):
    def test_median_balances_people_and_uses_lower_tie(self):
        train = batch([[1, 1]] * 7 + [[0, 0]], ["many"] * 7 + ["one"])
        controls = FixedControls().fit(train)
        result = controls.predict(train)
        np.testing.assert_array_equal(result["population_median"]["total_minutes"], 0.0)
        self.assertEqual(controls.fit_report_["population_median"]["evaluable_training_participants"], 2)

        reverse = batch([[0, 0]] * 7 + [[1, 1]], ["many"] * 7 + ["one"])
        reversed_controls = FixedControls().fit(reverse)
        self.assertEqual(reversed_controls.population_median_, 0.0)

    def test_weighted_median_minimizes_participant_macro_absolute_error(self):
        train = batch([[1, 1, 1, 1]] * 7 + [[1, 0, 0, 0], [0, 0, 0, 0]],
                      ["many"] * 7 + ["short", "none"])
        controls = FixedControls().fit(train)
        self.assertEqual(controls.population_median_, 0.5)
        true_totals = 0.5 * train["target"].sum(axis=1)
        objective = lambda constant: np.mean([
            np.mean(np.abs(true_totals[train["participant"] == pid] - constant))
            for pid in np.unique(train["participant"])
        ])
        self.assertLess(objective(controls.population_median_), objective(2.0))
        self.assertLess(objective(controls.population_median_), objective(0.0))

    def test_probability_balances_people_with_different_label_masks(self):
        train = batch([[1, -1], [1, 0], [1, 0], [0, 1], [-1, -1]],
                      ["many", "many", "many", "one", "unknown"])
        controls = FixedControls().fit(train)
        np.testing.assert_allclose(controls.population_probability_, [0.5, 0.5])
        report = controls.fit_report_
        self.assertEqual(report["population_probability"]["evaluable_training_participants_per_horizon"], [2, 2])
        self.assertEqual(report["population_median"]["complete_training_windows"], 3)
        self.assertEqual(report["population_median"]["evaluable_training_participants"], 2)
        self.assertEqual(report["per_participant"]["unknown"]["known_target_counts_per_horizon"], [0, 0])
        json.dumps(report, allow_nan=False)

    def test_unknown_future_does_not_become_a_complete_zero_total(self):
        train = batch([[1, 1], [0, -1], [0, -1], [0, -1]],
                      ["complete", "partial", "partial", "partial"])
        controls = FixedControls().fit(train)
        self.assertEqual(controls.population_median_, 1.0)
        np.testing.assert_allclose(controls.population_probability_, [0.5, 1.0])
        self.assertEqual(controls.fit_report_["population_probability"]["evaluable_training_participants_per_horizon"], [2, 1])

    def test_missing_horizon_fallback_and_unidentified_median_are_explicit(self):
        train = batch([[1, -1], [1, -1], [0, -1]], ["many", "many", "one"])
        controls = FixedControls().fit(train)
        np.testing.assert_allclose(controls.population_probability_, [0.5, 2 / 3])
        report = controls.fit_report_
        self.assertEqual(report["population_probability"]["fallback_horizon_indices"], [1])
        self.assertAlmostEqual(report["population_probability"]["fallback_prevalence"], 2 / 3)
        self.assertEqual(report["population_median"]["fit"], "expected_total_fallback_no_complete_training_windows")
        self.assertAlmostEqual(controls.population_median_, 7 / 12)
        prediction = controls.predict(train)
        np.testing.assert_allclose(prediction["population_median"]["total_minutes"], 7 / 12)
        json.dumps(report, allow_nan=False)

    def test_predict_never_reads_validation_labels_or_identifiers(self):
        train = batch([[1, 0], [0, 0]], ["a", "b"])
        controls = FixedControls().fit(train)
        report = copy.deepcopy(controls.fit_report_)
        expected = controls.predict({"history": train["history"]})

        class HistoryOnly(dict):
            def __getitem__(self, key):
                if key != "history":
                    raise AssertionError("prediction read non-history field: " + key)
                return super().__getitem__(key)

        poisoned = HistoryOnly(history=np.full((2, 4, 7), np.nan),
                               current=object(), target=object(), participant=object())
        actual = controls.predict(poisoned)
        for name in expected:
            for key in expected[name]:
                if expected[name][key] is None:
                    self.assertIsNone(actual[name][key])
                else:
                    np.testing.assert_array_equal(actual[name][key], expected[name][key])
        self.assertEqual(report, controls.fit_report_)
        actual["population_probability"]["probability"][:] = 0.99
        np.testing.assert_array_equal(controls.predict(poisoned)["population_probability"]["probability"],
                                      expected["population_probability"]["probability"])

    def test_zero_control_is_fixed_and_all_arms_use_metric_schema(self):
        train = batch([[1, 1, 1], [1, 0, 1]], ["a", "b"])
        controls = FixedControls().fit(train)
        result = controls.predict(train)
        self.assertEqual(set(result), {"zero_wake", "population_median", "population_probability"})
        for field in ("total_minutes", "probability", "path"):
            np.testing.assert_array_equal(result["zero_wake"][field], 0)
        self.assertIsNone(result["population_median"]["probability"])
        self.assertIsNone(result["population_median"]["path"])
        np.testing.assert_allclose(result["population_probability"]["total_minutes"],
                                   0.5 * result["population_probability"]["probability"].sum(axis=1))
        self.assertEqual(result["population_probability"]["path"].dtype, np.uint8)
        scored = evaluate_forecasts(train["target"], result, train["participant"])
        json.dumps(scored, allow_nan=False)
        empty = controls.predict({"history": np.empty((0, 4, 7))})
        self.assertEqual(empty["population_probability"]["probability"].shape, (0, 3))

    def test_rejects_unknown_training_targets_and_changed_history_length(self):
        with self.assertRaisesRegex(ValueError, "known training target"):
            FixedControls().fit(batch([[-1, -1]], ["a"]))
        controls = FixedControls().fit(batch([[0, 1]], ["a"]))
        with self.assertRaisesRegex(ValueError, "history length"):
            controls.predict({"history": np.zeros((1, 5, 7))})
        with self.assertRaises(RuntimeError):
            FixedControls().predict({"history": np.zeros((1, 4, 7))})


if __name__ == "__main__":
    unittest.main()
