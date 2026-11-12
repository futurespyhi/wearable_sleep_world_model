"""Bounded HTTP ranges for one verified member of the official release ZIP."""

import hashlib
import io
import os
from pathlib import Path, PurePosixPath
import re
import tempfile
import urllib.request
import zipfile

from .protocol import sha256_file


ARCHIVE_URL = "https://physionet.org/content/bidsleep-dataset/get-zip/1.0.1/"
ARCHIVE_PREFIXES = (
    "bidsleep-dataset-1.0.1/", "bidsleep-dataset/1.0.1/", "1.0.1/",
    "a-multi-night-instantaneous-heart-rate-and-accelerometry-dataset-with-eeg-sleep-stage-labels-1.0.1/",
)
MAX_RANGE_BYTES = 200_000_000
MAX_ARCHIVE_BYTES = 10_000_000_000
DIRECTORY_BUDGET_BYTES = 8_000_000
_CONTENT_RANGE = re.compile(r"bytes ([0-9]+)-([0-9]+)/([0-9]+)")


def _positive_integer(value, name):
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _content_length(response):
    value = response.headers.get("Content-Length", "")
    if not value.isdecimal():
        raise ValueError("missing or invalid Content-Length")
    return int(value)


class HTTPRangeReader(io.RawIOBase):
    """Seekable, bounded reader; a GET returning 200 is never consumed.

    HEAD establishes the archive size without reading its body. Every GET
    must return the exact requested inclusive range and the same total size.
    ``network_bytes`` counts consumed body bytes, including failed reads.
    The reader has both a per-request cap and a cumulative network budget.
    """

    def __init__(self, url, *, max_read_bytes=MAX_RANGE_BYTES,
                 max_total_bytes=MAX_RANGE_BYTES + DIRECTORY_BUDGET_BYTES,
                 max_archive_bytes=MAX_ARCHIVE_BYTES, timeout=30):
        super().__init__()
        self.url = url
        self.max_read_bytes = min(_positive_integer(max_read_bytes, "max_read_bytes"), MAX_RANGE_BYTES)
        self.max_total_bytes = _positive_integer(max_total_bytes, "max_total_bytes")
        self.timeout = timeout
        self.network_bytes = 0
        self.range_requests = 0
        self._position = 0
        self._headers = {"User-Agent": "sleep-g3-research/0.1", "Accept-Encoding": "identity"}
        request = urllib.request.Request(url, headers=self._headers, method="HEAD")
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if response.status != 200:
                raise ValueError("archive HEAD must return status 200")
            self.size = _content_length(response)
            if not 0 < self.size <= _positive_integer(max_archive_bytes, "max_archive_bytes"):
                raise ValueError("archive size exceeds cap or is empty")
            if response.headers.get("Content-Encoding", "identity").lower() != "identity":
                raise ValueError("encoded archive responses are unsupported")
            etag = response.headers.get("ETag")
            modified = response.headers.get("Last-Modified")
            self._validator = etag if etag and not etag.startswith("W/") else modified
            self._etag = etag

    def readable(self):
        return not self.closed

    def seekable(self):
        return not self.closed

    def tell(self):
        self._checkClosed()
        return self._position

    def seek(self, offset, whence=io.SEEK_SET):
        self._checkClosed()
        if not isinstance(offset, int):
            raise TypeError("seek offset must be an integer")
        bases = {io.SEEK_SET: 0, io.SEEK_CUR: self._position, io.SEEK_END: self.size}
        if whence not in bases:
            raise ValueError("invalid seek whence")
        position = bases[whence] + offset
        if position < 0:
            raise ValueError("negative seek position")
        self._position = position
        return position

    def read(self, size=-1):
        self._checkClosed()
        if not isinstance(size, int):
            raise TypeError("read size must be an integer")
        available = max(0, self.size - self._position)
        length = available if size < 0 else min(size, available)
        if length == 0:
            return b""
        if length > self.max_read_bytes:
            raise ValueError("requested HTTP range exceeds per-read byte cap")
        if self.network_bytes + length > self.max_total_bytes:
            raise ValueError("HTTP ranges exceed cumulative network byte budget")
        start, end = self._position, self._position + length - 1
        headers = {**self._headers, "Range": f"bytes={start}-{end}"}
        if self._validator:
            headers["If-Range"] = self._validator
        request = urllib.request.Request(self.url, headers=headers)
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            self.range_requests += 1
            if response.status != 206:
                raise ValueError("server did not honor Range with status 206; body not read")
            match = _CONTENT_RANGE.fullmatch(response.headers.get("Content-Range", ""))
            if match is None or tuple(map(int, match.groups())) != (start, end, self.size):
                raise ValueError("response Content-Range does not match requested archive range")
            if _content_length(response) != length:
                raise ValueError("range Content-Length does not match requested length")
            if response.headers.get("Content-Encoding", "identity").lower() != "identity":
                raise ValueError("encoded range responses are unsupported")
            if self._etag and response.headers.get("ETag", self._etag) != self._etag:
                raise ValueError("archive ETag changed between range requests")
            data = response.read(length)
            self.network_bytes += len(data)
            extra = response.read(1)
            self.network_bytes += len(extra)
            if len(data) != length or extra:
                raise ValueError("range body length does not match Content-Length")
        self._position += length
        return data

    def readinto(self, buffer):
        data = self.read(len(buffer))
        buffer[:len(data)] = data
        return len(data)


