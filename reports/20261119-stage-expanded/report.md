# Fixed 38-night four-stage forecast on HPG

Run `20261119-stage-expanded` completed on November 19, 2026. All six methods used 969 shared origins on 14 validation nights from seven participants, with 1,936 origins on 24 training nights from 12 other participants. Seven test subjects remained sealed. The latest measured wrist input at the first transition failed all three prespecified conditions for advancement.

The full 38-night audit passed and all 33 strict-reference controls matched. Masking one ACC epoch in each of two nights preserved every previously eligible origin in those nights. The [audit and coverage](audit.md) give raw source lines, mask impacts, the fixed roster, policy identity and cache checksums. The [reproduction record](reproduction.md) describes tests, the environment, training settings, submission commands and HPG paths.

| Run identity | Value |
| --- | --- |
| Spec / base | `a5499473ca01e5980e96ca68e5bfc21f1ffdae06` |
| Executed code for the four experiment jobs | `43107763185e044dbc1ee570fef2ddd5fbb44306` |
| Timestamp policy SHA256 | `e8174563798d2d43df1cd314daae64311bd15b0da272134c5e2338c515d4cac3` |
| Expanded cache identity | `769709116695441b2bf65146058aa4c33b6908c02918c6b75ad5e02b2c1d8dd9` |
| HPG artifact root | `/home/zi700688.ucf/wearable-sleep-artifacts/20261119-stage-expanded/` |

| Phase | Slurm job | Wall time | Measured process timing |
| --- | --- | ---: | --- |
| Regression and six-night smoke | 51964672 | 59 s | 121 tests passed. Six-night audit took 8.20 s and seed 0 fit/scoring took 9.00 s. Published endpoint scores reproduced exactly. |
| Fixed 38-night audit/cache | 51964674 | 121 s | 119.99 s, peak 216.7 MiB |
| Explicit CPU epoch | 51964901 | 4 s | One epoch 0.876 s, peak 452.2 MiB |
| All fits and scoring | 51964908 | 150 s | 149.12 s, peak 464.3 MiB |
| Verify saved predictions and export 60 leads | 51965076 | 1 s | 1,080 probability-score rows verified against all three published endpoints |

All five jobs exited 0. The supplemental export used commit `335779ec5a3e6ea873ba916376334b5cf8c357ed` on the saved predictions without refitting. [60-lead NLL and Brier](lead-curve.csv) · [Scheduler accounting](slurm.psv) · [Aggregate metrics](aggregate.json) · [Seed 0](seed-0.json) · [Seed 1](seed-1.json) · [Seed 2](seed-2.json)

Learned persistence had the highest macro-F1 at each endpoint. Direct prediction had the lowest full-horizon NLL and Brier. Fusion exceeded HR-only by a mean 0.0215 in +30 min macro-F1, with two positive paired differences and one tie. Among these wrist rollouts the evidence favors retaining fusion for comparison. It also supports keeping persistence and direct prediction as references. The explicit model missed every Wake target at the three reported endpoints. The seven validation participants contributed overlapping windows, so the result describes this cohort and training configuration.

**Do not advance the explicit wrist input under the prespecified criteria.** The +30 min explicit − fusion macro-F1 difference averaged -0.0163 (range -0.0454 to +0.0000). 0/3 seeds favored explicit. Mean full-horizon NLL changed by +0.0077 (lower is better). Mean +30 min Wake recall changed by -0.0064 (higher is better).

## Primary comparison and sensitivity

| Seed | Explicit F1 | Fusion F1 | Explicit − fusion | Excluding masked histories |
| --- | --- | --- | --- | --- |
| 0 | 0.1615 | 0.1649 | -0.0034 | -0.0033 |
| 1 | 0.1561 | 0.2015 | -0.0454 | -0.0456 |
| 2 | 0.1564 | 0.1564 | +0.0000 | +0.0000 |

The sensitivity analysis used the original fitted predictions and excluded 3 origins with masked historical ACC. Of 966 remaining origins, 884 had known +30 min labels and 82 did not. The 7 evaluable participants contributed 48 Wake, 419 Light, 148 Deep, 269 REM labels. The resulting mean difference was -0.0163.

## Endpoint scores

Each participant's confusion matrix has unit mass before averaging over participants and computing F1. Losses are averaged within participant and then across participants. Method scores below average over seeds. NE indicates unavailable support.

| Lead (min) | Participants | Known origins | Unknown origins | Wake | Light | Deep | REM |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 5 | 7 | 942 | 27 | 54 | 431 | 186 | 271 |
| 15 | 7 | 920 | 49 | 51 | 424 | 173 | 272 |
| 30 | 7 | 887 | 82 | 48 | 421 | 149 | 269 |

