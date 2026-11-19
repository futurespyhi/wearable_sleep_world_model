# Current-stage oracle on the fixed 38 nights

Using the expert stage at cutoff reduced +30-minute NLL from **1.1941 to 1.1435** on the 876 validation origins with both endpoint labels. The oracle used the row of the frozen training matrix corresponding to the observed current stage. The wearable forecast used the same matrix with its saved probabilities over current stages. Six of seven participants had lower overall NLL with the oracle, with an equal-participant mean paired difference of **−0.0507**.

This benefit depended on the endpoint stage. For the 341 origins with matching stages at cutoff and +30 minutes, the oracle improved on the wearable transition for all seven participants (mean difference **−0.1309**). For the 535 origins with different endpoint stages, oracle NLL was higher for six of seven (mean difference **+0.0122**). Access to the expert current stage therefore improved the average forecast on this cohort while leaving the changed-stage forecasts worse on average. Neighboring origins overlap. This comparison uses expert information available only in the offline diagnostic.

All four methods use the same origins within each lead and stratum. Both the stage at cutoff and the endpoint stage must be known. Same and changed compare those two stages.

| Lead | Stratum | People | Origins | Wake | Light | Deep | REM |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| +5 min | overall | 7 | 936 | 53 | 430 | 184 | 269 |
| +15 min | overall | 7 | 909 | 48 | 422 | 170 | 269 |
| +30 min | overall | 7 | 876 | 45 | 419 | 145 | 267 |
| +30 min | same | 7 | 341 | 25 | 192 | 54 | 70 |
| +30 min | changed | 7 | 535 | 20 | 227 | 91 | 197 |

The stage counts above refer to the future endpoint. NLL below averages within each person, then across people. Lower values are better.

| Lead | Stratum | Oracle transition | Estimated-state transition | Prior mixture | Stage prior |
| --- | --- | ---: | ---: | ---: | ---: |
| +5 min | overall | 0.8661 | 1.1348 | 1.1413 | 1.2214 |
| +15 min | overall | 1.0413 | 1.1914 | 1.1899 | 1.2107 |
| +30 min | overall | 1.1435 | 1.1941 | 1.1911 | 1.1919 |
| +30 min | same | 1.0135 | 1.1444 | 1.1426 | 1.1634 |
| +30 min | changed | 1.2270 | 1.2149 | 1.2072 | 1.1958 |

**Paired +30-minute NLL differences.** A negative value favors the oracle. Each difference uses the same origins for the oracle and its comparator. NE indicates no evaluable origins.

| Participant | Origins | Oracle − transition | Oracle − prior mixture | Oracle − stage prior |
| --- | ---: | ---: | ---: | ---: |
| Bidslab32 | 184 | -0.0026 | +0.0077 | +0.0056 |
| Bidslab35 | 118 | +0.0011 | +0.0062 | +0.0093 |
| Bidslab42 | 106 | -0.1143 | -0.0943 | -0.0907 |
| Bidslab45 | 144 | -0.0034 | -0.0202 | -0.0215 |
| Bidslab49 | 70 | -0.0522 | -0.0429 | -0.0394 |
| Bidslab50 | 131 | -0.1759 | -0.1843 | -0.2113 |
| Bidslab68 | 123 | -0.0076 | -0.0056 | +0.0088 |
| **Equal-participant mean** | — | -0.0507 | -0.0476 | -0.0485 |

<details><summary>Participant differences for same and changed stages</summary>

**Same stage**

| Participant | Origins | Oracle − transition | Oracle − prior mixture | Oracle − stage prior |
| --- | ---: | ---: | ---: | ---: |
| Bidslab32 | 86 | -0.0695 | -0.0574 | -0.0754 |
| Bidslab35 | 36 | -0.0386 | -0.0309 | -0.0566 |
| Bidslab42 | 24 | -0.1376 | -0.0729 | -0.1055 |
| Bidslab45 | 64 | -0.0261 | -0.0627 | -0.0778 |
| Bidslab49 | 28 | -0.1939 | -0.1982 | -0.2091 |
| Bidslab50 | 67 | -0.3871 | -0.4165 | -0.4664 |
| Bidslab68 | 36 | -0.0636 | -0.0651 | -0.0586 |
| **Equal-participant mean** | — | -0.1309 | -0.1291 | -0.1499 |

**Changed stage**

| Participant | Origins | Oracle − transition | Oracle − prior mixture | Oracle − stage prior |
| --- | ---: | ---: | ---: | ---: |
| Bidslab32 | 98 | +0.0561 | +0.0648 | +0.0767 |
| Bidslab35 | 82 | +0.0185 | +0.0225 | +0.0382 |
| Bidslab42 | 82 | -0.1074 | -0.1006 | -0.0864 |
| Bidslab45 | 80 | +0.0148 | +0.0138 | +0.0236 |
| Bidslab49 | 42 | +0.0423 | +0.0607 | +0.0738 |
| Bidslab50 | 64 | +0.0453 | +0.0588 | +0.0558 |
| Bidslab68 | 87 | +0.0156 | +0.0190 | +0.0367 |
| **Equal-participant mean** | — | +0.0122 | +0.0199 | +0.0312 |

</details>

**Current stage at cutoff.** The saved wearable estimate p_t had NLL 1.1177 and macro-F1 0.4106 on 953 labeled origins from 7 participants. 16 of 969 origins had unknown current stage.

| Current-stage label | Wake | Light | Deep | REM |
| --- | ---: | ---: | ---: | ---: |
| Origins | 57 | 433 | 193 | 270 |

Run `20261119-stage-oracle` reused the original 969 validation origins. The three controls reproduced the source changed-stage NLLs exactly. The expanded cache, saved outputs and train-fitted coefficients were verified against the previous run. Seven test participants stayed sealed. CPU Slurm job `51966781` completed in 2 seconds with 2 cores and 8 GiB. All three synthetic tests passed. The executed Git revision was `cc32870b7b58ab33a34354817fde2d6fe6be04b5`. HPG artifacts are under `/home/zi700688.ucf/wearable-sleep-artifacts/20261119-stage-oracle/`. [Aggregate metrics](metrics.json) · [Input identities and execution receipt](execution.json) · [Source transition comparison](../20261119-stage-transition/report.md)