def _existing_receipt(relative, destination, expected, byte_limit, network_bytes=0):
    if not destination.exists() and not destination.is_symlink():
        return None
    if not destination.is_file():
        raise ValueError("existing destination is not a regular file: " + relative)
    size = destination.stat().st_size
    if size > byte_limit:
        raise ValueError("existing file exceeds byte budget: " + relative)
    digest = sha256_file(destination)
    if digest != expected:
        raise ValueError("existing file checksum mismatch: " + relative)
    return {"path": relative, "bytes": size, "sha256": digest, "reused": True,
            "transport": "http_range_zip", "network_bytes": network_bytes}


def download_from_archive(relative, destination, expected, byte_limit=MAX_RANGE_BYTES):
    """Fetch only one named member, checking size, ZIP CRC, and catalog SHA256.

    ``byte_limit`` bounds the uncompressed selected file. Network traffic is
    separately bounded by that limit plus 8 MB for ZIP directory/header reads.
    ZIP64 interpretation and decompression are handled by ``zipfile``. No
    archive path is ever used to choose the destination, and no extraction
    API or archive-wide CRC test is called. Existing mismatches are retained.
    """
    _positive_integer(byte_limit, "byte_limit")
    if not isinstance(relative, str) or not relative or "\\" in relative or "\x00" in relative:
        raise ValueError("relative must be a safe POSIX catalog path")
    catalog_path = PurePosixPath(relative)
    if catalog_path.is_absolute() or ".." in catalog_path.parts or str(catalog_path) != relative or relative == ".":
        raise ValueError("relative must be a safe POSIX catalog path")
    if not isinstance(expected, str) or re.fullmatch(r"[0-9a-fA-F]{64}", expected) is None:
        raise ValueError("expected must be a catalog SHA256 digest")
    expected = expected.lower()
    destination = Path(destination)
    existing = _existing_receipt(relative, destination, expected, byte_limit)
    if existing is not None:
        return existing
    with HTTPRangeReader(ARCHIVE_URL, max_total_bytes=min(byte_limit, MAX_RANGE_BYTES) + DIRECTORY_BUDGET_BYTES) as remote:
        with zipfile.ZipFile(remote) as archive:
            accepted_names = {relative, *(prefix + relative for prefix in ARCHIVE_PREFIXES)}
            matches = [info for info in archive.infolist() if info.filename in accepted_names]
            if len(matches) != 1 or matches[0].is_dir():
                roots = sorted({info.filename.split("/")[0] for info in archive.infolist()})
                raise ValueError("archive must contain exactly one matching file: " + relative
                                 + "; archive root names=" + repr(roots[:5]))
            info = matches[0]
            if info.file_size > byte_limit or info.compress_size > MAX_RANGE_BYTES:
                raise ValueError("selected archive member exceeds byte budget: " + relative)
            if info.flag_bits & 1:
                raise ValueError("encrypted archive members are unsupported")
            with archive.open(info, "r") as member:
                payload = member.read(byte_limit + 1)
            if len(payload) > byte_limit or len(payload) != info.file_size:
                raise ValueError("selected archive member size mismatch or byte budget exceeded")
            digest = hashlib.sha256(payload).hexdigest()
            if digest != expected:
                raise ValueError("download checksum mismatch: " + relative)
        network_bytes = remote.network_bytes
        range_requests = remote.range_requests
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=destination.parent, prefix=destination.name + ".",
                                         suffix=".partial", delete=False) as output:
            temporary = Path(output.name)
            output.write(payload)
            output.flush()
            os.fsync(output.fileno())
        # Atomic no-replace publication: a concurrent writer cannot be overwritten.
        # Link+unlink preserves rename's atomic visibility without POSIX overwrite.
        try:
            os.link(temporary, destination)
        except FileExistsError:
            return _existing_receipt(relative, destination, expected, byte_limit, network_bytes)
        return {"path": relative, "bytes": len(payload), "sha256": digest, "reused": False,
                "transport": "http_range_zip", "network_bytes": network_bytes,
                "range_requests": range_requests, "archive_member": info.filename,
                "compressed_bytes": info.compress_size}
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
