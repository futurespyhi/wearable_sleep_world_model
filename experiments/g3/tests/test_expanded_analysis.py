import unittest

import numpy as np

from sleep_g3.expanded_analysis import night_balanced_totals, unique_event_scores


class ExpandedAnalysisTests(unittest.TestCase):
    def test_equal_night_weight_is_distinct_from_equal_origin_weight(self):
        target = np.zeros((4, 4), dtype=int)
        score = night_balanced_totals(target, np.array([0., 0., 4., 6.]),
                                      np.array(["a", "a", "a", "b"]), np.array(["1", "1", "2", "1"]))
        self.assertEqual(score["per_participant"]["a"]["mae_minutes"], 2.)
        self.assertEqual(score["mae_minutes"], 4.)

    def test_duplicate_origins_are_rates_not_any_hit(self):
        target = np.array([[0, 0, 1, 0, 0], [0, 1, 0, 0, 0]])
        arms = {"a": {"path": np.array([[0, 0, 1, 0, 0], [0, 0, 0, 0, 0]])}}
        score = unique_event_scores(target, arms, np.array(["p", "p"]), np.array(["1", "1"]), np.array([0., 30.]))
        result = score["arms"]["a"]
        self.assertEqual(len(result["events"]), 1)
        self.assertEqual(result["events"][0]["evaluable_origins"], 2)
        self.assertEqual(result["strata"]["1_epoch"]["event_then_participant_macro_origin_hit_rate"], .5)

    def test_overlap_hit_does_not_claim_duration_preserved(self):
        target = np.array([[0, 0, 1, 0, 0]])
        arms = {"a": {"path": np.array([[0, 1, 1, 0, 0]])}}
        event = unique_event_scores(target, arms, np.array(["p"]), np.array(["1"]), np.array([0.]))["arms"]["a"]["events"][0]
        self.assertEqual(event["origin_hit_rate"], 1.)
        self.assertEqual(event["mean_matched_iou"], .5)
        self.assertEqual(event["mean_matched_duration_error_seconds"], 30.)

    def test_unknown_or_boundary_events_are_not_made_complete(self):
        target = np.array([[1, 0, -1, 1, 0]])
        score = unique_event_scores(target, {"a": {"path": target == 1}}, np.array(["p"]), np.array(["1"]), np.array([0.]))
        self.assertEqual(score["arms"]["a"]["strata"]["all_short"]["unique_reference_events"], 0)


if __name__ == "__main__":
    unittest.main()
