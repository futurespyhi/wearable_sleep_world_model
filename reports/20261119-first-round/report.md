# Four-stage sleep forecast on HPG

Run `20261119-first-round` completed seed 0 on the fixed six-night smoke cohort. All six methods ran on CPU. The fixed 38-night audit identified five verified source files with timestamp anomalies. The complete-cohort cache gate stopped the expansion before epoch timing or training.

At +30 minutes explicit wrist-motion rollout scored **0.1930 macro-F1**, compared with **0.2051** for fusion rollout and **0.1783** for direct prediction. The explicit arm had zero Wake recall at all three leads and higher all-lead NLL than both comparators. Learned persistence led macro-F1 at all three leads. This run checks the implementation on two validation participants and one seed. The main model comparison requires the full audited cohort and all three seeds.

| Run identity | Value |
| --- | --- |
| Experiment basis | [Four-stage first-round spec](../../specs/2026-11-18_wearable_sleep_world_model.md) |
| Spec commit and branch base | `ce949469eb2e5531e1d539fb69645f6ca0a6bbaa` |
| Executed code commit | `182c89e56451fdc0f8dff39f36b0d41fbe6dc7a3` |
| Spec Git blob | `6240dbbe1e6290ff31d00a628c5843bd48ad8217` |
| Run configuration | Frozen 30-minute history and horizon, 30-second epochs, 10-epoch stride, 80% past common coverage, participant split seed 40 |
| Reference and cutoff | BIDSleep 1.0.1 expert labels, Wake / N1+N2 / N3 / REM, unknown masked. Sensor timestamps strictly before cutoff. |
| Train and validation | Smoke 4/2 people × 1 night. Expansion 12/7 people × 2 nights. Seven test participants remained sealed. |
| Aggregate artifacts | [Seed 0 scores and paired differences](seed-0.json), [audit and execution provenance](provenance.json) |

### Execution and checks

Jobs ran on `c0709a-s30.ufhpc` with 2 CPUs and 8 GiB each. The Milan burst queue showed a long wait. Both jobs moved to the development CPU partition `hpg-dev` under investment QoS `so589980.ucf` with their original limits and dependency.

| HPG job | Phase | Requested time | Wall time | State | Inside-process peak RSS |
| --- | --- | --- | --- | --- | --- |
| `51961125` | G3 regression, four-stage tests, six-night audit and seed 0 | 30 min | 58 s | COMPLETED `0:0` | 177.2 MiB audit, 440.0 MiB training and scoring |
| `51961273` | 38-night timestamp audit and cache | 2 h | 53 s | FAILED `3:0` (audit gate) | 177.9 MiB |

- The compute-node log shows 95 G3 regression and 15 new tests passed. These checked stage mapping and unknown masks, exact cutoff, per-epoch and cross-block wrist features, fixed 60-step state feedback, and exact equality of all 60 predictions for all six methods when raw data at and after a fixed cutoff were changed.
- Six-night data audit took 8.46 s and training plus scoring took 8.99 s. The expansion audit and diagnostics took 52.20 s. The process RSS values above come from `getrusage`; Slurm's batch wrapper RSS was recorded separately.
- Audit and G3 tests used shared Python 3.11.4, NumPy 1.25.2, SciPy 1.11.3 and site-local pandas 2.1.4. The neural tests and fits used the shared HPG PyTorch prefix `/apps/pytorch/1.13.0/bin/python`, Python 3.10.8, NumPy 1.26.0, SciPy 1.11.3, pandas 1.4.3 and PyTorch 1.13.0+cu117 on CPU.
- Neural arms used state dimension 32, action embedding dimension 16, batch size 64, Adam at 0.001, and 15 epochs. Huber delta was 1 in normalized HR units, with loss weight 0.1. The shared transition uses an affine gated residual. Persistence uses a fixed L2 0.01 multinomial classifier over past summaries at 1, 10, 30 and 60 steps. These are implementation choices for parameters left open by the spec.

### Expanded data audit

All 38 nights were visited in acquisition order. 22/24 training nights and 11/14 validation nights passed. Their cache files retain 1,761 training and 748 validation origins. Those are partial-coverage counts. The training command requires a complete audit, and the partial cache remains available for diagnostics.

Each issue below was confirmed from the original timestamp text after file checksums matched the acquisition receipt. The row numbers are physical CSV lines, including the header for motion. The scanner reads original row order. Each affected file had one reported event of the listed type. Every event was within a single 200,000-row block.

