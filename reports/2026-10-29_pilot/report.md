# Six-night pilot: scored diagnostic

- Run ID: `diagnostic_20261029T123226911439Z`.
- Experiment date: 2026-10-29. Handoff report reconstructed: 2026-11-12; not a rerun.
- Status: acquisition complete, audit complete, trained and scored; supplementary zero-Wake/event diagnosis complete.
- Question: does duration decoding improve future reference Wake burden without sacrificing short Wake events?
- Evidence class: diagnostic only; no novelty, clinical, generalization or intervention claim.

## Protocol and provenance

4 training and 2 validation participants, one night each; fixed seed-40 33/7/7 release-roster split, sealed test not downloaded/accessed. Wrist HR/ACC history 30min, future 30min, epochs 30s, stride 5min. Frozen alpha=10, dwell=2 epochs, soft penalty=1, threshold=.5; no validation parameter search.

- Protocol SHA256: `2b0906aeaf83b6ed44e7d0d41d30ad4ebcbd817beaede58bb84a8f3dd5f61336`.
- Official catalog SHA256: `13333dff4d4640167435188bc6019c1782684b96d09838cb7e7b3ad005a51460`.
- Historical source Git commit: unavailable. Retained run metadata records source hashes; the imported code snapshot is not a new experiment.
- Main job `48184562`: 2CPU/8GB, `c0709a-s1.ufhpc`, completed in 12m13s; 63 tests recorded passing.
- Supplement job `48190453`: 2CPU/4GB, 13s, two supplementary tests; no refit.
- Runtime metadata: Python 3.11.4, NumPy 1.25.2, CPU.

## Coverage and metrics

| Coverage | Train | Validation |
|---|---:|---:|
| People / nights | 4 / 4 | 2 / 2 |
| Candidate origins | 330 | 161 |
| Retained origins | 312 | 161 |
| Complete reference horizons | 287 | 121 |
| Known target epoch instances | 18108 | 8610 |
| Unknown/out-of-record target epoch instances | 612 | 1050 |

MAE and bias use complete horizons and are participant-macro; probability scores use valid target epochs and have a different denominator. Units for MAE/bias are minutes, bias=prediction-reference. CSV values below are rounded from the retained report, not full-precision raw metrics.

| Method | MAE | Bias | Brier | NLL |
|---|---:|---:|---:|---:|
| Population mean | 1.890 | +0.865 | — | — |
| Learned-current persistence | 5.662 | +5.365 | .1230 | 1.0915 |
| Transition matrix | 3.281 | +2.846 | .0677 | .2625 |
| Direct outcome | 1.983 | +1.631 | — | — |
| Direct trajectory | 2.541 | +2.370 | .0708 | .6324 |
| Same trajectory + soft | 1.869 | +1.476 | .0681 | .6279 |
| Same trajectory + hard | 1.534 | +.967 | .0684 | .6572 |
| Supplemental zero Wake | .828 | -.828 | .0683 | 1.8875 |

[Aggregate CSV](metrics.csv). The zero-Wake comparator was added after observing sparse outcomes; it was not part of model selection and original results were not overwritten.

96/121 complete validation windows contain zero Wake. Five short-event window instances correspond to one independent reference event from one person. None/soft/hard match 0/5; complete predicted-event counts are 13/9/9 with zero matches. Overlapping windows are not independent observations.

## Interpretation and next decision

Hard decoding lowers MAE relative to the same unconstrained trajectory but does not beat zero Wake. This can be consistent with reducing excessive Wake probability. It does not establish a useful duration mechanism or short-event preservation. Zero Wake has poor NLL, so MAE does not establish universal superiority. Summed probability predicts an expectation whereas MAE targets a median; neither outcome proves the sensors contain no information.

Clarify the estimand/use case and joint success criterion. The subsequent expansion addresses coverage and adds train-only median/constant-probability controls, but its audit failed before scoring.

## HPG artifacts

```text
/orange/so589980.ucf/zi700688.ucf/IoT_medical/g3_sleep_forecasting_20261029/
  RUN_REPORT.md
  work/pilot_seed40/manifests/
  work/pilot_seed40/results/diagnostic_20261029T123226911439Z/
    metrics.json
    fit_report.json
    run_metadata.json
    supplement_20261029T130928646586Z/
      zero_wake_metrics.json
      reference_summary.json
      metadata.json
```
