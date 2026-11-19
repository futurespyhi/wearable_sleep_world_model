#!/usr/bin/env bash
set -euo pipefail
task_mode=${1:?}
sleep_root=$(cd "$(dirname "$0")" && pwd)
sleep_snapshot=$sleep_root/code
sleep_historical=/orange/so589980.ucf/zi700688.ucf/IoT_medical/g3_sleep_forecasting_20261029
read -r sleep_commit < "$sleep_root/code_commit"
sleep_spec=a5499473ca01e5980e96ca68e5bfc21f1ffdae06
export STAGE_DEVICE=cpu
export STAGE_TIMESTAMP_POLICY=$sleep_snapshot/experiments/stage_forecast/expanded_timestamp_policy.json
export STAGE_REFERENCE_CACHE=/home/zi700688.ucf/wearable-sleep-artifacts/20261119-first-round/expanded-cache
sleep_args=(--parsable --account=so589980.ucf --qos=so589980.ucf --partition=hpg-dev --ntasks=1 --cpus-per-task=2 --mem=8G)
case "$task_mode" in
    smoke|benchmark) sleep_wall=00:30:00 ;;
    audit|expanded) sleep_wall=02:00:00 ;;
    *) exit 2 ;;
esac
if [[ $task_mode == audit ]]; then
    read -r smoke_job < "$sleep_root/smoke.job"
    sleep_args+=("--dependency=afterok:${smoke_job%%;*}" --kill-on-invalid-dep=yes)
fi
sleep_command=(sbatch "${sleep_args[@]}" "--time=$sleep_wall" "--job-name=sleep-$task_mode" "--output=$sleep_root/$task_mode-%j.log" "$sleep_snapshot/scripts/stage_forecast.sbatch" "$task_mode" "$sleep_snapshot" "$sleep_root" "$sleep_historical" "$sleep_spec" "$sleep_commit")
printf '%q ' "${sleep_command[@]}" > "$sleep_root/$task_mode.command"
printf '\n' >> "$sleep_root/$task_mode.command"
"${sleep_command[@]}" | tee "$sleep_root/$task_mode.job"
