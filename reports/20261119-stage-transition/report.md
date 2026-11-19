# Stage transition controls on the fixed 38 nights

At +30 minutes the empirical transition model scored **1.1989 NLL**, compared with **1.1955** for the prior mixture and **1.1963** for the stage prior. Lower NLL is better. Among 535 origins whose endpoint stage differed from the current reference stage, transition scored **1.2149** versus **1.2072** for the mixture. All three comparisons missed the prespecified criterion. At +5 min, transition had the lowest NLL (1.1358). The +30 min transition and mixture models both had zero Wake recall on 48 Wake targets. These differences describe seven validation participants with overlapping forecast windows.

All three controls used the identical saved current-stage probabilities from learned persistence at the 969 audited validation cutoffs. The 12 training participants contributed 1,936 origins. We held out both nights of each training participant together when fitting the prior mixture. Its prior weights at +5/+15/+30 min were 0.3365, 0.6038 and 0.9258. Each of the 60 transition matrices used empirical training counts from known reference pairs, and every current-stage row had support. Validation labels were used to score predictions and identify the changed-stage subgroup. An overall score requires a known target. The subgroup also requires a known current stage. NLL and confusion matrices use the same participant weighting as the source run. The seven test participants remained sealed. [Analysis plan](../../specs/2026-11-19_stage_transition_controls.md) · [Weights, matrices and training counts](fit.json) · [Aggregate metrics](metrics.json)

| Lead (min) | Participants | Known | Unknown | Wake | Light | Deep | REM |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| +5 | 7 | 942 | 27 | 54 | 431 | 186 | 271 |
| +15 | 7 | 920 | 49 | 51 | 424 | 173 | 272 |
| +30 | 7 | 887 | 82 | 48 | 421 | 149 | 269 |

| Method | Lead (min) | NLL ↓ | Macro-F1 ↑ | Wake recall ↑ |
| --- | ---: | ---: | ---: | ---: |
| persistence | +5 | 1.2033 | 0.3541 | 0.1217 |
| persistence | +15 | 1.3461 | 0.2807 | 0.0365 |
| persistence | +30 | 1.4533 | 0.2352 | 0.0386 |
| prior_mix | +5 | 1.1425 | 0.3212 | 0.1047 |
| prior_mix | +15 | 1.1942 | 0.2068 | 0.0365 |
| prior_mix | +30 | 1.1955 | 0.1564 | 0.0000 |
| transition | +5 | 1.1358 | 0.3251 | 0.1047 |
| transition | +15 | 1.1960 | 0.1678 | 0.0000 |
| transition | +30 | 1.1989 | 0.1564 | 0.0000 |
| stage_prior | +5 | 1.2229 | 0.1528 | 0.0000 |
| stage_prior | +15 | 1.2142 | 0.1534 | 0.0000 |
| stage_prior | +30 | 1.1963 | 0.1564 | 0.0000 |
| direct_mean | +5 | 1.1522 | 0.2672 | 0.0358 |
| direct_mean | +15 | 1.2034 | 0.2144 | 0.0061 |
| direct_mean | +30 | 1.2111 | 0.1772 | 0.0000 |

At +30 min, 535 of 876 origins with both stages known had a different target stage from the current stage (7 participants, target support 20 Wake, 227 Light, 91 Deep, 197 REM). 11 additional known +30 min targets had an unknown current stage.

| Method | +30 min changed-stage NLL ↓ |
| --- | ---: |
| persistence | 1.6226 |
| prior_mix | 1.2072 |
| transition | 1.2149 |
| stage_prior | 1.1958 |
| direct_mean | 1.2427 |

| +30 min NLL difference | All known targets | Changed stages |
| --- | ---: | ---: |
| Transition − prior mix | 0.0034 | 0.0077 |
| Transition − stage prior | 0.0027 | — |

Direct scores average the three independently scored seeds. NE means unavailable support.


CPU Slurm job `51965958` completed on `c0709a-s30` in 4 s with two CPU cores and 8 GiB allocated. All seven synthetic checks passed. The saved persistence, stage prior and all three direct forecasts reproduced the published endpoint NLL, macro-F1 and Wake recall exactly. The code and analysis plan used commit `2384b3b57ec28793918c132cacc9f940358f49b4`. The fixed cache identity was `769709116695441b2bf65146058aa4c33b6908c02918c6b75ad5e02b2c1d8dd9`. The per-origin forecasts remain on HPG in `/home/zi700688.ucf/wearable-sleep-artifacts/20261119-stage-transition/results/`. [Execution receipt and input hashes](execution.json) · [CPU launcher](../../scripts/stage_transition.sbatch) · [Source experiment](../20261119-stage-expanded/report.md)
