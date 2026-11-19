from pathlib import Path
import tempfile
import unittest

import numpy as np
from scipy.io import savemat

from sleep_g3 import data as g3
from sleep_g3.protocol import sha256_file
from stage_forecast import cache_gate
from stage_forecast.data import build_stage_windows, fit_standardizer, load_stage_night, SensorAuditFailure


class ExpandedCacheTests(unittest.TestCase):
    def test_reports_second_sensor_even_if_first_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "Bidslab99" / "1"
            path.mkdir(parents=True)
            start = 1600000000
            savemat(path / "labels.mat", {"recStart": start, "expert_label": [1, 3]})
            (path / "hr.csv").write_text("1600000001,70\n1600000000,70\n")
            (path / "motion.csv").write_text("Timestamp,x,y,z\n1600000001,0,0,1\n1600000000,1,0,0\n")
            policy = {"schema": "stage_event_time_v1", "events": []}
            sources = {name: {"status": "verified", "sha256": sha256_file(path / name)}
                       for name in ("hr.csv", "motion.csv")}
            with self.assertRaises(SensorAuditFailure) as info:
                load_stage_night(path, policy=policy, verified_sources=sources)
            for stream in ("hr", "acc"):
                self.assertEqual(info.exception.reports[stream]["status"], "failed")
                self.assertTrue(info.exception.reports[stream]["events"])

    def test_registered_epoch_is_absent_from_training_scaler_and_model_inputs(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "Bidslab99" / "1"
            path.mkdir(parents=True)
            start, epoch = 1600000000, 32
            labels = np.full(100, 3)
            savemat(path / "labels.mat", {"recStart": start, "expert_label": labels})
            hr, acc = [], ["Timestamp,x,y,z"]
            for i in range(len(labels)):
                left = start + 30 * i
                hr.append(f"{left},70")
                times = (left + 5, left + 1) if i == epoch else (left, left + 1)
                acc.extend([f"{times[0]},0,0,1", f"{times[1]},{10000 if i == epoch else 2},0,1"])
            (path / "hr.csv").write_text("\n".join(hr))
            (path / "motion.csv").write_text("\n".join(acc))
            sources = {name: {"status": "verified", "sha256": sha256_file(path / name)}
                       for name in ("hr.csv", "motion.csv")}
            base = start + 30 * epoch
            rule = {"path": "Bidslab99/1/motion.csv", "sha256": sources["motion.csv"]["sha256"],
                    "kind": "reversal", "rows": [2 + 2 * epoch, 3 + 2 * epoch],
                    "timestamps": [str(base + 5), str(base + 1)], "relation": "inside",
                    "action": "mask_acc_epoch", "epoch": epoch}
            episode, stage = load_stage_night(path, policy={"schema": "stage_event_time_v1", "events": [rule]},
                                               verified_sources=sources)
            windows, _ = build_stage_windows(episode, stage)
            scaler = fit_standardizer(windows)
            hr_inputs, acc_inputs = scaler.transform(windows.history)
            self.assertEqual(stage[epoch], 2)
            self.assertEqual(episode.features[epoch, 0], 70)
            self.assertEqual(episode.features[epoch, 6], 0)
            self.assertTrue(np.isnan(episode.features[epoch, 2:5]).all())
            self.assertAlmostEqual(scaler.center[3], 2.)
            np.testing.assert_array_equal(acc_inputs[0, epoch], np.zeros(4))
            self.assertEqual(hr_inputs[0, epoch, -1], 1)

    def test_coverage_tracks_a_window_lost_only_because_of_mask(self):
        count = 120
        stage = np.arange(count, dtype=np.int8) % 4
        raw = np.ones((count, 7))
        raw[:12, 5] = 0
        raw[32, 2:5] = np.nan
        raw[32, 6] = 0
        args = {"history_epochs": 60, "horizon_epochs": 60, "stride_epochs": 10,
                "min_history_coverage": .8}
        episode = g3.Episode("participant", "1", np.arange(count) * 30, raw,
                             (stage == 0).astype(np.int8),
                             {"acc": {"masked_epochs": [32], "masked_valid_sample_counts": {"32": 1}}})
        windows, _ = build_stage_windows(episode, stage, **args)
        coverage = cache_gate.mask_coverage(episode, windows, args)
        self.assertEqual(coverage["candidate_origins"], [60, 70, 80, 90])
        self.assertEqual(coverage["retained_origins"], [70, 80, 90])
        self.assertEqual(coverage["lost_due_to_mask"], [60])
        self.assertEqual(coverage["histories"][0]["joint_epochs_before"], 48)
        self.assertEqual(coverage["histories"][0]["joint_epochs_after"], 47)

    def test_changed_feature_missingness_cannot_pass_strict_reference(self):
        values = np.asarray([np.nan, 0, 1])
        cache_gate.equal_values("features", values, values.copy())
        with self.assertRaisesRegex(ValueError, "values differ"):
            cache_gate.equal_values("features", values, np.zeros(3))

    def test_expanded_gate_rejects_a_missing_night_or_wrong_policy(self):
        records = [{"participant": str(i // 2), "night": str(i % 2),
                    "partition": "train" if i < 24 else "validation"} for i in range(38)]
        manifest = {"selected_records": records, "test_downloaded": False}
        audit = {"acquisition_sha256": "acq", "protocol_sha256": "protocol", "selected_records": records,
                 "nights": [], "test_accessed": False, "failures": []}
        policy = {"acquisition_sha256": "acq", "protocol_sha256": "protocol", "events": []}
        with self.assertRaisesRegex(ValueError, "acquisition must agree"):
            cache_gate.verify_policy_manifest(audit, dict(policy, protocol_sha256="other"), manifest)
        with self.assertRaisesRegex(ValueError, "incomplete night inventory"):
            cache_gate.verify_complete_evidence(audit, policy, dict(manifest, files=[]))


if __name__ == "__main__":
    unittest.main()
