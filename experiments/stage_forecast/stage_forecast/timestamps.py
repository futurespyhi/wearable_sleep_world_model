"""Bounded forensic scan of the original CSV sequence after an order-guard failure."""

from __future__ import annotations

import csv
from decimal import Decimal, InvalidOperation
from pathlib import Path

import numpy as np


def _number(value: str) -> Decimal | None:
    try:
        number = Decimal(value)
    except InvalidOperation:
        return None
    return number if number.is_finite() else None


def inspect_timestamps(path: Path, start: float, stages: np.ndarray, chunk_rows: int) -> dict:
    """Check literal decimal timestamps, retaining row identity and bounded examples."""
    examples_limit = 12
    epoch = Decimal(30)
    interval_start = Decimal(str(start))
    interval_end = interval_start + len(stages) * epoch
    affected = np.zeros(len(stages), dtype=bool)
    counts = {
        "raw_rows": 0,
        "reversals": 0,
        "cross_chunk_reversals": 0,
        "reversal_spans_intersecting_label_interval": 0,
        "reversal_spans_intersecting_known_stage": 0,
        "reversal_pairs_both_inside_label_interval": 0,
        "adjacent_identical_timestamp_duplicates": 0,
        "adjacent_conflicting_timestamp_duplicates": 0,
        "nonfinite_or_invalid_timestamps": 0,
    }
    examples = {"reversals": [], "adjacent_duplicates": [], "invalid_timestamps": []}
    previous = None
    minimum = maximum = None
    largest = None

    with path.open(newline="") as stream:
        rows = csv.reader(stream)
        if path.name == "motion.csv":
            next(rows, None)
        for row in rows:
            if not row or (len(row) == 1 and not row[0].strip()):
                continue
            counts["raw_rows"] += 1
            line, index = rows.line_num, counts["raw_rows"]
            timestamp = _number(row[0])
            if timestamp is None:
                counts["nonfinite_or_invalid_timestamps"] += 1
                if len(examples["invalid_timestamps"]) < examples_limit:
                    examples["invalid_timestamps"].append({"csv_line": line, "data_row": index, "raw": row[0]})
                previous = None
                continue
            minimum = timestamp if minimum is None else min(minimum, timestamp)
            maximum = timestamp if maximum is None else max(maximum, timestamp)
            if previous is not None and timestamp <= previous[0]:
                previous_ts, previous_line, previous_index, previous_values = previous
                cross_chunk = (index - 1) % chunk_rows == 0
                pair = {
                    "previous_csv_line": previous_line, "csv_line": line,
                    "previous_data_row": previous_index, "data_row": index,
                    "previous_timestamp_raw": str(previous_ts), "timestamp_raw": str(timestamp),
                    "cross_chunk": cross_chunk,
                }
                if timestamp < previous_ts:
                    backward = previous_ts - timestamp
                    pair["delta_seconds"] = -float(backward)
                    counts["reversals"] += 1
                    counts["cross_chunk_reversals"] += int(cross_chunk)
                    pair["both_inside_label_interval"] = interval_start <= timestamp <= previous_ts < interval_end
                    counts["reversal_pairs_both_inside_label_interval"] += int(pair["both_inside_label_interval"])
                    if timestamp < interval_end and previous_ts >= interval_start:
                        low = int((max(timestamp, interval_start) - interval_start) // epoch)
                        high = min(len(stages) - 1, int((previous_ts - interval_start) // epoch))
                        pair["intersected_label_epochs_0based"] = [low, high]
                        counts["reversal_spans_intersecting_label_interval"] += 1
                        counts["reversal_spans_intersecting_known_stage"] += int((stages[low:high + 1] >= 0).any())
                        affected[low:high + 1] = True
                    if largest is None or pair["delta_seconds"] < largest["delta_seconds"]:
                        largest = pair
                    if len(examples["reversals"]) < examples_limit:
                        examples["reversals"].append(pair)
                else:
                    same_values = [_number(value) for value in row[1:]] == [
                        _number(value) for value in previous_values
                    ]
                    count_key = "adjacent_identical_timestamp_duplicates" if same_values else                         "adjacent_conflicting_timestamp_duplicates"
                    counts[count_key] += 1
                    pair["identical_measurements"] = same_values
                    if len(examples["adjacent_duplicates"]) < examples_limit:
                        examples["adjacent_duplicates"].append(pair)
            previous = timestamp, line, index, row[1:]

    covered = np.flatnonzero(affected)
    return {
        **counts,
        "raw_anomaly_confirmed": any(counts[key] for key in (
            "reversals", "adjacent_conflicting_timestamp_duplicates", "nonfinite_or_invalid_timestamps"
        )),
        "csv_line_convention": "1-based physical CSV line including the motion header",
        "data_row_convention": "1-based nonblank sample row excluding the motion header",
        "duplicate_scope": "adjacent equal timestamps in original row order",
        "chunk_rows": chunk_rows,
        "min_timestamp_raw": str(minimum) if minimum is not None else None,
        "max_timestamp_raw": str(maximum) if maximum is not None else None,
        "label_interval_unix": [start, float(interval_end)],
        "reference_epochs_intersected_by_reversal_spans": int(affected.sum()),
        "known_reference_epochs_intersected_by_reversal_spans": int(np.count_nonzero(affected & (stages >= 0))),
        "min_max_intersected_label_epoch_0based": [int(covered[0]), int(covered[-1])] if len(covered) else None,
        "largest_reversal": largest,
        "examples": examples,
    }
