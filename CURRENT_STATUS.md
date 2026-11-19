# Current status

In the binary endpoint-change diagnostic, recent HR and wrist RMS levels and changes did not improve the forecast over recording time and the current-stage probabilities at +5, +15 or +30 minutes. At +30 minutes, adding those summaries raised NLL by 0.00363 and Brier by 0.00147, with both differences above zero after each validation-participant omission. The proposed four-stage integration criterion was not met. [Endpoint-change scores and participant sensitivity](reports/20261119-endpoint-change/report.md)

On the 535 validation origins with different stages at cutoff and +30 min, the recording-time prior scored 1.1445 NLL, the time-specific transition using the wearable estimate scored 1.1504, and the same matrix using the expert cutoff stage scored 1.1549. The oracle did improve overall NLL (1.0837 vs 1.1082), with the benefit concentrated on matching endpoints. The +30 min change comparison did not pass. [Recording-time report and paired differences](reports/20261119-recording-time/report.md)

The current-stage oracle diagnostic is complete. With the same trained transition matrices and both endpoint labels known at +30 min, using the expert cutoff stage reduced NLL by 0.0507 on average across seven validation participants. The mean difference (oracle minus wearable transition) was −0.1309 on 341 same-stage origins and +0.0122 on 535 changed-stage origins. [Oracle report and participant-paired results](reports/20261119-stage-oracle/report.md)

The preceding CPU comparison reused the 969 fixed validation origins and saved current-stage probabilities. At +30 min, transition NLL was 1.1989, prior mixture 1.1955 and stage prior 1.1963. Among 535 changed-stage origins, transition scored 1.2149 versus 1.2072 for the mixture. The transition control did not meet the primary criterion. [Transition control report](reports/20261119-stage-transition/report.md)

The [fixed 38-night four-stage comparison](reports/20261119-stage-expanded/report.md) is complete. The primary comparison does not support moving the latest observed wrist motion to the first rollout transition. At +30 min, explicit minus fusion macro-F1 was −0.0034, −0.0454 and 0.0000 for seeds 0, 1 and 2 (mean −0.0163). Explicit also had higher mean full-horizon NLL and lower mean +30 min Wake recall. Removing the three validation histories touched by the ACC mask left the conclusion unchanged.

The [timestamp audit](reports/20261119-stage-expanded/audit.md) passed 38/38 nights. All 33 previously accepted nights reproduced their strict features and origins exactly. Fixed coverage comprises 1,936 training origins (12 people) and 969 validation origins (7 people). The seven test participants remained sealed.

Learned persistence had the highest macro-F1 at +5/+15/+30 minutes. Direct prediction had the lowest full-horizon NLL and Brier. These are validation results from three seeds and overlapping forecast windows. [All method scores](reports/20261119-stage-expanded/aggregate.json) · [Per-lead probability scores](reports/20261119-stage-expanded/lead-curve.csv)

The [first round](reports/20261119-first-round/report.md) provides the original strict audit and six-night regression reference. Earlier binary G3 results are in the [report index](reports/README.md).
