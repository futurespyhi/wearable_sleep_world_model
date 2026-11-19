import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import json

import numpy as np

from stage_forecast.metrics import score_seed, summarize_seeds
from stage_forecast.reporting import (
    METHODS, EXPANDED_CONTRASTS, score_expanded_seed, write_expanded_summary,
)


class StageMetricsTest(unittest.TestCase):
    def test_expanded_scores_use_same_predictions_and_gate_on_all_three_seeds(self):
        # Only the low-coverage history of the first person differs between
        # arms. The same cutoff epoch for the second person must stay included.
        people = np.array(["A", "A", "A", "B", "B"])
        cutoff = np.array([60, 70, 80, 60, 70])
        stage = np.full((5, 60), -1, dtype=int)
        stage[:, 59] = [3, 0, 1, 2, 3]
        val = SimpleNamespace(participant=people, night=np.repeat("1", 5), origin=cutoff, stage=stage)
        good = np.tile(np.array([0., 1., 0., 0.]), (5, 60, 1))
        good[:, 59] = np.eye(4)[stage[:, 59]]
        other = good.copy()
        other[0, 59] = np.eye(4)[0]
        probs = {arm: good if arm == "explicit" else other for arm in METHODS}
        audit = {"cache_identity_sha256": "example", "nights": [
            {"partition": "validation", "participant": "A", "night": "1",
             "mask_coverage": {"epochs": [0], "retained_origins": [60]}}
        ]}
        scored = score_seed(stage, people, val.night, cutoff * 30, probs, training_target=stage,
                            contrasts=EXPANDED_CONTRASTS)
        scored["fit"] = {}
        with TemporaryDirectory() as tmp:
            out = Path(tmp)
            scored["expanded"] = score_expanded_seed(val, probs, audit=audit, participant_output=out/"per_person.json")
            self.assertEqual(scored["expanded"]["restricted_primary_delta"], 0)
            self.assertEqual(scored["expanded"]["restricted_at_30"]["fusion"]["origins"], 4)
            self.assertEqual(set(json.loads((out/"per_person.json").read_text())), {"A", "B"})
            scores = {s: scored for s in (0, 1, 2)}
            aggregate = summarize_seeds(scores)
            write_expanded_summary(out, scores, aggregate)
            main = aggregate["expanded"]
            self.assertIs(main["advance_explicit"], True)
            self.assertGreater(main["primary"]["min_delta"], 0)
            self.assertEqual(main["restricted_primary"]["mean_delta"], 0)
            self.assertEqual(main["restricted_30_min_support"], dict.fromkeys(("Wake", "Light", "Deep", "REM"), 1))
            self.assertIn("Advance the explicit", (out/"results.md").read_text())
            # Missing seed evidence, a tied F1 seed, or worse calibration must
            # never independently satisfy all three progression criteria.
            partial = {0: scored}
            partial_aggregate = summarize_seeds(partial)
            write_expanded_summary(out, partial, partial_aggregate)
            self.assertIsNone(partial_aggregate["expanded"]["advance_explicit"])
            pair = aggregate["paired_differences"]["explicit_minus_fusion"]
            pair["leads"]["30"]["macro_f1"]["positive_seeds"] = 2
            write_expanded_summary(out, scores, aggregate)
            self.assertIs(aggregate["expanded"]["advance_explicit"], False)
            pair["leads"]["30"]["macro_f1"]["positive_seeds"] = 3
            pair["nll"]["mean_delta"] = 0.001
            write_expanded_summary(out, scores, aggregate)
            self.assertIs(aggregate["expanded"]["advance_explicit"], False)
            audit["nights"][0]["mask_coverage"]["retained_origins"] = [90]
            with self.assertRaisesRegex(ValueError, "missing from predictions"):
                score_expanded_seed(val, probs, audit=audit, participant_output=out/"per_person.json")

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
