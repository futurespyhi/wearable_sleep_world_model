import unittest
import numpy as np

from sleep_g3.diagnose import reference_summary


class ReferenceSummaryTests(unittest.TestCase):
    def test_repeated_windows_are_one_reference_event(self):
        y = np.array([[0, 0, 1, 0, 0], [0, 1, 0, 0, 0]])
        result = reference_summary(y, np.array(["p", "p"]), np.array(["1", "1"]),
                                   np.array([0, 30]))
        self.assertEqual(result["short_window_event_instances"], 2)
        self.assertEqual(result["unique_short_reference_events_observed_in_windows"], 1)

    def test_unknown_totals_and_distinct_people(self):
        y = np.array([[0, -1, 1, 0, 0], [0, 0, 1, 0, 0], [0, 0, 0, 0, 0]])
        result = reference_summary(y, np.array(["p", "q", "q"]), np.array(["1", "1", "1"]),
                                   np.array([0, 0, 150]))
        self.assertEqual(result["complete_origins"], 2)
        self.assertEqual(result["zero_wake_origins"], 1)
        self.assertEqual(result["unique_short_reference_events_observed_in_windows"], 1)
        self.assertIsNone(result["per_participant"]["p"]["mean_wake_minutes"])


if __name__ == "__main__":
    unittest.main()
