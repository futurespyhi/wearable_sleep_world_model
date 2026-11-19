# Experiment evidence

| Run ID | Experiment date | Status | Report |
|---|---|---|---|
| `diagnostic_20261029T123226911439Z` | 2026-10-29 | Scored diagnostic, 6 nights | [Pilot](2026-10-29_pilot/report.md) |
| `expanded_seed40_12t7v2n` | 2026-10-29 | Acquisition complete / audit failed / unscored | [Expansion](2026-10-29_expanded/report.md) |
| `20261119-first-round` | 2026-11-19 | Four-stage six-night seed 0 scored. Fixed 38-night audit blocked expanded timing and fit. | [First round](20261119-first-round/report.md) |
| `20261119-stage-expanded` | 2026-11-19 | 38/38 passed. Six matched methods on seven validation participants, three seeds. Explicit wrist input did not meet advancement criteria. | [Expanded four-stage results](20261119-stage-expanded/report.md) |
| `20261119-stage-transition` | 2026-11-19 | Fixed 38-night controls scored. At +30 min the empirical transition did not outperform prior shrinkage overall or on changed stages. | [Transition controls](20261119-stage-transition/report.md) |
| `20261119-stage-oracle` | 2026-11-19 | Known cutoff stage improved overall +30 min NLL and worsened changed-stage NLL relative to the wearable transition. | [Oracle diagnostic](20261119-stage-oracle/report.md) |
| `20261119-recording-time` | 2026-11-19 | On changed +30 min endpoints, time-only NLL was lower than either the wearable or expert-current-stage time-specific transition. | [Recording-time controls](20261119-recording-time/report.md) |

The two October reports were reconstructed on 2026-11-12 from retained local artifacts. They are not new runs. Original historical code was not committed in Git; do not substitute the repository-import commit for the code revision used in October. Use the retained source hashes and run metadata.

Use [the report template](../templates/EXPERIMENT_REPORT.md) for new runs. Keep observations, interpretation and proposed actions distinct. Include aggregate machine-readable metrics where useful, the scoring denominators, failure phase, and exact HPG artifact location.
