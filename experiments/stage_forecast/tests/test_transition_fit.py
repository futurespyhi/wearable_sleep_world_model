from dataclasses import replace
import json
import unittest
from unittest.mock import patch

import numpy as np

from stage_forecast import transition_fit as controls
from stage_forecast.data import StageWindows


def _synthetic_train():
    # Every person has a separate history and at least two possible current stages.
    rng = np.random.default_rng(13)
    participant = np.repeat(["p0", "p1", "p2"], 6)
    n = len(participant)
    current = np.tile([0, 1, 1, 2, 1, 3], 3)
    stage = (current[:, None] + np.arange(60)[None, :] // 15) % 4
    stage[0::3, -1] = -1
    history = rng.normal(size=(n, 60, 6))
    history[..., 2] = 3
    history[..., 5] = 9
    origin = np.tile(np.arange(1, 7) * 60, 3)
    return StageWindows(history, stage, np.ones((n, 60)), np.ones((n, 60), dtype=bool),
                        current, participant, np.full(n, "1"), origin, origin.astype(float) * 30)


class TransitionFitTests(unittest.TestCase):
    def test_per_lead_transition_uses_known_pairs_only_and_restores_missing_rows(self):
        current = np.array([0, 0, 1, -1, 2])
        future = np.full((5, 60), -1)
        future[:, 0] = [0, 2, 1, 3, -1]
        future[:, 1] = [1, 1, 3, -1, 0]
        matrix, details = controls._fit_transition(current, future)
        self.assertEqual(matrix.shape, (60, 4, 4))
        np.testing.assert_array_equal(matrix[0, 0], [.5, 0, .5, 0])
        np.testing.assert_array_equal(matrix[0, 1], [0, 1, 0, 0])
        np.testing.assert_array_equal(matrix[0, 2], [.25, .25, .25, .25])
        np.testing.assert_array_equal(matrix[1, 0], [0, 1, 0, 0])
        self.assertEqual(details["current_support"][0], [2, 1, 0, 0])
        np.testing.assert_allclose(matrix.sum(axis=-1), 1.)
        self.assertTrue(np.all(matrix >= 0.))

    def test_equal_participant_nll_independent_of_subject_origin_count(self):
        # The person with 9 origins always favors persistence, while the other
        # person favors the prior by an equal amount. The balanced optimum is 1/2.
        persons = np.array(["a"] * 9 + ["b"])
        future = np.full((10, 60), -1)
        future[:, 0] = 0
        future[:9, 1] = 0
        future[9:, 2] = 0
        p0 = np.array([.9] * 9 + [.1])
        posterior = np.column_stack([p0, 1-p0, np.zeros((10, 2))])
        priors = np.repeat(posterior[:, [1, 0, 2, 3]][:, None, :], 60, axis=1)
        alpha, metadata = controls._fit_weights(future, persons, posterior, priors)
        self.assertAlmostEqual(alpha[0], .5, places=6)
        self.assertEqual(alpha[1], 0.)
        self.assertEqual(alpha[2], 1.)
        self.assertEqual(metadata["participants"][:4], [2, 1, 1, 0])
        self.assertEqual(metadata["known_targets"][:4], [10, 9, 1, 0])
        self.assertIsNone(metadata["fitted_oof_nll"][3])
        self.assertAlmostEqual(metadata["fitted_oof_nll"][0], np.log(2))

    def test_held_labels_do_not_influence_their_own_fold_forecast(self):
        train = _synthetic_train()
        held = train.participant == "p1"
        changed_current = train.current_stage.copy()
        changed_stage = train.stage.copy()
        changed_current[held] = 3
        changed_stage[held] = 0
        with patch.object(controls, "fit_standardizer", wraps=controls.fit_standardizer) as scaler:
            posterior, priors, folds = controls._oof_predictions(train)
        for call, fold in zip(scaler.call_args_list, folds):
            self.assertNotIn(fold["held_out_participant"], call.args[0].participant)
            self.assertEqual(len(call.args[0].participant), 12)
        mutated = replace(train, current_stage=changed_current, stage=changed_stage)
        posterior2, priors2, _ = controls._oof_predictions(mutated)
        np.testing.assert_array_equal(posterior[held], posterior2[held])
        np.testing.assert_array_equal(priors[held], priors2[held])
        self.assertFalse(np.array_equal(priors[~held], priors2[~held]))
        alpha, matrices, metadata = controls.fit_controls(train)
        self.assertEqual(len(metadata["folds"]), 3)
        json.dumps(metadata, allow_nan=False)
        self.assertTrue(np.all((0. <= alpha) & (alpha <= 1.)))
        np.testing.assert_allclose(matrices.sum(axis=-1), 1.)


if __name__ == "__main__":
    unittest.main()
