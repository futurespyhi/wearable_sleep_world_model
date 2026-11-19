"""Past-only stage windows, training-history scaling, and audited cache IO."""

from __future__ import annotations

from dataclasses import dataclass, fields
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
from time import perf_counter
from typing import Any

import numpy as np
from scipy.io import loadmat

from sleep_g3 import data as g3
from sleep_g3.protocol import participant_split, read_catalog, select_records, sha256_file, write_json
from sleep_g3.runner import _acquisition, _window_kwargs

from . import cache_gate
from .timestamps import inspect_timestamps


STAGES = ("Wake", "Light", "Deep", "REM")
ENDPOINTS = (9, 29, 59)
HISTORY_EPOCHS = HORIZON_EPOCHS = 60
HISTORY_FEATURES = ("hr_mean", "hr_std", "hr_count", "acc_norm_std", "acc_diff_rms", "acc_count")
_HISTORY_COLUMNS = tuple(g3.FEATURE_NAMES.index(name) for name in HISTORY_FEATURES)
LABEL_MAP = np.array([0, 1, 1, 2, 3, -1], dtype=np.int8)
CACHE_SCHEMA = "stage_forecast_raw_windows_v1"
SENSORS_AND_LABEL = ("hr.csv", "motion.csv", "labels.mat")


@dataclass(frozen=True)
class StageWindows:
    history: np.ndarray
    stage: np.ndarray
    future_hr: np.ndarray
    future_hr_mask: np.ndarray
    current_stage: np.ndarray
    participant: np.ndarray
    night: np.ndarray
    origin: np.ndarray
    origin_time: np.ndarray


def map_stages(raw: Any) -> np.ndarray:
    # G3 already rejects non-vector, nonfinite, and unrecognized expert codes.
    g3._validate_labels(raw)
    return LABEL_MAP[np.asarray(raw).reshape(-1).astype(np.int64)]


class SensorFailure(ValueError):
    def __init__(self, path: Path, reason: ValueError, start: float, stage: np.ndarray):
        super().__init__(str(reason))
        self.path, self.start, self.stage = path, start, stage


def _counts_summary(count: np.ndarray) -> dict[str, int | float]:
    return {
        "min": int(count.min()),
        "median": float(np.median(count)),
        "max": int(count.max()),
        "nonempty_epochs": int(np.count_nonzero(count)),
        "epochs_with_two_or_more_samples": int(np.count_nonzero(count >= 2)),
    }


class SensorAuditFailure(ValueError):
    def __init__(self, reports):
        self.reports = reports
        reasons = {name: (report.get("error") or report.get("errors") or "see events") for name, report in reports.items()
                   if report["status"] != "complete"}
        super().__init__(f"sensor audit failed: {reasons}")


def load_stage_night(path: Path, participant: str | None = None, night: str | None = None,
                     *, policy=None, verified_sources=None):
    """Read and align G3 wrist features with the uncollapsed expert labels."""
    path = Path(path)
    mat = loadmat(path / "labels.mat", squeeze_me=True)
    if "recStart" not in mat or "expert_label" not in mat:
        raise ValueError("labels.mat requires recStart and expert_label")
    start = g3.parse_rec_start(mat["recStart"])
    stage = map_stages(mat["expert_label"])

    sensor, reports = {}, {}
    for kind, name in (("hr", "hr.csv"), ("acc", "motion.csv")):
        if policy is None:
            try:
                sensor[kind], reports[kind] = g3._aggregate_sensor(
                    path / name, start, len(stage), kind, collect_intervals=True
                )
            except ValueError as reason:
                raise SensorFailure(path / name, reason, start, stage) from reason
        else:
            from .timestamp_policy import aggregate_with_policy

            relative = f"{participant or path.parent.name}/{night or path.name}/{name}"
            source = verified_sources[name]
            if source["status"] != "verified":
                reports[kind] = {"status": "failed", "file": relative, "error": source["error"]}
                continue
            try:
                sensor[kind], reports[kind] = aggregate_with_policy(
                    path / name, start, len(stage), kind, relative=relative,
                    receipt_sha256=source["sha256"], policy=policy,
                )
            except Exception as error:
                reports[kind] = {"status": "failed", "file": relative,
                                 "error": f"{type(error).__name__}: {error}"}
            if reports[kind]["status"] != "complete":
                continue
        reports[kind]["samples_per_epoch"] = _counts_summary(sensor[kind]["count"])

    if policy is not None and any(report["status"] != "complete" for report in reports.values()):
        raise SensorAuditFailure(reports)

    hr, acc = sensor["hr"], sensor["acc"]
    features = np.column_stack([
        hr["mean"], hr["std"], acc["mean"], acc["std"], acc["diff_rms"], hr["count"], acc["count"],
    ])
    metadata = {
        "recording_start_unix": start,
        "recording_end_unix": start + len(stage) * g3.EPOCH_SECONDS,
        "epochs": len(stage),
        "label_source": "expert_label",
        "reference_stage_counts": dict(zip(STAGES, np.bincount(stage[stage >= 0], minlength=4).tolist())),
        "unknown_label_epochs": int(np.count_nonzero(stage < 0)),
        **reports,
    }
    # The G3 binary view serves only its shared origin-selection and coverage code.
    wake = np.where(stage < 0, -1, stage == 0).astype(np.int8)
    episode = g3.Episode(
        participant or path.parent.name,
        night or path.name,
        start + np.arange(len(stage), dtype=np.float64) * g3.EPOCH_SECONDS,
        features,
        wake,
        metadata,
    )
    return episode, stage


