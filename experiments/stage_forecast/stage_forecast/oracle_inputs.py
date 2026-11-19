"""Verify frozen predictions and train-fitted matrices for the current-stage oracle."""

from pathlib import Path

import numpy as np

from sleep_g3.protocol import sha256_file
from .transition_inputs import _receipt, _require, load_inputs, make_predictions


def load_oracle_inputs(expanded_root, transition_root, reports_root):
    """Return cached validation data, beliefs, matrices and matched saved controls."""
    reports = Path(reports_root)
    results = Path(transition_root) / "results"
    published = reports / "20261119-stage-transition"
    execution, execution_hash = _receipt(results / "execution.json", published / "execution.json")
    fit, fit_hash = _receipt(results / "fit.json", published / "fit.json")
    _require(execution["run_id"] == "20261119-stage-transition" and execution["status"] == "completed"
             and execution["test_accessed"] is False, "expected completed transition controls with sealed test")
    _, val, p_t, prior, directs, expanded = load_inputs(expanded_root, reports / "20261119-stage-expanded")
    _require(expanded == execution["inputs"], "expanded inputs differ from the published transition receipt")
    matrices = np.asarray(fit["transition_matrices"], dtype=float)
    reference = make_predictions(p_t, prior, directs, fit["prior_weights"], matrices)
    prediction_file = results / "control_predictions.npz"
    controls = {}
    with np.load(prediction_file, allow_pickle=False) as saved:
        for field in ("participant", "night", "origin_time"):
            _require(np.array_equal(saved[field], getattr(val, field)), f"saved transition {field} order mismatch")
        for name in ("persistence", "transition", "prior_mix"):
            probability = saved[name]
            _require(np.array_equal(probability, reference[name]),
                     f"saved {name} differs from the frozen beliefs and coefficients")
            if name != "persistence":
                controls[name] = probability
    # load_inputs verifies this prior against all three original forecast archives.
    controls["stage_prior"] = prior
    metadata = {
        **expanded,
        "transition_run_id": execution["run_id"],
        "transition_code_commit": execution["code_commit"],
        "transition_execution_sha256": execution_hash,
        "transition_fit_sha256": fit_hash,
        "transition_predictions_path": str(prediction_file.resolve()),
        "transition_predictions_sha256": sha256_file(prediction_file),
        "control_reconstruction": "exact across 969 origins, 60 leads and four stages",
    }
    return val, p_t, matrices, controls, metadata
