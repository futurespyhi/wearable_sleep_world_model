"""Score all 60 leads from the fixed expanded run's saved validation forecasts."""

import argparse
import csv
import json
from pathlib import Path
from tempfile import NamedTemporaryFile

import numpy as np
from sleep_g3.protocol import sha256_file

from .data import load_cache
from .metrics import EPOCH_SECONDS, HORIZON, LEAD_INDICES, STAGES, _groups, _probability_losses, _support, _target_mean
from .reporting import METHODS


def export(cache, output):
    execution = json.loads((output / "execution.json").read_text())
    if (execution["status"] != "completed" or execution["seeds"] != [0, 1, 2]
            or execution["audit_sha256"] != sha256_file(cache / "audit.json")):
        raise ValueError("expected completed three-seed execution and matching audited cache")
    val = load_cache(cache)["val"]
    known = val.stage >= 0
    groups = _groups(val.participant)
    support = [_support(val.stage[:, step]) for step in range(HORIZON)]
    participants = [sum(bool(known[g, step].any()) for g in groups) for step in range(HORIZON)]
    endpoint = {step: str(minutes) for minutes, step in LEAD_INDICES.items()}
    rows = []
    for seed in execution["seeds"]:
        scores = json.loads((output / f"seed-{seed}.json").read_text())["methods"]
        with np.load(output / f"seed-{seed}-predictions.npz", allow_pickle=False) as saved:
            for field in ("participant", "night", "origin_time"):
                if not np.array_equal(saved[field], getattr(val, field)):
                    raise ValueError(f"seed {seed} ordered {field} differs from cache")
            for arm in METHODS:
                probability = saved[f"stage_{arm}"]
                if (probability.shape != (*val.stage.shape, len(STAGES))
                        or not np.isfinite(probability).all() or (probability < 0).any()
                        or (probability > 1).any() or not np.allclose(probability.sum(axis=2), 1, atol=1e-6, rtol=1e-6)):
                    raise ValueError(f"invalid saved stage probabilities for seed {seed} {arm}")
                nll, brier = _probability_losses(val.stage, probability)
                for step, counts in enumerate(support):
                    losses = {metric: _target_mean(array[:, step], known[:, step], groups)
                              for metric, array in (("nll", nll), ("brier", brier))}
                    if step in endpoint:
                        reported = scores[arm]["leads"][endpoint[step]]
                        for metric, value in losses.items():
                            reference = reported[metric]
                            if ((reference is None) != (value is None) or
                                    (value is not None and not np.isclose(reference, value, rtol=1e-10, atol=1e-12))):
                                raise ValueError(f"seed {seed} {arm} step {step+1} {metric} differs from original score")
                        if counts != reported["support"] or participants[step] != reported["participants"]:
                            raise ValueError(f"seed {seed} {arm} step {step+1} support differs from original score")
                    n_known = sum(counts.values())
                    rows.append({"seed": seed, "method": arm, "lead_step": step + 1,
                                 "lead_minutes": (step + 1) * EPOCH_SECONDS / 60,
                                 "participants": participants[step], "known": n_known, "unknown": len(known) - n_known,
                                 **{f"support_{stage.lower()}": count for stage, count in counts.items()}, **losses})
    destination = output / "lead-curve.csv"
    with NamedTemporaryFile(mode="w", newline="", dir=output, delete=False) as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    Path(stream.name).replace(destination)
    print(f"Wrote {len(rows)} aggregate rows to {destination}. All endpoint scores agree.", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cache", type=Path)
    parser.add_argument("expanded_output", type=Path)
    args = parser.parse_args()
    export(args.cache, args.expanded_output)
