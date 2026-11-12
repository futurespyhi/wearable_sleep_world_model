"""Deterministic participant assignments before outcome inspection."""

import hashlib
import json
from pathlib import Path, PurePosixPath


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_catalog(path):
    entries = {}
    for line in Path(path).read_text().splitlines():
        if not line.strip():
            continue
        digest, relative = line.split(None, 1)
        relative = relative.strip().lstrip("*")
        candidate = PurePosixPath(relative)
        if candidate.is_absolute() or ".." in candidate.parts:
            raise ValueError("unsafe catalog path")
        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError("invalid SHA256 catalog entry")
        if relative in entries:
            raise ValueError("duplicate catalog entry")
        entries[relative] = digest
    return entries


def participant_split(participants, seed=40):
    roster = sorted(set(participants))
    if len(roster) < 10:
        raise ValueError("a release roster of at least ten participants is required")
    rank = lambda pid: hashlib.sha256((str(seed) + ":" + pid).encode()).hexdigest()
    # This participant was reserved for format inspection before any label read.
    reserved = ["Bidslab00"] if "Bidslab00" in roster else []
    remaining = sorted((p for p in roster if p not in reserved), key=rank)
    n_val = max(1, round(0.15 * len(roster)))
    n_test = max(1, round(0.15 * len(roster)))
    n_train = len(roster) - n_val - n_test
    train = reserved + remaining[:n_train - len(reserved)]
    val = remaining[n_train - len(reserved):n_train - len(reserved) + n_val]
    test = remaining[n_train - len(reserved) + n_val:]
    return {"train": train, "validation": val, "test_sealed": test}


def select_records(catalog, split, train_subjects=4, val_subjects=2, nights=1):
    if min(train_subjects, val_subjects, nights) < 1:
        raise ValueError("positive participant and night limits required")
    records = []
    for partition, count in (("train", train_subjects), ("validation", val_subjects)):
        if count > len(split[partition]):
            raise ValueError("requested participant limit exceeds split")
        for pid in split[partition][:count]:
            available = sorted({int(PurePosixPath(p).parts[1]) for p in catalog
                                if len(PurePosixPath(p).parts) == 3
                                and PurePosixPath(p).parts[0] == pid
                                and PurePosixPath(p).parts[1].isdigit()})
            complete = [n for n in available if all(
                f"{pid}/{n}/{name}" in catalog for name in ("hr.csv", "motion.csv", "labels.mat"))]
            if len(complete) < nights:
                raise ValueError("insufficient catalog nights; selection will not change silently")
            records.extend({"participant": pid, "night": str(n), "partition": partition}
                           for n in complete[:nights])
    if set(r["participant"] for r in records) & set(split["test_sealed"]):
        raise AssertionError("test participant selected")
    return records


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)