| Partition | File | CSV lines | Source issue | Label interval impact |
| --- | --- | --- | --- | --- |
| Train | `Bidslab36/1/motion.csv` | 54,622 → 54,623 | Timestamp decreased 0.183314 s | Intersected known epoch 32, zero-based |
| Train | `Bidslab44/1/hr.csv` | 6,681 and 6,682 | Equal timestamp, different readings | 35,021.298 s after label interval end |
| Validation | `Bidslab68/1/hr.csv` | 5,047 and 5,048 | Equal timestamp, different readings | 14,555.002 s after label interval end |
| Validation | `Bidslab35/1/motion.csv` | 36,713 → 36,714 | Timestamp decreased 0.162618 s | Intersected known epoch 25, zero-based |
| Validation | `Bidslab49/2/motion.csv` | 2,466,112 → 2,466,113 | Timestamp decreased 0.2552967 s | More than 87,808 s after label interval end |

The strict audit preserves the original file order and cohort. It reports the first failing sensor in each affected night, so later sensor files in a failed night may require another pass. No expanded epoch timing, device comparison, seeds 0/1/2 fit or validation scores exist. The next data decision is a documented rule for the two within-interval reversals and the three findings after the label interval, followed by a new audit of the same 38 nights.

### Reproduction and artifacts

The [Slurm script](../../scripts/stage_forecast.sbatch) ran with a Git archive of the pinned code commit. Positional arguments are mode (`smoke` or `audit`), extracted source snapshot, output root, historical G3 root, spec SHA and executed code SHA. The exact job scripts and aggregate receipts can be traced through the paths below. These are external HPG locations.

```text
/home/zi700688.ucf/wearable-sleep-artifacts/20261119-first-round/
  code/
  smoke-51961125.log
  smoke-cache/audit.json
  smoke-cache/audit_execution.json
  smoke/
    execution.json
    seed-0.json
    aggregate.json
    seed-0-predictions.npz
    seed-0-<arm>.pt
  audit-51961273.log
  expanded-cache/audit.json
  expanded-cache/audit_execution.json

/orange/so589980.ucf/zi700688.ucf/IoT_medical/g3_sleep_forecasting_20261029/
  work/pilot_seed40/manifests/acquisition.json
  work/expanded_seed40_12t7v2n/manifests/acquisition.json
```

## Six-night scoring details
Metric source `/home/zi700688.ucf/wearable-sleep-artifacts/20261119-first-round/smoke/seed-0.json` with execution record `/home/zi700688.ucf/wearable-sleep-artifacts/20261119-first-round/smoke/execution.json`.

### Validation coverage

The shared evaluation set contains 2 participants, 2 nights and 161 retained forecast origins. Of 121 complete reference horizons, 96 contain zero Wake. Across all leads there are 8,610 known label instances and 1,050 unknown or out-of-record instances.

| Lead | Participants | Known origins | Unknown origins | Wake | Light | Deep | REM |
| --- | --- | --- | --- | --- | --- | --- | --- |
| +5 min | 2 | 148 | 13 | 6 | 80 | 25 | 37 |
| +15 min | 2 | 144 | 17 | 6 | 78 | 23 | 37 |
| +30 min | 2 | 138 | 23 | 6 | 78 | 17 | 37 |

The table shows unweighted label support. The primary confusion matrix has unit total mass per participant before averaging and uses only known reference labels. A dash denotes an unestimated or unavailable quantity.

### Stage forecasts

Per-participant normalized confusion matrices determine F1 and Wake recall. +30 min is the priority lead.

| Method | +5 macro-F1 | +15 macro-F1 | +30 macro-F1 | +5 Wake recall | +15 Wake recall | +30 Wake recall |
| --- | --- | --- | --- | --- | --- | --- |
| Training stage prior | 0.1748 | 0.1749 | 0.1797 | 0.0000 | 0.0000 | 0.0000 |
| Learned persistence | 0.3957 | 0.2885 | 0.2688 | 0.3451 | 0.0000 | 0.0000 |
| HR + ACC direct | 0.2284 | 0.1749 | 0.1783 | 0.0000 | 0.0000 | 0.0000 |
| HR-only rollout | 0.1748 | 0.1735 | 0.1797 | 0.0000 | 0.0000 | 0.0000 |
| HR + ACC fusion rollout | 0.1743 | 0.1828 | 0.2051 | 0.0000 | 0.0000 | 0.0000 |
| Explicit wrist-motion rollout | 0.1735 | 0.1721 | 0.1930 | 0.0000 | 0.0000 | 0.0000 |

