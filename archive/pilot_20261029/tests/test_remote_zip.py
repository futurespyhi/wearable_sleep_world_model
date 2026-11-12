"""Offline HTTP range and selective ZIP transport checks."""

import hashlib
import io
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from sleep_g3.remote_zip import HTTPRangeReader, download_from_archive


class FakeResponse(io.BytesIO):
    def __init__(self, payload, status, headers, owner):
        super().__init__(payload)
        self.status, self.headers, self.owner = status, headers, owner

    def read(self, size=-1):
        self.owner.body_reads.append((self.status, size))
        return super().read(size)


class FakeHTTP:
    def __init__(self, payload, status=206, change_headers=None, body_delta=b""):
        self.payload, self.status = payload, status
        self.change_headers = change_headers or {}
        self.body_delta = body_delta
        self.ranges, self.body_reads, self.heads = [], [], 0

    def __call__(self, request, timeout=30):
        if request.get_method() == "HEAD":
            self.heads += 1
            return FakeResponse(b"", 200, {"Content-Length": str(len(self.payload)), "ETag": '"fixed"'}, self)
        match = re.fullmatch(r"bytes=([0-9]+)-([0-9]+)", request.get_header("Range"))
        start, end = map(int, match.groups())
        self.ranges.append((start, end))
        headers = {"Content-Length": str(end - start + 1),
                   "Content-Range": f"bytes {start}-{end}/{len(self.payload)}", "ETag": '"fixed"'}
        headers.update(self.change_headers)
        return FakeResponse(self.payload[start:end + 1] + self.body_delta, self.status, headers, self)


def fixture(prefix="", duplicates=False):
    output = io.BytesIO()
    selected = b"time,value\n" + b"100,1.25\n" * 400
    relative = "Bidslab00/1/hr.csv"
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("never/read.bin", b"x" * 300_000, compress_type=zipfile.ZIP_STORED)
        archive.writestr(prefix + relative, selected, compress_type=zipfile.ZIP_DEFLATED)
        if duplicates:
            archive.writestr(relative, selected, compress_type=zipfile.ZIP_DEFLATED)
    payload = output.getvalue()
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        unused = archive.getinfo("never/read.bin")
        unused_start = unused.header_offset + 30 + len(unused.filename.encode()) + len(unused.extra)
        unused_interval = (unused_start, unused_start + unused.compress_size)
    return payload, selected, relative, unused_interval