def build_stage_windows(episode: g3.Episode, stage: np.ndarray, **window_kwargs):
    """Use the same G3 origins and keep future targets outside model inputs."""
    if stage.shape != episode.wake.shape or not np.isin(stage, [-1, 0, 1, 2, 3]).all():
        raise ValueError("stage labels must match the epochs with values -1..3")
    raw = g3.build_windows([episode], **window_kwargs)
    times = raw["origin_time"]
    origins = np.rint((times - episode.epoch_start[0]) / g3.EPOCH_SECONDS).astype(np.int64)
    horizon = raw["target"].shape[1]
    future_index = origins[:, None] + np.arange(horizon)[None, :]
    observed = future_index < len(stage)
    y_stage = np.full(future_index.shape, -1, dtype=np.int8)
    y_hr = np.full(future_index.shape, np.nan, dtype=np.float64)
    y_stage[observed] = stage[future_index[observed]]
    y_hr[observed] = episode.features[future_index[observed], g3.FEATURE_NAMES.index("hr_mean")]
    return StageWindows(
        raw["history"][..., _HISTORY_COLUMNS],
        y_stage,
        y_hr,
        np.isfinite(y_hr),
        stage[origins - 1],
        raw["participant"],
        raw["night"],
        origins,
        times,
    ), raw["report"]