<details><summary>Per-class F1 and lead probability scores</summary>

| Method | Lead | Wake F1 | Light F1 | Deep F1 | REM F1 | NLL | Brier |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Training stage prior | +5 min | 0.0000 | 0.6994 | 0.0000 | 0.0000 | 1.1535 | 0.6386 |
| Training stage prior | +15 min | 0.0000 | 0.6995 | 0.0000 | 0.0000 | 1.1461 | 0.6346 |
| Training stage prior | +30 min | 0.0000 | 0.7190 | 0.0000 | 0.0000 | 1.1128 | 0.6147 |
| Learned persistence | +5 min | 0.2086 | 0.6318 | 0.2678 | 0.4745 | 1.4849 | 0.6809 |
| Learned persistence | +15 min | 0.0000 | 0.5905 | 0.2852 | 0.2784 | 1.9124 | 0.7659 |
| Learned persistence | +30 min | 0.0000 | 0.5782 | 0.2068 | 0.2904 | 1.9046 | 0.7668 |
| HR + ACC direct | +5 min | 0.0000 | 0.6973 | 0.0000 | 0.2163 | 1.0981 | 0.6190 |
| HR + ACC direct | +15 min | 0.0000 | 0.6995 | 0.0000 | 0.0000 | 1.1480 | 0.6413 |
| HR + ACC direct | +30 min | 0.0000 | 0.7133 | 0.0000 | 0.0000 | 1.1301 | 0.6310 |
| HR-only rollout | +5 min | 0.0000 | 0.6994 | 0.0000 | 0.0000 | 1.2344 | 0.6551 |
| HR-only rollout | +15 min | 0.0000 | 0.6940 | 0.0000 | 0.0000 | 1.1262 | 0.6217 |
| HR-only rollout | +30 min | 0.0000 | 0.7190 | 0.0000 | 0.0000 | 1.1343 | 0.6126 |
| HR + ACC fusion rollout | +5 min | 0.0000 | 0.6972 | 0.0000 | 0.0000 | 1.1744 | 0.6406 |
| HR + ACC fusion rollout | +15 min | 0.0000 | 0.6849 | 0.0000 | 0.0463 | 1.1174 | 0.6246 |
| HR + ACC fusion rollout | +30 min | 0.0000 | 0.7200 | 0.0000 | 0.1003 | 1.0921 | 0.6031 |
| Explicit wrist-motion rollout | +5 min | 0.0000 | 0.6939 | 0.0000 | 0.0000 | 1.1969 | 0.6461 |
| Explicit wrist-motion rollout | +15 min | 0.0000 | 0.6883 | 0.0000 | 0.0000 | 1.1481 | 0.6408 |
| Explicit wrist-motion rollout | +30 min | 0.0000 | 0.7221 | 0.0000 | 0.0497 | 1.1414 | 0.6261 |

</details>

<details><summary>Pooled and participant-balanced confusion matrices</summary>

Each cell gives pooled count / participant-balanced mass. For multiple seeds, each count is a mean of seed-specific counts. Rows are reference labels. Columns are predicted labels.

