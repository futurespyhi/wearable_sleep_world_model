# Current status

The [fixed 38-night four-stage comparison](reports/20261119-stage-expanded/report.md) is complete. The primary comparison does not support moving the latest observed wrist motion to the first rollout transition. At +30 min, explicit minus fusion macro-F1 was −0.0034, −0.0454 and 0.0000 for seeds 0, 1 and 2 (mean −0.0163). Explicit also had higher mean full-horizon NLL and lower mean +30 min Wake recall. Removing the three validation histories touched by the ACC mask left the conclusion unchanged.

The [timestamp audit](reports/20261119-stage-expanded/audit.md) passed 38/38 nights. All 33 previously accepted nights reproduced their strict features and origins exactly. Fixed coverage comprises 1,936 training origins (12 people) and 969 validation origins (7 people). The seven test participants remained sealed.

Learned persistence had the highest macro-F1 at +5/+15/+30 minutes. Direct prediction had the lowest full-horizon NLL and Brier. These are validation results from three seeds and overlapping forecast windows. [All method scores](reports/20261119-stage-expanded/aggregate.json) · [Per-lead probability scores](reports/20261119-stage-expanded/lead-curve.csv)

The [first round](reports/20261119-first-round/report.md) provides the original strict audit and six-night regression reference. Earlier binary G3 results are in the [report index](reports/README.md).
