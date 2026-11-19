"""Equivalence checks and cache identity for the fixed expanded audit."""

from collections import Counter
from dataclasses import fields
import hashlib
import json
from pathlib import Path

import numpy as np
from sleep_g3.protocol import sha256_file


def identity(audit):
    """Identify training input by source, policy, protocol and ordered cache bytes."""
    content = {key: audit[key] for key in ("acquisition_sha256", "protocol_sha256", "schema")}
    content["timestamp_policy_sha256"] = audit.get("timestamp_policy_sha256")
    content["records"] = [
        [row[key] for key in ("partition", "participant", "night", "cache_sha256")]
        for row in audit["nights"]
    ]
    return hashlib.sha256(json.dumps(content, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def reference_index(reference_root, policy, selected, audit):
    affected = {str(Path(event["path"]).parent) for event in policy["events"]}
    expected = {f"{r['participant']}/{r['night']}" for r in selected} - affected
    if len(expected) != 33 or len(selected) != 38:
        raise ValueError("expanded audit requires the original 33 strict nights and five affected nights")
    if reference_root is None or not (Path(reference_root) / "audit.json").exists():
        return {key: None for key in expected}
    root = Path(reference_root)
    path = root / "audit.json"
    published = Path(__file__).resolve().parents[3] / "reports/20261119-first-round/provenance.json"
    old_hash = json.loads(published.read_text())["audits"]["expanded-cache"]["audit_sha256"]
    if sha256_file(path) != old_hash:
        raise ValueError("strict reference audit differs from the published first-round SHA256")
    previous = json.loads(path.read_text())
    if (previous["selected_records"] != selected or previous["test_accessed"] is not False
            or previous["acquisition_sha256"] != audit["acquisition_sha256"]
            or previous["protocol_sha256"] != audit["protocol_sha256"]):
        raise ValueError("strict reference audit differs from selected protocol and acquisition")
    index = {f"{r['participant']}/{r['night']}": (root / r["cache"], r["cache_sha256"])
             for r in previous["nights"] if r["status"] == "complete"}
    if set(index) != expected:
        raise ValueError("strict reference nights differ from the original 33-night subset")
    audit.update(reference_audit_sha256=old_hash, reference_cache=str(root.resolve()))
    return index


def equal_values(name, actual, reference):
    """Require exact array and missingness equivalence, including float features."""
    if actual.dtype != reference.dtype or actual.shape != reference.shape:
        raise ValueError(f"strict reference shape or dtype differs for {name}")
    if not np.array_equal(actual, reference, equal_nan=actual.dtype.kind == "f"):
        raise ValueError(f"strict reference values differ for {name}")


def compare_strict(episode, stage, windows, strict_episode, strict_stage, strict_windows, reference):
    for name, actual, previous in (("labels", stage, strict_stage), ("features", episode.features, strict_episode.features),
                                   ("epoch_start", episode.epoch_start, strict_episode.epoch_start)):
        equal_values(name, actual, previous)
    for field in fields(windows):
        equal_values(field.name, getattr(windows, field.name), getattr(strict_windows, field.name))
    result = {"status": "identical", "epochs": len(stage), "origins": len(windows.origin),
              "full_epoch_reference": "strict G3 reaggregation", "prior_cache": "unavailable"}
    if reference is not None and reference[0].exists():
        path, checksum = reference
        if sha256_file(path) != checksum:
            raise ValueError(f"strict reference cache SHA mismatch for {path.name}")
        with np.load(path, allow_pickle=False) as old:
            for field in fields(windows):
                equal_values(field.name, getattr(windows, field.name), old[field.name])
        result.update(prior_cache="identical", prior_cache_sha256=checksum)
    return result


def mask_coverage(episode, windows, window_args):
    """Compare the same candidate origins before and after ACC count masking."""
    acc = episode.metadata["acc"]
    masked = np.asarray(acc["masked_epochs"], dtype=int)
    hr_count, acc_count = episode.features[:, 5], episode.features[:, 6]
    before_acc = acc_count.copy()
    for epoch in masked:
        if acc_count[epoch] != 0 or not np.isnan(episode.features[epoch, 2:5]).all():
            raise ValueError(f"incomplete ACC feature mask at epoch {epoch}")
        before_acc[epoch] = acc["masked_valid_sample_counts"][str(epoch)]
    before, after = (hr_count > 0) & (before_acc > 0), (hr_count > 0) & (acc_count > 0)
    result = {"epochs": masked.tolist(), "candidate_origins": [], "retained_origins": [],
              "coverage_rejected_origins": [], "lost_due_to_mask": [], "histories": []}
    length = window_args["history_epochs"]
    retained = set(windows.origin.tolist())
    for index in range(length, len(before) + 1, window_args["stride_epochs"]):
        if not ((index - length <= masked) & (masked < index)).any():
            continue
        section = slice(index - length, index)
        result["candidate_origins"].append(index)
        result["retained_origins" if index in retained else "coverage_rejected_origins"].append(index)
        if index not in retained and before[section].mean() >= window_args["min_history_coverage"]:
            result["lost_due_to_mask"].append(index)
        result["histories"].append({"origin": index, "joint_epochs_before": int(before[section].sum()),
                                    "joint_epochs_after": int(after[section].sum())})
    return result


def verify_policy_manifest(audit, policy, manifest):
    selected = manifest["selected_records"]
    if (policy["acquisition_sha256"] != audit["acquisition_sha256"]
            or policy["protocol_sha256"] != audit["protocol_sha256"]
            or selected != audit["selected_records"] or manifest["test_downloaded"] is not False
            or Counter(r["partition"] for r in selected) != {"train": 24, "validation": 14}):
        raise ValueError("expanded policy, protocol and fixed 38-night acquisition must agree")


def verify_complete_evidence(audit, policy, manifest):
    verify_policy_manifest(audit, policy, manifest)
    if audit["failures"] or audit["test_accessed"] is not False:
        raise ValueError("a completed train/validation audit without failures is required")
    receipts = {file["path"]: file for file in manifest["files"]}
    affected = {str(Path(event["path"]).parent) for event in policy["events"]}
    selected = manifest["selected_records"]
    if len(audit["nights"]) != len(selected):
        raise ValueError("expanded cache has incomplete night inventory")
    for row, record in zip(audit["nights"], selected):
        relative = f"{record['participant']}/{record['night']}"
        if row["status"] != "complete" or any(record[key] != row[key] for key in record):
            raise ValueError(f"night differs from manifest: {relative}")
        for name in ("hr.csv", "motion.csv", "labels.mat"):
            verified = row["verified_sources"][name]
            original = receipts[f"{relative}/{name}"]
            if (verified["status"] != "verified" or verified["sha256"] != original["sha256"]
                    or verified["bytes"] != original["bytes"]):
                raise ValueError(f"source identity mismatch: {relative}/{name}")
        for sensor, name in (("hr", "hr.csv"), ("acc", "motion.csv")):
            stream = row["metadata"][sensor]
            path = f"{relative}/{name}"
            if (stream["status"] != "complete" or stream["file"] != path
                    or stream["sha256"] != receipts[path]["sha256"]):
                raise ValueError(f"incomplete sensor audit for {path}")
            rules = [r for r in policy["events"] if r["path"] == path]
            def signature(event):
                return (tuple(event["rows"]), event["kind"], event["relation"], event["action"])
            if ({signature(ev) for ev in stream["events"] if ev["registered"]}
                    != {signature(rule) for rule in rules}):
                raise ValueError(f"registered audit events disagree with policy for {path}")
            expected_epochs = sorted({r["epoch"] for r in rules if r["action"] == "mask_acc_epoch"})
            if stream["masked_epochs"] != expected_epochs or (sensor == "acc" and
                    row["mask_coverage"]["epochs"] != expected_epochs):
                raise ValueError(f"applied epoch mask differs from policy for {path}")
        if relative not in affected and row.get("strict_reference", {}).get("status") != "identical":
            raise ValueError(f"missing strict reference comparison for {relative}")
