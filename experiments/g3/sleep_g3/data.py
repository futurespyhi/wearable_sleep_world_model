"""Causal 30-second wrist-sensor features and periodic future-Wake windows."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Iterable

import numpy as np
import pandas as pd
from scipy.io import loadmat


EPOCH_SECONDS = 30.0
CSV_CHUNK_ROWS = 200_000
FEATURE_NAMES = (
    "hr_mean",
    "hr_std",
    "acc_norm_mean",
    "acc_norm_std",
    "acc_diff_rms",
    "hr_count",
    "acc_count",
)
feature_names = FEATURE_NAMES
SOURCE_URL = "https://physionet.org/content/bidsleep-dataset/1.0.1/"


@dataclass
class Episode:
    participant: str
    night: str
    epoch_start: np.ndarray
    features: np.ndarray
    wake: np.ndarray
    metadata: dict[str, Any]


def parse_rec_start(value: Any, timezone: str = "America/New_York") -> float:
    """Parse BIDSleep recStart, rejecting ambiguous or nonexistent local times.

    The inspected 1.0.1 files use ISO local-time text. Numeric Unix seconds
    are UTC. MATLAB datenums (600000..900000) have no offset and are localized
    to ``timezone``. Other numeric magnitudes are rejected instead of guessed.
    """
    array = np.asarray(value)
    if array.size == 1:
        value = array.reshape(-1)[0]
    elif array.dtype.kind in "US" and all(len(str(x)) == 1 for x in array.flat):
        value = "".join(str(x) for x in array.flat)
    else:
        raise ValueError("recStart must contain one timestamp")
    if isinstance(value, (int, float, np.integer, np.floating)):
        number = float(value)
        if not np.isfinite(number):
            raise ValueError("recStart is not finite")
        if 600_000 <= number <= 900_000:
            day = int(number)
            parsed = datetime.fromordinal(day) - timedelta(days=366)
            parsed += timedelta(seconds=(number - day) * 86_400)
        elif 100_000_000 <= number < 10_000_000_000:
            return number
        else:
            raise ValueError("recStart numeric value is neither Unix seconds nor a supported MATLAB datenum")
    else:
        if isinstance(value, (bytes, np.bytes_)):
            value = value.decode("ascii")
        if isinstance(value, (datetime, np.datetime64)):
            parsed = value
        elif isinstance(value, (str, np.str_)):
            try:
                parsed = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
            except ValueError as exc:
                raise ValueError("recStart must use an ISO date and time") from exc
        else:
            raise ValueError(f"Unsupported recStart type: {type(value).__name__}")
    timestamp = pd.Timestamp(parsed)
    if timestamp.tzinfo is None:
        try:
            timestamp = timestamp.tz_localize(timezone, ambiguous="raise", nonexistent="raise")
        except Exception as exc:
            raise ValueError(f"Cannot unambiguously localize recStart {parsed!s} in {timezone}") from exc
    return float(timestamp.timestamp())


def _validate_labels(value: Any) -> np.ndarray:
    labels = np.asarray(value)
    if labels.ndim > 2 or (labels.ndim == 2 and min(labels.shape) != 1):
        raise ValueError("expert_label must be an epoch vector")
    labels = labels.reshape(-1)
    if not labels.size or not np.isin(labels, [0, 1, 2, 3, 4, 5]).all():
        raise ValueError("expert_label must be nonempty and contain only codes 0..5")
    wake = np.full(labels.size, -1, dtype=np.int8)
    wake[labels == 0] = 1
    wake[np.isin(labels, [1, 2, 3, 4])] = 0
    return wake


def _aggregate_sensor(
    path: Path,
    start: float,
    n_epochs: int,
    kind: str,
    *,
    collect_intervals: bool = False,
    select_raw: Callable[[np.ndarray], np.ndarray] | None = None,
) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    sums = np.zeros(n_epochs, dtype=np.float64)
    squares = np.zeros(n_epochs, dtype=np.float64)
    counts = np.zeros(n_epochs, dtype=np.int64)
    diff_squares = np.zeros(n_epochs, dtype=np.float64)
    diff_counts = np.zeros(n_epochs, dtype=np.int64)
    report: dict[str, Any] = {
        "rows": 0,
        "duplicates_dropped": 0,
        "invalid_measurement_rows": 0,
        "outside_label_interval_rows": 0,
        "aggregated_rows": 0,
        "first_timestamp": None,
        "last_timestamp": None,
        "order_policy": "nondecreasing; identical duplicates keep first; conflicting duplicates fail",
    }
    previous_raw: np.ndarray | None = None
    previous_acc: np.ndarray | None = None
    previous_epoch: int | None = None
    interval_count, interval_sum = 0, 0.0
    interval_minimum, interval_maximum = np.inf, -np.inf
    options = {"header": None} if kind == "hr" else {"header": 0}
    try:
        chunks = pd.read_csv(path, chunksize=CSV_CHUNK_ROWS, dtype=np.float64, **options)
    except pd.errors.EmptyDataError:
        chunks = []
    try:
        for chunk in chunks:
            expected = 2 if kind == "hr" else 4
            if chunk.shape[1] != expected:
                raise ValueError(f"{path.name}: expected {expected} columns")
            if kind == "acc" and list(chunk.columns) != ["Timestamp", "x", "y", "z"]:
                raise ValueError("motion.csv must have Timestamp,x,y,z headers")
            raw = chunk.to_numpy(dtype=np.float64)
            if select_raw is not None:
                raw = select_raw(raw)
            if not len(raw):
                continue
            timestamps = raw[:, 0]
            if not np.isfinite(timestamps).all():
                raise ValueError(f"{path.name}: timestamp is not finite")
            report["rows"] += int(len(raw))
            if report["first_timestamp"] is None:
                report["first_timestamp"] = float(timestamps[0])
            report["last_timestamp"] = float(timestamps[-1])
            deltas = np.diff(timestamps)
            if np.any(deltas < 0) or (
                previous_raw is not None and timestamps[0] < previous_raw[0]
            ):
                raise ValueError(f"{path.name}: timestamps must be nondecreasing; no automatic sorting")
            if collect_intervals:
                if previous_raw is not None:
                    deltas = np.r_[timestamps[0] - previous_raw[0], deltas]
                positive = deltas[deltas > 0]
                if positive.size:
                    interval_count += len(positive)
                    interval_sum += float(positive.sum())
                    interval_minimum = min(interval_minimum, float(positive.min()))
                    interval_maximum = max(interval_maximum, float(positive.max()))
                if previous_raw is not None:
                    deltas = deltas[1:]
            duplicate = np.r_[False, deltas == 0]
            if previous_raw is not None and timestamps[0] == previous_raw[0]:
                duplicate[0] = True
                if not np.array_equal(raw[0], previous_raw, equal_nan=True):
                    raise ValueError(f"{path.name}: conflicting duplicate timestamp")
            duplicate_rows = np.flatnonzero(duplicate[1:]) + 1
            if len(duplicate_rows):
                left, right = raw[duplicate_rows], raw[duplicate_rows - 1]
                if not ((left == right) | (np.isnan(left) & np.isnan(right))).all():
                    raise ValueError(f"{path.name}: conflicting duplicate timestamp")
            report["duplicates_dropped"] += int(duplicate.sum())
            previous_raw = raw[-1].copy()
            raw = raw[~duplicate]
            valid = np.isfinite(raw[:, 1:]).all(axis=1)
            if kind == "hr":
                valid &= raw[:, 1] > 0
            report["invalid_measurement_rows"] += int((~valid).sum())
            raw = raw[valid]
            inside = (raw[:, 0] >= start) & (raw[:, 0] < start + n_epochs * EPOCH_SECONDS)
            report["outside_label_interval_rows"] += int((~inside).sum())
            raw = raw[inside]
            if not len(raw):
                continue
            epochs = np.floor((raw[:, 0] - start) / EPOCH_SECONDS).astype(np.int64)
            values = raw[:, 1] if kind == "hr" else np.linalg.norm(raw[:, 1:], axis=1)
            counts += np.bincount(epochs, minlength=n_epochs)
            sums += np.bincount(epochs, weights=values, minlength=n_epochs)
            squares += np.bincount(epochs, weights=values * values, minlength=n_epochs)
            report["aggregated_rows"] += int(len(raw))
            if kind == "acc":
                acceleration = raw[:, 1:]
                if previous_acc is None:
                    differences = np.diff(acceleration, axis=0)
                    pair_epochs = epochs[1:]
                    same_epoch = epochs[1:] == epochs[:-1]
                else:
                    differences = np.diff(np.vstack([previous_acc, acceleration]), axis=0)
                    pair_epochs = epochs
                    same_epoch = epochs == np.r_[previous_epoch, epochs[:-1]]
                # Reset differences at epoch boundaries so a history never uses an older sample.
                squared = np.sum(differences[same_epoch] ** 2, axis=1)
                diff_squares += np.bincount(pair_epochs[same_epoch], weights=squared, minlength=n_epochs)
                diff_counts += np.bincount(pair_epochs[same_epoch], minlength=n_epochs)
                previous_acc = acceleration[-1].copy()
                previous_epoch = int(epochs[-1])
    finally:
        if hasattr(chunks, "close"):
            chunks.close()
    means = np.full(n_epochs, np.nan)
    std = np.full(n_epochs, np.nan)
    present = counts > 0
    means[present] = sums[present] / counts[present]
    std[present] = np.sqrt(np.maximum(squares[present] / counts[present] - means[present] ** 2, 0))
    differences = np.full(n_epochs, np.nan)
    pairs = diff_counts > 0
    differences[pairs] = np.sqrt(diff_squares[pairs] / diff_counts[pairs])
    if collect_intervals:
        report["positive_raw_sample_intervals_seconds"] = {
            "count": interval_count,
            "min": interval_minimum if interval_count else None,
            "max": interval_maximum if interval_count else None,
            "mean": interval_sum / interval_count if interval_count else None,
        }
    return {"mean": means, "std": std, "count": counts, "diff_rms": differences}, report


def load_bidsleep_night(
    path: str | Path,
    participant: str | None = None,
    night: str | None = None,
    timezone: str = "America/New_York",
) -> Episode:
    """Load one public BIDSleep night without interpolation or future features.

    Missing continuous features remain NaN and counts remain zero. Acceleration
    differences use consecutive valid samples within the same 30-second epoch.
    Expert codes 0, 1..4, and 5 map to Wake 1, sleep 0, and unknown -1.
    """
    path = Path(path)
    mat = loadmat(path / "labels.mat", squeeze_me=True)
    if "recStart" not in mat or "expert_label" not in mat:
        raise ValueError("labels.mat requires recStart and expert_label")
    start = parse_rec_start(mat["recStart"], timezone)
    wake = _validate_labels(mat["expert_label"])
    n_epochs = len(wake)
    hr, hr_report = _aggregate_sensor(path / "hr.csv", start, n_epochs, "hr")
    acc, acc_report = _aggregate_sensor(path / "motion.csv", start, n_epochs, "acc")
    features = np.column_stack([
        hr["mean"], hr["std"], acc["mean"], acc["std"], acc["diff_rms"],
        hr["count"], acc["count"],
    ])
    metadata = {
        "source": SOURCE_URL,
        "path": str(path.resolve()),
        "label_source": "expert_label",
        "raw_label_codes": {"0": "wake", "1..4": "sleep", "5": "unknown"},
        "wake_codes": {"1": "wake", "0": "sleep", "-1": "unknown"},
        "rec_start_raw": str(np.asarray(mat["recStart"]).squeeze()),
        "timezone_for_naive_rec_start": timezone,
        "recording_start_unix": start,
        "recording_end_unix": start + n_epochs * EPOCH_SECONDS,
        "epoch_seconds": EPOCH_SECONDS,
        "epochs": n_epochs,
        "unknown_label_epochs": int((wake < 0).sum()),
        "feature_names": list(FEATURE_NAMES),
        "epoch_interval": "[epoch_start, epoch_start + 30s)",
        "interpolation": "none",
        "std_convention": "population",
        "acc_diff_rms": "sqrt(mean(squared L2 consecutive acceleration difference)); reset each epoch",
        "hr": hr_report,
        "acc": acc_report,
    }
    return Episode(
        participant=str(participant if participant is not None else path.parent.name),
        night=str(night if night is not None else path.name),
        epoch_start=start + np.arange(n_epochs, dtype=np.float64) * EPOCH_SECONDS,
        features=features,
        wake=wake,
        metadata=metadata,
    )


def _check_episode(episode: Episode) -> None:
    length = len(episode.epoch_start)
    if episode.epoch_start.ndim != 1 or episode.features.shape != (length, len(FEATURE_NAMES)):
        raise ValueError("Episode requires epoch_start[T] and features[T,7]")
    if episode.wake.shape != (length,) or not np.isin(episode.wake, [-1, 0, 1]).all():
        raise ValueError("Episode wake must have shape [T] and values -1, 0, 1")
    if not np.isfinite(episode.epoch_start).all() or not np.allclose(
        np.diff(episode.epoch_start), EPOCH_SECONDS, atol=1e-6, rtol=0
    ):
        raise ValueError("Episode timestamps must form a finite 30-second grid")
    if not np.isfinite(episode.features[:, 5:]).all() or np.any(episode.features[:, 5:] < 0):
        raise ValueError("Episode sample counts must be finite and nonnegative")


def build_windows(
    episodes: Iterable[Episode],
    history_epochs: int = 60,
    horizon_epochs: int = 60,
    stride_epochs: int = 10,
    min_history_coverage: float = 0.8,
) -> dict[str, Any]:
    """Return periodic windows, retaining all future missingness in target.

    Origin i observes epochs [i-H, i) and targets [i, i+T). Origins run from
    H through the recording end on a fixed stride; future availability and
    labels never gate inclusion. Both sensor counts must be positive for a
    history epoch to count toward coverage. ``current`` is the retrospective
    label at i-1 for training/evaluation only, never an input feature.
    """
    for name, value in (("history_epochs", history_epochs), ("horizon_epochs", horizon_epochs), ("stride_epochs", stride_epochs)):
        if not isinstance(value, (int, np.integer)) or isinstance(value, bool) or value < 1:
            raise ValueError(f"{name} must be a positive integer")
    if not np.isfinite(min_history_coverage) or not 0 <= min_history_coverage <= 1:
        raise ValueError("min_history_coverage must be between zero and one")
    histories, targets, current, participants, nights, times = [], [], [], [], [], []
    report: dict[str, Any] = {
        "candidate_origins": 0,
        "history_coverage_rejected": 0,
        "retained_origins": 0,
        "full_future_span_origins": 0,
        "complete_target_origins": 0,
        "unknown_current_origins": 0,
        "full_future_sensor_coverage_origins": 0,
        "target_epochs_total": 0,
        "target_epochs_observed": 0,
        "target_epochs_valid": 0,
        "target_epochs_unknown_inside_recording": 0,
        "target_epochs_beyond_recording": 0,
        "history_epochs": int(history_epochs),
        "horizon_epochs": int(horizon_epochs),
        "stride_epochs": int(stride_epochs),
        "min_history_coverage": float(min_history_coverage),
        "coverage_rule": "both hr_count and acc_count positive in a history epoch",
        "selection": "elapsed-time grid and past sensor coverage only",
        "current_semantics": "retrospective wake label at origin minus one epoch; training/evaluation only",
        "episodes": [],
    }
    for episode in episodes:
        _check_episode(episode)
        length = len(episode.epoch_start)
        covered = (episode.features[:, 5] > 0) & (episode.features[:, 6] > 0)
        episode_report = {
            "participant": episode.participant,
            "night": episode.night,
            "epochs": length,
            "candidate_origins": 0,
            "retained_origins": 0,
            "complete_target_origins": 0,
        }
        for index in range(history_epochs, length + 1, stride_epochs):
            report["candidate_origins"] += 1
            episode_report["candidate_origins"] += 1
            if np.mean(covered[index - history_epochs:index]) < min_history_coverage:
                report["history_coverage_rejected"] += 1
                continue
            target = np.full(horizon_epochs, -1, dtype=np.int8)
            observed = min(horizon_epochs, length - index)
            target[:observed] = episode.wake[index:index + observed]
            histories.append(episode.features[index - history_epochs:index].copy())
            targets.append(target)
            current.append(episode.wake[index - 1])
            participants.append(episode.participant)
            nights.append(episode.night)
            times.append(float(episode.epoch_start[0] + index * EPOCH_SECONDS))
            complete = bool(np.all(target >= 0))
            report["retained_origins"] += 1
            episode_report["retained_origins"] += 1
            report["full_future_span_origins"] += int(observed == horizon_epochs)
            report["complete_target_origins"] += int(complete)
            episode_report["complete_target_origins"] += int(complete)
            report["unknown_current_origins"] += int(episode.wake[index - 1] < 0)
            report["full_future_sensor_coverage_origins"] += int(
                observed == horizon_epochs and covered[index:index + observed].all()
            )
            report["target_epochs_total"] += horizon_epochs
            report["target_epochs_observed"] += observed
            report["target_epochs_valid"] += int((target >= 0).sum())
            report["target_epochs_unknown_inside_recording"] += int((target[:observed] < 0).sum())
            report["target_epochs_beyond_recording"] += horizon_epochs - observed
        report["episodes"].append(episode_report)
    report["target_epochs_unknown"] = report["target_epochs_total"] - report["target_epochs_valid"]
    return {
        "history": np.stack(histories) if histories else np.empty((0, history_epochs, len(FEATURE_NAMES)), dtype=np.float64),
        "target": np.stack(targets) if targets else np.empty((0, horizon_epochs), dtype=np.int8),
        "current": np.asarray(current, dtype=np.int8),
        "participant": np.asarray(participants, dtype=str),
        "night": np.asarray(nights, dtype=str),
        "origin_time": np.asarray(times, dtype=np.float64),
        "report": report,
    }
