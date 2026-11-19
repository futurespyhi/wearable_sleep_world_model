# Recording time as a control for four-stage sleep forecasts

On the 535 validation origins where the stage at +30 minutes differed from the stage at cutoff, the time-only prior had the lowest participant-balanced NLL among all seven methods (1.1445). Using the saved wearable current-stage distribution with the time-specific transition matrix scored 1.1504. Even the offline oracle, which used the true current stage to select a row of that same matrix, scored 1.1549. The oracle beat time-only for one of seven participants in this stratum. The wearable transition beat it for three of seven.

Across all 876 evaluable +30-minute origins, the oracle beat time-only by 0.0245 NLL. On the 341 same-stage origins it improved by 0.0440, while on changed origins it worsened by 0.0104. Each comparison averages the paired NLL differences across people in the relevant stratum. Conditioning the prior on elapsed recording time alone reduced overall NLL by 0.0837 versus the frozen global stage prior.

The long-horizon stage-change forecast did not pass the prespecified comparison on these seven validation participants. Improving the wearable estimate of the current stage alone has no demonstrated advantage for this endpoint. The shorter-lead **overall** advantage over time-only persisted at +5 and +15 minutes for the oracle (−0.2712 and −0.1119). For the wearable transition it persisted only at +5 minutes (−0.0297 at +5 and +0.0046 at +15). On **changed** endpoints neither forecast improved on time-only at either shorter lead. The windows overlap within nights.

The run reused the fixed 38-night cache, all 969 validation origins and the saved current-stage probabilities. It computed τ from the cutoff and that night's audited recording start. The four bins [0,2), [2,4), [4,6) and [6,∞) hours held 420/576/550/390 training origins and 224/296/278/171 validation origins before lead-specific masks. The fit used only the 1,936 origins from 12 training participants. Each bin and lead prior used known future stages. Each transition row used pairs with both stages known. Each distribution received 20 pseudo-observations in total, weighted by its matching frozen global prior or transition row. Seven test participants stayed sealed. [Prespecified comparison](../../specs/2026-11-19_recording_time_controls.md) · [Parent oracle report](../20261119-stage-oracle/report.md)

Slurm job `51967701` completed on `c0709a-s30` in 3 seconds with 2 CPUs and 8 GiB allocated. All six tests passed. The scoring process used 160.2 MiB peak RSS. The four frozen methods reproduced all 120 checked NLLs from the parent report exactly, including each person's +30-minute scores. The base commit was `2a5cf60b6400068340bc0d8cac3448c62786af6d`. The code and protocol ran at `d06f6c367c6a676ceb1123c4e6cd51314e7c5cdc`. The fitted arrays and full log are under `/home/zi700688.ucf/wearable-sleep-artifacts/20261119-recording-time/`. [Scores and paired differences](metrics.json) · [Execution and input identities](execution.json)

## Validation coverage

All seven forecasts use the same origins with known current and target stages. Same and changed describe the two endpoints. Class counts refer to the future label.

| Lead (min) | Stratum | People | Origins | Wake | Light | Deep | REM |
| --- | --- | --- | --- | --- | --- | --- | --- |
| +5 | overall | 7 | 936 | 53 | 430 | 184 | 269 |
| +5 | same | 7 | 697 | 32 | 325 | 145 | 195 |
| +5 | changed | 7 | 239 | 21 | 105 | 39 | 74 |
| +15 | overall | 7 | 909 | 48 | 422 | 170 | 269 |
| +15 | same | 7 | 510 | 27 | 247 | 94 | 142 |
| +15 | changed | 7 | 399 | 21 | 175 | 76 | 127 |
| +30 | overall | 7 | 876 | 45 | 419 | 145 | 267 |
| +30 | same | 7 | 341 | 25 | 192 | 54 | 70 |
| +30 | changed | 7 | 535 | 20 | 227 | 91 | 197 |

## Participant-balanced NLL

| Lead (min) | Stratum | stage_prior | prior_mix | transition | oracle | time_only | time_transition | time_oracle |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| +5 | overall | 1.2214 | 1.1413 | 1.1348 | 0.8661 | 1.1231 | 1.0934 | 0.8519 |
| +5 | same | 1.2093 | 1.0637 | 1.0584 | 0.2815 | 1.0794 | 1.0120 | 0.2759 |
| +5 | changed | 1.2480 | 1.3417 | 1.3309 | 2.4327 | 1.2357 | 1.3018 | 2.3869 |
| +15 | overall | 1.2107 | 1.1899 | 1.1914 | 1.0413 | 1.1123 | 1.1169 | 1.0004 |
| +15 | same | 1.1959 | 1.1002 | 1.1060 | 0.6352 | 1.0418 | 1.0163 | 0.6079 |
| +15 | changed | 1.2218 | 1.2924 | 1.2888 | 1.5444 | 1.1944 | 1.2338 | 1.4879 |
| +30 | overall | 1.1919 | 1.1911 | 1.1941 | 1.1435 | 1.1082 | 1.1160 | 1.0837 |
| +30 | same | 1.1634 | 1.1426 | 1.1444 | 1.0135 | 1.0317 | 1.0463 | 0.9877 |
| +30 | changed | 1.1958 | 1.2072 | 1.2149 | 1.2270 | 1.1445 | 1.1504 | 1.1549 |

