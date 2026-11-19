from dataclasses import fields
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from scipy.io import savemat

from sleep_g3 import data as g3
from stage_forecast.data import (
    ENDPOINTS, StageWindows, build_stage_windows, fit_standardizer, load_stage_night, map_stages,
)
from stage_forecast.timestamps import inspect_timestamps


START = 1600000000


def _write_night(path: Path, mutate_future: bool = False):
    path.mkdir(parents=True, exist_ok=True)
    labels = np.arange(120) % 6
    if mutate_future:
        labels[60:] = 4
    savemat(path / "labels.mat", {"recStart": START, "expert_label": labels})
    hr_rows = []
    acc_rows = ["Timestamp,x,y,z\n"]
    for epoch in range(len(labels)):
        seconds = START + 30 * epoch
        future_delta = 40 if mutate_future and epoch >= 60 else 0
        if epoch != 61:
            hr_rows.extend([f"{seconds},{60 + epoch + future_delta}\n", f"{seconds + 2},{62 + epoch}\n"])
        acc_rows.extend([f"{seconds},{future_delta},0,1\n", f"{seconds + 2},0,0,1\n"])
    (path / "hr.csv").write_text("".join(hr_rows))
    (path / "motion.csv").write_text("".join(acc_rows))


def cutoff_mutation_histories(path: Path, *, masked=False) -> tuple[StageWindows, StageWindows]:
    """Reparse raw future mutations, keeping the shared 30-minute history."""
    first_origin = []
    for mutate in (False, True):
        _write_night(path, mutate)
        args = {}
        if masked:
            from sleep_g3.protocol import sha256_file
            motion_file = path / "motion.csv"
            rows = motion_file.read_text().splitlines()
            ts = START + 30 * 32
            rows[65] = f"{ts + 3},0,0,1"
            motion_file.write_text("\n".join(rows) + "\n")
            sources = {name: {"status": "verified", "sha256": sha256_file(path / name)}
                       for name in ("motion.csv", "hr.csv")}
            event = {"path": f"{path.parent.name}/{path.name}/motion.csv",
                     "sha256": sources["motion.csv"]["sha256"], "kind": "reversal",
                     "rows": [66, 67], "timestamps": [str(ts + 3), str(ts + 2)],
                     "relation": "inside", "epoch": 32, "action": "mask_acc_epoch"}
            args = {"policy": {"schema": "stage_event_time_v1", "events": [event]}, "verified_sources": sources}
        episode, labels = load_stage_night(path, **args)
        if masked:
            np.testing.assert_array_equal(episode.features[32, 2:5], [np.nan] * 3)
            assert episode.features[32, 6] == 0
        windows, _ = build_stage_windows(episode, labels)
        first = windows.origin == 60
        first_origin.append(StageWindows(**{
            field.name: getattr(windows, field.name)[first] for field in fields(windows)
        }))
    return tuple(first_origin)


