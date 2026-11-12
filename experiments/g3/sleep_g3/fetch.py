"""Bounded downloads of the public BIDSleep release, with immutable selection."""

import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from .protocol import participant_split, read_catalog, select_records, sha256_file, write_json

BASE_URL = "https://physionet.org/files/bidsleep-dataset/1.0.1/"
FILE_BYTE_LIMIT = 200_000_000
METADATA_BYTE_LIMIT = 2_000_000
RECORD_FILES = ("hr.csv", "labels.mat", "motion.csv")


def _positive_budget(value):
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError("byte budget must be a positive integer")
    return value


def download(relative, destination, expected=None, byte_limit=200_000_000):
    _positive_budget(byte_limit)
    destination = Path(destination)
    if destination.exists() or destination.is_symlink():
        if not destination.is_file():
            raise ValueError("existing destination is not a regular file: " + relative)
        size = destination.stat().st_size
        if size > byte_limit:
            raise ValueError("existing file exceeds byte budget: " + relative)
        digest = sha256_file(destination)
        if expected is not None and digest != expected:
            raise ValueError("existing file checksum mismatch: " + relative)
        return {"path": relative, "bytes": size, "sha256": digest, "reused": True}
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".partial")
    count = 0
    request = urllib.request.Request(BASE_URL + relative, headers={"User-Agent": "sleep-g3-research/0.1"})
    with urllib.request.urlopen(request, timeout=30) as response, open(temporary, "wb") as output:
        content_length = response.headers.get("Content-Length")
        if content_length and int(content_length) > byte_limit:
            raise ValueError("download exceeds remaining byte budget")
        for chunk in iter(lambda: response.read(1024 * 1024), b""):
            count += len(chunk)
            if count > byte_limit:
                raise ValueError("download exceeded byte budget")
            output.write(chunk)
    digest = sha256_file(temporary)
    if expected is not None and digest != expected:
        raise ValueError("download checksum mismatch: " + relative)
    temporary.replace(destination)
    return {"path": relative, "bytes": count, "sha256": digest, "reused": False}


def _reuse_manifest(root, reuse_root):
    if reuse_root is None:
        return None
    reuse_root = Path(reuse_root).resolve()
    if root.resolve() == reuse_root:
        raise ValueError("reuse root must differ from acquisition root")
    manifest_path = reuse_root / "manifests" / "acquisition.json"
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("status") != "complete" or manifest.get("test_downloaded") is not False:
        raise ValueError("reuse requires a complete acquisition with sealed test data")
    if manifest.get("source") != BASE_URL:
        raise ValueError("reuse source release does not match")
    eligible = {"LICENSE.txt", "README.md"}
    seen = set()
    for record in manifest["selected_records"]:
        pid, night, partition = record["participant"], record["night"], record["partition"]
        if (partition not in ("train", "validation")
                or pid not in manifest["split"][partition]
                or pid in manifest["split"]["test_sealed"]
                or not isinstance(night, str) or not night.isdecimal()
                or (pid, night) in seen):
            raise ValueError("reuse acquisition has an invalid selected record")
        seen.add((pid, night))
        eligible.update(f"{pid}/{night}/{name}" for name in RECORD_FILES)
    files = {}
    for record in manifest["files"]:
        relative = record["path"]
        if relative in eligible:
            if relative in files:
                raise ValueError("reuse acquisition has duplicate file receipts")
            files[relative] = record
    return {"root": reuse_root, "manifest": manifest, "files": files,
            "manifest_sha256": sha256_file(manifest_path)}


def _reuse_file(relative, destination, expected, byte_limit, reuse):
    if reuse is None or relative not in reuse["files"]:
        return None
    recorded = reuse["files"][relative]
    if recorded["sha256"] != expected:
        raise ValueError("reuse receipt checksum differs from catalog: " + relative)
    source = reuse["root"] / "raw" / "bidsleep_1.0.1" / relative
    resolved = source.resolve()
    # A linked source must still name the selected participant/night/file.
    parts = PurePosixPath(relative).parts
    if resolved.parts[-len(parts):] != parts:
        raise ValueError("reuse source resolves outside its selected record: " + relative)
    destination = Path(destination)
    if destination.exists() or destination.is_symlink():
        receipt = download(relative, destination, expected, byte_limit)
    else:
        if not source.is_file():
            raise ValueError("reuse source is not a regular file: " + relative)
        size = source.stat().st_size
        if size > byte_limit:
            raise ValueError("reuse file exceeds byte budget: " + relative)
        if size != recorded["bytes"] or sha256_file(source) != expected:
            raise ValueError("reuse source checksum or size mismatch: " + relative)
        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            destination.symlink_to(resolved)
        except FileExistsError:
            receipt = download(relative, destination, expected, byte_limit)
        else:
            receipt = {"path": relative, "bytes": size, "sha256": expected, "reused": True}
    if destination.is_symlink() and destination.resolve() == resolved:
        receipt.update({"reuse_method": "symlink", "reuse_source": str(resolved),
                        "network_bytes": 0})
    return receipt