Each difference below subtracts the time_only NLL. Negative values favor the named method.

| Lead (min) | Stratum | stage_prior | prior_mix | transition | oracle | time_transition | time_oracle |
| --- | --- | --- | --- | --- | --- | --- | --- |
| +5 | overall | +0.0982 | +0.0182 | +0.0117 | -0.2570 | -0.0297 | -0.2712 |
| +5 | same | +0.1299 | -0.0157 | -0.0210 | -0.7979 | -0.0674 | -0.8035 |
| +5 | changed | +0.0123 | +0.1060 | +0.0952 | +1.1969 | +0.0661 | +1.1512 |
| +15 | overall | +0.0985 | +0.0776 | +0.0792 | -0.0709 | +0.0046 | -0.1119 |
| +15 | same | +0.1542 | +0.0585 | +0.0642 | -0.4066 | -0.0255 | -0.4339 |
| +15 | changed | +0.0274 | +0.0980 | +0.0943 | +0.3500 | +0.0394 | +0.2935 |
| +30 | overall | +0.0837 | +0.0829 | +0.0859 | +0.0352 | +0.0078 | -0.0245 |
| +30 | same | +0.1316 | +0.1108 | +0.1127 | -0.0183 | +0.0145 | -0.0440 |
| +30 | changed | +0.0514 | +0.0627 | +0.0704 | +0.0825 | +0.0059 | +0.0104 |

The following paired differences subtract each previously frozen method from its recording-time counterpart. A negative value favors the recording-time method.

| Lead (min) | Stratum | time_only − stage_prior | time_transition − transition | time_oracle − oracle |
| --- | --- | --- | --- | --- |
| +5 | overall | -0.0982 | -0.0414 | -0.0142 |
| +5 | same | -0.1299 | -0.0464 | -0.0056 |
| +5 | changed | -0.0123 | -0.0291 | -0.0457 |
| +15 | overall | -0.0985 | -0.0746 | -0.0409 |
| +15 | same | -0.1542 | -0.0897 | -0.0272 |
| +15 | changed | -0.0274 | -0.0549 | -0.0565 |
| +30 | overall | -0.0837 | -0.0782 | -0.0598 |
| +30 | same | -0.1316 | -0.0981 | -0.0257 |
| +30 | changed | -0.0514 | -0.0644 | -0.0722 |

<details><summary>Per-participant paired NLL differences and origin counts for all leads</summary>

Each row gives the baseline NLL followed by method minus baseline NLL on the same origins. NE denotes empty support. The JSON also contains each person's method scores and matched frozen comparisons.

