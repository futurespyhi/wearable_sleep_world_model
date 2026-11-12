"""Bounded downloads of the public BIDSleep release, with immutable selection."""

import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from .protocol import participant_split, read_catalog, select_records, sha256_file, write_json

BASE_URL = "https://physionet.org/files/bidsleep-dataset/1.0.1/"


def download(relative, destination, expected=None, byte_limit=200_000_000):
    destination = Path(destination)
    if destination.exists():
        if expected is not None and sha256_file(destination) != expected:
            raise ValueError("existing file checksum mismatch: " + relative)
        return {"path": relative, "bytes": destination.stat().st_size,
                "sha256": sha256_file(destination), "reused": True}
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


def acquire(root, train_subjects=4, val_subjects=2, nights=1, seed=40,
            metadata_only=False, max_total_bytes=900_000_000, archive_transport=False):
    root = Path(root)
    raw = root / "raw" / "bidsleep_1.0.1"
    catalog_record = download("SHA256SUMS.txt", raw / "SHA256SUMS.txt", byte_limit=2_000_000)
    catalog = read_catalog(raw / "SHA256SUMS.txt")
    roster = {p.split("/")[0] for p in catalog if p.startswith("Bidslab") and len(p.split("/")) == 3}
    split = participant_split(roster, seed)
    records = select_records(catalog, split, train_subjects, val_subjects, nights)
    manifest_path = root / "manifests" / "acquisition.json"
    identity = {"source": BASE_URL, "catalog_sha256": catalog_record["sha256"],
                "split_seed": seed, "split": split, "selected_records": records}
    if manifest_path.exists():
        previous = json.loads(manifest_path.read_text())
        if any(previous.get(k) != v for k, v in identity.items()):
            raise ValueError("acquisition selection changed; use a new root")
    receipt = {**identity, "status": "metadata_ready", "test_downloaded": False,
               "created_utc": datetime.now(timezone.utc).isoformat(), "files": [catalog_record],
               "byte_budget": max_total_bytes,
               "transport_mode": "selected_zip_members" if archive_transport else "individual_files",
               "retained_partial_bytes": sum(p.stat().st_size for p in raw.rglob("*.partial")),
               "selection_rule": "hash participant split; Bidslab00 reserved train; first catalog nights; no label selection"}
    write_json(manifest_path, receipt)
    try:
        for relative in ("LICENSE.txt", "README.md"):
            receipt["files"].append(download(relative, raw / relative, catalog[relative], 2_000_000))
        if not metadata_only:
            for record in records:
                for name in ("hr.csv", "labels.mat", "motion.csv"):
                    relative = f"{record['participant']}/{record['night']}/{name}"
                    remaining = max_total_bytes - receipt["retained_partial_bytes"] - sum(r["bytes"] for r in receipt["files"])
                    if remaining <= 0:
                        raise ValueError("acquisition byte budget exhausted")
                    fetch_file = download
                    if archive_transport and name == "motion.csv":
                        from .remote_zip import download_from_archive
                        fetch_file = download_from_archive
                    receipt["files"].append(fetch_file(relative, raw / relative, catalog[relative],
                                                       min(200_000_000, remaining)))
                    write_json(manifest_path, receipt)
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
