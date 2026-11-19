"""Whole-stream physical-row audit, followed by event-time filtering for G3 aggregation."""

from __future__ import annotations

import csv
from decimal import Decimal
from io import BytesIO
from itertools import islice
from pathlib import Path

import numpy as np
import pandas as pd

from sleep_g3 import data as g3
from .timestamps import _number


def _raw_fields(line):
    return next(csv.reader([line.decode("ascii")]))


def _timestamp_chunk(lines):
    # A correctly rounded float is monotone in the literal value. Equal floats
    # are also candidates, so even a sub-ULP reversal gets a Decimal check.
    try:
        table = pd.read_csv(
            BytesIO(b"".join(lines)), header=None, usecols=[0], dtype=np.float64,
            float_precision="round_trip", skip_blank_lines=False,
        )
        timestamps = table.iloc[:, 0].to_numpy()
        if len(timestamps) == len(lines):
            return timestamps
    except (pd.errors.ParserError, ValueError, OverflowError):
        pass
    # Isolate malformed literals with their original physical lines.
    def parse(line):
        value = _number(_raw_fields(line)[0])
        return float(value) if value is not None else np.nan
    return np.fromiter((parse(line) for line in lines), dtype=float, count=len(lines))


def _measurements_equal(left, right):
    if len(left) != len(right):
        return False
    for first, second in zip(left, right):
        a, b = _number(first), _number(second)
        if a is None or b is None:
            if first.strip().lower() != second.strip().lower():
                return False
        elif a != b:
            return False
    return True


