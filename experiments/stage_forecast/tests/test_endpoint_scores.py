import json
import unittest

import numpy as np

from stage_forecast.endpoint_scores import render_endpoint, score_endpoint
from stage_forecast.metrics import NLL_EPS


class EndpointScoreTests(unittest.TestCase):
    def test_person_weighting_and_omission_reversing_positive_full_result(self):
        # First person's three accurate forecasts must have the same total weight
        # as the second person's inaccurate forecast.
        y = [1, 0, 1, 0]
        arms = {"A": [.5] * 4, "B": [.5] * 4, "C": [.95, .05, .95, .60]}
        score = score_endpoint(y, ["first"] * 3 + ["second"], arms)
        json.dumps(score, allow_nan=False)
        total = score["overall"]
        self.assertEqual((total["origins"], total["positive"], total["negative"]), (4, 2, 2))
        self.assertAlmostEqual(total["methods"]["C"]["nll"], -(np.log(.95) + np.log(.4)) / 2)
        self.assertAlmostEqual(total["methods"]["C"]["brier"], (.05 ** 2 + .6 ** 2) / 2)
        self.assertTrue(score["decision"]["overall_gain"])
        self.assertFalse(score["decision"]["stable_gain"])
        self.assertEqual(score["decision"]["gain_by_omitted_person"], {"first": False, "second": True})
        first_omitted = score["leave_one_out"]["first"]
        self.assertEqual(first_omitted["methods"], score["per_participant"]["second"]["methods"])
        self.assertAlmostEqual(first_omitted["paired_differences"]["C_minus_A"]["brier"], .36 - .25)
        self.assertIn("failed", render_endpoint(score))

    def test_strict_gain_gate_and_single_class_participant(self):
        y = [1, 1, 0]
        arms = {"A": [.25, .25, .75], "B": [.5, .5, .5], "C": [.9, .9, .1]}
        score = score_endpoint(y, ["a", "b", "c"], arms)
        self.assertTrue(score["decision"]["stable_gain"])
        self.assertEqual(score["per_participant"]["a"]["negative"], 0)
        self.assertLess(score["overall"]["paired_differences"]["B_minus_A"]["nll"], 0)
        arms["B"] = list(arms["C"])
        self.assertFalse(score_endpoint(y, ["a", "b", "c"], arms)["decision"]["stable_gain"])

    def test_binary_floor_and_unavailable_or_invalid_inputs(self):
        score = score_endpoint([1, 0], ["p", "p"], dict.fromkeys("ABC", [0., 1.]))
        self.assertAlmostEqual(score["overall"]["methods"]["A"]["nll"], -np.log(NLL_EPS))
        self.assertEqual(score["overall"]["methods"]["A"]["brier"], 1.)
        self.assertIsNone(score["decision"]["stable_gain"])
        self.assertIsNone(score["leave_one_out"]["p"]["methods"]["C"]["nll"])
        with self.assertRaisesRegex(ValueError, "binary"):
            score_endpoint([-1], ["p"], dict.fromkeys("ABC", [.25]))
        with self.assertRaisesRegex(ValueError, "finite"):
            score_endpoint([0], ["p"], dict.fromkeys("ABC", [float("nan")]))


if __name__ == "__main__":
    unittest.main()
