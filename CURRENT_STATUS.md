# Current status

The current task is [four-stage sleep forecasting](specs/2026-11-18_wearable_sleep_world_model.md) from Apple Watch heart rate and wrist acceleration available at the cutoff. The six-night seed 0 smoke completed on HPG. The fixed 38-night run is blocked by the timestamp audit. See the [first-round report](reports/20261119-first-round/report.md).

| Item | Status |
| --- | --- |
| Implementation | Stage cache and past-only forecasts, six matched methods, scoring and Slurm launcher |
| Regression and synthetic checks | 110 passed, including cutoff invariance for all 60 predictions |
| Six-night smoke | Job `51961125`, 4 training and 2 validation people. All six methods scored with seed 0. |
| 38-night expansion | Job `51961273`, 33/38 nights audited and cached. Five timestamp failures confirmed against original source text. |
| 38-night CPU timing and seeds 0/1/2 | Pending a complete fixed-cohort audit |
| Test holdout | All 7 test participants remain sealed |

The smoke's +30-minute macro-F1 was 0.1930 for explicit wrist-motion rollout, 0.2051 for fusion rollout and 0.1783 for direct prediction. Learned persistence reached 0.2688. The smoke verifies the pipeline on two validation participants and one seed. The planned three-seed comparison requires the 38-night cohort.

Two motion reversals intersect the annotated interval. One further motion reversal and two conflicting HR duplicates occur after their label intervals. A documented handling rule and a new audit of the fixed cohort are needed before expanded fitting. The [report](reports/20261119-first-round/report.md) lists exact CSV lines and artifact locations.

The October binary G3 reports remain available through the [report index](reports/README.md). The four-stage experiment reuses the acquisition and origin rules from G3. Forecast scoring and conclusions for the two tasks remain distinct.
