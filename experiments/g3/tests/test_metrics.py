"""Focused validation of participant weighting, missingness, and Wake runs."""

import json
import math
import unittest

import numpy as np

from sleep_g3.metrics import _match_events, evaluate_forecasts, paired_delta


def arm(total, probability=None, path=None):
    return {"total_minutes": np.asarray(total), "probability": probability, "path": path}


class ForecastMetricsTest(unittest.TestCase):
    def test_unequal_window_counts_have_equal_participant_weight(self):
        target = np.zeros((4, 2), dtype=int)
        receipt = evaluate_forecasts(target, {"a": arm([0, 0, 0, 1], np.array([[0, 0]] * 3 + [[1, 1]]))}, ["many"] * 3 + ["one"])
        result = receipt["arms"]["a"]
        self.assertEqual(result["total_wake"]["mae_minutes"], 0.5)
        self.assertEqual(result["total_wake"]["bias_minutes"], 0.5)
        self.assertEqual(result["probability"]["brier"], 0.5)
        self.assertEqual(result["probability"]["ece"], 0.5)
        self.assertEqual(result["total_wake"]["evaluable_origins"], 4)
        self.assertEqual(result["total_wake"]["evaluable_participants"], 2)

    def test_unknown_labels_use_different_denominators(self):
        target = np.array([[0, 1, 0, 0], [1, -1, -1, -1], [-1, -1, -1, -1]])
        probability = np.array([[0, 1, 0, 0], [0, 0, 0, 0], [1, 1, 1, 1]])
        receipt = evaluate_forecasts(target, {"a": arm([0.5, 2, 2], probability)}, ["p", "p", "unknown"])
        result = receipt["arms"]["a"]
        self.assertEqual(result["total_wake"]["evaluable_origins"], 1)
        self.assertEqual(result["total_wake"]["evaluable_participants"], 1)
        self.assertEqual(result["total_wake"]["mae_minutes"], 0)
        self.assertEqual(result["probability"]["evaluable_origins"], 2)
        self.assertEqual(result["probability"]["valid_epochs"], 5)
        self.assertEqual(result["probability"]["brier"], 0.5)
        self.assertEqual(result["probability"]["ece"], 0.5)
        self.assertIsNone(result["per_participant"]["unknown"]["probability"]["brier"])
        self.assertEqual(receipt["coverage"]["candidate_origins"], 3)
        self.assertEqual(receipt["coverage"]["candidate_participants"], 2)
        json.dumps(receipt, allow_nan=False)

    def test_expected_total_supplied_total_and_hard_map_are_distinct(self):
        target = np.array([[0, 1, 0, 0]])
        receipt = evaluate_forecasts(target, {"a": arm([0.5], np.full((1, 4), 0.2), np.zeros((1, 4)))}, ["p"])
        result = receipt["arms"]["a"]
        self.assertEqual(result["total_wake"]["mae_minutes"], 0)
        self.assertAlmostEqual(result["probability"]["expected_total_wake"]["mae_minutes"], 0.1)
        self.assertEqual(result["hard_map"]["total_wake"]["mae_minutes"], 0.5)

    def test_direct_outcome_has_only_total_metrics(self):
        result = evaluate_forecasts(np.array([[0, 1]]), {"direct": arm([0.5])}, ["p"])["arms"]["direct"]
        self.assertIsNone(result["probability"])
        self.assertIsNone(result["hard_map"])
        self.assertEqual(result["total_wake"]["mae_minutes"], 0)

    def test_short_events_are_not_erased_from_target(self):
        target = np.array([[0, 1, 0, 1, 1, 0, 1, 1, 1, 0]])
        result = evaluate_forecasts(target, {"erased": arm([0], path=np.zeros_like(target)), "retained": arm([3], path=target)}, ["p"])
        erased = result["arms"]["erased"]["hard_map"]["events"]
        retained = result["arms"]["retained"]["hard_map"]["events"]
        self.assertEqual(erased["short_event_instances"], 2)
        self.assertEqual(erased["true_event_instances"], 3)
        self.assertEqual(erased["short_event_recall_macro"], 0)
        self.assertIsNone(erased["event_precision_macro"])
        self.assertEqual(retained["short_event_recall_macro"], 1)
        self.assertEqual(retained["event_precision_pooled"], 1)

    def test_event_matching_maximizes_cardinality_before_iou(self):
        self.assertEqual(set(_match_events([(1, 6), (7, 8)], [(1, 2), (3, 8)])), {(0, 0), (1, 1)})
        target = np.array([[0, 1, 1, 1, 1, 1, 0, 1, 0, 0]])
        path = np.array([[0, 1, 0, 1, 1, 1, 1, 1, 0, 0]])
        events = evaluate_forecasts(target, {"a": arm([3], path=path)}, ["p"])["arms"]["a"]["hard_map"]["events"]
        self.assertEqual(events["matched_event_instances"], 2)
        self.assertEqual(events["short_event_recall_pooled"], 1)
        self.assertEqual(events["false_positive_event_instances"], 0)

    def test_one_predicted_run_cannot_detect_two_events(self):
        target = np.array([[0, 1, 0, 1, 0]])
        path = np.array([[0, 1, 1, 1, 0]])
        result = evaluate_forecasts(target, {"a": arm([1.5], path=path)}, ["p"])["arms"]["a"]["hard_map"]
        self.assertEqual(result["events"]["matched_short_event_instances"], 1)
        self.assertEqual(result["events"]["short_event_recall_pooled"], 0.5)
        self.assertEqual(result["false_wake"]["false_positive_wake_minutes"], 0.5)

    def test_boundary_and_unknown_labels_censor_events(self):
        target = np.array([[1, 0, 1, -1, 1, 0, 0, 1, 0, 1]])
        path = np.array([[1, 0, 1, 0, 1, 0, 0, 1, 0, 1]])
        events = evaluate_forecasts(target, {"a": arm([2.5], path=path)}, ["p"])["arms"]["a"]["hard_map"]["events"]
        self.assertEqual(events["true_event_instances"], 1)
        self.assertEqual(events["short_event_instances"], 1)
        self.assertEqual(events["predicted_event_instances"], 1)
        self.assertEqual(events["censored_true_wake_runs"], 4)
        self.assertEqual(events["unscored_predicted_wake_runs"], 4)
        self.assertEqual(events["short_event_recall_pooled"], 1)

    def test_prediction_inside_censored_true_run_is_not_false_event(self):
        target = np.array([[1, 1, 0, 0, 0]])
        path = np.array([[0, 1, 0, 0, 0]])
        events = evaluate_forecasts(target, {"a": arm([0.5], path=path)}, ["p"])["arms"]["a"]["hard_map"]["events"]
        self.assertEqual(events["predicted_event_instances"], 0)
        self.assertEqual(events["unscored_predicted_wake_runs"], 1)
        self.assertIsNone(events["short_event_recall_macro"])

    def test_event_macro_and_pooled_denominators_and_no_event_people(self):
        target = np.array([[0, 1, 0]] * 4 + [[0, 0, 0]])
        path = np.array([[0, 1, 0]] * 3 + [[0, 0, 0], [0, 1, 0]])
        result = evaluate_forecasts(target, {"a": arm([0.5] * 5, path=path)}, ["many"] * 3 + ["one", "none"])["arms"]["a"]
        events = result["hard_map"]["events"]
        self.assertEqual(events["short_event_recall_macro"], 0.5)
        self.assertEqual(events["short_event_recall_pooled"], 0.75)
        self.assertEqual(events["event_precision_macro"], 0.5)
        self.assertEqual(events["event_precision_pooled"], 0.75)
        self.assertEqual(events["false_positive_event_instances"], 1)
        self.assertEqual(events["participants_with_short_events"], 2)
        self.assertIsNone(result["per_participant"]["none"]["hard_map"]["events"]["short_event_recall"])
        self.assertEqual(events["count_unit"], "window_event_instances")

    def test_false_wake_minutes_mask_unknown_and_balance_origins(self):
        target = np.array([[0, 0, 0, 0], [0, -1, -1, -1], [1, 1, 1, 1]])
        path = np.array([[0, 0, 0, 0], [1, 1, 1, 1], [1, 1, 1, 1]])
        false_wake = evaluate_forecasts(target, {"a": arm([0, 2, 2], path=path)}, ["p", "p", "nosleep"])["arms"]["a"]["hard_map"]["false_wake"]
        self.assertEqual(false_wake["evaluable_origins"], 2)
        self.assertEqual(false_wake["evaluable_participants"], 1)
        self.assertEqual(false_wake["false_positive_wake_minutes"], 0.25)
        self.assertEqual(false_wake["false_positive_wake_minutes_sum"], 0.5)
        self.assertEqual(false_wake["false_positive_wake_fraction"], 0.5)

    def test_exact_probability_endpoints_have_finite_nll(self):
        target = np.array([[0, 1]])
        result = evaluate_forecasts(target, {"a": arm([0.5], np.array([[1, 0]]))}, ["p"])["arms"]["a"]["probability"]
        self.assertTrue(math.isfinite(result["nll"]))
        self.assertGreater(result["nll"], 27)
        self.assertEqual(result["brier"], 1)
        self.assertEqual(result["ece"], 1)

    def test_invalid_probability_rejected_even_at_unknown_labels(self):
        target = np.array([[0, -1]])
        for bad_value in (float("nan"), float("inf"), -0.1, 1.1):
            with self.subTest(value=bad_value), self.assertRaises(ValueError):
                evaluate_forecasts(target, {"a": arm([0], np.array([[0, bad_value]]))}, ["p"])

    def test_invalid_target_path_total_and_shapes(self):
        with self.assertRaises(ValueError):
            evaluate_forecasts(np.array([[0, 2]]), {"a": arm([0])}, ["p"])
        with self.assertRaises(ValueError):
            evaluate_forecasts(np.array([[0, 1]]), {"a": arm([float("nan")])}, ["p"])
        with self.assertRaises(ValueError):
            evaluate_forecasts(np.array([[0, 1]]), {"a": arm([0], path=np.array([[0, 0.5]]))}, ["p"])
        with self.assertRaises(ValueError):
            evaluate_forecasts(np.array([[0, 1]]), {"a": arm([0], np.array([0, 1]))}, ["p"])

    def test_empty_and_short_horizons_have_defined_missing_event_scores(self):
        for target, people in ((np.empty((0, 1), dtype=int), []), (np.array([[0]]), ["p"])):
            result = evaluate_forecasts(target, {"a": arm(np.zeros(len(target)), path=np.zeros_like(target))}, people)
            self.assertIsNone(result["arms"]["a"]["hard_map"]["events"]["short_event_recall_macro"])
            json.dumps(result, allow_nan=False)

    def test_paired_delta_small_sample_and_cluster_bootstrap(self):
        small = evaluate_forecasts(np.zeros((2, 2)), {"a": arm([1, 0]), "b": arm([0, 0])}, ["a", "b"])
        delta = paired_delta(small, "a", "b")
        self.assertEqual(delta["participant_count"], 2)
        self.assertEqual(delta["mean_delta"], 0.5)
        self.assertIsNone(delta["percentile_interval_95"])
        self.assertEqual(delta["interpretation"], "exploratory_not_confirmatory")
        larger = evaluate_forecasts(np.zeros((6, 2)), {"a": arm([0, 0, 0.5, 0.5, 0.5, 0.5]), "b": arm([0] * 6)}, ["a", "a", "b", "c", "d", "e"])
        delta = paired_delta(larger, "a", "b", n_resamples=100, seed=17)
        self.assertEqual(delta["participant_count"], 5)
        self.assertEqual(delta["mean_delta"], 0.4)
        self.assertEqual(delta, paired_delta(larger, "a", "b", n_resamples=100, seed=17))
        self.assertIsNotNone(delta["percentile_interval_95"])


if __name__ == "__main__":
    unittest.main()