def _pair(left, right, rows, start, end, cross_chunk):
    a, b = _raw_fields(left), _raw_fields(right)
    first, second = _number(a[0]), _number(b[0])
    if first is None or second is None or first < second:
        return None
    lo, hi = second, first
    if hi < start:
        relation = "before"
    elif lo >= end:
        relation = "after"
    elif start <= lo <= hi < end:
        relation = "inside"
    else:
        relation = "cross_boundary"
    overlap = None
    if lo < end and hi >= start:
        last = int((end - start) / 30) - 1
        overlap = [int((max(lo, start) - start) // 30), min(last, int((hi - start) // 30))]
    if first != second:
        kind = "reversal"
    elif _measurements_equal(a[1:], b[1:]):
        kind = "identical_duplicate"
    else:
        kind = "conflicting_duplicate"
    return {
        "kind": kind, "rows": rows, "timestamps": [a[0], b[0]],
        "delta_seconds": float(second - first), "cross_chunk": cross_chunk,
        "relation": relation, "intersected_epochs": overlap,
    }


def _scan(path, kind, start, end):
    """Find all anomalies before any filtering, even after crossing the recording end."""
    start, end = Decimal(str(start)), Decimal(str(end))
    events = []
    chunk_rows = g3.CSV_CHUNK_ROWS
    previous = None
    n_rows = 0
    with path.open("rb") as stream:
        line_offset = 0
        if kind == "acc":
            header = stream.readline()
            if _raw_fields(header) != ["Timestamp", "x", "y", "z"]:
                raise ValueError("motion.csv must have Timestamp,x,y,z headers (line 1)")
            line_offset = 1
        while lines := list(islice(stream, chunk_rows)):
            numbers = np.arange(line_offset + 1, line_offset + 1 + len(lines))
            line_offset += len(lines)
            if any(line.isspace() for line in lines):
                keep = [i for i, line in enumerate(lines) if not line.isspace()]
                numbers, lines = numbers[keep], [lines[i] for i in keep]
            if not lines:
                continue
            ts = _timestamp_chunk(lines)
            n_rows += len(ts)
            for i in np.flatnonzero(~np.isfinite(ts)):
                events.append({"kind": "invalid_timestamp", "rows": [int(numbers[i])],
                               "timestamps": [_raw_fields(lines[i])[0]], "relation": "unknown",
                               "intersected_epochs": None, "cross_chunk": False})
            prior_ts = previous[0] if previous else np.nan
            suspect = np.flatnonzero(ts <= np.r_[prior_ts, ts[:-1]])
            for i in suspect:
                if i == 0 and previous is None:
                    continue
                left, left_line = (previous[1], previous[2]) if i == 0 else (lines[i - 1], numbers[i - 1])
                event = _pair(left, lines[i], [int(left_line), int(numbers[i])], start, end, bool(i == 0))
                if event:
                    events.append(event)
            previous = ts[-1], lines[-1], int(numbers[-1])
    return n_rows, events


def _apply_policy(events, expected, kind, receipt):
    seen_rows = set()
    masks = set()
    errors = []
    for event in events:
        rows = tuple(event["rows"])
        rule = expected.get(rows)
        if event["kind"] == "identical_duplicate":
            action = "keep_first"
        elif event["relation"] in ("before", "after"):
            action = "outside_interval"
        else:
            action = "block"
        if rule is not None:
            matches = (
                rule["sha256"] == receipt and rule["kind"] == event["kind"]
                and rule["relation"] == event["relation"]
                and [_number(x) for x in rule["timestamps"]] == [_number(x) for x in event["timestamps"]]
            )
            if not matches:
                action = "block"
            elif rule["action"] == "mask_acc_epoch":
                epoch = rule["epoch"]
                if (kind == "acc" and event["kind"] == "reversal" and event["relation"] == "inside"
                        and event["intersected_epochs"] == [epoch, epoch]):
                    masks.add(epoch)
                    action = rule["action"]
                else:
                    action = "block"
            elif action != rule["action"]:
                action = "block"
            seen_rows.add(rows)
        event.update(action=action, registered=rule is not None)
        if action == "block":
            errors.append(f'{event["kind"]} at lines {list(rows)} ({event["relation"]})')
    for rows in sorted(expected.keys() - seen_rows):
        errors.append(f"registered event absent at lines {list(rows)}")
    return sorted(masks), errors


def aggregate_with_policy(path: Path, start: float, n_epochs: int, kind: str, *,
                          relative: str, receipt_sha256: str, policy: dict):
    end = start + n_epochs * g3.EPOCH_SECONDS
    report = {"file": relative, "sha256": receipt_sha256, "status": "failed",
              "interval_unix": [start, end], "events": [], "masked_epochs": [],
              "masked_valid_sample_counts": {}, "errors": []}
    try:
        if policy["schema"] != "stage_event_time_v1":
            raise ValueError("unsupported timestamp policy schema")
        rules = [row for row in policy["events"] if row["path"] == relative]
        expected = {tuple(row["rows"]): row for row in rules}
        if len(expected) != len(rules):
            raise ValueError("duplicate timestamp rules for the same physical lines")
        rows, events = _scan(path, kind, start, end)
        masks, errors = _apply_policy(events, expected, kind, receipt_sha256)
        report.update(rows=rows, events=events, masked_epochs=masks, errors=errors)
        if errors:
            return None, report
        masked_counts = {str(epoch): 0 for epoch in masks}
        outside_count = 0

        def select(raw):
            nonlocal outside_count
            timestamps = raw[:, 0]
            inside = (start <= timestamps) & (timestamps < end)
            outside_count += int((~inside).sum())
            for epoch in masks:
                left = start + epoch * g3.EPOCH_SECONDS
                in_mask = (left <= timestamps) & (timestamps < left + g3.EPOCH_SECONDS)
                masked_counts[str(epoch)] += int(np.isfinite(raw[in_mask, 1:]).all(axis=1).sum())
                inside &= ~in_mask
            return raw[inside]

        # The normal G3 checks and reducer run on the remaining, original-order
        # samples. Chunk boundaries and the within-epoch difference rule stay intact.
        sensor, reduced = g3._aggregate_sensor(
            path, start, n_epochs, kind, collect_intervals=True, select_raw=select,
        )
        report.update(reduced, rows=rows, reduced_stream_rows=reduced["rows"],
                      positive_interval_scope="selected stream before identical deduplication",
                      outside_label_interval_rows=outside_count,
                      masked_valid_sample_counts=masked_counts, status="complete")
        return sensor, report
    except (ValueError, OverflowError, OSError, csv.Error) as error:
        report["errors"].append(str(error))
        return None, report
