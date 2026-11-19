# Can recent wrist signals predict a different sleep stage at the endpoint?

At +30 minutes, adding recent HR and wrist movement (C) increased binary NLL by 0.00363 and Brier by 0.00147 versus the same model using recording time and current-stage probabilities (B). C also scored worse than recording time alone (A), by 0.00157 NLL and 0.00054 Brier. Removing any one of the seven validation participants left C worse than B on both measures. The +30-minute comparison does not support feeding C's change probability back into the four-stage forecast.

| Lead | Origins with different endpoints / scored | A NLL / Brier | B NLL / Brier | C NLL / Brier | Omissions where C beats both on both metrics |
|---|---:|---:|---:|---:|---:|
| +5 min | 239 / 936 | 0.57865 / 0.19482 | 0.57861 / 0.19478 | 0.58120 / 0.19578 | 0/7 |
| +15 min | 399 / 909 | 0.68682 / 0.24686 | 0.68601 / 0.24646 | 0.68687 / 0.24689 | 1/7 |
| +30 min | 535 / 876 | 0.66256 / 0.23486 | 0.66050 / 0.23393 | 0.66413 / 0.23540 | 0/7 |

B had the lowest average loss at all three leads. At +30 minutes, B's small improvement over A persisted on both scores after each omission. C showed no average gain over A or B at +5 or +15 minutes either. At +15 minutes it beat both on both measures only after omitting Bidslab50. These comparisons cover seven validation participants whose windows overlap within nights.

**Target and predictors.** A positive is a difference between the reference stage in the last completed epoch and the stage at the forecast endpoint. A change followed by a return to the starting stage scores as zero. A used the four recording-time bins [0,2), [2,4), [4,6) and 6+ hours since the night's audited recStart. B added the four wearable probabilities of the current stage. C also used each signal's mean over the last 5 minutes before cutoff and its difference from the preceding 25-minute mean. The two signals were epoch mean HR and the within-epoch RMS of successive accelerometer vector differences. The model used four additional features and respected the original sensor masks.

**Fit and evaluation.** All three arms used logistic regression at each lead, with equal weight per eligible training origin, a fixed L2 coefficient of 0.01 and an unpenalized intercept. The train split contributed 1,904, 1,862 and 1,806 labeled pairs at +5, +15 and +30 minutes respectively. Continuous feature standardization and missing-value imputation used only eligible training rows. The current-stage estimate for each training participant used a scaler and classifier fitted to the other 11. Validation used the saved probabilities, which an independent refit on all 12 training participants reproduced exactly. The 969 fixed validation origins and each participant's same/changed support matched the parent report. Only origins with both stage labels known contributed to scores. Seven test participants stayed sealed.

The tables below give each participant equal weight. Brier is the squared error of the event probability. Negative paired differences favor the first arm. Leave-one-person-out rows keep the fitted model fixed and remove one validation participant from scoring. The prespecified stability criterion requires both C–A and C–B to be negative on both scores for the full sample and after every omission. All comparisons use unrounded values. [Protocol](../../specs/2026-11-19_endpoint_change.md) · [Parent recording-time report](../20261119-recording-time/report.md)

Slurm CPU job `51968086` completed on `c0709a-s30` in 3 seconds with 2 CPUs and 8 GiB allocated. Seven targeted tests passed. The diagnostic process took 1.65 seconds with 205.7 MiB peak RSS. The base was `5af00c4e57456e42bd25939b566c94f8ad7588a4`. Code and protocol ran at `b4b64b311db051d8d8fc7277805446e6fa8b7543`. The fitted coefficients and retained predictions are under `/home/zi700688.ucf/wearable-sleep-artifacts/20261119-endpoint-change/results/`. [Full-precision metrics](metrics.json) · [Execution receipt and input identities](execution.json)

<details><summary>+5 minutes · participant scores, paired differences and sensitivity</summary>

The prespecified stability criterion **failed**. The comparison covered 936 origins from 7 participants, with 239 positives and 697 negatives. Each participant contributes equally. Lower NLL and Brier are better.

| Arm | NLL | Brier |
| --- | --- | --- |
| A | 0.5787 | 0.1948 |
| B | 0.5786 | 0.1948 |
| C | 0.5812 | 0.1958 |

| Validation cohort | C − A NLL | C − A Brier | C − B NLL | C − B Brier | B − A NLL | B − A Brier |
| --- | --- | --- | --- | --- | --- | --- |
| All eligible participants | +0.0026 | +0.0010 | +0.0026 | +0.0010 | -0.0000 | -0.0000 |

