# Project collaboration instructions

Read `CURRENT_STATUS.md`, `docs/PROJECT_BRIEF.md`, `docs/DECISIONS.md`, and the relevant task and report before implementation. User instructions and already granted authorization take precedence over this workflow.

- This repository coordinates research and implementation. The current G3 results are diagnostic; do not invent novelty, clinical utility, intervention effects, or completed experiments.
- `specs/` and issues must distinguish proposals from selected tasks. Execute the user's assigned/authorized work; an unselected idea in a document is not an instruction to launch experiments.
- Use a focused branch for a research or implementation task. Record the base commit and task link. Check for concurrent changes before integrating; preserve user edits.
- All data downloads, bulk hashing, aggregation, model execution, tests and browser jobs on HPG run in Slurm compute allocations. The login node is for lightweight inspection, source edits and Git operations.
- Use `scripts/run_g3.sh` to run this checkout. Select `experiments/g3/expanded_protocol.json` explicitly for the expanded 12/7/2 configuration; its adjacent `protocol.json` is the original pilot protocol.
- Keep source data and historical runs intact. New experiments use distinct artifact directories. Do not silently sort anomalous timestamps, skip records, resample on future labels, tune on sealed test data, or change metrics after inspecting outcomes.
- Store raw data, individual predictions, caches, weights, full logs and dependency environments outside Git. Publish aggregate evidence and reproducibility metadata in `reports/`, with paths to HPG artifacts.
- Record failures and partial completion explicitly: fetch complete is not audit complete; audit complete is not scored. Each report identifies code commit or historical source hashes, protocol, split, environment, job, coverage and limitations.
- After implementation or an experiment, update the relevant report and `CURRENT_STATUS.md`. Separate observed results, interpretations and proposed next steps. Link reviewed claims to the run that supports them.
- Web AI review should cite the branch/commit and run_id it read. Put alternative ideas in separate proposals; reconcile them through `docs/DECISIONS.md` rather than overwriting experimental facts.
- Canva presentations and Overleaf manuscripts derive numerical claims from reports. Preserve code-generated scientific figures and their source data. App authentication and remote URLs are not stored with credentials in repository files.
