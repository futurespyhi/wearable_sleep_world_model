"""Audit public pilot records and run validation-only reference comparisons."""

import json
import os
import pickle
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from .data import Episode, FEATURE_NAMES, build_windows, load_bidsleep_night
from .metrics import evaluate_forecasts
from .models import BaselineSuite
from .protocol import read_catalog, select_records, sha256_file, write_json

CONFIG = Path(__file__).resolve().parent.parent / "protocol.json"


def _configuration(protocol_path=None):
    return json.loads(Path(protocol_path or CONFIG).read_text())


def _acquisition(root, config=None):
    manifest = json.loads((Path(root) / "manifests" / "acquisition.json").read_text())
    if manifest["status"] != "complete":
        raise ValueError("acquisition is incomplete")
    config = _configuration() if config is None else config
    if manifest["split_seed"] != config["split_seed"]:
        raise ValueError("acquisition split seed does not match protocol")
    partitions = [manifest["split"][key] for key in ("train", "validation", "test_sealed")]
    all_people = [pid for group in partitions for pid in group]
    if len(all_people) != len(set(all_people)):
        raise ValueError("participant splits must be disjoint and unique")
    identities = [(r["participant"], r["night"]) for r in manifest["selected_records"]]
    if len(identities) != len(set(identities)):
        raise ValueError("duplicate participant/night record")
    expected_catalog = config.get("expected_catalog_sha256")
    if expected_catalog and manifest["catalog_sha256"] != expected_catalog:
        raise ValueError("catalog changed from the frozen release")
    selected = {r["participant"] for r in manifest["selected_records"]}
    if selected & set(manifest["split"]["test_sealed"]):
        raise ValueError("sealed test participant present")
    for record in manifest["selected_records"]:
        if record["partition"] not in ("train", "validation"):
            raise ValueError("this pilot supports train and validation only")
        if record["participant"] not in manifest["split"][record["partition"]]:
            raise ValueError("record split assignment mismatch")
    for partition, key in (("train", "pilot_train_subjects"), ("validation", "pilot_validation_subjects")):
        records = [r for r in manifest["selected_records"] if r["partition"] == partition]
        people = {r["participant"] for r in records}
        if len(people) != config[key] or any(
            sum(r["participant"] == pid for r in records) != config["pilot_nights_per_subject"]
            for pid in people
        ):
            raise ValueError("acquisition sample sizes do not match protocol; use a matching config and new root")
        if people != set(manifest["split"][partition][:config[key]]):
            raise ValueError("selected participants are not the frozen split prefix")
    return manifest


def _window_kwargs(config):
    return {"history_epochs": config["history_epochs"], "horizon_epochs": config["horizon_epochs"],
            "stride_epochs": config["stride_epochs"],
            "min_history_coverage": config["minimum_history_coverage"]}


