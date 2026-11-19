"""Build the shareable audit receipt alongside the full HPG audit."""
from collections import Counter


def audit_summary(audit):
    rows = audit["nights"]
    summary = {k: v for k, v in audit.items() if k not in ("nights", "failures", "selected_records")}
    summary["failures"] = [{k: r[k] for k in ("participant", "night", "partition", "error", "sensor_reports")
                            if k in r} for r in audit["failures"]]
    summary["records"] = []
    stats = {}
    for partition in ("train", "validation"):
        counts = Counter()
        for row in rows:
            if row["partition"] == partition:
                counts.update({k: v for k, v in row.get("windows", {}).items()
                               if k in ("candidate_origins", "history_coverage_rejected", "retained_origins",
                                        "full_future_span_origins", "complete_target_origins", "target_epochs_valid",
                                        "target_epochs_unknown_inside_recording", "target_epochs_beyond_recording")})
        stats[partition] = dict(counts)
    summary["origin_counts"] = stats
    for row in rows:
        record = {k: row[k] for k in ("participant", "night", "partition", "status", "cache_sha256",
                                      "strict_reference", "verified_sources") if k in row}
        if row.get("mask_coverage", {}).get("epochs"):
            record["mask_coverage"] = row["mask_coverage"]
        metadata = row.get("metadata", row.get("sensor_reports", {}))
        record["sensors"] = {}
        for sensor in ("hr", "acc"):
            if sensor in metadata:
                info = metadata[sensor]
                record["sensors"][sensor] = {k: info[k] for k in ("status", "events", "error", "file",
                         "rows", "errors", "outside_label_interval_rows", "reduced_stream_rows", "masked_epochs", "masked_valid_sample_counts") if k in info}
        summary["records"].append(record)
    return summary
