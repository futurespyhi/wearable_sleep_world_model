import argparse
import json
import os
import platform
from pathlib import Path


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description="Past-only sleep forecasting diagnostic pilot")
    commands = parser.add_subparsers(dest="command", required=True)
    fetch = commands.add_parser("fetch", help="bounded public BIDSleep acquisition; test remains sealed")
    fetch.add_argument("--root", type=Path, required=True)
    fetch.add_argument("--train-subjects", type=int, default=4)
    fetch.add_argument("--val-subjects", type=int, default=2)
    fetch.add_argument("--nights", type=int, default=1)
    fetch.add_argument("--seed", type=int, default=40)
    fetch.add_argument("--metadata-only", action="store_true")
    fetch.add_argument("--archive", action="store_true", help="read only selected HR, label, and motion members through bounded ZIP ranges")
    fetch.add_argument("--max-total-bytes", type=int, default=900_000_000)
    fetch.add_argument("--max-file-bytes", type=int, default=200_000_000)
    fetch.add_argument("--reuse-root", type=Path, help="reuse verified selected files from a completed acquisition")
    for name in ("audit", "run", "diagnose", "analyze"):
        command = commands.add_parser(name)
        command.add_argument("--root", type=Path, required=True)
        if name in ("audit", "run"):
            command.add_argument("--protocol", type=Path, help="explicit protocol for this run; defaults to the original pilot")
    args = parser.parse_args()
    if not os.environ.get("SLURM_JOB_ID") or platform.node().startswith("login"):
        parser.error("all pipeline commands must execute through srun on an allocated compute node")
    if args.command == "fetch":
        from .fetch import acquire
        result = acquire(args.root, args.train_subjects, args.val_subjects, args.nights,
                         args.seed, args.metadata_only, args.max_total_bytes, args.archive,
                         args.reuse_root, args.max_file_bytes)
    elif args.command == "diagnose":
        from .diagnose import diagnose
        result = diagnose(args.root)
    elif args.command == "analyze":
        from .expanded_analysis import analyze
        result = analyze(args.root)
    else:
        from . import runner
        result = getattr(runner, args.command)(args.root, args.protocol)
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