| Participant | Lead (min) | Stratum | Origins | time_only NLL | stage_prior | prior_mix | transition | oracle | time_transition | time_oracle |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Bidslab32 | +5 | overall | 194 | 0.8912 | +0.1821 | +0.0814 | +0.0801 | -0.3410 | +0.0372 | -0.3644 |
| Bidslab32 | +5 | same | 164 | 0.8664 | +0.1897 | +0.0612 | +0.0582 | -0.6002 | +0.0122 | -0.6163 |
| Bidslab32 | +5 | changed | 30 | 1.0266 | +0.1402 | +0.1918 | +0.1997 | +1.0757 | +0.1740 | +1.0123 |
| Bidslab32 | +15 | overall | 190 | 0.8758 | +0.1679 | +0.1134 | +0.1196 | -0.0072 | +0.0306 | -0.0663 |
| Bidslab32 | +15 | same | 123 | 0.8225 | +0.1978 | +0.0996 | +0.1085 | -0.2445 | +0.0095 | -0.3028 |
| Bidslab32 | +15 | changed | 67 | 0.9737 | +0.1129 | +0.1387 | +0.1399 | +0.4283 | +0.0692 | +0.3678 |
| Bidslab32 | +30 | overall | 184 | 0.8654 | +0.1408 | +0.1387 | +0.1490 | +0.1464 | +0.0397 | +0.0457 |
| Bidslab32 | +30 | same | 86 | 0.7559 | +0.1724 | +0.1544 | +0.1664 | +0.0969 | +0.0589 | +0.0180 |
| Bidslab32 | +30 | changed | 98 | 0.9614 | +0.1131 | +0.1249 | +0.1337 | +0.1898 | +0.0228 | +0.0701 |
| Bidslab35 | +5 | overall | 127 | 1.2224 | +0.0397 | -0.0883 | -0.0980 | +0.0161 | -0.1104 | +0.0437 |
| Bidslab35 | +5 | same | 77 | 1.1261 | +0.0960 | -0.1577 | -0.1664 | -0.8488 | -0.1915 | -0.8445 |
| Bidslab35 | +5 | changed | 50 | 1.3707 | -0.0470 | +0.0185 | +0.0073 | +1.3479 | +0.0144 | +1.4115 |
| Bidslab35 | +15 | overall | 121 | 1.2388 | +0.0089 | -0.0337 | -0.0406 | -0.0730 | -0.0437 | -0.0249 |
| Bidslab35 | +15 | same | 59 | 1.1111 | +0.0606 | -0.0937 | -0.0881 | -0.4682 | -0.0865 | -0.4290 |
| Bidslab35 | +15 | changed | 62 | 1.3604 | -0.0404 | +0.0233 | +0.0047 | +0.3031 | -0.0029 | +0.3596 |
| Bidslab35 | +30 | overall | 118 | 1.2470 | -0.0280 | -0.0249 | -0.0198 | -0.0188 | +0.0313 | +0.0227 |
| Bidslab35 | +30 | same | 36 | 1.1506 | -0.0102 | -0.0359 | -0.0282 | -0.0668 | +0.0521 | +0.0290 |
| Bidslab35 | +30 | changed | 82 | 1.2893 | -0.0359 | -0.0201 | -0.0161 | +0.0023 | +0.0221 | +0.0200 |
| Bidslab42 | +5 | overall | 111 | 1.3379 | -0.0796 | -0.1567 | -0.1672 | -0.2422 | -0.2148 | -0.2430 |
| Bidslab42 | +5 | same | 76 | 1.3344 | -0.0696 | -0.2522 | -0.2706 | -1.0597 | -0.3203 | -1.0402 |
| Bidslab42 | +5 | changed | 35 | 1.3455 | -0.1013 | +0.0507 | +0.0574 | +1.5332 | +0.0143 | +1.4881 |
| Bidslab42 | +15 | overall | 109 | 1.2994 | -0.0449 | -0.0621 | -0.0375 | -0.1942 | -0.0649 | -0.1901 |
| Bidslab42 | +15 | same | 54 | 1.2232 | +0.0187 | -0.1181 | -0.0894 | -0.5666 | -0.1541 | -0.5221 |
| Bidslab42 | +15 | changed | 55 | 1.3743 | -0.1074 | -0.0071 | +0.0136 | +0.1715 | +0.0227 | +0.1358 |
| Bidslab42 | +30 | overall | 106 | 1.2335 | +0.0196 | +0.0232 | +0.0431 | -0.0712 | -0.0139 | -0.1310 |
| Bidslab42 | +30 | same | 24 | 1.1489 | +0.0398 | +0.0072 | +0.0720 | -0.0656 | +0.0022 | -0.0036 |
| Bidslab42 | +30 | changed | 82 | 1.2583 | +0.0136 | +0.0278 | +0.0346 | -0.0728 | -0.0186 | -0.1683 |
| Bidslab45 | +5 | overall | 149 | 0.9892 | +0.0817 | +0.0247 | +0.0068 | -0.0481 | -0.0300 | -0.0529 |
| Bidslab45 | +5 | same | 107 | 0.9036 | +0.1311 | +0.0321 | +0.0156 | -0.6381 | -0.0334 | -0.6373 |
| Bidslab45 | +5 | changed | 42 | 1.2075 | -0.0440 | +0.0058 | -0.0156 | +1.4551 | -0.0214 | +1.4359 |
| Bidslab45 | +15 | overall | 147 | 0.9650 | +0.0870 | +0.0879 | +0.0801 | -0.0028 | +0.0080 | -0.0371 |
| Bidslab45 | +15 | same | 79 | 0.8424 | +0.1505 | +0.0986 | +0.0873 | -0.2690 | -0.0066 | -0.2999 |
| Bidslab45 | +15 | changed | 68 | 1.1074 | +0.0132 | +0.0754 | +0.0718 | +0.3065 | +0.0249 | +0.2682 |
| Bidslab45 | +30 | overall | 144 | 0.9420 | +0.0788 | +0.0775 | +0.0607 | +0.0574 | -0.0153 | -0.0004 |
| Bidslab45 | +30 | same | 64 | 0.8244 | +0.0846 | +0.0694 | +0.0329 | +0.0068 | -0.0247 | -0.0070 |
| Bidslab45 | +30 | changed | 80 | 1.0361 | +0.0742 | +0.0840 | +0.0830 | +0.0978 | -0.0077 | +0.0048 |
| Bidslab49 | +5 | overall | 75 | 1.0632 | +0.2411 | +0.1669 | +0.1551 | -0.2732 | +0.0557 | -0.3314 |
| Bidslab49 | +5 | same | 57 | 0.9860 | +0.2822 | +0.1215 | +0.1207 | -0.7143 | +0.0229 | -0.7394 |
| Bidslab49 | +5 | changed | 18 | 1.3077 | +0.1109 | +0.3106 | +0.2643 | +1.1239 | +0.1595 | +0.9606 |
| Bidslab49 | +15 | overall | 73 | 1.0444 | +0.2439 | +0.2364 | +0.2469 | +0.0259 | +0.0544 | -0.1053 |
| Bidslab49 | +15 | same | 43 | 0.9588 | +0.3149 | +0.2156 | +0.2297 | -0.3159 | +0.0200 | -0.4011 |
| Bidslab49 | +15 | changed | 30 | 1.1670 | +0.1422 | +0.2663 | +0.2715 | +0.5160 | +0.1036 | +0.3188 |
| Bidslab49 | +30 | overall | 70 | 1.0465 | +0.2325 | +0.2360 | +0.2453 | +0.1931 | -0.0121 | +0.0175 |
| Bidslab49 | +30 | same | 28 | 0.9294 | +0.3861 | +0.3753 | +0.3710 | +0.1770 | -0.0134 | +0.0126 |
| Bidslab49 | +30 | changed | 42 | 1.1246 | +0.1300 | +0.1431 | +0.1615 | +0.2038 | -0.0111 | +0.0208 |
| Bidslab50 | +5 | overall | 147 | 1.2810 | +0.1649 | -0.0307 | -0.0243 | -0.5683 | -0.0487 | -0.5943 |
| Bidslab50 | +5 | same | 117 | 1.3014 | +0.1940 | -0.0552 | -0.0453 | -0.9581 | -0.0697 | -0.9805 |
| Bidslab50 | +5 | changed | 30 | 1.2014 | +0.0513 | +0.0648 | +0.0580 | +0.9522 | +0.0331 | +0.9118 |
| Bidslab50 | +15 | overall | 140 | 1.2897 | +0.1592 | +0.0679 | +0.0731 | -0.2141 | +0.0030 | -0.2838 |
| Bidslab50 | +15 | same | 84 | 1.3295 | +0.2453 | +0.0815 | +0.0970 | -0.5992 | +0.0019 | -0.6936 |
| Bidslab50 | +15 | changed | 56 | 1.2299 | +0.0299 | +0.0474 | +0.0372 | +0.3635 | +0.0046 | +0.3310 |
| Bidslab50 | +30 | overall | 131 | 1.3374 | +0.1009 | +0.0739 | +0.0655 | -0.1104 | +0.0164 | -0.1495 |
| Bidslab50 | +30 | same | 67 | 1.4727 | +0.1542 | +0.1043 | +0.0750 | -0.3122 | +0.0001 | -0.3957 |
| Bidslab50 | +30 | changed | 64 | 1.1958 | +0.0450 | +0.0420 | +0.0555 | +0.1008 | +0.0335 | +0.1082 |
| Bidslab68 | +5 | overall | 133 | 1.0772 | +0.0578 | +0.1297 | +0.1290 | -0.3427 | +0.1029 | -0.3560 |
| Bidslab68 | +5 | same | 99 | 1.0382 | +0.0858 | +0.1400 | +0.1407 | -0.7663 | +0.1078 | -0.7662 |
| Bidslab68 | +5 | changed | 34 | 1.1907 | -0.0239 | +0.0995 | +0.0951 | +0.8905 | +0.0886 | +0.8384 |
| Bidslab68 | +15 | overall | 129 | 1.0727 | +0.0675 | +0.1334 | +0.1125 | -0.0312 | +0.0450 | -0.0757 |
| Bidslab68 | +15 | same | 68 | 1.0048 | +0.0913 | +0.1257 | +0.1044 | -0.3828 | +0.0372 | -0.3885 |
| Bidslab68 | +15 | changed | 61 | 1.1484 | +0.0410 | +0.1419 | +0.1217 | +0.3608 | +0.0537 | +0.2731 |
| Bidslab68 | +30 | overall | 123 | 1.0858 | +0.0414 | +0.0558 | +0.0577 | +0.0502 | +0.0082 | +0.0233 |
| Bidslab68 | +30 | same | 36 | 0.9404 | +0.0946 | +0.1011 | +0.0996 | +0.0360 | +0.0265 | +0.0387 |
| Bidslab68 | +30 | changed | 87 | 1.1460 | +0.0194 | +0.0371 | +0.0404 | +0.0561 | +0.0006 | +0.0170 |

</details>
