from types import SimpleNamespace
import unittest

import numpy as np

from stage_forecast.endpoint_models import fit_endpoint_models


def inputs():
    n = 32
    labels = np.zeros((n, 60), dtype=int)
    i = np.arange(n)
    labels[:, 9] = i % 2
    labels[:, 29] = (i // 2) % 2
    labels[:, 59] = 1 - i % 2
    current = np.zeros(n, dtype=int)
    current[-2] = -1
    labels[-1, :] = -1
    train = SimpleNamespace(current_stage=current, stage=labels)
    bins = (i // 8)
    p_t = np.tile([0.2, 0.3, 0.3, 0.2], (n, 1))
    sensors = np.column_stack((i % 2, np.full(n, np.nan), i, np.ones(n))).astype(float)
    sensors[-2:, 0] = 1000
    return train, bins, p_t, sensors


class EndpointModelTests(unittest.TestCase):
    def test_endpoint_polarity_and_exclusion_of_unknown_labels(self):
        train, bins, p_t, sensors = inputs()
        features = np.array([[0, np.nan, 14.5, 1], [1, np.nan, 14.5, 1]])
        pred, details = fit_endpoint_models(train, bins, [0, 0], p_t, p_t[:2], sensors, features)
        self.assertEqual(details["lead_minutes"], [5, 15, 30])
        for minute in ("5", "15", "30"):
            fit = details["leads"][minute]
            self.assertEqual(fit["known"], 30)
            self.assertEqual(fit["excluded"], 2)
            self.assertEqual([len(fit["arms"][a]["slopes"]) for a in "ABC"], [4, 8, 12])
            self.assertAlmostEqual(fit["arms"]["C"]["center"][8], 0.5)
            self.assertEqual(fit["arms"]["C"]["finite_training_counts"][9], 0)
        for arm in ("A", "B"):
            np.testing.assert_array_equal(pred[arm][0], pred[arm][1])
        self.assertGreater(pred["C"][1, 0], pred["C"][0, 0])
        self.assertLess(pred["C"][1, 2], pred["C"][0, 2])

    def test_validation_cannot_affect_fit_and_missing_uses_training_mean(self):
        train, bins, p_t, sensors = inputs()
        reference = np.array([[0.5, np.nan, 14.5, 1.]])
        missing = np.full((1, 4), np.nan)
        _, fit0 = fit_endpoint_models(train, bins, [0], p_t, p_t[:1], sensors, reference)
        old, fit1 = fit_endpoint_models(train, bins, [0, 2], p_t, p_t[:2], sensors,
                                       np.concatenate((reference, 1e4 + reference)))
        new, fit2 = fit_endpoint_models(train, bins, [0], p_t, p_t[:1], sensors, missing)
        self.assertEqual(fit0, fit1)
        self.assertEqual(fit0, fit2)
        np.testing.assert_allclose(new["C"][0], old["C"][0], rtol=0, atol=1e-14)
