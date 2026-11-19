"""Read the frozen expanded validation forecasts and apply train-only transition controls."""

import hashlib
import json
from pathlib import Path

import numpy as np

from sleep_g3.protocol import sha256_file
from .baselines import stage_prior
from .data import load_cache


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _receipt(local, published):
    digest = sha256_file(local)
    _require(digest == sha256_file(published), f"{local.name} differs from the published receipt")
    return json.loads(published.read_text()), digest


def _probabilities(name, value, shape):
    array = np.asarray(value)
    _require(array.shape == shape, f"{name} has shape {array.shape}, expected {shape}")
    _require(np.isfinite(array).all() and (array >= 0).all() and (array <= 1).all()
             and np.allclose(array.sum(axis=-1), 1, rtol=1e-6, atol=1e-6),
             f"{name} must hold finite normalized class probabilities")
    return array


def load_inputs(source_root, published_dir):
    root, published = Path(source_root), Path(published_dir)
    cache, output = root / "expanded-cache", root / "expanded"
    execution, execution_hash = _receipt(output / "execution.json", published / "execution.json")
    audit_receipt, audit_execution_hash = _receipt(
        cache / "audit_execution.json", published / "audit-execution.json",
    )
    _require(execution["status"] == "completed" and execution["seeds"] == [0, 1, 2]
             and execution["mode"] == "run" and execution["phase"] == "expanded"
             and execution["run_id"] == "20261119-stage-expanded", "expected the completed fixed 38-night run")
    audit = json.loads((cache / "audit.json").read_text())
    audit_sha = sha256_file(cache / "audit.json")
    _require(execution["audit_sha256"] == audit_sha == audit_receipt["audit_sha256"]
             and audit_receipt["audit_status"] == "complete"
             and all(execution[k] == audit_receipt[k] for k in ("run_id", "code_commit", "spec_commit")),
             "source files do not identify the published expanded audit")
    for key in ("cache_identity_sha256", "timestamp_policy_sha256"):
        _require(audit[key] == execution[key], f"expanded audit differs from execution at {key}")
    _require(audit["test_accessed"] is False and len(audit["selected_records"]) == 38
             and audit["split_sizes"].get("test_sealed") == 7, "expected sealed fixed 38-night audit")
    windows = load_cache(cache)
    train, val = windows["train"], windows["val"]
    n = len(val.origin)
    _require(len(train.origin) == 1936 and n == 969 and
             execution["origins"] == {"train": 1936, "validation": 969}, "unexpected original origin counts")
    train_people = set(train.participant)
    val_people = set(val.participant)
    _require(len(train_people) == 12 and len(val_people) == 7 and train_people.isdisjoint(val_people),
             "expected 12 training and seven disjoint validation participants")
    keys = [(str(p), str(night), int(o)) for p, night, o in zip(val.participant, val.night, val.origin)]
    _require(len(set(keys)) == n, "duplicate validation origins")
    key_hash = hashlib.sha256(json.dumps(keys, separators=(",", ":")).encode()).hexdigest()
    # Only authenticate the original scoring targets and validity here.
    # Neither them nor a current validation label is passed to make_predictions.
    target_bytes = np.ascontiguousarray(val.stage, dtype="i1")
    target_hash = hashlib.sha256(target_bytes.tobytes()).hexdigest()
    mask_hash = hashlib.sha256(np.ascontiguousarray(target_bytes >= 0, dtype="u1").tobytes()).hexdigest()
    prior = stage_prior(train.stage, n)
    p_t = None
    directs, files = {}, {}
    for seed in range(3):
        seed_scores, score_hash = _receipt(output / f"seed-{seed}.json", published / f"seed-{seed}.json")
        original = seed_scores["expanded"]
        _require(original["ordered_validation_keys_sha256"] == key_hash
                 and original["ordered_stage_targets_sha256"] == target_hash
                 and original["cache_identity_sha256"] == execution["cache_identity_sha256"],
                 f"seed {seed} original target, order or cache digest mismatch")
        path = output / f"seed-{seed}-predictions.npz"
        files[path.name] = {"sha256": sha256_file(path), "original_scores_sha256": score_hash}
        with np.load(path, allow_pickle=False) as saved:
            for field in ("participant", "night", "origin_time"):
                _require(np.array_equal(saved[field], getattr(val, field)), f"seed {seed} {field} order mismatch")
            repeated = _probabilities("persistence", saved["stage_persistence"], (n, 60, 4))
            if p_t is None:
                p_t = repeated[:, 0, :].copy()
            _require((repeated == p_t[:, None, :]).all(), f"seed {seed} persistence differs by seed or horizon")
            _require(np.array_equal(saved["stage_stage_prior"], prior),
                     f"seed {seed} prior differs from training labels or origins")
            directs[f"direct_{seed}"] = _probabilities("direct", saved["stage_direct"], (n, 60, 4))
    metadata = {
        "source_root": str(root.resolve()), "source_run_id": execution["run_id"],
        "source_spec_commit": execution["spec_commit"], "source_code_commit": execution["code_commit"],
        "cache_identity_sha256": execution["cache_identity_sha256"], "audit_sha256": audit_sha,
        "timestamp_policy_sha256": execution["timestamp_policy_sha256"],
        "acquisition_sha256": audit["acquisition_sha256"], "protocol_sha256": audit["protocol_sha256"],
        "execution_sha256": execution_hash, "audit_execution_sha256": audit_execution_hash,
        "ordered_validation_keys_sha256": key_hash, "ordered_stage_targets_sha256": target_hash,
        "ordered_validity_mask_uint8_sha256": mask_hash, "prediction_files": files,
        "origins": execution["origins"], "test_accessed": False,
    }
    return train, val, p_t, prior, directs, metadata


def make_predictions(p_t, prior, directs, weights, matrices):
    """Apply lead-specific coefficients and row-stochastic operators to saved beliefs."""
    n = len(p_t)
    state = _probabilities("current belief", p_t, (n, 4))
    prior = _probabilities("prior", prior, (n, 60, 4))
    transitions = _probabilities("transition rows", matrices, (60, 4, 4))
    w = np.asarray(weights)
    _require(w.shape == (60,) and np.isfinite(w).all() and ((w >= 0) & (w <= 1)).all(),
             "expected one convex mixture coefficient per lead")
    _require(set(directs) == {f"direct_{seed}" for seed in range(3)}, "expected original direct seeds 0,1,2")
    persistence = np.broadcast_to(state[:, None, :], prior.shape)
    predictions = {
        "persistence": persistence,
        "prior_mix": (1 - w[None, :, None]) * persistence + w[None, :, None] * prior,
        "transition": np.einsum("nc,hcd->nhd", state, transitions),
        "stage_prior": prior,
    }
    return {**predictions, **{k: _probabilities(k, v, prior.shape) for k, v in directs.items()}}
