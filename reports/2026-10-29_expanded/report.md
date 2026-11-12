# 38-night expansion: audit failed, unscored

- Run/work ID: `expanded_seed40_12t7v2n`.
- Experiment date: 2026-10-29. Handoff reconstructed: 2026-11-12; not a rerun.
- Status: acquisition complete; audit failed; model fitting/scoring/analyze not reached.
- Scope: fixed first 12 train and all 7 validation participants, two catalog-ordered nights each, same seed-40 33/7/7 split; sealed test untouched.
- Hypothesis: duration gains, if any, should survive simple controls and short-event evaluation on broader fixed coverage.
- Frozen comparison: original seven methods plus zero Wake, participant-weighted training median and per-horizon constant probability. No validation sweep.

## Provenance and resources

- Protocol SHA256: `a9810ed6f6272bf775b2a81e0afc97bdd24ce0ed559f510c73502d2aa9fe3032`.
- Official catalog SHA256: `13333dff4d4640167435188bc6019c1782684b96d09838cb7e7b3ad005a51460`.
- Historical Git commit: unavailable; use source/protocol hashes and retained logs. Imported repository code is a snapshot, not a completed expanded run.
- Budget: 2CPU/8GB/2h, account `so589980.ucf`, QoS `so589980.ucf-b`, partition `hpg-milan`, no GPU; 8GB selected-file budget, 350MB per decompressed file.

## Observed sequence

1. Job `48205992`: 94 tests passed; acquisition failed because a 213,851,009-byte motion file exceeded the original 200MB limit. No fit.
2. Job `48206605`: ZIP-directory-only preflight found 114 selected data files / 38 nights, maximum 305,534,262 bytes. Only decompressed-file budget changed to 350MB; split, sample and scientific parameters did not change.
3. Job `48210060`: 95 tests passed, all selected acquisition checks completed. Logical total 4,876,305,786 bytes including metadata; no test payload; no retained partial in the expanded root.
4. Audit completed 12 training nights, then failed with `motion.csv: timestamps must be nondecreasing; no automatic sorting`.

Job `48210060` exited `1:0` after 1h19m57s on `c0709a-s14.ufhpc`; it was not a timeout. Acquisition finished at `2026-10-29T17:42:36.889908+00:00`.

From acquisition order and the last audited record, the next file to inspect is `Bidslab36/1/motion.csv`. The error prints only the basename; no raw row-level diagnosis has established the reversal location, magnitude, cause, chunk boundary or overlap with the label interval.

## What cannot be reported

No complete 38-night origin coverage, nonzero-Wake distribution, independent short-event inventory or model ranking exists. Download success and test success do not imply a completed experiment. Do not extrapolate the pilot numbers to this larger cohort.

## Next step

Use [the timestamp-audit proposal](../../specs/2026-11-12_timestamp_audit.md) to locate the failure. Preserve original raw files, failed audit receipt and partial caches; do not silently sort, omit records or select a different sample. Choose a documented handling protocol before resuming complete audit, then fitting and analysis.

## HPG artifacts

```text
/orange/so589980.ucf/zi700688.ucf/IoT_medical/g3_sleep_forecasting_20261029/
  iterations/expanded_20261029/RUN_REPORT.md
  iterations/expanded_20261029/EXPERIMENT_PLAN.md
  work/expanded_seed40_12t7v2n/manifests/acquisition.json
  work/expanded_seed40_12t7v2n/manifests/audit.json
  work/expanded_seed40_12t7v2n/manifests/archive_size_preflight.json
  work/expanded_seed40_12t7v2n/operations/job_48210060.log
```