| Method | Lead | Reference | Wake | Light | Deep | REM |
| --- | --- | --- | --- | --- | --- | --- |
| Training stage prior | +5 min | Wake | 0 / 0.0000 | 6 / 0.0414 | 0 / 0.0000 | 0 / 0.0000 |
| Training stage prior | +5 min | Light | 0 / 0.0000 | 80 / 0.5377 | 0 / 0.0000 | 0 / 0.0000 |
| Training stage prior | +5 min | Deep | 0 / 0.0000 | 25 / 0.1705 | 0 / 0.0000 | 0 / 0.0000 |
| Training stage prior | +5 min | REM | 0 / 0.0000 | 37 / 0.2504 | 0 / 0.0000 | 0 / 0.0000 |
| Training stage prior | +15 min | Wake | 0 / 0.0000 | 6 / 0.0426 | 0 / 0.0000 | 0 / 0.0000 |
| Training stage prior | +15 min | Light | 0 / 0.0000 | 78 / 0.5379 | 0 / 0.0000 | 0 / 0.0000 |
| Training stage prior | +15 min | Deep | 0 / 0.0000 | 23 / 0.1622 | 0 / 0.0000 | 0 / 0.0000 |
| Training stage prior | +15 min | REM | 0 / 0.0000 | 37 / 0.2574 | 0 / 0.0000 | 0 / 0.0000 |
| Training stage prior | +30 min | Wake | 0 / 0.0000 | 6 / 0.0445 | 0 / 0.0000 | 0 / 0.0000 |
| Training stage prior | +30 min | Light | 0 / 0.0000 | 78 / 0.5612 | 0 / 0.0000 | 0 / 0.0000 |
| Training stage prior | +30 min | Deep | 0 / 0.0000 | 17 / 0.1257 | 0 / 0.0000 | 0 / 0.0000 |
| Training stage prior | +30 min | REM | 0 / 0.0000 | 37 / 0.2686 | 0 / 0.0000 | 0 / 0.0000 |
| Learned persistence | +5 min | Wake | 2 / 0.0143 | 2 / 0.0136 | 0 / 0.0000 | 2 / 0.0136 |
| Learned persistence | +5 min | Light | 10 / 0.0670 | 55 / 0.3701 | 2 / 0.0143 | 13 / 0.0863 |
| Learned persistence | +5 min | Deep | 1 / 0.0071 | 18 / 0.1205 | 4 / 0.0286 | 2 / 0.0143 |
| Learned persistence | +5 min | REM | 1 / 0.0071 | 19 / 0.1299 | 0 / 0.0000 | 17 / 0.1134 |
| Learned persistence | +15 min | Wake | 0 / 0.0000 | 5 / 0.0352 | 0 / 0.0000 | 1 / 0.0074 |
| Learned persistence | +15 min | Light | 8 / 0.0550 | 50 / 0.3452 | 1 / 0.0074 | 19 / 0.1304 |
| Learned persistence | +15 min | Deep | 3 / 0.0221 | 13 / 0.0894 | 4 / 0.0294 | 3 / 0.0213 |
| Learned persistence | +15 min | REM | 3 / 0.0213 | 23 / 0.1614 | 1 / 0.0074 | 10 / 0.0673 |
| Learned persistence | +30 min | Wake | 0 / 0.0000 | 5 / 0.0368 | 0 / 0.0000 | 1 / 0.0077 |
| Learned persistence | +30 min | Light | 10 / 0.0727 | 48 / 0.3465 | 1 / 0.0077 | 19 / 0.1344 |
| Learned persistence | +30 min | Deep | 3 / 0.0231 | 8 / 0.0599 | 2 / 0.0154 | 4 / 0.0274 |
| Learned persistence | +30 min | REM | 0 / 0.0000 | 27 / 0.1942 | 0 / 0.0000 | 10 / 0.0744 |
| HR + ACC direct | +5 min | Wake | 0 / 0.0000 | 6 / 0.0414 | 0 / 0.0000 | 0 / 0.0000 |
| HR + ACC direct | +5 min | Light | 0 / 0.0000 | 77 / 0.5178 | 0 / 0.0000 | 3 / 0.0200 |
| HR + ACC direct | +5 min | Deep | 0 / 0.0000 | 25 / 0.1705 | 0 / 0.0000 | 0 / 0.0000 |
| HR + ACC direct | +5 min | REM | 0 / 0.0000 | 32 / 0.2176 | 0 / 0.0000 | 5 / 0.0328 |
| HR + ACC direct | +15 min | Wake | 0 / 0.0000 | 6 / 0.0426 | 0 / 0.0000 | 0 / 0.0000 |
| HR + ACC direct | +15 min | Light | 0 / 0.0000 | 78 / 0.5379 | 0 / 0.0000 | 0 / 0.0000 |
| HR + ACC direct | +15 min | Deep | 0 / 0.0000 | 23 / 0.1622 | 0 / 0.0000 | 0 / 0.0000 |
| HR + ACC direct | +15 min | REM | 0 / 0.0000 | 37 / 0.2574 | 0 / 0.0000 | 0 / 0.0000 |
| HR + ACC direct | +30 min | Wake | 0 / 0.0000 | 6 / 0.0445 | 0 / 0.0000 | 0 / 0.0000 |
| HR + ACC direct | +30 min | Light | 0 / 0.0000 | 77 / 0.5544 | 0 / 0.0000 | 1 / 0.0068 |
| HR + ACC direct | +30 min | Deep | 0 / 0.0000 | 17 / 0.1257 | 0 / 0.0000 | 0 / 0.0000 |
| HR + ACC direct | +30 min | REM | 0 / 0.0000 | 37 / 0.2686 | 0 / 0.0000 | 0 / 0.0000 |
| HR-only rollout | +5 min | Wake | 0 / 0.0000 | 6 / 0.0414 | 0 / 0.0000 | 0 / 0.0000 |
| HR-only rollout | +5 min | Light | 0 / 0.0000 | 80 / 0.5377 | 0 / 0.0000 | 0 / 0.0000 |
| HR-only rollout | +5 min | Deep | 0 / 0.0000 | 25 / 0.1705 | 0 / 0.0000 | 0 / 0.0000 |
| HR-only rollout | +5 min | REM | 0 / 0.0000 | 37 / 0.2504 | 0 / 0.0000 | 0 / 0.0000 |
| HR-only rollout | +15 min | Wake | 0 / 0.0000 | 6 / 0.0426 | 0 / 0.0000 | 0 / 0.0000 |
| HR-only rollout | +15 min | Light | 0 / 0.0000 | 77 / 0.5313 | 1 / 0.0066 | 0 / 0.0000 |
| HR-only rollout | +15 min | Deep | 0 / 0.0000 | 23 / 0.1622 | 0 / 0.0000 | 0 / 0.0000 |
| HR-only rollout | +15 min | REM | 0 / 0.0000 | 37 / 0.2574 | 0 / 0.0000 | 0 / 0.0000 |
| HR-only rollout | +30 min | Wake | 0 / 0.0000 | 6 / 0.0445 | 0 / 0.0000 | 0 / 0.0000 |
| HR-only rollout | +30 min | Light | 0 / 0.0000 | 78 / 0.5612 | 0 / 0.0000 | 0 / 0.0000 |
| HR-only rollout | +30 min | Deep | 0 / 0.0000 | 17 / 0.1257 | 0 / 0.0000 | 0 / 0.0000 |
| HR-only rollout | +30 min | REM | 0 / 0.0000 | 37 / 0.2686 | 0 / 0.0000 | 0 / 0.0000 |
| HR + ACC fusion rollout | +5 min | Wake | 0 / 0.0000 | 5 / 0.0342 | 1 / 0.0071 | 0 / 0.0000 |
| HR + ACC fusion rollout | +5 min | Light | 0 / 0.0000 | 79 / 0.5313 | 1 / 0.0064 | 0 / 0.0000 |
| HR + ACC fusion rollout | +5 min | Deep | 0 / 0.0000 | 25 / 0.1705 | 0 / 0.0000 | 0 / 0.0000 |
| HR + ACC fusion rollout | +5 min | REM | 0 / 0.0000 | 37 / 0.2504 | 0 / 0.0000 | 0 / 0.0000 |
| HR + ACC fusion rollout | +15 min | Wake | 0 / 0.0000 | 6 / 0.0426 | 0 / 0.0000 | 0 / 0.0000 |
| HR + ACC fusion rollout | +15 min | Light | 0 / 0.0000 | 75 / 0.5174 | 0 / 0.0000 | 3 / 0.0205 |
| HR + ACC fusion rollout | +15 min | Deep | 0 / 0.0000 | 23 / 0.1622 | 0 / 0.0000 | 0 / 0.0000 |
| HR + ACC fusion rollout | +15 min | REM | 0 / 0.0000 | 36 / 0.2508 | 0 / 0.0000 | 1 / 0.0066 |
| HR + ACC fusion rollout | +30 min | Wake | 0 / 0.0000 | 6 / 0.0445 | 0 / 0.0000 | 0 / 0.0000 |
| HR + ACC fusion rollout | +30 min | Light | 0 / 0.0000 | 77 / 0.5544 | 0 / 0.0000 | 1 / 0.0068 |
| HR + ACC fusion rollout | +30 min | Deep | 0 / 0.0000 | 17 / 0.1257 | 0 / 0.0000 | 0 / 0.0000 |
| HR + ACC fusion rollout | +30 min | REM | 0 / 0.0000 | 35 / 0.2541 | 0 / 0.0000 | 2 / 0.0145 |
| Explicit wrist-motion rollout | +5 min | Wake | 0 / 0.0000 | 6 / 0.0414 | 0 / 0.0000 | 0 / 0.0000 |
| Explicit wrist-motion rollout | +5 min | Light | 1 / 0.0064 | 79 / 0.5313 | 0 / 0.0000 | 0 / 0.0000 |
| Explicit wrist-motion rollout | +5 min | Deep | 0 / 0.0000 | 25 / 0.1705 | 0 / 0.0000 | 0 / 0.0000 |
| Explicit wrist-motion rollout | +5 min | REM | 0 / 0.0000 | 37 / 0.2504 | 0 / 0.0000 | 0 / 0.0000 |
| Explicit wrist-motion rollout | +15 min | Wake | 0 / 0.0000 | 6 / 0.0426 | 0 / 0.0000 | 0 / 0.0000 |
| Explicit wrist-motion rollout | +15 min | Light | 0 / 0.0000 | 76 / 0.5248 | 0 / 0.0000 | 2 / 0.0132 |
| Explicit wrist-motion rollout | +15 min | Deep | 0 / 0.0000 | 23 / 0.1622 | 0 / 0.0000 | 0 / 0.0000 |
| Explicit wrist-motion rollout | +15 min | REM | 0 / 0.0000 | 37 / 0.2574 | 0 / 0.0000 | 0 / 0.0000 |
| Explicit wrist-motion rollout | +30 min | Wake | 0 / 0.0000 | 6 / 0.0445 | 0 / 0.0000 | 0 / 0.0000 |
| Explicit wrist-motion rollout | +30 min | Light | 0 / 0.0000 | 78 / 0.5612 | 0 / 0.0000 | 0 / 0.0000 |
| Explicit wrist-motion rollout | +30 min | Deep | 0 / 0.0000 | 17 / 0.1257 | 0 / 0.0000 | 0 / 0.0000 |
| Explicit wrist-motion rollout | +30 min | REM | 0 / 0.0000 | 36 / 0.2617 | 0 / 0.0000 | 1 / 0.0068 |

