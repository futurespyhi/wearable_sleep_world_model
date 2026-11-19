"""Join fixed forecast origins to audited recording starts and authenticate frozen controls."""

import json
from pathlib import Path

import numpy as np

from .oracle_inputs import load_oracle_inputs
from .recording_time_fit import recording_bins
from .transition_inputs import _receipt, _require


def _partition_bins(windows, audit, partition):
    """Look up each night's own audited recStart before assigning origin-time bins."""
    nights = [record for record in audit["nights"] if record["partition"] == partition]
    starts = {(record["participant"], record["night"]): float(record["metadata"]["recording_start_unix"])
              for record in nights}
    observed = set(zip(windows.participant, windows.night))
    _require(len(nights) == len(starts) and observed == starts.keys(),
             f"{partition} night keys differ between retained origins and audit")
    return recording_bins(windows, starts)


def load_time_inputs(expanded_root, transition_root, oracle_root, reports_root):
    """Load the original global controls and compute elapsed-time bins from cutoff timestamps."""
    results = Path(oracle_root) / "results"
    published = Path(reports_root) / "20261119-stage-oracle"
    execution, execution_hash = _receipt(results / "execution.json", published / "execution.json")
    _, metrics_hash = _receipt(results / "metrics.json", published / "metrics.json")
    _require(execution["run_id"] == "20261119-stage-oracle" and execution["status"] == "completed"
             and execution["test_accessed"] is False, "expected completed oracle with sealed test")
    train, val, p_t, matrices, controls, frozen = load_oracle_inputs(
        expanded_root, transition_root, reports_root, include_train=True,
    )
    _require(frozen == execution["inputs"], "parent oracle inputs differ from the expanded cache or control fit")
    audit_path = Path(expanded_root) / "expanded-cache" / "audit.json"
    audit = json.loads(audit_path.read_text())
    train_bin = _partition_bins(train, audit, "train")
    val_bin = _partition_bins(val, audit, "validation")
    prior = controls["stage_prior"][0]
    # Unknown current labels are excluded from oracle scoring. Fill those
    # entries with a normalized prior so they never index a matrix with -1.
    oracle = controls["stage_prior"].copy()
    known = val.current_stage >= 0
    _require(np.isin(val.current_stage, [-1, 0, 1, 2, 3]).all(), "invalid expert current stage")
    oracle[known] = matrices[:, val.current_stage[known], :].transpose(1, 0, 2)
    parent_controls = {**controls, "oracle": oracle}
    metadata = {
        **frozen,
        "oracle_run_id": execution["run_id"], "oracle_code_commit": execution["code_commit"],
        "oracle_execution_sha256": execution_hash, "oracle_metrics_sha256": metrics_hash,
        "recording_start_source": "expanded-cache/audit.json nights[].metadata.recording_start_unix",
        "bin_boundaries_seconds": [7200, 14400, 21600], "bin_interval": "left-closed, right-open",
        "bin_origin_counts": {"train": np.bincount(train_bin, minlength=4).tolist(),
                              "validation": np.bincount(val_bin, minlength=4).tolist()},
        "oracle_unknown_current_placeholder": "training stage prior at each lead, excluded from oracle scores",
    }
    return train, val, p_t, prior, matrices, parent_controls, train_bin, val_bin, metadata
