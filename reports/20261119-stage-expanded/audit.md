# Timestamp and cache audit of the fixed 38 nights

All 24 training nights (12 people) and 14 validation nights (7 people) passed. The audit checked both complete sensor CSVs per night in original row order, including across read chunks. All 114 source files (HR, ACC and expert labels) matched the acquisition receipt. The five registered events accounted for all detected timestamp anomalies. All seven test participants remained sealed. [Per-night audit and source checksums](audit_summary.json)

| Split | Candidate origins | Rejected by history coverage | Retained | Complete 60-stage targets | Valid target epochs | Unknown inside recording | Beyond recording |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Training | 2,042 | 106 | 1,936 | 1,792 | 111,786 | 831 | 3,543 |
| Validation | 1,119 | 150 | 969 | 856 | 55,176 | 978 | 1,986 |

Each origin required at least 48 of 60 historical epochs with both HR and ACC. Future labels did not gate origin inclusion. Target epoch counts above include all 60 leads and count observations in overlapping horizons more than once.

| Split | Source file | Physical lines (1-based) | Observed event | Treatment |
| --- | --- | --- | --- | --- |
| Train | `Bidslab36/1/motion.csv` | 54622–54623 | −0.183314 s within epoch 32 | Masked 1,507 valid ACC samples from that epoch |
| Validation | `Bidslab35/1/motion.csv` | 36713–36714 | −0.162618 s within epoch 25 | Masked 1,508 valid ACC samples from that epoch |
| Train | `Bidslab44/1/hr.csv` | 6681–6682 | Conflicting measurements at one timestamp after the annotation interval | Both rows outside the feature interval |
| Validation | `Bidslab68/1/hr.csv` | 5047–5048 | Conflicting measurements at one timestamp after the annotation interval | Both rows outside the feature interval |
| Validation | `Bidslab49/2/motion.csv` | 2466112–2466113 | −0.2552967 s after the annotation interval | Both rows outside the feature interval |

Feature aggregation used `recStart ≤ timestamp < recStart + 30 × number_of_epochs`. In each of the two masked epochs, the ACC mean, standard deviation and adjacent-difference RMS were missing and the ACC count was zero before checking coverage or fitting the scaler. HR and stage labels were retained. For Bidslab36, all four affected origins (epoch boundaries 60, 70, 80 and 90) went from 60 covered epochs to 59. For Bidslab35, origin 60 went from 57 to 56, and origins 70 and 80 went from 60 to 59. All seven affected origins remained eligible. The validation sensitivity analysis therefore excludes exactly three of 969 origins. Epoch indices are zero-based. [Timestamp policy](../../experiments/stage_forecast/expanded_timestamp_policy.json)

For the 33 nights that had already passed (22 training and 11 validation), strict G3 reaggregation reproduced every epoch time, stage label and all seven sensor features exactly, including missing values. Every window array, including cutoff times, target masks and histories, also matched the checksum-verified first-round cache exactly. [First-round provenance](../20261119-first-round/provenance.json)

| Audit identity | Value |
| --- | --- |
| Spec commit | `a5499473ca01e5980e96ca68e5bfc21f1ffdae06` |
| Code commit | `43107763185e044dbc1ee570fef2ddd5fbb44306` |
| Protocol SHA256 | `a9810ed6f6272bf775b2a81e0afc97bdd24ce0ed559f510c73502d2aa9fe3032` |
| Timestamp policy SHA256 | `e8174563798d2d43df1cd314daae64311bd15b0da272134c5e2338c515d4cac3` |
| Acquisition manifest SHA256 | `0eee6117f4f51aab91b46bba98341e8ae975218cfec01d638378a98c7a47c343` |
| BIDSleep release catalog SHA256 | `13333dff4d4640167435188bc6019c1782684b96d09838cb7e7b3ad005a51460` |
| Prior strict audit SHA256 | `eb0256279c0e1762764c9a5922e3c369ae01ad86c9714931a441ef793d929e8f` |
| Expanded audit.json SHA256 | `99ab09c041feb8c0ca2edb58317324e367cc7786ebfb720c5373cd384c304a3c` |
| Cache identity SHA256 (ordered cache hashes, policy, protocol, manifest and schema) | `769709116695441b2bf65146058aa4c33b6908c02918c6b75ad5e02b2c1d8dd9` |

Slurm job `51964674` ran on `c0709a-s30.ufhpc` with 2 CPUs and 8 GiB allocated. The audit took 120.0 s and the process peaked at 216.7 MiB RSS. On HPG, the full `audit.json`, `audit_execution.json` and 38 cached window files are under `/home/zi700688.ucf/wearable-sleep-artifacts/20261119-stage-expanded/expanded-cache/`. The verified acquisition is under `/orange/so589980.ucf/zi700688.ucf/IoT_medical/g3_sleep_forecasting_20261029/work/expanded_seed40_12t7v2n/`.