class RemoteZipTest(unittest.TestCase):
    def test_physionet_title_prefix_matches_selected_release(self):
        prefix = "a-multi-night-instantaneous-heart-rate-and-accelerometry-dataset-with-eeg-sleep-stage-labels-1.0.1/"
        payload, selected, relative, unused = fixture(prefix)
        fake = FakeHTTP(payload)
        with tempfile.TemporaryDirectory() as directory, patch("sleep_g3.remote_zip.urllib.request.urlopen", fake):
            destination = Path(directory) / "hr.csv"
            result = download_from_archive(relative, destination, hashlib.sha256(selected).hexdigest(), 10_000)
            self.assertEqual(result["archive_member"], prefix + relative)
            self.assertEqual(destination.read_bytes(), selected)
            for start, end in fake.ranges:
                self.assertFalse(start < unused[1] and end >= unused[0])

    def test_seek_and_exact_ranges_with_bounded_reads(self):
        fake = FakeHTTP(b"abcdefghij")
        with patch("sleep_g3.remote_zip.urllib.request.urlopen", fake):
            with HTTPRangeReader("https://example.test/archive", max_read_bytes=4, max_total_bytes=6) as reader:
                self.assertEqual(reader.read(3), b"abc")
                self.assertEqual(reader.tell(), 3)
                self.assertEqual(reader.seek(-2, io.SEEK_END), 8)
                self.assertEqual(reader.read(), b"ij")
                self.assertEqual(reader.network_bytes, 5)
                reader.seek(0)
                with self.assertRaises(ValueError):
                    reader.read()
                with self.assertRaises(ValueError):
                    reader.read(2)
        self.assertEqual(fake.ranges, [(0, 2), (8, 9)])

    def test_200_is_rejected_before_any_body_read(self):
        fake = FakeHTTP(b"abcdefghij", status=200)
        with patch("sleep_g3.remote_zip.urllib.request.urlopen", fake):
            with HTTPRangeReader("https://example.test/archive") as reader:
                with self.assertRaisesRegex(ValueError, "status 206"):
                    reader.read(2)
        self.assertEqual(fake.body_reads, [])

    def test_invalid_range_headers_rejected_before_body_read(self):
        for headers in ({"Content-Range": "bytes 1-2/10"}, {"Content-Length": "9"},
                        {"Content-Range": "bytes 0-1/11"}, {"ETag": '"changed"'}):
            fake = FakeHTTP(b"abcdefghij", change_headers=headers)
            with self.subTest(headers=headers), patch("sleep_g3.remote_zip.urllib.request.urlopen", fake):
                with HTTPRangeReader("https://example.test/archive") as reader:
                    with self.assertRaises(ValueError):
                        reader.read(2)
                self.assertEqual(fake.body_reads, [])

    def test_oversized_body_is_rejected(self):
        fake = FakeHTTP(b"abcdefghij", body_delta=b"extra")
        with patch("sleep_g3.remote_zip.urllib.request.urlopen", fake):
            with HTTPRangeReader("https://example.test/archive") as reader:
                with self.assertRaisesRegex(ValueError, "body length"):
                    reader.read(2)

    def test_selected_member_only_and_verified_reuse(self):
        archive, selected, relative, unused = fixture()
        fake = FakeHTTP(archive)
        with tempfile.TemporaryDirectory() as directory, patch("sleep_g3.remote_zip.urllib.request.urlopen", fake):
            destination = Path(directory) / "explicit_destination.csv"
            expected = hashlib.sha256(selected).hexdigest()
            receipt = download_from_archive(relative, destination, expected, byte_limit=10_000)
            self.assertEqual(destination.read_bytes(), selected)
            self.assertFalse(receipt["reused"])
            self.assertEqual(receipt["path"], relative)
            self.assertEqual(receipt["transport"], "http_range_zip")
            self.assertLess(receipt["network_bytes"], len(archive) // 10)
            for start, end in fake.ranges:
                self.assertFalse(start < unused[1] and end >= unused[0])
            request_count = len(fake.ranges)
            reused = download_from_archive(relative, destination, expected, byte_limit=10_000)
            self.assertTrue(reused["reused"])
            self.assertEqual(reused["network_bytes"], 0)
            self.assertEqual(len(fake.ranges), request_count)
            self.assertEqual(list(Path(directory).glob("*.partial")), [])

    def test_version_prefix_and_ambiguous_matching(self):
        for duplicates in (False, True):
            archive, selected, relative, _ = fixture("bidsleep-dataset-1.0.1/", duplicates=duplicates)
            fake = FakeHTTP(archive)
            with self.subTest(duplicates=duplicates), tempfile.TemporaryDirectory() as directory:
                with patch("sleep_g3.remote_zip.urllib.request.urlopen", fake):
                    destination = Path(directory) / "chosen.csv"
                    if duplicates:
                        with self.assertRaisesRegex(ValueError, "exactly one"):
                            download_from_archive(relative, destination, hashlib.sha256(selected).hexdigest())
                        self.assertFalse(destination.exists())
                    else:
                        receipt = download_from_archive(relative, destination, hashlib.sha256(selected).hexdigest())
                        self.assertEqual(receipt["archive_member"], "bidsleep-dataset-1.0.1/" + relative)

    def test_budget_and_hash_mismatch_never_publish(self):
        archive, selected, relative, _ = fixture()
        for budget, expected in ((2, hashlib.sha256(selected).hexdigest()), (10_000, "0" * 64)):
            fake = FakeHTTP(archive)
            with self.subTest(budget=budget), tempfile.TemporaryDirectory() as directory:
                destination = Path(directory) / "chosen.csv"
                with patch("sleep_g3.remote_zip.urllib.request.urlopen", fake), self.assertRaises(ValueError):
                    download_from_archive(relative, destination, expected, byte_limit=budget)
                self.assertFalse(destination.exists())
                self.assertEqual(list(Path(directory).glob("*.partial")), [])

    def test_existing_mismatch_is_preserved_without_network(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "chosen.csv"
            destination.write_bytes(b"preserve me")
            with patch("sleep_g3.remote_zip.urllib.request.urlopen") as opener:
                with self.assertRaisesRegex(ValueError, "existing file checksum mismatch"):
                    download_from_archive("Bidslab00/1/hr.csv", destination, "0" * 64)
                opener.assert_not_called()
            self.assertEqual(destination.read_bytes(), b"preserve me")

    def test_path_traversal_is_rejected_without_network(self):
        with patch("sleep_g3.remote_zip.urllib.request.urlopen") as opener:
            for relative in ("../escape", "/absolute", "a/../b", "a\\b", "a//b"):
                with self.subTest(relative=relative), self.assertRaises(ValueError):
                    download_from_archive(relative, "/tmp/not-created-by-test", "0" * 64)
            opener.assert_not_called()


if __name__ == "__main__":
    unittest.main()
