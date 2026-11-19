#!/bin/bash
set -euo pipefail
root=/home/zi700688.ucf/wearable-sleep-artifacts/20261119-stage-expanded
export G3_PYTHON=/apps/pytorch/1.13.0/bin/python
export G3_DEPS_ROOT=
bash "$root/analysis-code/scripts/run_stage_forecast.sh" -m stage_forecast.lead_curve "$root/expanded-cache" "$root/expanded"
