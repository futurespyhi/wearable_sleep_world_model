#!/bin/bash
#SBATCH --job-name=sleep-recordtime
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:10:00
set -euo pipefail
snapshot=${1:?git archive}
artifacts=${2:?artifact parent}
output=${3:?new output directory}
revision=${4:?code commit}
export G3_PYTHON=/apps/pytorch/1.13.0/bin/python
export G3_DEPS_ROOT=
launcher="$snapshot/scripts/run_stage_forecast.sh"
bash "$launcher" -m unittest discover -v -s "$snapshot/experiments/stage_forecast/tests" -p 'test_recording_time*.py'
bash "$launcher" -m stage_forecast.recording_time "$artifacts/20261119-stage-expanded" \
    "$artifacts/20261119-stage-transition" "$artifacts/20261119-stage-oracle" "$snapshot/reports" "$output" "$revision"
