from dataclasses import replace
from types import SimpleNamespace
import unittest

import numpy as np

from stage_forecast.baselines import fit_persistence, predict_persistence
from stage_forecast.data import StageWindows, fit_standardizer
from stage_forecast.endpoint_features import prepare_posteriors, recent_features


class EndpointFeatureTests(unittest.TestCase):
    def test_recent_summaries_use_only_valid_epochs_and_preceding_disjoint_window(self):
        raw = np.ones((3, 60, 6))
        raw[..., 2] = 2
        raw[..., 5] = 2
        raw[:, :50, 0] = 60
        raw[:, 50:, 0] = 72
        raw[:, :50, 4] = 2
        raw[:, 50:, 4] = 3
        raw[0, 49, [0, 4]] = [1000, 500]
        raw[0, 49, [2, 5]] = 0
        raw[0, 50, [0, 4]] = [1000, 500]
        raw[0, 50, [2, 5]] = [0, 1]
        raw[1, :50, 5] = 0
        raw[2, 50:, 2] = 0
        expected = [[72, 3, 12, 1], [72, 3, 12, np.nan], [np.nan, 3, np.nan, 1]]
        np.testing.assert_allclose(recent_features(raw), expected, equal_nan=True)

    def test_held_person_predictions_match_an_independent_fit_and_frozen_check_detects_drift(self):
        rng = np.random.default_rng(7)
        persons = np.repeat(["A", "B", "C"], 8)
        n = len(persons)
        history = rng.normal(size=(n, 60, 6))
        history[..., [2, 5]] = 4
        current = np.tile(np.arange(4), 6)
        train = StageWindows(history, np.tile(current[:, None], (1, 60)), np.ones((n,60)),
                             np.ones((n,60), bool), current, persons, np.full(n, "1"),
                             np.tile(np.arange(1,9)*60, 3), np.tile(np.arange(1,9)*1800., 3))
        val = SimpleNamespace(history=history[:3].copy(), participant=np.full(3, "D"))

        def refit(data, held_history):
            scaler = fit_standardizer(data)
            hr, acc = scaler.transform(data.history)
            fitted = fit_persistence(hr, acc, data.current_stage)
            return predict_persistence(fitted, *scaler.transform(held_history))[:, 0, :]

        saved = refit(train, val.history)
        oof, checked, metadata = prepare_posteriors(train, val, saved)
        self.assertTrue(metadata["validation_pt_exact"])
        np.testing.assert_array_equal(saved, checked)
        selected = persons != "A"
        fold = replace(train, **{key: value[selected] for key, value in vars(train).items()})
        np.testing.assert_array_equal(oof[~selected], refit(fold, train.history[~selected]))
        self.assertEqual(len(metadata["oof_folds"]), 3)
        with self.assertRaisesRegex(ValueError, "frozen validation posterior"):
            prepare_posteriors(train, val, saved[:, ::-1])


if __name__ == "__main__":
    unittest.main()
