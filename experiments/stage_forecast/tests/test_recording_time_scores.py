import json
import unittest
from types import SimpleNamespace

import numpy as np

from stage_forecast.recording_time_scores import METHODS, render_time, score_time


class RecordingTimeScoreTest(unittest.TestCase):
    def setUp(self):
        target = np.full((6, 60), -1)
        target[:, 59] = [0, 1, 2, 0, -1, 0]
        target[1, 9] = 0
        current = np.array([0, 1, 1, 2, 3, -1])
        self.val = SimpleNamespace(stage=target, current_stage=current, participant=np.array(list("AAABBC")),
                                   night=np.repeat("1", 6), origin_time=np.arange(6))
        self.probs = {name: np.full((6, 60, 4), .25) for name in METHODS}
        for i, label in enumerate((0, 1, 2, 0)):
            observed = .7 if i < 3 else .4
            self.probs["time_transition"][i, 59] = (1 - observed) / 3
            self.probs["time_transition"][i, 59, label] = observed
        self.probs["time_oracle"][~(current >= 0)] = np.nan

    def test_different_support_for_each_lead_and_paired_person_differences(self):
        scores = score_time(self.val, self.probs)
        json.dumps(scores, allow_nan=False)
        self.assertEqual([scores["leads"][key]["overall"]["origins"] for key in ("5", "15", "30")], [1, 0, 4])
        last = scores["leads"]["30"]
        self.assertEqual(last["overall"]["support"], {"Wake": 2, "Light": 1, "Deep": 1, "REM": 0})
        self.assertEqual(last["changed"]["participants"], 2)
        self.assertEqual(last["same"]["participants"], 1)
        self.assertEqual(scores["common_masks"]["30"]["current_unknown_target_known"], 1)
        patient = scores["per_participant"]
        for key, true_probability in (("A", .7), ("B", .4)):
            row = patient[key]["30"]["overall"]
            self.assertAlmostEqual(row["minus_time_only"]["time_transition"], np.log(.25 / true_probability))
        self.assertIsNone(patient["B"]["30"]["same"]["minus_frozen"]["time_transition"])
        self.assertIsNone(patient["C"]["30"]["overall"]["nll"]["time_only"])
        person_mean = (-np.log(.7) - np.log(.4)) / 2
        self.assertAlmostEqual(last["overall"]["nll"]["time_transition"], person_mean)
        self.assertAlmostEqual(last["overall"]["minus_frozen"]["time_transition"], person_mean + np.log(.25))
        self.assertEqual(last["overall"]["minus_frozen"]["time_only"], 0)
        self.assertIn("time_only NLL", render_time(scores))

    def test_shared_both_known_mask_and_valid_forecasts(self):
        # A forecast modification on a target-known, current-unknown row cannot
        # change a wearable comparison, either overall or in the strata.
        before = score_time(self.val, self.probs)
        self.probs["time_transition"][5, 59] = [1., 0., 0., 0.]
        self.assertEqual(before["leads"], score_time(self.val, self.probs)["leads"])
        self.probs["time_transition"][3, 59] = [1., 1., 0., 0.]
        with self.assertRaisesRegex(ValueError, "normalized"):
            score_time(self.val, self.probs)


if __name__ == "__main__":
    unittest.main()
