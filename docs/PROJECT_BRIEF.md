# Research brief

## Objective

Develop a useful, evidence-grounded wearable sleep forecasting study. Start with a falsifiable task and strong same-information baselines; decide on world-model architecture only after demonstrating what state/duration modeling must add.

Current candidate G3: at 02:00, use only 01:30–02:00 wrist HR/ACC to predict reference Wake minutes during 02:00–02:30, and evaluate whether duration priors trade burden accuracy for missing true short Wake runs. The candidate preceded the pilot; the pilot exposed measurement and baseline requirements.

## Frozen diagnostic definition

- BIDSleep 1.0.1; Apple Watch HR/ACC, Dreem 2 expert-reviewed reference, not full PSG.
- 30-second epochs, 60-epoch history, 60-epoch horizon, 10-epoch origin stride.
- At least 80% of historical epochs contain both HR and ACC samples; future labels/availability do not select origins.
- Seed 40 participant split: 33 train / 7 validation / 7 sealed test. Pilot selected 4/2 people and one night; expansion selected 12/7 and two nights.
- Unknown reference stays -1. Current reference state is not a validation input. Preprocessing fits training data only.
- Same direct-trajectory predictor with none/soft/hard decoding; ridge alpha 10, minimum dwell 2 epochs, soft penalty 1, threshold 0.5.
- Primary metric: participant-macro complete-horizon Wake-minute MAE. Report bias, Brier/NLL, false Wake and independent short-event coverage/recall alongside it.

## Unresolved decisions

- What practical use case needs a next-30-minute Wake forecast?
- Is the desired output a conditional expectation, median, threshold risk or full distribution? Summed marginal probabilities estimate an expectation; MAE targets the median.
- What improvement and event/participant coverage constitute sufficient evidence?
- Does duration modeling help beyond direct prediction and constant/shrinkage controls?
- Can the nearest work already answer the same task? Thirty-minute forecasting and raw/soft/hard comparisons are not standalone novelty claims.

## Alternatives and data routes

G1 (multi-night adaptation) remains an alternative; G2 (deployable origin timing) primarily audits G1. PMData and TILES are candidates for longer histories, with device-label and access limitations. DREAMT 2.2.0 is a candidate for G3 clinical-reference evaluation; access/DUA and alignment/valid-label intervals are unverified. No suitable action assignment/delivery/execution logs have been established for an intervention branch.

## Evidence boundaries

The current implementation is ridge/Markov/duration decoding, not a validated neural latent world model or a NormWear-2 reproduction. The pilot does not establish generalization, novelty, clinical usefulness or intervention effects. Zero Wake winning MAE does not prove the sensors contain no information; a better NLL than deterministic zero does not prove information gain without a nonzero constant comparison.

Read [current reports](../reports/README.md), then [research synthesis](research/2026-10-29_research_gap_to_data_synthesis.md) and [nearest-work update](research/NEAREST_WORK_UPDATE.md). Historical plans describe their own timepoint and do not override later run status.
