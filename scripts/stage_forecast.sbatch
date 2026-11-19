#!/usr/bin/env bash
set -euo pipefail

# Pass a Git archive extracted from CODE_COMMIT, so queued jobs are insulated
# from later edits to the task branch.
mode="${1:?mode required}"
checkout="${2:?source snapshot required}"
artifacts="${3:?artifact root required}"
historical="${4:?historical source root required}"
spec_commit="${5:?spec commit required}"
code_commit="${6:?code commit required}"
stage_python="${STAGE_PYTHON:-/apps/pytorch/1.13.0/bin/python}"
canonical_python=/apps/python/3.11/bin/python
launcher="$checkout/scripts/run_stage_forecast.sh"
export PYTHONUNBUFFERED=1
mkdir -p "$artifacts"

stage() {
    G3_PYTHON="$stage_python" G3_DEPS_ROOT= bash "$launcher" "$@"
}

g3() {
    G3_PYTHON="$canonical_python" G3_DEPS_ROOT="$historical/deps" bash "$launcher" "$@"
}

audit() {
    g3 -m stage_forecast audit --spec-commit "$spec_commit" --code-commit "$code_commit" \
        --source-root "$historical/work/$1" --protocol "$checkout/experiments/g3/$2" --output "$3"
}

case "$mode" in
    smoke)
        g3 -m unittest discover -v -s "$checkout/experiments/g3/tests"
        stage_tests="$checkout/experiments/stage_forecast/tests"
        g3 -m unittest discover -v -s "$stage_tests" -p test_stage_data.py
        g3 -m unittest discover -v -s "$stage_tests" -p test_stage_metrics.py
        if stage -c 'import numpy, scipy, pandas, torch; print(numpy.__version__, scipy.__version__, pandas.__version__, torch.__version__, torch.ones(1))'; then
            stage -m unittest discover -v -s "$stage_tests" -p test_stage_models.py
            audit pilot_seed40 protocol.json "$artifacts/smoke-cache"
            stage -m stage_forecast run --spec-commit "$spec_commit" --code-commit "$code_commit" \
                --cache "$artifacts/smoke-cache" --output "$artifacts/smoke" --seeds 0
        else
            printf 'PyTorch runtime unavailable. Run the stage-prior and persistence fallback.\n' >&2
            audit pilot_seed40 protocol.json "$artifacts/smoke-cache"
            g3 -m stage_forecast run --spec-commit "$spec_commit" --code-commit "$code_commit" \
                --cache "$artifacts/smoke-cache" --output "$artifacts/smoke-baselines" --seeds 0 --baselines-only
        fi
        ;;
    audit)
        audit expanded_seed40_12t7v2n expanded_protocol.json "$artifacts/expanded-cache"
        ;;
    benchmark)
        stage -m stage_forecast benchmark --spec-commit "$spec_commit" --code-commit "$code_commit" \
            --cache "$artifacts/expanded-cache" --output "$artifacts/benchmark-${STAGE_DEVICE:-cpu}" \
            --device "${STAGE_DEVICE:-cpu}" --seeds 0
        ;;
    expanded)
        stage -m stage_forecast run --spec-commit "$spec_commit" --code-commit "$code_commit" \
            --cache "$artifacts/expanded-cache" --output "$artifacts/expanded" \
            --device "${STAGE_DEVICE:-cpu}" --seeds 0 1 2
        ;;
    *)
        printf 'Unknown mode: %s\n' "$mode" >&2
        exit 2
        ;;
esac
