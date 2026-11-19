import unittest
import numpy as np
from stage_forecast.transition_inputs import make_predictions


class TransitionPredictionTests(unittest.TestCase):
    def test_horizon_weights_and_asymmetric_transition_orientation(self):
        pt = np.array([[0.1, 0.2, 0.3, 0.4], [0.42, 0.18, 0.08, 0.32]])
        priors = np.full((2, 60, 4), 0.25)
        direct = {f"direct_{s}": priors.copy() for s in range(3)}
        weights = np.linspace(0, 1, 60)
        matrices = np.tile(np.eye(4), (60, 1, 1))
        matrices[-1] = np.roll(np.eye(4), 1, axis=1)
        pred = make_predictions(pt, priors, direct, weights, matrices)
        np.testing.assert_allclose(pred["persistence"][:, -1], pt)
        np.testing.assert_allclose(pred["prior_mix"][:, 0], pt)
        np.testing.assert_allclose(pred["prior_mix"][:, -1], priors[:, -1])
        np.testing.assert_allclose(pred["transition"][:, 0], pt)
        np.testing.assert_allclose(pred["transition"][:, -1], np.roll(pt, 1, axis=1))
