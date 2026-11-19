"""Check the fixed six-night regression against the published seed 0 scores."""

import json
import sys
from pathlib import Path

from sleep_g3.protocol import sha256_file, write_json


def check(reference_path, output):
    reference = json.loads(reference_path.read_text())
    actual_path = output / "seed-0.json"
    actual = json.loads(actual_path.read_text())
    if reference["coverage"] != actual["coverage"] or set(reference["methods"]) != set(actual["methods"]):
        raise ValueError("Six-night regression changed the cohort, target support, or methods")
    deltas = {}
    for method, original in reference["methods"].items():
        current = actual["methods"][method]
        deltas[method] = {}
        for lead, before in original["leads"].items():
            after = current["leads"][lead]
            for key in ("support", "origins", "unknown", "pooled_confusion_matrix"):
                if after[key] != before[key]:
                    raise ValueError(f"Six-night regression changed {method} +{lead} {key}")
            deltas[method][lead] = {
                key: after[key] - before[key] for key in ("macro_f1", "wake_recall", "nll", "brier")
            }
    largest = max(abs(value) for method in deltas.values() for lead in method.values() for value in lead.values())
    write_json(output / "regression.json", {
        "reference_seed_sha256": sha256_file(reference_path), "actual_seed_sha256": sha256_file(actual_path),
        "coverage": actual["coverage"], "endpoint_differences": deltas, "largest_absolute_difference": largest,
        "all_endpoint_confusion_matrices_equal": True,
    })
    print(f"Six-night smoke checked against published scores, maximum endpoint difference {largest:.9g}")


if __name__ == "__main__":
    check(Path(sys.argv[1]), Path(sys.argv[2]))