def audit(root, protocol_path=None):
    root = Path(root)
    protocol_path = Path(protocol_path or CONFIG)
    config = _configuration(protocol_path)
    manifest = _acquisition(root, config)
    source_root = root / "raw" / "bidsleep_1.0.1"
    catalog_path = source_root / "SHA256SUMS.txt"
    if sha256_file(catalog_path) != manifest["catalog_sha256"]:
        raise ValueError("catalog changed after acquisition")
    expected = select_records(read_catalog(catalog_path), manifest["split"],
                              config["pilot_train_subjects"], config["pilot_validation_subjects"],
                              config["pilot_nights_per_subject"])
    if manifest["selected_records"] != expected:
        raise ValueError("selected records are not the frozen catalog prefix")
    previous_audit = root / "manifests" / "audit.json"
    if previous_audit.exists() and json.loads(previous_audit.read_text())["protocol_sha256"] != sha256_file(protocol_path):
        raise ValueError("protocol changed in an existing root; use a new root")
    sources = {record["path"]: record for record in manifest["files"]}
    (root / "processed").mkdir(parents=True, exist_ok=True)
    report = {"evidence_class": "diagnostic_only", "protocol_sha256": sha256_file(protocol_path),
              "source": manifest["source"], "catalog_sha256": manifest["catalog_sha256"],
              "test_accessed": False, "nights": [], "status": "running",
              "host": platform.node(), "slurm_job_id": os.environ.get("SLURM_JOB_ID")}
    episodes = {"train": [], "validation": []}
    try:
        for record in manifest["selected_records"]:
            relative = f"{record['participant']}/{record['night']}"
            for name in ("hr.csv", "motion.csv", "labels.mat"):
                source = relative + "/" + name
                if sha256_file(source_root / source) != sources[source]["sha256"]:
                    raise ValueError("raw file changed after acquisition: " + source)
            episode = load_bidsleep_night(source_root / relative,
                                          participant=record["participant"], night=record["night"])
            cache_name = f"{record['participant']}_{record['night']}.npz"
            np.savez_compressed(root / "processed" / cache_name,
                                epoch_start=episode.epoch_start, features=episode.features,
                                wake=episode.wake, metadata=np.asarray(json.dumps(episode.metadata)))
            episodes[record["partition"]].append(episode)
            single = build_windows([episode], **_window_kwargs(config))
            night_report = {**record, "cache": cache_name, "metadata": episode.metadata,
                            "epochs": int(len(episode.wake)),
                            "valid_reference_epochs": int((episode.wake >= 0).sum()),
                            "wake_reference_epochs": int((episode.wake == 1).sum()),
                            "windows": single["report"],
                            "cache_sha256": sha256_file(root / "processed" / cache_name)}
            report["nights"].append(night_report)
            write_json(root / "manifests" / "audit.json", report)
            print("audited", record["partition"], record["participant"], record["night"],
                  "origins", len(single["target"]), flush=True)
        report["partitions"] = {key: build_windows(value, **_window_kwargs(config))["report"]
                                for key, value in episodes.items()}
        report["status"] = "complete"
        report["finished_utc"] = datetime.now(timezone.utc).isoformat()
        write_json(root / "manifests" / "audit.json", report)
    except Exception as error:
        report["status"] = "failed"
        report["error"] = f"{type(error).__name__}: {error}"
        write_json(root / "manifests" / "audit.json", report)
        raise
    return {"status": report["status"], "nights": len(report["nights"]),
            "test_accessed": False,
            "partitions": {key: {k: v for k, v in value.items() if k != "episodes"}
                           for key, value in report["partitions"].items()}}


def load_cached(root, protocol_path=None):
    root = Path(root)
    protocol_path = Path(protocol_path or CONFIG)
    acquisition = _acquisition(root, _configuration(protocol_path))
    audit_path = root / "manifests" / "audit.json"
    report = json.loads(audit_path.read_text())
    if report["status"] != "complete" or report["protocol_sha256"] != sha256_file(protocol_path):
        raise ValueError("a complete audit of the current protocol is required")
    expected = {(r["participant"], r["night"], r["partition"])
                for r in acquisition["selected_records"]}
    actual = {(r["participant"], r["night"], r["partition"]) for r in report["nights"]}
    if actual != expected or len(actual) != len(report["nights"]):
        raise ValueError("audit inventory does not match acquisition")
    episodes = {"train": [], "validation": []}
    for record in report["nights"]:
        cache = root / "processed" / record["cache"]
        if sha256_file(cache) != record["cache_sha256"]:
            raise ValueError("processed cache changed")
        with np.load(cache, allow_pickle=False) as arrays:
            episode = Episode(record["participant"], record["night"], arrays["epoch_start"],
                              arrays["features"], arrays["wake"], json.loads(str(arrays["metadata"])))
        episodes[record["partition"]].append(episode)
    return episodes


