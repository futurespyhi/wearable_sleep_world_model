import unittest
from types import SimpleNamespace

import numpy as np

from stage_forecast.transition_scores import METHODS, STEPS, render_scores, score_comparison


class TransitionScoreTests(unittest.TestCase):
    def setUp(self):
        self.labels = np.array([0, 1, 2, 3, 1, -1, 0])
        stage = np.full((7, 60), -1, dtype=int)
        stage[:, STEPS] = self.labels[:, None]
        self.val = SimpleNamespace(
            stage=stage, current_stage=np.array([1, 1, 1, -1, 2, 3, 0]),
            participant=np.array(list("AAAABBB")), night=np.repeat("1", 7), origin_time=np.arange(7),
        )
        self.probs = {arm: np.full((7, 3, 4), .25) for arm in METHODS}

    def test_changed_targets_count_both_known_and_equal_weight_people(self):
        p = self.probs["transition"]
        for row, target in enumerate(self.labels):
            if target < 0:
                continue
            correct = .8 if row < 4 else .4
            p[row, :, :] = (1 - correct) / 3
            p[row, :, target] = correct
        # Reproduce one arm via full 60-lead storage so endpoint indices must match.
        full = np.full((7, 60, 4), .25)
        full[:, STEPS] = p
        self.probs["direct_0"] = full
        scores = score_comparison(self.val, self.probs)
        changed = scores["changed_30"]
        self.assertEqual(changed["origins"], 3)
        self.assertEqual(changed["participants"], 2)
        self.assertEqual(changed["support"], {"Wake": 1, "Light": 1, "Deep": 1, "REM": 0})
        self.assertEqual((changed["both_known"], changed["unchanged"], changed["current_unknown_target_known"]), (5, 2, 1))
        self.assertEqual(scores["coverage"]["30"]["origins"], 6)
        self.assertEqual(scores["coverage"]["30"]["unknown"], 1)
        expected_loss = -(.5 * np.log(.8) + .5 * np.log(.4))
        self.assertAlmostEqual(scores["methods"]["transition"]["changed_30_nll"], expected_loss)
        self.assertAlmostEqual(scores["paired_nll_differences"]["changed_transition_minus_prior_mix"],
                               expected_loss + np.log(.25))
        direct = scores["methods"]["direct_mean"]["leads"]["30"]
        self.assertAlmostEqual(direct["nll"], (expected_loss - 2 * np.log(.25)) / 3)
        self.assertEqual(scores["methods"]["direct_0"]["leads"]["30"]["macro_f1"], 1)
        self.assertIn("3 of 5", render_scores(scores))

    def test_unknown_current_allows_primary_but_missing_classes_and_empty_stratum_are_unavailable(self):
        self.val.current_stage[:] = -1
        self.val.stage[self.labels == 3, :] = -1
        scores = score_comparison(self.val, self.probs)
        self.assertEqual(scores["coverage"]["30"]["origins"], 5)
        self.assertIsNone(scores["methods"]["transition"]["leads"]["30"]["macro_f1"])
        self.assertIsNone(scores["methods"]["transition"]["changed_30_nll"])
        self.assertEqual(scores["changed_30"]["participants"], 0)
        self.assertIsNone(scores["paired_nll_differences"]["changed_transition_minus_prior_mix"])
        self.assertEqual(scores["paired_nll_differences"]["transition_minus_prior_mix"], 0)

    def test_rejects_duplicate_origins_and_invalid_forecasts(self):
        self.val.origin_time[0] = self.val.origin_time[1]
        with self.assertRaisesRegex(ValueError, "unique"):
            score_comparison(self.val, self.probs)
        self.val.origin_time[0] = 0
        self.probs["transition"][2, 1, 0] = -0.2
        with self.assertRaisesRegex(ValueError, "normalized endpoint probabilities"):
            score_comparison(self.val, self.probs)


if __name__ == "__main__":
    unittest.main()
