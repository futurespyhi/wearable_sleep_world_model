import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
from scipy.io import savemat

from sleep_g3.data import Episode, build_windows, load_bidsleep_night, parse_rec_start


START_TEXT = "2021-12-02 23:11:25"
START = 1638504685.0


def episode(length=150, labels=None):
    features = np.tile(np.array([60, 2, 1, 0.1, 0.01, 6, 1500]), (length, 1)).astype(float)
    return Episode(
        "p1", "1", START + 30 * np.arange(length), features,
        np.zeros(length, dtype=np.int8) if labels is None else np.asarray(labels, dtype=np.int8), {},
    )


class TimestampTests(unittest.TestCase):
    def test_inspected_schema_and_numeric_forms(self):
        self.assertEqual(parse_rec_start(np.array([START_TEXT])), START)
        self.assertEqual(parse_rec_start(START), START)
        self.assertEqual(parse_rec_start("2021-12-03T04:11:25+00:00"), START)
        datenum = pd.Timestamp(START_TEXT).to_pydatetime().toordinal() + 366 + (23 * 3600 + 11 * 60 + 25) / 86400
        self.assertAlmostEqual(parse_rec_start(datenum), START, places=4)

    def test_dst_ambiguity_and_nonexistent_time_rejected(self):
        for text in ["2021-11-07 01:30:00", "2021-03-14 02:30:00"]:
            with self.subTest(text=text), self.assertRaisesRegex(ValueError, "unambiguously"):
                parse_rec_start(text)
        self.assertEqual(parse_rec_start("2021-11-07T01:30:00-04:00"), 1636263000)

    def test_numeric_milliseconds_and_unstructured_text_rejected(self):
        for value in [START * 1000, np.nan, "12/02/2021 23:11:25", [1, 2]]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_rec_start(value)


class LoaderTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name) / "Bidslab00" / "1"
        self.root.mkdir(parents=True)

    def tearDown(self):
        self.directory.cleanup()

    def write_night(self, hr, acc, labels=(0, 1, 5, 4)):
        savemat(self.root / "labels.mat", {"recStart": START_TEXT, "expert_label": np.array(labels)})
        pd.DataFrame(hr).to_csv(self.root / "hr.csv", header=False, index=False)
        pd.DataFrame(acc, columns=["Timestamp", "x", "y", "z"]).to_csv(self.root / "motion.csv", index=False)

    def test_half_open_edges_unknowns_and_no_interpolation(self):
        self.write_night(
            [[START - 1, 10], [START, 60], [START + 29.99, 80], [START + 30, 90], [START + 120, 999]],
            [[START - 1, 10, 0, 0], [START, 1, 0, 0], [START + 29, 3, 0, 0], [START + 30, 9, 0, 0]],
        )
        loaded = load_bidsleep_night(self.root)
        np.testing.assert_array_equal(loaded.wake, [1, 0, -1, 0])
        np.testing.assert_allclose(loaded.features[0], [70, 10, 2, 1, 2, 2, 2])
        self.assertEqual(loaded.features[1, 0], 90)
        self.assertTrue(np.isnan(loaded.features[1, 4]))
        self.assertTrue(np.isnan(loaded.features[2, :5]).all())
        np.testing.assert_array_equal(loaded.features[2, 5:], [0, 0])
        self.assertEqual(loaded.metadata["hr"]["outside_label_interval_rows"], 2)
        self.assertEqual(loaded.participant, "Bidslab00")
        self.assertEqual(loaded.metadata["raw_label_codes"]["5"], "unknown")

    def test_chunk_stability_and_duplicate_boundary(self):
        hr = [[START, 60], [START + 1, 64], [START + 1, 64], [START + 30, 70]]
        acc = [[START, 1, 0, 0], [START + 1, 2, 0, 0], [START + 1, 2, 0, 0], [START + 2, 4, 0, 0], [START + 30, 8, 0, 0]]
        self.write_night(hr, acc)
        with patch("sleep_g3.data.CSV_CHUNK_ROWS", 100):
            whole = load_bidsleep_night(self.root)
        with patch("sleep_g3.data.CSV_CHUNK_ROWS", 2):
            chunked = load_bidsleep_night(self.root)
        np.testing.assert_allclose(whole.features, chunked.features, equal_nan=True)
        self.assertEqual(chunked.metadata["acc"]["duplicates_dropped"], 1)
        self.assertEqual(chunked.metadata["hr"]["duplicates_dropped"], 1)
        self.assertAlmostEqual(chunked.features[0, 4], np.sqrt(2.5))

    def test_conflicting_duplicates_and_nonmonotonic_input_fail(self):
        for hr in [
            [[START, 60], [START, 61]],
            [[START + 1, 60], [START, 61]],
        ]:
            with self.subTest(hr=hr):
                self.write_night(hr, [[START, 1, 0, 0]])
                with patch("sleep_g3.data.CSV_CHUNK_ROWS", 1), self.assertRaises(ValueError):
                    load_bidsleep_night(self.root)

    def test_future_sensor_and_label_change_cannot_change_past_features(self):
        hr = [[START + i * 30, 60 + i] for i in range(4)]
        acc = [[START + i * 30 + j, i + j + 1, 0, 0] for i in range(4) for j in [0, 1]]
        self.write_night(hr, acc)
        before = load_bidsleep_night(self.root)
        for row in hr[2:]:
            row[1] += 100
        for row in acc[4:]:
            row[1] += 100
        self.write_night(hr, acc, labels=(0, 1, 0, 0))
        after = load_bidsleep_night(self.root)
        np.testing.assert_array_equal(before.features[:2], after.features[:2])
        np.testing.assert_array_equal(before.wake[:2], after.wake[:2])
        self.assertFalse(np.array_equal(before.features[2:], after.features[2:]))

    def test_unknown_label_codes_fail_without_falling_back_to_dreem(self):
        self.write_night([[START, 60]], [[START, 1, 0, 0]], labels=(0, 9))
        with self.assertRaisesRegex(ValueError, "codes 0..5"):
            load_bidsleep_night(self.root)