def acquire(root, train_subjects=4, val_subjects=2, nights=1, seed=40,
            metadata_only=False, max_total_bytes=900_000_000, archive_transport=False,
            reuse_root=None, max_file_bytes=None):
    _positive_budget(max_total_bytes)
    max_file_bytes = FILE_BYTE_LIMIT if max_file_bytes is None else _positive_budget(max_file_bytes)
    root = Path(root)
    reuse = _reuse_manifest(root, reuse_root)
    raw = root / "raw" / "bidsleep_1.0.1"
    partial_bytes = sum(p.stat().st_size for p in raw.rglob("*.partial"))
    remaining = max_total_bytes - partial_bytes
    if remaining <= 0:
        raise ValueError("acquisition byte budget exhausted by retained partial files")
    catalog_record = download("SHA256SUMS.txt", raw / "SHA256SUMS.txt",
                              byte_limit=min(METADATA_BYTE_LIMIT, remaining))
    catalog = read_catalog(raw / "SHA256SUMS.txt")
    roster = {p.split("/")[0] for p in catalog if p.startswith("Bidslab") and len(p.split("/")) == 3}
    split = participant_split(roster, seed)
    records = select_records(catalog, split, train_subjects, val_subjects, nights)
    manifest_path = root / "manifests" / "acquisition.json"
    identity = {"source": BASE_URL, "catalog_sha256": catalog_record["sha256"],
                "split_seed": seed, "split": split, "selected_records": records}
    if reuse is not None and any(reuse["manifest"].get(key) != identity[key]
                                 for key in ("catalog_sha256", "split_seed", "split")):
        raise ValueError("reuse catalog or participant split does not match acquisition")
    if manifest_path.exists():
        previous = json.loads(manifest_path.read_text())
        if any(previous.get(k) != v for k, v in identity.items()):
            raise ValueError("acquisition selection changed; use a new root")
    receipt = {**identity, "status": "metadata_ready", "test_downloaded": False,
               "created_utc": datetime.now(timezone.utc).isoformat(), "files": [catalog_record],
               "byte_budget": max_total_bytes,
               "per_file_byte_budget": max_file_bytes,
               "byte_budget_scope": "selected files including reused files and retained partials",
               "transport_mode": "selected_zip_members" if archive_transport else "individual_files",
               "retained_partial_bytes": partial_bytes,
               "selection_rule": "hash participant split; Bidslab00 reserved train; first catalog nights; no label selection"}
    if reuse is not None:
        receipt.update({"reuse_root": str(reuse["root"]),
                        "reuse_acquisition_sha256": reuse["manifest_sha256"]})
    write_json(manifest_path, receipt)

    def fetch_selected(relative, per_file_limit, archive=False):
        remaining = max_total_bytes - partial_bytes - sum(r["bytes"] for r in receipt["files"])
        if remaining <= 0:
            raise ValueError("acquisition byte budget exhausted")
        limit = min(per_file_limit, remaining)
        destination = raw / relative
        result = _reuse_file(relative, destination, catalog[relative], limit, reuse)
        if result is None:
            fetch_file = download
            if archive:
                from .remote_zip import download_from_archive
                fetch_file = download_from_archive
            result = fetch_file(relative, destination, catalog[relative], limit)
        receipt["files"].append(result)
        write_json(manifest_path, receipt)

    try:
        for relative in ("LICENSE.txt", "README.md"):
            fetch_selected(relative, METADATA_BYTE_LIMIT)
        if not metadata_only:
            for record in records:
                for name in RECORD_FILES:
                    relative = f"{record['participant']}/{record['night']}/{name}"
                    fetch_selected(relative, max_file_bytes, archive_transport)
                print("downloaded", record["partition"], record["participant"], record["night"], flush=True)
            receipt["status"] = "complete"
        receipt["finished_utc"] = datetime.now(timezone.utc).isoformat()
        write_json(manifest_path, receipt)
    except BaseException as error:
        receipt["status"] = "interrupted" if isinstance(error, KeyboardInterrupt) else "failed"
        receipt["error"] = f"{type(error).__name__}: {error}"
        write_json(manifest_path, receipt)
        raise
    return {"status": receipt["status"], "participants_in_release": len(roster),
            "selected_nights": len(records), "split_counts": {k: len(v) for k, v in split.items()},
            "bytes": sum(r["bytes"] for r in receipt["files"]), "test_downloaded": False}