class StageDataTests(unittest.TestCase):
    def test_label_map_endpoints_and_out_of_recording_mask(self):
        np.testing.assert_array_equal(map_stages([0, 1, 2, 3, 4, 5]), [0, 1, 1, 2, 3, -1])
        with self.assertRaises(ValueError):
            map_stages([6])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "Bidslab00" / "1"
            _write_night(path)
            episode, labels = load_stage_night(path)
            windows, _ = build_stage_windows(episode, labels)
        self.assertEqual(ENDPOINTS, (9, 29, 59))
        self.assertEqual(len(windows.history), len(windows.origin))
        self.assertEqual(windows.history.shape, (7, 60, 6))
        np.testing.assert_array_equal(windows.origin, [60, 70, 80, 90, 100, 110, 120])
        np.testing.assert_array_equal(windows.stage[0, list(ENDPOINTS)], [2, -1, -1])
        self.assertFalse(windows.future_hr_mask[0, 1])
        self.assertTrue(np.isnan(windows.future_hr[0, 1]))
        self.assertTrue(windows.future_hr_mask[0, 29], "unknown stage is independent of HR availability")
        np.testing.assert_array_equal(windows.stage[-1], np.full(60, -1))
        self.assertFalse(windows.future_hr_mask[-1].any())

    def test_cutoff_preserves_origin_and_history_after_future_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            original, changed = cutoff_mutation_histories(Path(tmp) / "Bidslab00" / "1")
        self.assertEqual(original.origin_time[0], START + 60 * 30)
        np.testing.assert_array_equal(original.origin_time, changed.origin_time)
        np.testing.assert_array_equal(original.origin, changed.origin)
        np.testing.assert_array_equal(original.history, changed.history)
        self.assertFalse(np.array_equal(original.stage, changed.stage))
        self.assertFalse(np.array_equal(original.future_hr, changed.future_hr))
        self.assertEqual(original.future_hr[0, 0], 121)
        self.assertEqual(changed.future_hr[0, 0], 141)
        self.assertEqual(original.history[0, -1, 0], 120)

    def test_motion_action_uses_pairs_only_within_epoch_across_chunks(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "motion.csv"
            path.write_text(
                "Timestamp,x,y,z\n"
                "1600000000,0,0,1\n"
                "1600000001,0.1,0,1\n"
                "1600000002,0,0,1\n"
                "1600000030,0,0,1\n"
                "1600000031,0,0,1\n"
                "1600000060,0,0,1\n"
            )
            with patch.object(g3, "CSV_CHUNK_ROWS", 2):
                acc, report = g3._aggregate_sensor(path, START, 4, "acc", collect_intervals=True)
        np.testing.assert_array_equal(acc["count"], [3, 2, 1, 0])
        np.testing.assert_allclose(acc["diff_rms"][:2], [0.1, 0.0], atol=1e-12)
        np.testing.assert_allclose(acc["std"][:2], [np.std([1, np.hypot(0.1, 1), 1]), 0], atol=1e-12)
        self.assertTrue(np.isnan(acc["diff_rms"][2:]).all())
        self.assertEqual(report["positive_raw_sample_intervals_seconds"], {
            "count": 5, "min": 1, "max": 29, "mean": 12
        })
        # A real zero-motion epoch stays valid, unlike one-sample or missing epochs.
        with tempfile.TemporaryDirectory() as tmp:
            training, _ = cutoff_mutation_histories(Path(tmp) / "Bidslab00" / "1")
        standardizer = fit_standardizer(training)
        probe = np.column_stack([
            np.full(4, np.nan), np.full(4, np.nan), np.zeros(4),
            acc["std"], acc["diff_rms"], acc["count"],
        ])[None]
        hr_inputs, acc_inputs = standardizer.transform(probe)
        np.testing.assert_array_equal(acc_inputs[0, :, -1], [1, 1, 0, 0])
        np.testing.assert_array_equal(acc_inputs[0, 2:, :2], np.zeros((2, 2)))
        np.testing.assert_array_equal(hr_inputs, np.zeros_like(hr_inputs))

    def test_scaler_counts_distinct_history_epochs_and_excludes_targets(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "Bidslab00" / "1"
            _write_night(path)
            episode, labels = load_stage_night(path)
            windows, _ = build_stage_windows(episode, labels)
        selected = windows.origin <= 70
        training = StageWindows(**{
            field.name: getattr(windows, field.name)[selected] for field in fields(windows)
        })
        scale = fit_standardizer(training)
        expected = np.delete(61 + np.arange(70), 61)
        self.assertAlmostEqual(scale.hr_center, expected.mean())
        self.assertAlmostEqual(scale.hr_scale, expected.std())

    def test_timestamp_forensics_physical_rows_and_reference_overlap(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "motion.csv"
            path.write_text(
                "Timestamp,x,y,z\n"
                "1599999999,0,0,1\n"
                "1600000032,0,0,1\n"
                "1600000029,0,0,1\n"
                "1600000029,0.0,0,1\n"
                "1600000029,1,0,1\n"
            )
            result = inspect_timestamps(path, START, np.array([0, -1]), chunk_rows=2)
        self.assertTrue(result["raw_anomaly_confirmed"])
        self.assertEqual(result["reversals"], 1)
        self.assertEqual(result["cross_chunk_reversals"], 1)
        self.assertEqual(result["adjacent_identical_timestamp_duplicates"], 1)
        self.assertEqual(result["adjacent_conflicting_timestamp_duplicates"], 1)
        first = result["examples"]["reversals"][0]
        self.assertEqual((first["previous_csv_line"], first["csv_line"]), (3, 4))
        self.assertEqual(first["delta_seconds"], -3)
        self.assertEqual(first["intersected_label_epochs_0based"], [0, 1])
        self.assertEqual(result["known_reference_epochs_intersected_by_reversal_spans"], 1)


if __name__ == "__main__":
    unittest.main()
