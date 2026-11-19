from types import SimpleNamespace
import unittest

import numpy as np

from stage_forecast.recording_time_inputs import _partition_bins


class RecordingTimeInputTests(unittest.TestCase):
    @staticmethod
    def fixture():
        # Identical cutoff elapsed times on two different dates. Only the
        # original recording's start can map both sets to the expected bins.
        start_a, start_b = 1600000000.25, 1600111111.75
        offsets = np.array([239, 240, 479, 480, 719, 720])
        nights = np.array(["1", "2", "1", "2", "1", "2"])
        starts = np.where(nights == "1", start_a, start_b)
        windows = SimpleNamespace(participant=np.repeat("p", 6), night=nights,
                                  origin=offsets, origin_time=starts + 30 * offsets)
        rows = [{"participant": "p", "night": night, "partition": "train",
                 "metadata": {"recording_start_unix": start}} for night, start in (("1", start_a), ("2", start_b))]
        return windows, {"nights": rows}

    def test_half_open_bin_uses_this_nights_cutoff(self):
        windows, audit = self.fixture()
        np.testing.assert_array_equal(_partition_bins(windows, audit, "train"), [0, 1, 1, 2, 2, 3])

    def test_epoch_index_and_recstart_must_both_reproduce_cutoff(self):
        windows, audit = self.fixture()
        windows.origin_time[3] += 30
        with self.assertRaises(ValueError):
            _partition_bins(windows, audit, "train")
        windows, audit = self.fixture()
        audit["nights"][0]["metadata"]["recording_start_unix"] += 30
        with self.assertRaises(ValueError):
            _partition_bins(windows, audit, "train")