@dataclass(frozen=True)
class Standardizer:
    center: np.ndarray
    scale: np.ndarray

    @property
    def hr_center(self) -> float:
        return float(self.center[0])

    @property
    def hr_scale(self) -> float:
        return float(self.scale[0])

    def transform(self, history: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        values, hr_valid, acc_valid = _valid_continuous_values(history)
        standardized = np.where(np.isfinite(values), (values - self.center) / self.scale, 0)
        hr = np.concatenate([
            standardized[..., :2], np.log1p(history[..., 2:3]), hr_valid,
        ], axis=-1)
        acc = np.concatenate([
            standardized[..., 2:], np.log1p(history[..., 5:6]), acc_valid[..., None],
        ], axis=-1)
        return hr.astype(np.float32), acc.astype(np.float32)


def _valid_continuous_values(history: np.ndarray):
    hr_valid = np.isfinite(history[..., :2]) & (history[..., 2:3] > 0)
    acc_valid = (history[..., 5] >= 2) & np.isfinite(history[..., 3:5]).all(axis=-1)
    values = np.concatenate([
        np.where(hr_valid, history[..., :2], np.nan),
        np.where(acc_valid[..., None], history[..., 3:5], np.nan),
    ], axis=-1)
    return values, hr_valid, acc_valid


def fit_standardizer(training: StageWindows) -> Standardizer:
    """Fit on distinct epochs that appear in retained training histories."""
    n, length, _ = training.history.shape
    if not n:
        raise ValueError("standardization requires at least one training history")
    # Integer epoch identities avoid floating-point rounding and repeated weighting.
    _, nights = np.unique(
        np.stack([training.participant, training.night], axis=-1), axis=0, return_inverse=True
    )
    indices = training.origin[:, None] + np.arange(-length, 0)[None, :]
    coordinates = np.stack([np.broadcast_to(nights[:, None], indices.shape), indices], axis=-1)
    _, first = np.unique(coordinates.reshape(-1, 2), axis=0, return_index=True)
    values, _, _ = _valid_continuous_values(training.history.reshape(-1, len(HISTORY_FEATURES))[first])
    center = np.zeros(4)
    scale = np.ones(4)
    for channel, column in enumerate(values.T):
        finite = column[np.isfinite(column)]
        if finite.size:
            center[channel] = finite.mean()
            deviation = finite.std()
            if deviation > 0:
                scale[channel] = deviation
    if not np.isfinite(values[:, 0]).any():
        raise ValueError("no valid training history HR means")
    return Standardizer(center, scale)


def _acquired_records(source_root: Path, config: dict):
    manifest_path = source_root / "manifests" / "acquisition.json"
    manifest = _acquisition(source_root, config)
    if manifest["test_downloaded"] is not False:
        raise ValueError("acquisition did not preserve the sealed test split")
    raw_root = source_root / "raw" / "bidsleep_1.0.1"
    catalog_path = raw_root / "SHA256SUMS.txt"
    if sha256_file(catalog_path) != manifest["catalog_sha256"]:
        raise ValueError("catalog changed after acquisition")
    catalog = read_catalog(catalog_path)
    roster = {
        parts[0]
        for entry in catalog
        if len(parts := entry.split("/")) == 3 and parts[2] == "labels.mat"
    }
    split = participant_split(roster, seed=config["split_seed"])
    if manifest["split"] != split or [len(split[k]) for k in ("train", "validation", "test_sealed")] != [33, 7, 7]:
        raise ValueError("acquisition differs from the frozen 33/7/7 participant split")
    expected = select_records(
        catalog, split, config["pilot_train_subjects"], config["pilot_validation_subjects"],
        config["pilot_nights_per_subject"],
    )
    if manifest["selected_records"] != expected:
        raise ValueError("acquisition differs from the frozen catalog prefix")
    receipts = {row["path"]: row for row in manifest["files"]}
    if len(receipts) != len(manifest["files"]):
        raise ValueError("duplicate acquisition receipts")
    expected_payloads = {
        f"{row['participant']}/{row['night']}/{name}"
        for row in expected
        for name in SENSORS_AND_LABEL
    }
    observed_payloads = {name for name in receipts if name.endswith(SENSORS_AND_LABEL)}
    if expected_payloads != observed_payloads:
        raise ValueError("acquisition payload receipt inventory differs from frozen records")
    for relative in sorted(expected_payloads):
        if receipts[relative]["sha256"] != catalog[relative]:
            raise ValueError(f"acquisition receipt differs from release checksum: {relative}")
    return raw_root, manifest, sha256_file(manifest_path), receipts


def _write_windows(path: Path, windows: StageWindows) -> None:
    temp = path.with_suffix(".tmp")
    with temp.open("wb") as stream:
        np.savez_compressed(stream, **{field.name: getattr(windows, field.name) for field in fields(windows)})
    temp.replace(path)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _verify_sources(relative, raw_root, receipts):
    verified = {}
    for name in SENSORS_AND_LABEL:
        raw_relative = str(relative / name)
        receipt = receipts[raw_relative]
        source = {"path": raw_relative, "sha256": receipt["sha256"], "bytes": receipt["bytes"]}
        try:
            raw = raw_root / raw_relative
            source["observed_bytes"] = raw.stat().st_size
            source["observed_sha256"] = sha256_file(raw)
            if source["observed_bytes"] != source["bytes"] or source["observed_sha256"] != source["sha256"]:
                raise ValueError(f"raw file changed after acquisition: {raw_relative}")
            source["status"] = "verified"
        except (OSError, ValueError) as error:
            source.update(status="failed", error=str(error))
        verified[name] = source
    return verified


def build_cache(source_root: Path, protocol_path: Path, cache_root: Path,
                timestamp_policy=None, reference_cache=None) -> dict:
    """Verify the frozen cohort and record every night; expose only a complete cache."""
    source_root, protocol_path, cache_root = map(Path, (source_root, protocol_path, cache_root))
    source_root, cache_root = source_root.resolve(), cache_root.resolve()
    if cache_root == source_root or source_root in cache_root.parents or cache_root in source_root.parents:
        raise ValueError("stage cache must be outside the historical acquisition and enclosing directory")
    cache_root.mkdir(parents=True, exist_ok=True)
    audit_path = cache_root / "audit.json"
    protocol_sha256 = sha256_file(protocol_path)
    # Exclusive start prevents overwriting a failed audit or interleaving two jobs.
    with (cache_root / "audit_started").open("x"):
        pass
    start_time = perf_counter()
    audit = {
        "schema": CACHE_SCHEMA, "status": "running", "started_utc": _now(),
        "source_root": str(source_root), "cache_root": str(cache_root),
        "protocol_sha256": protocol_sha256, "test_accessed": False,
        "host": platform.node(), "slurm_job_id": os.environ.get("SLURM_JOB_ID"),
        "stage_data_sha256": sha256_file(__file__), "g3_data_sha256": sha256_file(g3.__file__),
        "features": list(HISTORY_FEATURES), "stages": list(STAGES),
        "nights": [], "failures": [],
    }
    write_json(audit_path, audit)
    try:
        config = json.loads(protocol_path.read_text())
        definition = tuple(
            config[key]
            for key in ("epoch_seconds", "history_epochs", "horizon_epochs", "stride_epochs",
                        "minimum_history_coverage", "split_seed")
        )
        if definition != (30, HISTORY_EPOCHS, HORIZON_EPOCHS, 10, 0.8, 40):
            raise ValueError("G3 protocol does not match the selected stage origin definition")
        raw_root, manifest, acquisition_hash, receipts = _acquired_records(source_root, config)
        audit.update(
            acquisition_sha256=acquisition_hash,
            catalog_sha256=manifest["catalog_sha256"],
            split_seed=manifest["split_seed"],
            split_sizes={key: len(value) for key, value in manifest["split"].items()},
            selected_records=manifest["selected_records"],
            expected_nights=len(manifest["selected_records"]),
        )
        policy = None
        references = {}
        window_args = _window_kwargs(config)
        if timestamp_policy is not None:
            policy_path = Path(timestamp_policy).resolve()
            policy = json.loads(policy_path.read_text())
            audit.update(timestamp_policy=str(policy_path), timestamp_policy_sha256=sha256_file(policy_path))
            cache_gate.verify_policy_manifest(audit, policy, manifest)
            references = cache_gate.reference_index(reference_cache, policy, manifest["selected_records"], audit)
        for record in manifest["selected_records"]:
            begin_night = perf_counter()
            relative = Path(record["participant"], record["night"])
            night = dict(record)
            try:
                verified = _verify_sources(relative, raw_root, receipts)
                night["verified_sources"] = verified
                for name in (SENSORS_AND_LABEL if policy is None else ("labels.mat",)):
                    if verified[name]["status"] != "verified":
                        raise ValueError(verified[name]["error"])
                episode, stage = load_stage_night(
                    raw_root / relative, record["participant"], record["night"],
                    policy=policy, verified_sources=verified,
                )
                night["metadata"] = episode.metadata
                windows, coverage = build_stage_windows(episode, stage, **window_args)
                if policy is not None:
                    night["mask_coverage"] = cache_gate.mask_coverage(episode, windows, window_args)
                    if str(relative) in references:
                        strict_episode, strict_stage = load_stage_night(raw_root / relative)
                        strict_windows, _ = build_stage_windows(strict_episode, strict_stage, **window_args)
                        night["strict_reference"] = cache_gate.compare_strict(
                            episode, stage, windows, strict_episode, strict_stage, strict_windows,
                            references[str(relative)],
                        )
                cache_name = f"{record['participant']}_{record['night']}.npz"
                cache_path = cache_root / cache_name
                _write_windows(cache_path, windows)
                night.update(
                    status="complete", cache=cache_name, cache_sha256=sha256_file(cache_path),
                    windows=coverage,
                )
            except Exception as error:
                night.update(status="failed", error=f"{type(error).__name__}: {error}")
                if isinstance(error, SensorAuditFailure):
                    night["sensor_reports"] = error.reports
                if isinstance(error, SensorFailure):
                    night["file"] = str(error.path.relative_to(raw_root))
                    if "timestamp" in str(error):
                        try:
                            night["timestamp_diagnosis"] = inspect_timestamps(
                                error.path, error.start, error.stage, g3.CSV_CHUNK_ROWS,
                            )
                        except Exception as diagnosis_error:
                            night["diagnosis_error"] = f"{type(diagnosis_error).__name__}: {diagnosis_error}"
                audit["failures"].append(night)
            night["elapsed_seconds"] = perf_counter() - begin_night
            audit["nights"].append(night)
            write_json(audit_path, audit)
            print(f"{record['partition']} {relative}: {night['status']}", night.get("error", ""), flush=True)
        audit["partitions"] = {
            key: {
                "complete_nights": sum(r["status"] == "complete" and r["partition"] == key for r in audit["nights"]),
                "expected_nights": sum(r["partition"] == key for r in audit["nights"]),
                "retained_origins_in_completed_nights": sum(
                    r["windows"]["retained_origins"]
                    for r in audit["nights"] if r["status"] == "complete" and r["partition"] == key
                ),
            }
            for key in ("train", "validation")
        }
        if not audit["failures"]:
            if policy is not None:
                cache_gate.verify_complete_evidence(audit, policy, manifest)
            audit["cache_identity_sha256"] = cache_gate.identity(audit)
        audit["status"] = "failed" if audit["failures"] else "complete"
    except Exception as error:
        audit.update(status="failed", error=f"{type(error).__name__}: {error}")
    audit.update(elapsed_seconds=perf_counter() - start_time, finished_utc=_now())
    write_json(audit_path, audit)
    return audit


def load_cache(cache_root: Path, timestamp_policy=None) -> dict[str, StageWindows]:
    cache_root = Path(cache_root)
    audit = json.loads((cache_root / "audit.json").read_text())
    if audit["status"] != "complete" or audit["schema"] != CACHE_SCHEMA or audit["test_accessed"] is not False:
        raise ValueError("a complete train/validation-only stage audit is required")
    if timestamp_policy is not None or audit.get("timestamp_policy_sha256"):
        policy_path = Path(timestamp_policy) if timestamp_policy is not None else (
            Path(__file__).resolve().parents[1] / "expanded_timestamp_policy.json"
        )
        if sha256_file(policy_path) != audit.get("timestamp_policy_sha256"):
            raise ValueError("expanded cache has a different timestamp policy or no applied policy")
        manifest_path = Path(audit["source_root"]) / "manifests" / "acquisition.json"
        if sha256_file(manifest_path) != audit["acquisition_sha256"]:
            raise ValueError("acquisition manifest changed since audit")
        cache_gate.verify_complete_evidence(audit, json.loads(policy_path.read_text()),
                                            json.loads(manifest_path.read_text()))
        if cache_gate.identity(audit) != audit.get("cache_identity_sha256"):
            raise ValueError("expanded cache identity differs from its recorded inputs")
    expected = audit["selected_records"]
    actual = [
        {key: rec[key] for key in ("participant", "night", "partition")}
        for rec in audit["nights"] if rec["status"] == "complete"
    ]
    if expected != actual or len(expected) != len(audit["nights"]):
        raise ValueError("stage cache inventory differs from the audited acquisition")
    datasets = {"train": [], "val": []}
    fields_names = [field.name for field in fields(StageWindows)]
    partition_key = {"train": "train", "validation": "val"}
    for record in audit["nights"]:
        cache = cache_root / record["cache"]
        if sha256_file(cache) != record["cache_sha256"]:
            raise ValueError(f"stage cache changed: {cache.name}")
        with np.load(cache, allow_pickle=False) as values:
            datasets[partition_key[record["partition"]]].append({key: values[key] for key in fields_names})
    return {
        partition: StageWindows(**{
            key: np.concatenate([night[key] for night in nights]) for key in fields_names
        })
        for partition, nights in datasets.items()
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--protocol", required=True, type=Path)
    parser.add_argument("--cache-root", required=True, type=Path)
    parser.add_argument("--timestamp-policy", type=Path)
    parser.add_argument("--reference-cache", type=Path)
    args = parser.parse_args()
    audit = build_cache(args.source_root, args.protocol, args.cache_root, args.timestamp_policy, args.reference_cache)
    print(json.dumps({key: audit[key] for key in ("status", "cache_root", "elapsed_seconds")}, indent=2))
    return 0 if audit["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