### Participant scores and paired differences

| Participant | Origins | Positive | Negative | A NLL | A Brier | B NLL | B Brier | C NLL | C Brier |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Bidslab32 | 194 | 30 | 164 | 0.4556 | 0.1392 | 0.4569 | 0.1396 | 0.4637 | 0.1423 |
| Bidslab35 | 127 | 50 | 77 | 0.7288 | 0.2625 | 0.7309 | 0.2632 | 0.7286 | 0.2618 |
| Bidslab42 | 111 | 35 | 76 | 0.6442 | 0.2240 | 0.6419 | 0.2230 | 0.6582 | 0.2287 |
| Bidslab45 | 149 | 42 | 107 | 0.5975 | 0.2035 | 0.5974 | 0.2034 | 0.5952 | 0.2028 |
| Bidslab49 | 75 | 18 | 57 | 0.5481 | 0.1813 | 0.5456 | 0.1802 | 0.5360 | 0.1766 |
| Bidslab50 | 147 | 30 | 117 | 0.5132 | 0.1651 | 0.5157 | 0.1661 | 0.5242 | 0.1703 |
| Bidslab68 | 133 | 34 | 99 | 0.5632 | 0.1883 | 0.5620 | 0.1878 | 0.5626 | 0.1881 |

| Participant | C − A NLL | C − A Brier | C − B NLL | C − B Brier | B − A NLL | B − A Brier |
| --- | --- | --- | --- | --- | --- | --- |
| Bidslab32 | +0.0081 | +0.0031 | +0.0068 | +0.0026 | +0.0013 | +0.0005 |
| Bidslab35 | -0.0002 | -0.0007 | -0.0023 | -0.0014 | +0.0021 | +0.0007 |
| Bidslab42 | +0.0140 | +0.0047 | +0.0163 | +0.0057 | -0.0023 | -0.0009 |
| Bidslab45 | -0.0023 | -0.0007 | -0.0022 | -0.0006 | -0.0001 | -0.0001 |
| Bidslab49 | -0.0121 | -0.0047 | -0.0096 | -0.0036 | -0.0026 | -0.0011 |
| Bidslab50 | +0.0110 | +0.0051 | +0.0085 | +0.0041 | +0.0025 | +0.0010 |
| Bidslab68 | -0.0006 | -0.0002 | +0.0007 | +0.0003 | -0.0012 | -0.0004 |

### Omit one validation participant

Each row reaggregates the original predictions after removing that participant. Passing requires all four C-versus-A and C-versus-B differences to be strictly negative.

| Omitted | Remaining people | Origins | Positive | Negative | C − A NLL | C − A Brier | C − B NLL | C − B Brier | B − A NLL | B − A Brier | Pass |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Bidslab32 | 6 | 742 | 209 | 533 | +0.0016 | +0.0006 | +0.0019 | +0.0007 | -0.0003 | -0.0001 | no |
| Bidslab35 | 6 | 809 | 189 | 620 | +0.0030 | +0.0012 | +0.0034 | +0.0014 | -0.0004 | -0.0002 | no |
| Bidslab42 | 6 | 825 | 204 | 621 | +0.0006 | +0.0003 | +0.0003 | +0.0002 | +0.0003 | +0.0001 | no |
| Bidslab45 | 6 | 787 | 197 | 590 | +0.0034 | +0.0012 | +0.0034 | +0.0013 | -0.0000 | -0.0000 | no |
| Bidslab49 | 6 | 861 | 221 | 640 | +0.0050 | +0.0019 | +0.0046 | +0.0018 | +0.0004 | +0.0001 | no |
| Bidslab50 | 6 | 789 | 209 | 580 | +0.0011 | +0.0003 | +0.0016 | +0.0005 | -0.0005 | -0.0002 | no |
| Bidslab68 | 6 | 803 | 205 | 598 | +0.0031 | +0.0012 | +0.0029 | +0.0011 | +0.0002 | +0.0000 | no |

</details>

<details><summary>+15 minutes · participant scores, paired differences and sensitivity</summary>

The prespecified stability criterion **failed**. The comparison covered 909 origins from 7 participants, with 399 positives and 510 negatives. Each participant contributes equally. Lower NLL and Brier are better.

| Arm | NLL | Brier |
| --- | --- | --- |
| A | 0.6868 | 0.2469 |
| B | 0.6860 | 0.2465 |
| C | 0.6869 | 0.2469 |