</details>

### Paired differences

Each row subtracts the comparison method from the explicit wrist-motion rollout on the same participants and forecast origins. Higher F1 and recall and lower NLL and Brier are favorable.

| Explicit minus | Lead | Δ macro-F1 | Δ Wake recall | Δ NLL | Δ Brier |
| --- | --- | --- | --- | --- | --- |
| HR + ACC fusion rollout | +5 min | -0.0008 | +0.0000 | +0.0225 | +0.0055 |
| HR + ACC fusion rollout | +15 min | -0.0107 | +0.0000 | +0.0307 | +0.0162 |
| HR + ACC fusion rollout | +30 min | -0.0121 | +0.0000 | +0.0493 | +0.0229 |
| HR + ACC direct | +5 min | -0.0549 | +0.0000 | +0.0987 | +0.0271 |
| HR + ACC direct | +15 min | -0.0028 | +0.0000 | +0.0001 | -0.0005 |
| HR + ACC direct | +30 min | +0.0146 | +0.0000 | +0.0113 | -0.0050 |

| Explicit minus | All-lead Δ NLL | All-lead Δ Brier |
| --- | --- | --- |
| HR + ACC fusion rollout | +0.0300 | +0.0147 |
| HR + ACC direct | +0.0433 | +0.0163 |

