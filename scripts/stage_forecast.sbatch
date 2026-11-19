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
    local cohort=$1 protocol=$2 output=$3
    shift 3
    g3 -m stage_forecast audit --spec-commit "$spec_commit" --code-commit "$code_commit" \
        --source-root "$historical/work/$cohort" --protocol "$checkout/experiments/g3/$protocol" --output "$output" "$@"
}

case "$mode" in
    smoke)
        g3 -m unittest discover -v -s "$checkout/experiments/g3/tests"
        stage_tests="$checkout/experiments/stage_forecast/tests"
        for suite in "$stage_tests"/test_*.py; do
            [[ ${suite##*/} == test_stage_models.py ]] && continue
            g3 -m unittest discover -v -s "$stage_tests" -p "${suite##*/}"
        done
        stage -c 'import torch; print(torch.__version__)'
        stage -m unittest discover -v -s "$stage_tests" -p test_stage_models.py
        audit pilot_seed40 protocol.json "$artifacts/smoke-cache"
        stage -m stage_forecast run --spec-commit "$spec_commit" --code-commit "$code_commit" \
            --cache "$artifacts/smoke-cache" --output "$artifacts/smoke" --seeds 0
        stage -m stage_forecast.regression "$checkout/reports/20261119-first-round/seed-0.json" "$artifacts/smoke"
        ;;
    audit)
        audit_args=(--timestamp-policy "${STAGE_TIMESTAMP_POLICY:?expanded audit requires the fixed policy}")
        if [[ -n ${STAGE_REFERENCE_CACHE:-} ]]; then
            audit_args+=(--reference-cache "$STAGE_REFERENCE_CACHE")
        fi
        audit expanded_seed40_12t7v2n expanded_protocol.json "$artifacts/expanded-cache" "${audit_args[@]}"
        ;;
    benchmark|expanded)
        command=benchmark
        output="benchmark-${STAGE_DEVICE:-cpu}"
        seeds=(0)
        if [[ $mode == expanded ]]; then
            command=run
            output=expanded
            seeds=(0 1 2)
        fi
        stage -m stage_forecast "$command" --spec-commit "$spec_commit" --code-commit "$code_commit" \
            --cache "$artifacts/expanded-cache" --output "$artifacts/$output" \
            --timestamp-policy "${STAGE_TIMESTAMP_POLICY:?expanded comparison requires the fixed policy}" \
            --device "${STAGE_DEVICE:-cpu}" --seeds "${seeds[@]}"
        ;;
    *)
        printf 'Unknown mode: %s\n' "$mode" >&2
        exit 2
        ;;
esac
