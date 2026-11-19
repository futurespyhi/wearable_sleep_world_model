import unittest

import numpy as np

from stage_forecast.metrics import score_seed, summarize_seeds


class StageMetricsTest(unittest.TestCase):
    def test_equal_participants_endpoint_missing_and_pairing(self):
        target = np.full((5, 60), -1, dtype=int)
        target[:, 9] = (0, 1, 2, 3, 0)
        target[:, 29] = (0, 1, 2, -1, 0)
        explicit = np.broadcast_to(np.eye(4)[1], (5, 60, 4)).copy()
        explicit[:, 9] = np.eye(4)[[0, 1, 2, 3, 1]]
        fusion = explicit.copy()
        fusion[4, 9] = np.eye(4)[0]
        hr = np.full((5, 60), np.nan)
        hr[0, 0] = 70
        prediction_hr = np.full((5, 60), 68)
        result = score_seed(
            target, ["A"] * 4 + ["B"], [1] * 5, [0, 300, 600, 900, 0],
            {"explicit": explicit, "fusion": fusion}, training_target=target,
            future_hr=hr, hr_predictions={"explicit": prediction_hr}, last_hr=[65] * 5,
            contrasts=[("explicit", "fusion")],
        )
        five = result["methods"]["explicit"]["leads"]["5"]
        self.assertEqual(five["support"], {"Wake": 2, "Light": 1, "Deep": 1, "REM": 1})
        self.assertEqual(five["participants"], 2)
        self.assertAlmostEqual(five["wake_recall"], 0.2)
        self.assertAlmostEqual(five["macro_f1"], (1 / 3 + 1 / 3 + 1 + 1) / 4)
        self.assertAlmostEqual(five["normalized_confusion_matrix"][0][1], 0.5)
        self.assertAlmostEqual(five["brier"], 1)
        self.assertAlmostEqual(five["nll"], -0.5 * np.log(1e-12))
        fifteen = result["methods"]["explicit"]["leads"]["15"]
        self.assertIsNone(fifteen["macro_f1"])
        self.assertIsNone(fifteen["f1"]["REM"])
        self.assertEqual(fifteen["f1"]["Wake"], 0.0)
        self.assertEqual(fifteen["unknown"], 1)
        self.assertEqual(result["methods"]["explicit"]["leads"]["30"]["unknown"], 5)
        self.assertEqual(result["methods"]["explicit"]["hr"]["mae_bpm"], 2.0)
        self.assertEqual(result["hr_last_observation"]["mae_bpm"], 5.0)
        five_diff = result["paired_differences"]["explicit_minus_fusion"]["leads"]["5"]
        self.assertAlmostEqual(five_diff["macro_f1"], five["macro_f1"] - 1.0)
        combined = summarize_seeds({0: result, 1: result})
        pair = combined["paired_differences"]["explicit_minus_fusion"]["leads"]
        self.assertEqual(pair["5"]["macro_f1"]["negative_seeds"], 2)
        self.assertEqual(pair["15"]["macro_f1"]["seeds_evaluated"], 0)

    def test_wake_matching_threshold_and_absolute_event_deduplication(self):
        target = np.ones((2, 60), dtype=int)
        target[0, 12] = target[1, 2] = 0
        probabilities = np.broadcast_to(np.eye(4)[1], (2, 60, 4)).copy()
        probabilities[0, 12] = [0.5, 0.5, 0, 0]
        probabilities[1, 2] = [0.49, 0.51, 0, 0]
        training = np.ones((3, 60), dtype=int)
        training[:2] = 0
        result = score_seed(
            target, ["A", "A"], [1, 1], [0, 300], {"explicit": probabilities},
            training_target=training, training_participant=["A", "A", "B"],
        )
        method = result["methods"]["explicit"]
        wake = method["short_wake_events"]["1_epoch"]
        self.assertEqual(wake["unique_reference_events"], 1)
        self.assertEqual(wake["evaluable_event_origin_instances"], 2)
        self.assertEqual(wake["events_with_multiple_evaluable_origins"], 1)
        self.assertEqual(wake["unique_event_recall_any_origin"], 1.0)
        self.assertEqual(wake["participant_macro_event_origin_hit_rate"], 0.5)
        self.assertAlmostEqual(method["wake_minutes"]["mean_expected_minutes"], 0.2475)
        self.assertEqual(result["wake_minute_controls"]["training_median"]["constant_minutes"], 0.0)


if __name__ == "__main__":
    unittest.main()