### Probability, heart rate and Wake-minute diagnostics

Probability and HR scores average valid target epochs within participant and then average participants. The Brier score sums squared errors over the four classes. Wake-minute scores use complete label horizons with participant weighting. Expected Wake minutes sum predicted Wake probabilities times 0.5.

| Method | NLL | Brier | HR MAE (bpm) | HR targets | Mean Wake (min) | Wake MAE (min) | Wake bias (min) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Training stage prior | 1.1336 | 0.6241 | — | — | 1.8443 | 1.9991 | 1.0161 |
| Learned persistence | 1.7352 | 0.7238 | — | — | 3.2276 | 3.2824 | 2.3993 |
| HR + ACC direct | 1.1283 | 0.6287 | 4.5019 | 9258 | 1.4799 | 1.6230 | 0.6516 |
| HR-only rollout | 1.1551 | 0.6268 | 5.7628 | 9258 | 2.1027 | 2.1071 | 1.2744 |
| HR + ACC fusion rollout | 1.1417 | 0.6303 | 5.5900 | 9258 | 2.3785 | 2.3561 | 1.5502 |
| Explicit wrist-motion rollout | 1.1717 | 0.6450 | 5.1868 | 9258 | 2.7283 | 2.5862 | 1.9001 |
| Last observed HR | — | — | 5.0087 | 9258 | — | — | — |
| Training Wake-minute median | — | — | — | — | 0.0000 | 0.8283 | -0.8283 |
| Zero Wake minutes | — | — | — | — | 0.0000 | 0.8283 | -0.8283 |

