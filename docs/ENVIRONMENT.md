# HPG environment and artifact locations

Verified 2026-11-12 from lightweight inspection and retained experiment metadata; no experiment was rerun during repository bootstrap.

## Compute

Control host: `login9.ufhpc`; Bash; Slurm account `so589980.ucf`, partition `hpg-milan`, CPU burst QoS `so589980.ucf-b`. Recorded main diagnostic allocations use 2 CPU / 8 GB; expansion budget is 2 hours. Supplement jobs used 2 CPU / 4 GB. These are allocated resources, not physical-node specifications. G3 used no GPU.

Downloads, bulk checksums, preprocessing, tests, training, scoring and browser jobs belong on compute nodes. `scripts/run_g3.sh` checks allocation and hostname and uses the code in this checkout.

## Python

Default HPG interpreter: `/apps/python/3.11/bin/python`. Pilot metadata records Python 3.11.4 and NumPy 1.25.2. Current shared SciPy installation metadata is 1.11.3; project pandas metadata is 2.1.4. Historical run metadata did not lock all installed packages.

The original runtime uses shared Python plus isolated pandas under the canonical project's `deps/`; it does not activate Conda. No dedicated G3 Conda environment or complete lockfile has been established. The account's other Conda environments are unrelated evidence.

Actual requirement ranges: NumPy >=1.25,<2; SciPy >=1.11,<2; pandas >=2.1,<2.2. For this checkout, set `G3_DEPS_ROOT` to the existing isolated dependencies when reusing the HPG runtime:

```bash
export G3_PYTHON=/apps/python/3.11/bin/python
export G3_DEPS_ROOT=/orange/so589980.ucf/zi700688.ucf/IoT_medical/g3_sleep_forecasting_20261029/deps
```

`G3_PYTHON` may be changed for a separately prepared environment. Set it explicitly and record the actual versions in new run reports. The launcher sets OpenBLAS/OMP/MKL thread counts to 1. Default shell `python3` is not assumed to match the experiment interpreter.

## External artifacts

Canonical historical root:

```text
/orange/so589980.ucf/zi700688.ucf/IoT_medical/g3_sleep_forecasting_20261029/
  work/pilot_seed40/
  work/expanded_seed40_12t7v2n/
```

Blue's same-named directory is a symbolic link. Some expanded raw files also link to verified pilot files. Do not overwrite these historical results with new checkout runs.

Logical verified file totals: pilot 754,799,848 bytes plus a retained, excluded 75,497,472-byte partial; expansion 4,876,305,786 bytes including metadata, with no retained partial in its new root. These are not physical disk usage, network traffic or quota balances. Check allocation/quota before a new substantial run.

Use a new external work directory for each subsequent protocol/run revision. `G3_WORK_ROOT` in examples is a user-selected artifact path, not a repository default and not automatically created by the launcher.

## Historical browser delivery

Node 20.20.0 and Playwright were used with containerized Chrome. The saved 10/29 14:55 browser report predates the 17:48 slides revision; their HTML hashes differ. It is not evidence that the latest HTML was verified. Preserve prior reports before another browser run.
