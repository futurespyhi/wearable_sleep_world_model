import json
import tempfile
import unittest
from pathlib import Path

from sleep_g3.runner import _acquisition
from sleep_g3.runner import _configuration


class RunnerGuardTests(unittest.TestCase):
    def manifest(self):
        split = {"train": ["p0", "p1", "p2", "p3"],
                 "validation": ["p4", "p5"], "test_sealed": ["p6"]}
        records = [{"participant": p, "night": "1", "partition": partition}
                   for partition in ("train", "validation") for p in split[partition]]
        return {"status": "complete", "split_seed": 40, "split": split,
                "selected_records": records}

    def check(self, manifest):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "manifests").mkdir()
            (root / "manifests" / "acquisition.json").write_text(json.dumps(manifest))
            return _acquisition(root)

    def test_default_sample_passes(self):
        self.assertEqual(len(self.check(self.manifest())["selected_records"]), 6)

    def test_different_seed_cannot_claim_default_protocol(self):
        manifest = self.manifest()
        manifest["split_seed"] = 41
        with self.assertRaisesRegex(ValueError, "split seed"):
            self.check(manifest)

    def test_incomplete_participant_inventory_fails(self):
        manifest = self.manifest()
        manifest["selected_records"].pop()
        with self.assertRaisesRegex(ValueError, "sample sizes"):
            self.check(manifest)

    def test_sealed_test_record_fails_before_cache_loading(self):
        manifest = self.manifest()
        manifest["selected_records"][0]["participant"] = "p6"
        with self.assertRaisesRegex(ValueError, "sealed test"):
            self.check(manifest)

    def test_overlapping_participant_splits_fail(self):
        manifest = self.manifest()
        manifest["split"]["validation"][0] = "p0"
        with self.assertRaisesRegex(ValueError, "disjoint"):
            self.check(manifest)

    def test_duplicate_night_fails(self):
        manifest = self.manifest()
        manifest["selected_records"].append(manifest["selected_records"][0].copy())
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.check(manifest)

    def test_explicit_protocol_does_not_change_default(self):
        original = _configuration()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "expanded.json"
            expanded = {**original, "pilot_train_subjects": 12, "pilot_validation_subjects": 7}
            path.write_text(json.dumps(expanded))
            self.assertEqual(_configuration(path)["pilot_train_subjects"], 12)
            self.assertEqual(_configuration(), original)


if __name__ == "__main__":
    unittest.main()