### Short Wake events

The short Wake event score uses the fixed Wake probability threshold of 0.5 and G3's one-to-one overlap matching. Unique event recall counts an event if any evaluable origin hits it. The participant macro rate averages per-event fractions of origins with a hit.

| Method | Duration | Unique events | People | Repeated events | Event-origin instances | Hit origins | Any-origin recall | Participant macro rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Training stage prior | All short | 1 | 1 | 1 | 5 | 0.0 | 0.0000 | 0.0000 |
| Training stage prior | 1 epoch | 0 | 0 | 0 | 0 | 0.0 | — | — |
| Training stage prior | 2 epochs | 1 | 1 | 1 | 5 | 0.0 | 0.0000 | 0.0000 |
| Learned persistence | All short | 1 | 1 | 1 | 5 | 0.0 | 0.0000 | 0.0000 |
| Learned persistence | 1 epoch | 0 | 0 | 0 | 0 | 0.0 | — | — |
| Learned persistence | 2 epochs | 1 | 1 | 1 | 5 | 0.0 | 0.0000 | 0.0000 |
| HR + ACC direct | All short | 1 | 1 | 1 | 5 | 0.0 | 0.0000 | 0.0000 |
| HR + ACC direct | 1 epoch | 0 | 0 | 0 | 0 | 0.0 | — | — |
| HR + ACC direct | 2 epochs | 1 | 1 | 1 | 5 | 0.0 | 0.0000 | 0.0000 |
| HR-only rollout | All short | 1 | 1 | 1 | 5 | 0.0 | 0.0000 | 0.0000 |
| HR-only rollout | 1 epoch | 0 | 0 | 0 | 0 | 0.0 | — | — |
| HR-only rollout | 2 epochs | 1 | 1 | 1 | 5 | 0.0 | 0.0000 | 0.0000 |
| HR + ACC fusion rollout | All short | 1 | 1 | 1 | 5 | 0.0 | 0.0000 | 0.0000 |
| HR + ACC fusion rollout | 1 epoch | 0 | 0 | 0 | 0 | 0.0 | — | — |
| HR + ACC fusion rollout | 2 epochs | 1 | 1 | 1 | 5 | 0.0 | 0.0000 | 0.0000 |
| Explicit wrist-motion rollout | All short | 1 | 1 | 1 | 5 | 0.0 | 0.0000 | 0.0000 |
| Explicit wrist-motion rollout | 1 epoch | 0 | 0 | 0 | 0 | 0.0 | — | — |
| Explicit wrist-motion rollout | 2 epochs | 1 | 1 | 1 | 5 | 0.0 | 0.0000 | 0.0000 |

### Run and training measurements

Job `51961125` ran on `c0709a-s30.ufhpc` with 2 allocated CPUs and `cpu` as the model device. The process took 8.99 s and reached 440.0 MiB peak host RSS. Packages were numpy 1.26.0, scipy 1.11.3, pandas 1.4.3, torch 1.13.0+cu117.

Training used 312 origins. The stage prior and fitted persistence together took 0.02 s. Persistence fit 256 coefficients including intercept terms.

| Seed | Method | Parameters | Epochs | Fit (s) | Mean epoch (s) | Predict (s) | Process peak RSS (MiB) | Peak GPU allocation (MiB) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | HR + ACC direct | 32780 | 15 | 1.41 | 0.09 | 0.01 | 431.0 | — |
| 0 | HR-only rollout | 18709 | 15 | 2.09 | 0.14 | 0.02 | 439.0 | — |
| 0 | HR + ACC fusion rollout | 18709 | 15 | 2.10 | 0.14 | 0.02 | 439.0 | — |
| 0 | Explicit wrist-motion rollout | 18709 | 15 | 2.12 | 0.14 | 0.02 | 440.0 | — |

Host RSS is the process high-water mark at the end of each fit.

| Seed | Scoring and prediction export (s) |
| --- | --- |
| 0 | 0.08 |
