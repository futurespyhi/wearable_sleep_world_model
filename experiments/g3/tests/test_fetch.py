import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sleep_g3.fetch import BASE_URL, acquire, download
from sleep_g3.protocol import participant_split, select_records, sha256_file


class Response(io.BytesIO):
    def __init__(self, body, content_length=None):
        super().__init__(body)
        self.headers = {} if content_length is None else {"Content-Length": str(content_length)}


class FetchTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.donor = self.base / "pilot"
        self.root = self.base / "expanded"
        self.roster = [f"Bidslab{i:02d}" for i in range(47)]
        self.split = participant_split(self.roster)
        self.payloads = {"LICENSE.txt": b"Fixture license\n", "README.md": b"Fixture release\n"}
        for pid in self.roster:
            for night in (1, 2):
                for name in ("hr.csv", "labels.mat", "motion.csv"):
                    relative = f"{pid}/{night}/{name}"
                    self.payloads[relative] = (relative + "\n").encode("ascii")
        self.catalog = {relative: hashlib.sha256(payload).hexdigest()
                        for relative, payload in self.payloads.items()}
        self.catalog_bytes = "".join(f"{digest}  {relative}\n"
                                     for relative, digest in sorted(self.catalog.items())).encode("ascii")
        self.catalog_digest = hashlib.sha256(self.catalog_bytes).hexdigest()

    def write_source(self, train=4, validation=2, nights=1):
        selected = select_records(self.catalog, self.split, train, validation, nights)
        relatives = ["LICENSE.txt", "README.md"] + [
            f"{record['participant']}/{record['night']}/{name}"
            for record in selected for name in ("hr.csv", "labels.mat", "motion.csv")]
        raw = self.donor / "raw" / "bidsleep_1.0.1"
        raw.mkdir(parents=True)
        (raw / "SHA256SUMS.txt").write_bytes(self.catalog_bytes)
        files = [{"path": "SHA256SUMS.txt", "bytes": len(self.catalog_bytes),
                  "sha256": self.catalog_digest}]
        for relative in relatives:
            destination = raw / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(self.payloads[relative])
            files.append({"path": relative, "bytes": len(self.payloads[relative]),
                          "sha256": self.catalog[relative]})
        manifest = {"source": BASE_URL, "status": "complete", "test_downloaded": False,
                    "catalog_sha256": self.catalog_digest, "split_seed": 40,
                    "split": self.split, "selected_records": selected, "files": files}
        self.save_source_manifest(manifest)
        return manifest

    def save_source_manifest(self, manifest):
        path = self.donor / "manifests" / "acquisition.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(manifest), encoding="utf-8")

    def prepare_root(self, metadata=False):
        raw = self.root / "raw" / "bidsleep_1.0.1"
        raw.mkdir(parents=True)
        (raw / "SHA256SUMS.txt").write_bytes(self.catalog_bytes)
        if metadata:
            for relative in ("LICENSE.txt", "README.md"):
                (raw / relative).write_bytes(self.payloads[relative])
        return raw

    def acquire(self, **kwargs):
        with patch("builtins.print"):
            return acquire(self.root, **kwargs)

    def acquired_manifest(self):
        return json.loads((self.root / "manifests" / "acquisition.json").read_text())

    def archive_download(self, relative, destination, expected, byte_limit):
        payload = self.payloads[relative]
        self.assertEqual(hashlib.sha256(payload).hexdigest(), expected)
        if len(payload) > byte_limit:
            raise ValueError("selected archive member exceeds byte budget: " + relative)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(payload)
        return {"path": relative, "bytes": len(payload), "sha256": expected,
                "reused": False, "transport": "http_range_zip", "network_bytes": len(payload)}

    def test_reuse_is_selected_only_verified_and_records_provenance(self):
        source = self.write_source(train=5, validation=3, nights=2)
        raw = self.prepare_root()
        sealed = f"{self.split['test_sealed'][0]}/1/motion.csv"
        sealed_path = self.donor / "raw" / "bidsleep_1.0.1" / sealed
        sealed_path.parent.mkdir(parents=True)
        sealed_path.write_bytes(self.payloads[sealed])
        source["files"].append({"path": sealed, "bytes": len(self.payloads[sealed]),
                                "sha256": self.catalog[sealed]})
        self.save_source_manifest(source)
        before = (self.donor / "manifests" / "acquisition.json").read_bytes()
        with patch("sleep_g3.fetch.urllib.request.urlopen") as opener, \
                patch("sleep_g3.fetch.sha256_file", wraps=sha256_file) as hasher:
            result = self.acquire(reuse_root=self.donor, archive_transport=True)
        opener.assert_not_called()
        self.assertEqual(result["status"], "complete")
        manifest = self.acquired_manifest()
        self.assertEqual(manifest["reuse_root"], str(self.donor))
        self.assertEqual(manifest["reuse_acquisition_sha256"], hashlib.sha256(before).hexdigest())
        chosen = {f"{r['participant']}/{r['night']}/{name}"
                  for r in manifest["selected_records"] for name in ("hr.csv", "labels.mat", "motion.csv")}
        for entry in manifest["files"]:
            if entry["path"] == "SHA256SUMS.txt":
                continue
            path = raw / entry["path"]
            self.assertTrue(path.is_symlink())
            self.assertEqual(entry["reuse_method"], "symlink")
            self.assertEqual(path.resolve(), Path(entry["reuse_source"]))
            self.assertEqual(entry["network_bytes"], 0)
        donor_raw = self.donor / "raw" / "bidsleep_1.0.1"
        for call in hasher.call_args_list:
            path = Path(call.args[0])
            if path.is_relative_to(donor_raw):
                self.assertIn(str(path.relative_to(donor_raw)), chosen | {"LICENSE.txt", "README.md"})
        self.assertFalse((raw / sealed).exists())
        self.assertEqual((self.donor / "manifests" / "acquisition.json").read_bytes(), before)
        with patch("sleep_g3.fetch.urllib.request.urlopen") as opener:
            self.assertEqual(self.acquire(reuse_root=self.donor)["status"], "complete")
        opener.assert_not_called()
        self.assertTrue(all(entry.get("reuse_method") == "symlink"
                            for entry in self.acquired_manifest()["files"][1:]))

    def test_incompatible_sources_fail_before_raw_reads(self):
        original = self.write_source()
        self.prepare_root()
        variants = []
        for key, value in (("status", "failed"), ("test_downloaded", True),
                           ("source", BASE_URL + "other/"), ("catalog_sha256", "0" * 64),
                           ("split_seed", 41)):
            altered = json.loads(json.dumps(original))
            altered[key] = value
            variants.append(altered)
        altered = json.loads(json.dumps(original))
        altered["split"]["train"].reverse()
        variants.append(altered)
        altered = json.loads(json.dumps(original))
        altered["selected_records"][0]["participant"] = self.split["test_sealed"][0]
        variants.append(altered)
        for altered in variants:
            self.save_source_manifest(altered)
            with self.subTest(manifest=altered), \
                    patch("sleep_g3.fetch.urllib.request.urlopen") as opener, \
                    patch("sleep_g3.fetch.sha256_file", wraps=sha256_file) as hasher:
                with self.assertRaises(ValueError):
                    self.acquire(reuse_root=self.donor)
                opener.assert_not_called()
                self.assertFalse(any(Path(call.args[0]).name in ("hr.csv", "labels.mat", "motion.csv")
                                     for call in hasher.call_args_list))
            self.assertFalse((self.root / "manifests" / "acquisition.json").exists())

    def test_same_root_is_rejected_without_network_or_manifest_change(self):
        self.write_source()
        manifest = self.donor / "manifests" / "acquisition.json"
        before = manifest.read_bytes()
        with patch("sleep_g3.fetch.urllib.request.urlopen") as opener:
            with self.assertRaisesRegex(ValueError, "must differ"):
                acquire(self.donor, reuse_root=self.donor)
        opener.assert_not_called()
        self.assertEqual(manifest.read_bytes(), before)

    def test_corrupted_source_is_preserved_and_never_linked(self):
        source = self.write_source()
        raw = self.prepare_root()
        record = source["selected_records"][0]
        relative = f"{record['participant']}/{record['night']}/hr.csv"
        donor_file = self.donor / "raw" / "bidsleep_1.0.1" / relative
        corrupted = b"!" * donor_file.stat().st_size
        donor_file.write_bytes(corrupted)
        with patch("sleep_g3.fetch.urllib.request.urlopen") as opener:
            with self.assertRaisesRegex(ValueError, "checksum or size mismatch"):
                self.acquire(reuse_root=self.donor)
        opener.assert_not_called()
        self.assertFalse((raw / relative).is_symlink())
        self.assertEqual(donor_file.read_bytes(), corrupted)
        self.assertEqual(self.acquired_manifest()["status"], "failed")

    def test_source_link_to_unselected_record_is_rejected_before_hashing(self):
        source = self.write_source()
        self.prepare_root()
        record = source["selected_records"][0]
        relative = f"{record['participant']}/{record['night']}/hr.csv"
        donor_raw = self.donor / "raw" / "bidsleep_1.0.1"
        selected_file = donor_raw / relative
        sealed_file = donor_raw / self.split["test_sealed"][0] / "1" / "hr.csv"
        sealed_file.parent.mkdir(parents=True)
        sealed_file.write_bytes(self.payloads[relative])
        selected_file.unlink()
        selected_file.symlink_to(sealed_file)
        with patch("sleep_g3.fetch.sha256_file", wraps=sha256_file) as hasher:
            with self.assertRaisesRegex(ValueError, "outside its selected record"):
                self.acquire(reuse_root=self.donor)
        self.assertFalse(any(Path(call.args[0]) in (selected_file, sealed_file)
                             for call in hasher.call_args_list))

    def test_unreceipted_source_file_is_not_read_and_archive_fetches_it(self):
        source = self.write_source()
        self.prepare_root()
        record = source["selected_records"][0]
        relative = f"{record['participant']}/{record['night']}/hr.csv"
        source["files"] = [entry for entry in source["files"] if entry["path"] != relative]
        self.save_source_manifest(source)
        donor_file = self.donor / "raw" / "bidsleep_1.0.1" / relative
        with patch("sleep_g3.remote_zip.download_from_archive", side_effect=self.archive_download) as fetcher, \
                patch("sleep_g3.fetch.sha256_file", wraps=sha256_file) as hasher:
            self.acquire(reuse_root=self.donor, archive_transport=True)
        self.assertEqual([call.args[0] for call in fetcher.call_args_list], [relative])
        self.assertNotIn(donor_file, [Path(call.args[0]) for call in hasher.call_args_list])

    def test_archive_dispatch_includes_hr_labels_and_motion(self):
        self.prepare_root(metadata=True)
        with patch("sleep_g3.fetch.urllib.request.urlopen") as opener, \
                patch("sleep_g3.remote_zip.download_from_archive", side_effect=self.archive_download) as fetcher:
            result = self.acquire(archive_transport=True)
        opener.assert_not_called()
        relatives = [call.args[0] for call in fetcher.call_args_list]
        self.assertEqual(len(relatives), 18)
        self.assertEqual({path.name for path in map(Path, relatives)}, {"hr.csv", "labels.mat", "motion.csv"})
        self.assertEqual(result["status"], "complete")

    def test_archive_validation_failure_is_not_retried_or_downloaded_directly(self):
        self.prepare_root(metadata=True)
        with patch("sleep_g3.fetch.urllib.request.urlopen") as opener, \
                patch("sleep_g3.remote_zip.download_from_archive", side_effect=ValueError("checksum mismatch")) as fetcher:
            with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                self.acquire(archive_transport=True)
        opener.assert_not_called()
        self.assertEqual(fetcher.call_count, 1)
        self.assertEqual(self.acquired_manifest()["status"], "failed")

    def test_reused_files_and_metadata_count_against_total_budget(self):
        source = self.write_source()
        raw = self.prepare_root()
        metadata_bytes = len(self.catalog_bytes) + len(self.payloads["LICENSE.txt"]) + len(self.payloads["README.md"])
        with self.assertRaisesRegex(ValueError, "byte budget"):
            self.acquire(reuse_root=self.donor, max_total_bytes=metadata_bytes + 1)
        manifest = self.acquired_manifest()
        self.assertEqual(manifest["status"], "failed")
        self.assertEqual(sum(entry["bytes"] for entry in manifest["files"]), metadata_bytes)
        first = source["selected_records"][0]
        self.assertFalse((raw / first["participant"] / first["night"] / "hr.csv").is_symlink())
        with self.assertRaisesRegex(ValueError, "byte budget"):
            self.acquire(reuse_root=self.donor, metadata_only=True,
                         max_total_bytes=len(self.catalog_bytes) + 1)
        self.assertEqual(self.acquired_manifest()["status"], "failed")

    def test_per_file_limit_is_checked_before_reading_reuse_source(self):
        self.write_source()
        self.prepare_root()
        with patch("sleep_g3.fetch.FILE_BYTE_LIMIT", 1), \
                patch("sleep_g3.fetch.sha256_file", wraps=sha256_file) as hasher:
            with self.assertRaisesRegex(ValueError, "reuse file exceeds byte budget"):
                self.acquire(reuse_root=self.donor)
        self.assertFalse(any(Path(call.args[0]).name in ("hr.csv", "labels.mat", "motion.csv")
                             for call in hasher.call_args_list))

    def test_retained_partial_budget_is_applied_before_catalog_reuse(self):
        raw = self.prepare_root()
        (raw / "old.partial").write_bytes(b"1234")
        with self.assertRaisesRegex(ValueError, "byte budget"):
            self.acquire(metadata_only=True, max_total_bytes=len(self.catalog_bytes) + 3)
        self.assertEqual((raw / "old.partial").read_bytes(), b"1234")

    def test_explicit_member_budget_resumes_same_selection(self):
        self.write_source()
        self.prepare_root()
        with patch("sleep_g3.fetch.FILE_BYTE_LIMIT", 1):
            with self.assertRaisesRegex(ValueError, "reuse file exceeds byte budget"):
                self.acquire(reuse_root=self.donor)
            before = self.acquired_manifest()["selected_records"]
            result = self.acquire(reuse_root=self.donor, max_file_bytes=350_000_000)
        self.assertEqual(result["status"], "complete")
        self.assertEqual(self.acquired_manifest()["selected_records"], before)
        self.assertEqual(self.acquired_manifest()["per_file_byte_budget"], 350_000_000)

    def test_changed_selection_cannot_overwrite_existing_acquisition(self):
        self.write_source()
        self.prepare_root()
        self.acquire(reuse_root=self.donor)
        path = self.root / "manifests" / "acquisition.json"
        before = path.read_bytes()
        with self.assertRaisesRegex(ValueError, "selection changed"):
            self.acquire(reuse_root=self.donor, nights=2)
        self.assertEqual(path.read_bytes(), before)

    def test_existing_individual_file_cannot_bypass_byte_budget(self):
        destination = self.base / "existing.csv"
        destination.write_bytes(b"1234")
        with patch("sleep_g3.fetch.urllib.request.urlopen") as opener:
            with self.assertRaisesRegex(ValueError, "exceeds byte budget"):
                download("existing.csv", destination, byte_limit=3)
        opener.assert_not_called()
        self.assertEqual(destination.read_bytes(), b"1234")

    def test_individual_download_over_budget_never_publishes(self):
        for content_length in (None, 4):
            with self.subTest(content_length=content_length):
                destination = self.base / f"download-{content_length}.csv"
                with patch("sleep_g3.fetch.urllib.request.urlopen", return_value=Response(b"1234", content_length)):
                    with self.assertRaisesRegex(ValueError, "byte budget"):
                        download("small.csv", destination, byte_limit=3)
                self.assertFalse(destination.exists())


if __name__ == "__main__":
    unittest.main()
