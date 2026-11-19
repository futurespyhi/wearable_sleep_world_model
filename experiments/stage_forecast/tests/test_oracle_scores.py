import json
import unittest
from types import SimpleNamespace

import numpy as np

from stage_forecast.metrics import NLL_EPS
from stage_forecast.oracle_scores import CONTROLS, score_oracle


class OracleStageScoresTest(unittest.TestCase):
    def setUp(self):
        current = np.array([0, 1, 2, -1, 3, 1, -1])
        stage = np.full((7, 60), -1)
        stage[:, 59] = [0, 1, 3, 2, 0, -1, -1]
        stage[:, 29] = current
        stage[2, 9] = 2
        self.val = SimpleNamespace(stage=stage, current_stage=current, participant=np.array(list("AAAABBC")),
                                   night=np.repeat("1", 7), origin_time=np.arange(7))
        self.p = np.full((7, 4), .1)
        self.p[np.arange(7), np.maximum(0, current)] = .7
        self.matrices = np.tile(.6 * np.eye(4) + .1, (60, 1, 1))
        self.matrices[9] = np.eye(4)
        self.controls = {key: np.full((7, 60, 4), .25) for key in CONTROLS}

    def calculate(self):
        return score_oracle(self.val, self.p, self.matrices, self.controls)

    def test_per_lead_masks_equal_participant_weights_and_paired_deltas(self):
        scores = self.calculate()
        json.dumps(scores, allow_nan=False)
        self.assertEqual([scores["leads"][m]["overall"]["origins"] for m in ("5", "15", "30")], [1, 5, 4])
        self.assertEqual(scores["leads"]["5"]["overall"]["nll"]["oracle"], 0)
        groups = scores["leads"]["30"]
        self.assertEqual(scores["common_masks"]["30"], {"both_known": 4, "current_unknown_target_known": 1,
                                                       "current_known_target_unknown": 1, "both_unknown": 1})
        self.assertEqual(groups["overall"]["support"], {"Wake": 2, "Light": 1, "Deep": 0, "REM": 1})
        a_loss = (-2 * np.log(.7) - np.log(.1)) / 3
        b_loss = -np.log(.1)
        self.assertAlmostEqual(groups["overall"]["nll"]["oracle"], (a_loss + b_loss) / 2)
        self.assertAlmostEqual(groups["same"]["nll"]["oracle"], -np.log(.7))
        self.assertEqual(groups["same"]["participants"], 1)
        self.assertEqual(groups["changed"]["participants"], 2)
        pp = scores["participants_30"]
        for control in CONTROLS:
            self.assertAlmostEqual(pp["A"]["overall"]["oracle_minus"][control], a_loss + np.log(.25))
            self.assertAlmostEqual(pp["B"]["overall"]["oracle_minus"][control], b_loss + np.log(.25))
            self.assertIsNone(pp["C"]["overall"]["oracle_minus"][control])
            self.assertAlmostEqual(scores["paired_mean_check_30"]["overall"][control],
                                   (a_loss + b_loss) / 2 + np.log(.25))
        current = scores["current_stage"]
        self.assertEqual(current["origins"], 5)
        self.assertEqual(current["macro_f1"], 1.)
        self.assertAlmostEqual(current["nll"], -np.log(.7))

    def test_true_current_selects_only_oracle_row_and_empty_strata_have_no_scores(self):
        base = self.calculate()
        self.val.current_stage[0] = 2
        changed = self.calculate()["leads"]["30"]["overall"]
        self.assertGreater(changed["nll"]["oracle"], base["leads"]["30"]["overall"]["nll"]["oracle"])
        for control in CONTROLS:
            self.assertEqual(changed["nll"][control], base["leads"]["30"]["overall"]["nll"][control])
        self.val.current_stage[:] = -1
        scores = self.calculate()
        self.assertIsNone(scores["current_stage"]["macro_f1"])
        self.assertIsNone(scores["current_stage"]["nll"])
        self.assertEqual(scores["leads"]["30"]["overall"]["participants"], 0)
        self.assertIsNone(scores["paired_mean_check_30"]["changed"]["transition"])

    def test_matrix_uses_declared_horizon_and_nll_floor(self):
        # A zero empirical transition at precisely index 9 has the historical NLL floor.
        self.val.stage[2, 9] = 3
        self.assertAlmostEqual(self.calculate()["leads"]["5"]["overall"]["nll"]["oracle"], -np.log(NLL_EPS))
        self.matrices[9, 0, 0] = .5
        with self.assertRaisesRegex(ValueError, "normalized"):
            self.calculate()


if __name__ == "__main__":
    unittest.main()
