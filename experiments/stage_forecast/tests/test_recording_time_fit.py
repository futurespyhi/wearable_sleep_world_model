from types import SimpleNamespace
import unittest

import numpy as np

from stage_forecast.recording_time_fit import fit_time, make_time_predictions


class RecordingTimeFitTests(unittest.TestCase):
    def test_shrinkage_counts_known_future_and_known_pairs_separately(self):
        # At the first lead, bin 0 has three observed targets but only two
        # paired observations because one cutoff label is unknown.
        target = np.full((5, 60), -1)
        target[:, 0] = [2, 3, 1, 0, -1]
        target[:, 1] = [0, 0, -1, 3, 2]
        train = SimpleNamespace(stage=target, current_stage=np.array([0, 0, -1, 1, 1]))
        bins = np.array([0, 0, 0, 1, 1])
        prior = np.full((60, 4), .25)
        prior[1] = [.4, .2, .3, .1]
        transition = np.broadcast_to(np.eye(4), (60, 4, 4)).copy()
        transition[1, 0] = [.25, .25, .5, 0]
        priors, matrices, info = fit_time(train, bins, prior, transition)
        np.testing.assert_allclose(priors[0, 0], np.array([5, 6, 6, 6]) / 23)
        np.testing.assert_allclose(matrices[0, 0, 0], np.array([20, 0, 1, 1]) / 22)
        np.testing.assert_allclose(priors[0, 1], np.array([10, 4, 6, 2]) / 22)
        np.testing.assert_allclose(matrices[0, 1, 0], np.array([7, 5, 10, 0]) / 22)
        self.assertEqual(info["known_target_support"][0][0], 3)
        self.assertEqual(info["known_pair_support_per_row"][0][0], [2, 0, 0, 0])
        self.assertEqual(info["training_origins_by_bin"], [3, 2, 0, 0])
        np.testing.assert_array_equal(priors[2], prior)
        np.testing.assert_array_equal(matrices[2], transition)
        np.testing.assert_array_equal(matrices[0, 0, 1], transition[0, 1])
        np.testing.assert_allclose(priors.sum(axis=-1), 1.)
        np.testing.assert_allclose(matrices.sum(axis=-1), 1.)

    def test_future_axis_orientation_and_current_label_only_affects_oracle(self):
        priors = np.repeat(np.eye(4)[:, None, :], 60, axis=1)
        matrices = np.broadcast_to(np.eye(4), (4, 60, 4, 4)).copy()
        matrices[1, 59] = np.eye(4)[[1, 2, 3, 0]]
        bins = np.array([0, 1, 1])
        pt = np.array([[.1, .2, .3, .4], [.4, .1, .3, .2], [0, 0, 1., 0]])
        result = make_time_predictions(bins, pt, [0, 3, -1], priors, matrices)
        changed = make_time_predictions(bins, pt, [3, 0, 2], priors, matrices)
        for method in ("time_only", "time_transition"):
            np.testing.assert_array_equal(result[method], changed[method])
            self.assertEqual(result[method].shape, (3, 60, 4))
        np.testing.assert_array_equal(result["time_transition"][1, 59], [.2, .4, .1, .3])
        np.testing.assert_array_equal(result["time_transition"][1, 58], pt[1])
        np.testing.assert_array_equal(result["time_only"][:, 59], priors[bins, 59, :])
        np.testing.assert_array_equal(result["time_oracle"][1, 59], [1, 0, 0, 0])
        np.testing.assert_array_equal(changed["time_oracle"][1, 59], [0, 1, 0, 0])
        np.testing.assert_array_equal(result["time_oracle"][2], priors[1])
        np.testing.assert_array_equal(changed["time_oracle"][2, 59], [0, 0, 0, 1])


if __name__ == "__main__":
    unittest.main()
