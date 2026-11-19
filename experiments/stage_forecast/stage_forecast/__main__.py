"""HPG entry point for four-stage audit, timing, and scoring."""

import argparse
import importlib
import os
import platform
import resource
import socket
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from sleep_g3.protocol import sha256_file, write_json


def now():
    return datetime.now(timezone.utc).isoformat()


def environment(neural=False):
    packages = {}
    names = ("numpy", "scipy", "pandas", "torch") if neural else ("numpy", "scipy", "pandas")
    for name in names:
        module = importlib.import_module(name)
        packages[name] = {"version": module.__version__, "path": module.__file__}
    return {
        "python": sys.version,
        "python_path": sys.executable,
        "packages": packages,
        "platform": platform.platform(),
        "host": socket.gethostname(),
        "slurm_job_id": os.environ.get("SLURM_JOB_ID"),
        "cpus_per_task": os.environ.get("SLURM_CPUS_PER_TASK"),
    }


def identity(args):
    return {
        "spec_commit": args.spec_commit,
        "code_commit": args.code_commit,
        "run_id": args.output.parent.name,
        "phase": args.output.name,
        "created_utc": now(),
        "environment": environment(neural=args.command != "audit" and not args.baselines_only),
    }


def audit(args):
    from .data import build_cache

    args.output.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    provenance = identity(args)
    provenance.update({
        "source_root": str(args.source_root),
        "protocol": str(args.protocol),
        "protocol_sha256": sha256_file(args.protocol),
        "audit_status": "running",
    })
    metadata = args.output / "audit_execution.json"
    if metadata.exists():
        raise FileExistsError(f"Use a distinct output directory: {args.output}")
    write_json(metadata, provenance)
    try:
        result = build_cache(args.source_root, args.protocol, args.output)
        provenance["audit_status"] = result["status"]
    except Exception as exc:
        provenance["audit_status"] = "error"
        provenance["error"] = str(exc)
        raise
    finally:
        provenance["elapsed_seconds"] = time.monotonic() - started
        provenance["peak_rss_mib"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
        write_json(metadata, provenance)
    print(f"Audit {result['status']} in {provenance['elapsed_seconds']:.1f}s: {args.output}", flush=True)
    return 0 if result["status"] == "complete" else 3


def run(args):
    import numpy as np

    from .baselines import fit_persistence, predict_persistence, stage_prior
    from .data import fit_standardizer, load_cache
    from .metrics import score_seed, summarize_seeds

    args.output.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    provenance = identity(args)
    audit_path = args.cache / "audit.json"
    provenance.update({
        "mode": args.command,
        "device": args.device,
        "seeds": args.seeds,
        "epochs": args.epochs,
        "cache": str(args.cache),
        "audit_sha256": sha256_file(audit_path),
        "status": "running",
    })
    execution_path = args.output / "execution.json"
    if execution_path.exists():
        raise FileExistsError(f"Use a distinct output directory: {args.output}")
    write_json(execution_path, provenance)
    try:
        windows = load_cache(args.cache)
        train, val = windows["train"], windows["val"]
        scaler = fit_standardizer(train)
        train_hr, train_acc = scaler.transform(train.history)
        val_hr, val_acc = scaler.transform(val.history)
        scaled_target = ((train.future_hr - scaler.hr_center) / scaler.hr_scale).astype(np.float32)
        hr_history = val.history[..., 0]
        last_hr = np.full(len(hr_history), np.nan)
        usable = np.isfinite(hr_history).any(axis=1)
        indices = hr_history.shape[1] - 1 - np.argmax(np.isfinite(hr_history[usable, ::-1]), axis=1)
        last_hr[usable] = hr_history[usable, indices]
        provenance["origins"] = {"train": len(train.stage), "validation": len(val.stage)}
        provenance["standardization"] = {
            "channels": ["hr_mean", "hr_std", "acc_norm_std", "acc_diff_rms"],
            "center": scaler.center.tolist(),
            "scale": scaler.scale.tolist(),
        }

        if args.command == "benchmark":
            from .models import fit_model

            _, details = fit_model(
                "explicit", train_hr, train_acc, train.stage, scaled_target,
                train.future_hr_mask, seed=args.seeds[0], device=args.device, epochs=1,
            )
            write_json(args.output / "timing.json", details)
        else:
            baseline_started = time.monotonic()
            persistence = fit_persistence(train_hr, train_acc, train.current_stage)
            baselines = {
                "stage_prior": stage_prior(train.stage, len(val.stage)),
                "persistence": predict_persistence(persistence, val_hr, val_acc),
            }
            provenance["baseline_seconds"] = time.monotonic() - baseline_started
            provenance["persistence"] = persistence.metadata
            scores = {}
            if not args.baselines_only:
                import torch

                from .models import ARMS, fit_model, predict

            for seed in args.seeds:
                probabilities = dict(baselines)
                hr_predictions = {}
                timing = {}
                for arm in (() if args.baselines_only else ARMS):
                    write_json(execution_path, {**provenance, "active_seed": seed, "active_arm": arm})
                    print(f"Fitting {arm} seed={seed} on {args.device}", flush=True)
                    model, timing[arm] = fit_model(
                        arm, train_hr, train_acc, train.stage, scaled_target,
                        train.future_hr_mask, seed=seed, device=args.device, epochs=args.epochs,
                    )
                    prediction_started = time.monotonic()
                    probabilities[arm], scaled_pred = predict(model, val_hr, val_acc, device=args.device)
                    timing[arm]["prediction_seconds"] = time.monotonic() - prediction_started
                    hr_predictions[arm] = scaled_pred * scaler.hr_scale + scaler.hr_center
                    torch.save(
                        {
                            "model": {name: value.detach().cpu() for name, value in model.state_dict().items()},
                            "arm": arm,
                            "hr_features": train_hr.shape[-1],
                            "acc_features": train_acc.shape[-1],
                            "code_commit": args.code_commit,
                            "spec_commit": args.spec_commit,
                        },
                        args.output / f"seed-{seed}-{arm}.pt",
                    )
                    print(f"Finished {arm} seed={seed} in {timing[arm]['fit_seconds']:.2f}s", flush=True)
                contrasts = [] if args.baselines_only else [("explicit", "fusion"), ("explicit", "direct")]
                scoring_started = time.monotonic()
                scores[seed] = score_seed(
                    val.stage, val.participant, val.night, val.origin_time, probabilities,
                    training_target=train.stage, training_participant=train.participant,
                    future_hr=val.future_hr, future_hr_mask=val.future_hr_mask,
                    hr_predictions=hr_predictions, last_hr=last_hr, contrasts=contrasts,
                )
                np.savez_compressed(
                    args.output / f"seed-{seed}-predictions.npz",
                    participant=val.participant, night=val.night, origin_time=val.origin_time,
                    **{f"stage_{key}": value for key, value in probabilities.items()},
                    **{f"hr_{key}": value for key, value in hr_predictions.items()},
                )
                scores[seed]["fit"] = timing
                scores[seed]["scoring_seconds"] = time.monotonic() - scoring_started
                write_json(args.output / f"seed-{seed}.json", scores[seed])
            write_json(args.output / "aggregate.json", summarize_seeds(scores))
        provenance["status"] = "completed"
    except Exception as exc:
        provenance["status"] = "failed"
        provenance["error"] = str(exc)
        raise
    finally:
        provenance["elapsed_seconds"] = time.monotonic() - started
        provenance["peak_rss_mib"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
        write_json(execution_path, provenance)
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("audit", "benchmark", "run"):
        command = commands.add_parser(name)
        command.add_argument("--output", required=True, type=Path)
        command.add_argument("--spec-commit", required=True)
        command.add_argument("--code-commit", required=True)
        if name == "audit":
            command.add_argument("--source-root", required=True, type=Path)
            command.add_argument("--protocol", required=True, type=Path)
        else:
            command.add_argument("--cache", required=True, type=Path)
            command.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
            command.add_argument("--seeds", type=int, nargs="+", required=True)
            command.add_argument("--epochs", type=int, default=15)
            command.add_argument("--baselines-only", action="store_true")
    args = parser.parse_args(argv)
    if args.command == "audit":
        return audit(args)
    if args.command == "benchmark" and (len(args.seeds) != 1 or args.baselines_only):
        parser.error("benchmark needs exactly one seed and the neural environment")
    if args.epochs != 15:
        parser.error("the first-round comparison fixes training at 15 epochs")
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