| Validation cohort | C − A NLL | C − A Brier | C − B NLL | C − B Brier | B − A NLL | B − A Brier |
| --- | --- | --- | --- | --- | --- | --- |
| All eligible participants | +0.0000 | +0.0000 | +0.0009 | +0.0004 | -0.0008 | -0.0004 |

### Participant scores and paired differences

| Participant | Origins | Positive | Negative | A NLL | A Brier | B NLL | B Brier | C NLL | C Brier |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Bidslab32 | 190 | 67 | 123 | 0.6679 | 0.2375 | 0.6747 | 0.2409 | 0.6782 | 0.2426 |
| Bidslab35 | 121 | 62 | 59 | 0.6970 | 0.2519 | 0.6986 | 0.2527 | 0.6948 | 0.2508 |
| Bidslab42 | 109 | 55 | 54 | 0.7062 | 0.2565 | 0.6989 | 0.2528 | 0.7045 | 0.2555 |
| Bidslab45 | 147 | 68 | 79 | 0.6826 | 0.2447 | 0.6798 | 0.2434 | 0.6805 | 0.2438 |
| Bidslab49 | 73 | 30 | 43 | 0.6885 | 0.2477 | 0.6848 | 0.2459 | 0.6700 | 0.2389 |
| Bidslab50 | 140 | 56 | 84 | 0.6831 | 0.2450 | 0.6822 | 0.2445 | 0.6990 | 0.2528 |
| Bidslab68 | 129 | 61 | 68 | 0.6824 | 0.2447 | 0.6831 | 0.2450 | 0.6811 | 0.2439 |

| Participant | C − A NLL | C − A Brier | C − B NLL | C − B Brier | B − A NLL | B − A Brier |
| --- | --- | --- | --- | --- | --- | --- |
| Bidslab32 | +0.0103 | +0.0051 | +0.0035 | +0.0017 | +0.0068 | +0.0034 |
| Bidslab35 | -0.0022 | -0.0011 | -0.0038 | -0.0019 | +0.0016 | +0.0008 |
| Bidslab42 | -0.0017 | -0.0009 | +0.0056 | +0.0027 | -0.0073 | -0.0036 |
| Bidslab45 | -0.0020 | -0.0009 | +0.0008 | +0.0004 | -0.0028 | -0.0014 |
| Bidslab49 | -0.0185 | -0.0089 | -0.0148 | -0.0070 | -0.0037 | -0.0018 |
| Bidslab50 | +0.0158 | +0.0077 | +0.0168 | +0.0082 | -0.0010 | -0.0005 |
| Bidslab68 | -0.0013 | -0.0007 | -0.0021 | -0.0011 | +0.0007 | +0.0004 |

### Omit one validation participant

Each row reaggregates the original predictions after removing that participant. Passing requires all four C-versus-A and C-versus-B differences to be strictly negative.

| Omitted | Remaining people | Origins | Positive | Negative | C − A NLL | C − A Brier | C − B NLL | C − B Brier | B − A NLL | B − A Brier | Pass |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Bidslab32 | 6 | 719 | 332 | 387 | -0.0017 | -0.0008 | +0.0004 | +0.0002 | -0.0021 | -0.0010 | no |
| Bidslab35 | 6 | 788 | 337 | 451 | +0.0004 | +0.0002 | +0.0016 | +0.0008 | -0.0012 | -0.0006 | no |
| Bidslab42 | 6 | 800 | 344 | 456 | +0.0003 | +0.0002 | +0.0001 | +0.0001 | +0.0003 | +0.0001 | no |
| Bidslab45 | 6 | 762 | 331 | 431 | +0.0004 | +0.0002 | +0.0009 | +0.0004 | -0.0005 | -0.0002 | no |
| Bidslab49 | 6 | 836 | 369 | 467 | +0.0031 | +0.0015 | +0.0035 | +0.0017 | -0.0003 | -0.0002 | no |
| Bidslab50 | 6 | 769 | 343 | 426 | -0.0026 | -0.0013 | -0.0018 | -0.0009 | -0.0008 | -0.0004 | yes |
| Bidslab68 | 6 | 780 | 338 | 442 | +0.0003 | +0.0002 | +0.0013 | +0.0007 | -0.0011 | -0.0005 | no |

</details>

<details><summary>+30 minutes · participant scores, paired differences and sensitivity</summary>

The prespecified stability criterion **failed**. The comparison covered 876 origins from 7 participants, with 535 positives and 341 negatives. Each participant contributes equally. Lower NLL and Brier are better.

