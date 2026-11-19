#!/bin/bash
#SBATCH --job-name=sleep-oracle
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:10:00
set -euo pipefail
snapshot=${1:?git archive}
expanded=${2:?expanded artifact root}
transition=${3:?transition artifact root}
output=${4:?new output directory}
revision=${5:?source commit}
export G3_PYTHON=/apps/pytorch/1.13.0/bin/python
export G3_DEPS_ROOT=
launcher="$snapshot/scripts/run_stage_forecast.sh"
bash "$launcher" -m unittest discover -v -s "$snapshot/experiments/stage_forecast/tests" -p test_oracle_scores.py
bash "$launcher" -m stage_forecast.oracle_diagnostic "$expanded" "$transition" "$snapshot/reports" "$output" "$revision"
