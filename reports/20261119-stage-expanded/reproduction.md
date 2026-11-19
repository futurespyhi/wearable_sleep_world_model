# Execution and reproduction

Run `20261119-stage-expanded` used the BIDSleep 1.0.1 acquisition already on HPG. A clean worktree started at the selected research spec. The four experiment jobs ran the same Git archive on CPU. Expanded training read the exact cache used in the benchmark. Acquisition, timestamp policy, cache checksums and the sealed split are documented in the [audit](audit.md).

| Input | Identity |
| --- | --- |
| Research spec and branch point | `a5499473ca01e5980e96ca68e5bfc21f1ffdae06`, [expanded comparison](../../specs/2026-11-19_stage_expanded_comparison.md), Git blob `5890729976bf095d118c7916a456de6e2dd7107d` |
| Executed data, training and scoring code | `43107763185e044dbc1ee570fef2ddd5fbb44306` |
| Cohort | Split seed 40, 12 train and seven validation participants, two nights each |
| Methods | Stage prior and learned persistence fitted once on training participants. Four neural arms independently trained at seeds 0, 1, 2 for 15 epochs. Adam at 0.001, batch 64, state 32, action embedding 16, masked CE plus 0.1 × masked HR Huber. |
| Forecast | Each cutoff uses 60 completed 30-second epochs and predicts the next 60. Cutoffs are spaced 10 epochs apart. Unknown and beyond-record stage targets are excluded from scoring. HR and ACC scaling uses distinct epochs in retained training histories. |
| Matched inputs | Fusion and explicit use the same past sensors and context. Latest measured wrist motion enters the initializer for fusion and the first transition for explicit. All 59 subsequent transitions use the evolving predicted state and the unknown wrist token. |

The smoke ran 121 tests on the compute node, including 95 G3 regressions. These covered cross-chunk timestamp reversals and duplicates, interval boundaries, masking before coverage and scaling, both streams after a failure, and future-value mutation after a fixed cutoff. Under both the strict path and the registered-epoch policy, changing future sensors and stage labels preserved all 60 predictions for every method. On the six-night seed 0 regression the predicted confusion matrices matched at all three endpoints for all six methods. The maximum absolute change in endpoint macro-F1, Wake recall, NLL and Brier was zero. [Smoke comparison](smoke-regression.json)

All four jobs used the investment QoS and account `so589980.ucf` on `hpg-dev`, node `c0709a-s30`, with two CPU cores, 8 GiB RAM and no GPU. Canonical audit/test Python was 3.11.4 with NumPy 1.25.2 and pandas 2.1.4. Neural training and scoring used the shared PyTorch prefix at `/apps/pytorch/1.13.0/bin/python`, Python 3.10.8, torch 1.13.0+cu117 (CPU), NumPy 1.26.0, SciPy 1.11.3, pandas 1.4.3. The launchers set OMP, OpenBLAS and MKL threads to one.

The explicit benchmark completed one training epoch in 0.8763 s with 31 optimizer updates and a process peak of 452.2 MiB. The generic execution receipt retains the 15-epoch configuration shared by all modes. The timing receipt records the executed benchmark epoch and its duration. All three seeds fit comfortably in one two-hour CPU allocation. [Epoch timing](cpu-epoch.json) · [Benchmark receipt](benchmark-execution.json)

The submission helper records the expanded shell commands and Slurm IDs under the run root. Reproduction requires the same historical root and receipt, the prior reference cache and an empty output directory. Set the full training code SHA in `code_commit` and extract its Git archive into `code/`. Run the helper in the order `smoke`, `audit`, `benchmark`, `expanded`, checking the audit and benchmark receipts before the next submission. The six-night smoke uses the strict policy. [Submission helper](submit.sh) · [Slurm launcher](../../scripts/stage_forecast.sbatch) · [Scheduler accounting](slurm.psv)

HPG artifact root is `/home/zi700688.ucf/wearable-sleep-artifacts/20261119-stage-expanded/`. Inside, `expanded-cache/` contains 38 per-night caches and the full audit, `benchmark-cpu/` contains the timing, and `expanded/` contains per-seed predictions, participant summaries, scores and four neural checkpoints per seed. Logs use `<mode>-<jobid>.log`. Raw inputs remain at `/orange/so589980.ucf/zi700688.ucf/IoT_medical/g3_sleep_forecasting_20261029/work/expanded_seed40_12t7v2n/`. [Audit environment](audit-execution.json) · [Fit environment](execution.json)

The [actual submission commands](submissions.txt) include the selected account, queue, time limits, dependencies, snapshots and run root. The final [60-lead export](lead-curve.sbatch) checked saved validation identifiers against the audited cache and reproduced all three reported endpoint probability scores and supports. The phase-specific process timing and Slurm IDs are in the [main report](report.md).