| Arm | NLL | Brier |
| --- | --- | --- |
| A | 0.6626 | 0.2349 |
| B | 0.6605 | 0.2339 |
| C | 0.6641 | 0.2354 |

| Validation cohort | C − A NLL | C − A Brier | C − B NLL | C − B Brier | B − A NLL | B − A Brier |
| --- | --- | --- | --- | --- | --- | --- |
| All eligible participants | +0.0016 | +0.0005 | +0.0036 | +0.0015 | -0.0021 | -0.0009 |

### Participant scores and paired differences

| Participant | Origins | Positive | Negative | A NLL | A Brier | B NLL | B Brier | C NLL | C Brier |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Bidslab32 | 184 | 98 | 86 | 0.6986 | 0.2524 | 0.7038 | 0.2547 | 0.7092 | 0.2575 |
| Bidslab35 | 118 | 82 | 36 | 0.6143 | 0.2116 | 0.6064 | 0.2083 | 0.5991 | 0.2052 |
| Bidslab42 | 106 | 82 | 24 | 0.5840 | 0.1969 | 0.5921 | 0.2007 | 0.6007 | 0.2051 |
| Bidslab45 | 144 | 80 | 64 | 0.6951 | 0.2506 | 0.6917 | 0.2490 | 0.7024 | 0.2538 |
| Bidslab49 | 70 | 42 | 28 | 0.6805 | 0.2434 | 0.6695 | 0.2384 | 0.6740 | 0.2410 |
| Bidslab50 | 131 | 64 | 67 | 0.7461 | 0.2751 | 0.7415 | 0.2729 | 0.7546 | 0.2764 |
| Bidslab68 | 123 | 87 | 36 | 0.6194 | 0.2140 | 0.6184 | 0.2134 | 0.6089 | 0.2087 |

| Participant | C − A NLL | C − A Brier | C − B NLL | C − B Brier | B − A NLL | B − A Brier |
| --- | --- | --- | --- | --- | --- | --- |
| Bidslab32 | +0.0106 | +0.0051 | +0.0053 | +0.0028 | +0.0053 | +0.0023 |
| Bidslab35 | -0.0152 | -0.0064 | -0.0073 | -0.0031 | -0.0079 | -0.0033 |
| Bidslab42 | +0.0167 | +0.0082 | +0.0085 | +0.0043 | +0.0081 | +0.0039 |
| Bidslab45 | +0.0073 | +0.0032 | +0.0106 | +0.0048 | -0.0034 | -0.0016 |
| Bidslab49 | -0.0065 | -0.0024 | +0.0045 | +0.0026 | -0.0110 | -0.0050 |
| Bidslab50 | +0.0085 | +0.0013 | +0.0131 | +0.0036 | -0.0046 | -0.0022 |
| Bidslab68 | -0.0104 | -0.0052 | -0.0095 | -0.0047 | -0.0010 | -0.0005 |

### Omit one validation participant

Each row reaggregates the original predictions after removing that participant. Passing requires all four C-versus-A and C-versus-B differences to be strictly negative.

| Omitted | Remaining people | Origins | Positive | Negative | C − A NLL | C − A Brier | C − B NLL | C − B Brier | B − A NLL | B − A Brier | Pass |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Bidslab32 | 6 | 692 | 437 | 255 | +0.0001 | -0.0002 | +0.0033 | +0.0013 | -0.0033 | -0.0015 | no |
| Bidslab35 | 6 | 758 | 453 | 305 | +0.0044 | +0.0017 | +0.0054 | +0.0022 | -0.0011 | -0.0005 | no |
| Bidslab42 | 6 | 770 | 453 | 317 | -0.0009 | -0.0007 | +0.0028 | +0.0010 | -0.0038 | -0.0017 | no |
| Bidslab45 | 6 | 732 | 455 | 277 | +0.0006 | +0.0001 | +0.0025 | +0.0009 | -0.0018 | -0.0008 | no |
| Bidslab49 | 6 | 806 | 493 | 313 | +0.0029 | +0.0010 | +0.0035 | +0.0013 | -0.0006 | -0.0003 | no |
| Bidslab50 | 6 | 745 | 471 | 274 | +0.0004 | +0.0004 | +0.0021 | +0.0011 | -0.0016 | -0.0007 | no |
| Bidslab68 | 6 | 753 | 448 | 305 | +0.0036 | +0.0015 | +0.0058 | +0.0025 | -0.0022 | -0.0010 | no |

</details>