class WindowTests(unittest.TestCase):
    def test_origins_are_periodic_and_future_unknowns_remain(self):
        sample = episode(150)
        sample.wake[60] = -1
        sample.wake[59] = -1
        result = build_windows([sample])
        np.testing.assert_array_equal(result["origin_time"], START + 30 * np.arange(60, 151, 10))
        self.assertEqual(result["history"].shape, (10, 60, 7))
        self.assertEqual(result["target"].shape, (10, 60))
        self.assertEqual(result["target"][0, 0], -1)
        self.assertEqual(result["current"][0], -1)
        self.assertTrue((result["target"][-1] == -1).all())
        report = result["report"]
        self.assertEqual(report["candidate_origins"], 10)
        self.assertEqual(report["full_future_span_origins"], 4)
        self.assertEqual(report["complete_target_origins"], 3)
        self.assertEqual(report["target_epochs_total"], 600)
        self.assertEqual(report["target_epochs_beyond_recording"], 210)
        self.assertEqual(report["target_epochs_unknown_inside_recording"], 1)
        self.assertEqual(report["target_epochs_valid"], 389)

    def test_origin_selection_and_history_are_label_independent(self):
        original = episode(150)
        relabeled = episode(150, labels=np.full(150, -1))
        first, second = build_windows([original]), build_windows([relabeled])
        np.testing.assert_array_equal(first["origin_time"], second["origin_time"])
        np.testing.assert_array_equal(first["history"], second["history"])
        self.assertTrue((second["target"] == -1).all())

    def test_future_invariance_and_past_only_coverage(self):
        original = episode(150)
        changed = episode(150)
        changed.features[60:] = np.array([999, 999, 999, 999, 999, 0, 0])
        changed.wake[60:] = 1
        first = build_windows([original])
        second = build_windows([changed])
        self.assertEqual(second["origin_time"][0], first["origin_time"][0])
        np.testing.assert_array_equal(second["history"][0], first["history"][0])
        self.assertTrue((second["target"][0] == 1).all())
        self.assertEqual(second["report"]["full_future_sensor_coverage_origins"], 0)

    def test_coverage_requires_both_modalities_and_boundary_is_inclusive(self):
        sample = episode(60)
        sample.features[:12, 5] = 0
        result = build_windows([sample], min_history_coverage=0.8)
        self.assertEqual(len(result["history"]), 1)
        sample.features[12, 6] = 0
        result = build_windows([sample], min_history_coverage=0.8)
        self.assertEqual(result["history"].shape, (0, 60, 7))
        self.assertEqual(result["target"].shape, (0, 60))
        self.assertEqual(result["report"]["history_coverage_rejected"], 1)

    def test_invalid_grid_or_configuration_fails(self):
        sample = episode(150)
        sample.epoch_start[1] += 1
        with self.assertRaisesRegex(ValueError, "grid"):
            build_windows([sample])
        with self.assertRaises(ValueError):
            build_windows([], stride_epochs=0)
        with self.assertRaises(ValueError):
            build_windows([], min_history_coverage=1.1)


if __name__ == "__main__":
    unittest.main()