def run(root, protocol_path=None):
    root = Path(root)
    protocol_path = Path(protocol_path or CONFIG)
    config = _configuration(protocol_path)
    episodes = load_cached(root, protocol_path)
    batches = {key: build_windows(value, **_window_kwargs(config)) for key, value in episodes.items()}
    for key, minimum in (("train", 2), ("validation", 2)):
        complete = (batches[key]["target"] >= 0).all(axis=1)
        people = np.unique(batches[key]["participant"][complete])
        if len(people) < minimum:
            raise ValueError(f"{key} needs at least {minimum} participants with full reference horizons")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    output = root / "results" / ("diagnostic_" + stamp)
    output.mkdir(parents=True, exist_ok=False)
    code_root = Path(__file__).resolve().parent.parent
    source_paths = sorted((code_root / "sleep_g3").glob("*.py"))
    receipt = {"status": "running", "evidence_class": "diagnostic_only",
               "started_utc": datetime.now(timezone.utc).isoformat(),
               "command": [sys.executable, *sys.argv], "host": platform.node(), "device": "cpu",
               "slurm_job_id": os.environ.get("SLURM_JOB_ID"),
               "python": platform.python_version(), "numpy": np.__version__,
               "protocol": config, "protocol_sha256": sha256_file(protocol_path),
               "protocol_path": str(protocol_path.resolve()),
               "code_sha256": {str(p.relative_to(code_root)): sha256_file(p) for p in source_paths},
               "acquisition_sha256": sha256_file(root / "manifests" / "acquisition.json"),
               "audit_sha256": sha256_file(root / "manifests" / "audit.json"),
               "test_accessed": False, "feature_names": list(FEATURE_NAMES)}
    write_json(output / "run_metadata.json", receipt)
    try:
        model = BaselineSuite(seed=config["split_seed"], ridge_alpha=config["ridge_alpha"],
                              min_epochs=config["minimum_dwell_epochs"], soft_penalty=config["soft_penalty"])
        model.fit(batches["train"], train_episodes=episodes["train"])
        arms = model.predict(batches["validation"])
        if config.get("include_reference_controls", False):
            from .controls import FixedControls
            controls = FixedControls().fit(batches["train"])
            arms.update(controls.predict(batches["validation"]))
            model.fit_report_["reference_controls"] = controls.fit_report_
            with open(output / "reference_controls.pkl", "wb") as stream:
                pickle.dump(controls, stream, protocol=4)
        evaluation = evaluate_forecasts(batches["validation"]["target"], arms,
                                        batches["validation"]["participant"],
                                        epoch_seconds=config["epoch_seconds"],
                                        short_max_epochs=config["short_event_max_epochs"])
        write_json(output / "metrics.json", evaluation)
        write_json(output / "fit_report.json", model.fit_report_)
        with open(output / "model.pkl", "wb") as stream:
            pickle.dump(model, stream, protocol=4)
        arrays = {"target": batches["validation"]["target"],
                  "participant": batches["validation"]["participant"],
                  "night": batches["validation"]["night"],
                  "origin_time": batches["validation"]["origin_time"]}
        for name, prediction in arms.items():
            for key, value in prediction.items():
                if value is not None:
                    arrays[name + "__" + key] = value
        np.savez_compressed(output / "validation_predictions.npz", **arrays)
        receipt["status"] = "scored_diagnostic"
        receipt["finished_utc"] = datetime.now(timezone.utc).isoformat()
        receipt["fit_report"] = model.fit_report_
        write_json(output / "run_metadata.json", receipt)
        write_json(root / "latest_run.json", {"path": str(output), "status": receipt["status"]})
        with open(root / "run_registry.jsonl", "a") as stream:
            stream.write(json.dumps({"path": str(output), "status": receipt["status"],
                                     "protocol_sha256": receipt["protocol_sha256"],
                                     "finished_utc": receipt["finished_utc"]}) + "\n")
        return {"output": str(output), "status": receipt["status"],
                "coverage": evaluation["coverage"],
                "wake_minutes_mae": {name: values["total_wake"]["mae_minutes"]
                                     for name, values in evaluation["arms"].items()},
                "test_accessed": False}
    except Exception as error:
        receipt["status"] = "failed_diagnostic"
        receipt["error"] = f"{type(error).__name__}: {error}"
        write_json(output / "run_metadata.json", receipt)
        raise
