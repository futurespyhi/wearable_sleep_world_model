# Locate the expanded motion timestamp failure

Status: **proposed; not launched**. Author: Codex, based on retained failure evidence. This is a data diagnosis, not a new model experiment or permission to change the frozen cohort.

## Goal and evidence

Determine where and why the expanded audit hits nondecreasing-timestamp failure. Start from the [failed-run report](../reports/2026-10-29_expanded/report.md). Acquisition order identifies `Bidslab36/1/motion.csv` as the first file to inspect; confirm this from receipts before processing.

## Execution contract

- Base commit: record the actual repository HEAD when this task is selected; historical experiment predates repository import.
- Run location: Slurm compute node. Suggested diagnostic budget: 2CPU, 4GB, 30min; stop and report if exceeded rather than silently extending.
- Read only the identified file and necessary recording metadata with bounded chunks; output counts and bounded examples, not a full CSV dump.
- Record first/all reversal counts, row indices, adjacent values, negative delta magnitudes, cross-chunk status, identical/conflicting duplicate counts, and relationship to the reference interval.
- Keep original bytes and row order intact. Write the diagnosis into a new artifact directory and a new aggregate report.
- Do not train, tune thresholds, replace participants, sort data in place or modify the original failed audit receipt.

## Completion and decision

Complete when an auditable report identifies the anomaly and its reference-time impact, with code/source identity, command, job, resource use and limitations. If the expected file is not responsible, follow the acquisition sequence using the logs and report that correction explicitly.

Propose handling options with their implications for input cutoff and missingness. Selecting a handling protocol is a separate research decision; continue any work already authorized by the user without adding an unnecessary approval step.
