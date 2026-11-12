# Research decisions

Record evidence, alternatives and consequences. A proposal is not automatically selected because an AI wrote it; explicit user direction can select work without an extra approval round.

| Date | Status | Decision / question | Basis |
|---|---|---|---|
| 2026-10-29 | Historical diagnostic protocol | Fixed BIDSleep split and past-only 30min→30min task; sealed test untouched | Imported protocols; pilot/expanded reports |
| 2026-10-29 | Historical scope | Use lightweight baselines and duration decoding to test task/measurement feasibility | No demonstrated need for a neural latent model |
| 2026-10-29 | Open research question | Expectation vs median vs risk; practical use of Wake burden; minimum joint evidence | Sparse pilot outcomes and insufficient independent events |
| 2026-11-12 | Implemented local preparation | Prepare a focused code/evidence repository for the user's requested GitHub collaboration | User requests GitHub-mediated web AI ↔ HPG Codex workflow |
| 2026-11-12 | User-selected destination; Git remote configured | Use [futurespyhi/wearable_sleep_world_model](https://github.com/futurespyhi/wearable_sleep_world_model), `origin` over SSH, integration branch `main` | User supplied repository URL; initial remote had no commits; existing HPG SSH identity can access it |
| 2026-11-12 | Pending application setup | ChatGPT/Claude repository authorization and Canva/Overleaf connections | Git transport does not configure or verify web application permissions |
| 2026-11-12 | Proposed, not launched | Locate the expanded timestamp-order failure before selecting a repair rule | [Timestamp audit spec](../specs/2026-11-12_timestamp_audit.md) |

For a new decision record: date, status, originating issue/spec, base commit, referenced run IDs, chosen option, rejected alternatives and consequences for the frozen protocol.
