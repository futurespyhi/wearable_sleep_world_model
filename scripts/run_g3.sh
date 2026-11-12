#!/usr/bin/env bash
set -euo pipefail

g3_repo_root="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
if [[ -z "${SLURM_JOB_ID:-}" ]] || [[ "$(hostname)" == login* ]]; then
    echo "Run with srun on an allocated compute node." >&2
    exit 2
fi

g3_code_root="$g3_repo_root/experiments/g3"
g3_module_path="$g3_code_root"
if [[ -n "${G3_DEPS_ROOT:-}" ]]; then
    if [[ ! -d "$G3_DEPS_ROOT" ]]; then
        echo "G3_DEPS_ROOT does not point to an existing dependency directory." >&2
        exit 2
    fi
    g3_module_path="$G3_DEPS_ROOT:$g3_module_path"
fi
export PYTHONPATH="$g3_module_path${PYTHONPATH:+:$PYTHONPATH}"
export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
# Python -m searches the working directory before PYTHONPATH. Do not let an
# invocation from the historical Orange tree import its old sleep_g3 package.
cd "$g3_repo_root"
exec "${G3_PYTHON:-/apps/python/3.11/bin/python}" "$@"
