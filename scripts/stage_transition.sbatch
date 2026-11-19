#!/bin/bash
#SBATCH --job-name=sleep-transition
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:15:00
set -euo pipefail
snapshot=${1:?extracted Git archive}
source_run=${2:?expanded run directory}
output=${3:?new output directory}
revision=${4:?full Git commit}
export G3_PYTHON=/apps/pytorch/1.13.0/bin/python
export G3_DEPS_ROOT=
launcher="$snapshot/scripts/run_stage_forecast.sh"
bash "$launcher" -m unittest discover -v -s "$snapshot/experiments/stage_forecast/tests" -p 'test_transition*.py'
bash "$launcher" -m stage_forecast.state_comparison "$source_run" "$snapshot/reports/20261119-stage-expanded" "$output" "$revision"