| Method | Lead (min) | Macro-F1 | Wake recall | NLL | Brier | Wake F1 | Light F1 | Deep F1 | REM F1 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| stage_prior | 5 | 0.1528 | 0.0000 | 1.2229 | 0.6775 | 0.0000 | 0.6112 | 0.0000 | 0.0000 |
| stage_prior | 15 | 0.1534 | 0.0000 | 1.2142 | 0.6747 | 0.0000 | 0.6138 | 0.0000 | 0.0000 |
| stage_prior | 30 | 0.1564 | 0.0000 | 1.1963 | 0.6657 | 0.0000 | 0.6257 | 0.0000 | 0.0000 |
| persistence | 5 | 0.3541 | 0.1217 | 1.2033 | 0.6632 | 0.1743 | 0.5615 | 0.3818 | 0.2988 |
| persistence | 15 | 0.2807 | 0.0365 | 1.3461 | 0.7108 | 0.0512 | 0.5622 | 0.2588 | 0.2506 |
| persistence | 30 | 0.2352 | 0.0386 | 1.4533 | 0.7520 | 0.0533 | 0.5506 | 0.1206 | 0.2162 |
| direct | 5 | 0.2672 | 0.0358 | 1.1522 | 0.6487 | 0.0596 | 0.5846 | 0.3721 | 0.0526 |
| direct | 15 | 0.2144 | 0.0061 | 1.2034 | 0.6741 | 0.0115 | 0.6049 | 0.1600 | 0.0811 |
| direct | 30 | 0.1772 | 0.0000 | 1.2111 | 0.6811 | 0.0000 | 0.6087 | 0.0000 | 0.1002 |
| hr_only | 5 | 0.1528 | 0.0000 | 1.1835 | 0.6692 | 0.0000 | 0.6112 | 0.0000 | 0.0000 |
| hr_only | 15 | 0.1875 | 0.0061 | 1.1990 | 0.6737 | 0.0115 | 0.6079 | 0.1014 | 0.0291 |
| hr_only | 30 | 0.1528 | 0.0000 | 1.2715 | 0.7018 | 0.0000 | 0.4480 | 0.0000 | 0.1631 |
| fusion | 5 | 0.1858 | 0.0113 | 1.1613 | 0.6595 | 0.0217 | 0.6082 | 0.1135 | 0.0000 |
| fusion | 15 | 0.1980 | 0.0182 | 1.2037 | 0.6759 | 0.0337 | 0.6065 | 0.1272 | 0.0246 |
| fusion | 30 | 0.1743 | 0.0064 | 1.2527 | 0.6977 | 0.0121 | 0.5155 | 0.0082 | 0.1613 |
| explicit | 5 | 0.1526 | 0.0000 | 1.1746 | 0.6646 | 0.0000 | 0.6103 | 0.0000 | 0.0000 |
| explicit | 15 | 0.1830 | 0.0000 | 1.1962 | 0.6721 | 0.0000 | 0.6060 | 0.1182 | 0.0078 |
| explicit | 30 | 0.1580 | 0.0000 | 1.2828 | 0.7077 | 0.0000 | 0.4608 | 0.0074 | 0.1638 |

## Paired differences across seeds

| Arm − reference | F1 +5 | F1 +15 | F1 +30 | Full NLL | Full Brier |
| --- | --- | --- | --- | --- | --- |
| explicit − fusion | -0.0332 | -0.0150 | -0.0163 | +0.0077 | +0.0033 |
| explicit − direct | -0.1146 | -0.0314 | -0.0192 | +0.0154 | +0.0071 |
| fusion − hr_only | +0.0330 | +0.0105 | +0.0215 | -0.0090 | -0.0044 |
| fusion − direct | -0.0814 | -0.0164 | -0.0030 | +0.0078 | +0.0038 |
| stage_prior − persistence | -0.2013 | -0.1272 | -0.0787 | -0.1149 | -0.0302 |
| direct − persistence | -0.0869 | -0.0663 | -0.0579 | -0.1262 | -0.0322 |
| hr_only − persistence | -0.2013 | -0.0932 | -0.0824 | -0.1094 | -0.0240 |
| fusion − persistence | -0.1683 | -0.0827 | -0.0609 | -0.1184 | -0.0283 |
| explicit − persistence | -0.2015 | -0.0977 | -0.0772 | -0.1107 | -0.0250 |

Fusion − HR-only measures the contribution of wrist amplitude, count and availability together. Direct prediction uses a distinct readout and parameter count.

## Full-horizon and auxiliary scores

| Method | Parameters¹ | NLL | Brier | Wake minutes MAE | Wake minutes bias | Short Wake recall² | Short events | HR MAE (bpm) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| stage_prior | — | 1.2169 | 0.6755 | 2.7760 | 0.3489 | 0.0000 | 12 | — |
| persistence | — | 1.3317 | 0.7057 | 2.7546 | 0.2509 | 0.0000 | 12 | — |
| direct | 32780 | 1.2056 | 0.6735 | 2.5694 | -0.0017 | 0.0278 | 12 | 3.4803 |
| hr_only | 18709 | 1.2223 | 0.6817 | 2.8000 | 0.5370 | 0.0000 | 12 | 4.1422 |
| fusion | 18709 | 1.2133 | 0.6774 | 2.7845 | 0.4540 | 0.0000 | 12 | 3.9459 |
| explicit | 18709 | 1.2210 | 0.6807 | 2.7835 | 0.4283 | 0.0000 | 12 | 4.2381 |

¹ Neural trainable parameters. ² Reference events comprise 1–2 Wake epochs and are matched by absolute participant/night event boundaries. Recall counts each reference event once if any evaluable origin hits it.

The seed JSONs include the participant-normalized and pooled confusion matrices, each class F1, short-event duration strata, event-then-participant macro hit rates, Wake-minute controls, last-observed HR control, parameter counts and training times. The same validation participants appear in every seed, and neighboring forecast windows overlap. Differences describe this fixed validation cohort.
