# Current status

- Context verified: **2026-11-12**.
- Latest completed predictive experiment: **2026-10-29 pilot**, run `diagnostic_20261029T123226911439Z`.
- Current stage: research-question refinement and data/measurement diagnosis.
- GitHub connection: local bootstrap only; remote URL and account authorization remain to be established.

## Research state

G3 asks whether duration priors improve next-30-minute reference Wake burden from the same past 30 minutes of wrist HR/ACC, without increasing short-Wake misses. Novelty and useful mechanism gains have not been established. The post-meeting priority recorded in the session summary is close reading and narrowing the research question; the original meeting-feedback document was not independently retrieved in this bootstrap.

## Evidence

| Run | Status | What is established |
|---|---|---|
| [Six-night pilot](reports/2026-10-29_pilot/report.md) | Scored diagnostic | 4 train / 2 validation people, one night each. Hard MAE 1.534 min versus unconstrained 2.541, but zero Wake 0.828. Only one independent short reference event was evaluable. |
| [38-night expansion](reports/2026-10-29_expanded/report.md) | Acquisition complete; audit failed; not trained/scored | 12 train / 7 validation people, two nights each. Timestamp ordering guard failed after 12 training nights. No expanded method ranking exists. |

No sealed-test payload has been used by these diagnostics. No G3 GPU, vLLM or LLM-weight workload is part of the recorded experiments.

## Next work

1. Clarify the use case, output (expectation/median/risk/distribution), nearest work and joint success criterion.
2. If continuing the data diagnosis, use the [timestamp-audit proposal](specs/2026-11-12_timestamp_audit.md) to localize the first failure, before choosing any handling rule.
3. Only after complete audit, run the frozen comparison and report coverage plus burden/probability/event metrics together.

There is no scheduled experiment or autonomous web-AI review loop configured by this bootstrap. Connecting an app does not itself create a trigger.

## Context corrections

The old session summary contains a reversed “allowed conclusions” sentence and incorrect dependency constraints. The supported conclusion is that the small pilot does **not establish** duration benefits or short-event preservation; it also does not establish that wrist data contain no information. Actual requirements are NumPy >=1.25,<2; SciPy >=1.11,<2; pandas >=2.1,<2.2. See [environment](docs/ENVIRONMENT.md).

The old Overleaf repository in `IoT_medical/paper/` is a February AD manuscript, not the current sleep project. Existing Orange code/data/results remain the historical evidence source; copied code provenance is in [SOURCE_IMPORT.json](docs/SOURCE_IMPORT.json).
