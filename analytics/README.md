# Person 1: notebook and batch workflow

Develop on `analytics2`. This implementation uses the empty analytics scaffold
from `main` and does not depend on the `analytics` branch.

## Open the notebook

From the repository root:

```bash
.venv/bin/python -m pip install -r analytics/requirements.txt
.venv/bin/python -m ipykernel install --prefix .venv --name cutscope-analytics --display-name 'CutScope analytics'
.venv/bin/python -m jupyterlab analytics/notebooks/01_data_audit.ipynb
```

Choose **CutScope analytics**, then run cells from top to bottom. The kernel and
dependencies are already installed in this checkout's `.venv`.

Default input is `~/Desktop/hackathon-2026-official/track-2/data`. To use another
location, set `CUTSCOPE_DATA_DIR` before opening Jupyter, or change `DATA_DIR` in
the setup cell. The official repository, `track-2`, and `data` folders are all
accepted. Inputs are read in place; they are not copied or changed.

Notebook sections cover source verification, field schemas and missingness,
measured versus allocated hours, outcomes, workload mix, weighted utilization,
candidate overlap, idle-rule reproduction, individual job evidence, and node
failure history. The calculation functions are imported from `analytics/`;
the notebook does not maintain a second financial calculation pipeline.

The tracked notebook is an output-free source template. Clear outputs before
committing, or save executed copies under ignored `generated/` or
`analytics/notebooks/local/`. Official data and derived outputs stay local.

## Generate the first backend snapshot

```bash
.venv/bin/python -m analytics.build_analysis
.venv/bin/python -m backend.validate_analysis generated/analysis.json --check-api
```

Optional arguments:

```bash
.venv/bin/python -m analytics.build_analysis --data-dir ~/Desktop/hackathon-2026-official --price 2.50 --price-book-version cutscope-assumption-v1
```

This first stage exports the existing `summary`, `opportunities`, `jobs`, and
`metadata` envelope. `opportunities` and `jobs` are deliberately empty: no
recoverability, risk pricing, or interval attribution has been established yet.
Metadata contains provenance, quality diagnostics, and overlapping candidate
cohort consumption. Backend APIs do not expose this producer metadata.

The default $2.50/GPU-hour is an explicit scenario assumption, not an official
cloud price, verified bill, or cash-savings claim. All headline calculations
use measured DCGM `gpu_hours`. The final-walltime allocation estimate remains
a comparison with a separately labeled known subtotal and missing count.

## Verification

```bash
.venv/bin/python -m pytest analytics/tests/test_baseline.py -q
.venv/bin/python ~/Desktop/hackathon-2026-official/track-2/scripts/checksum_data.py
```

The loader independently checks the three consumed files using the official
hash algorithm. If the manifest is absent, verification is marked unknown;
a present mismatching hash stops loading. The official command checks all five
files, including resource and edge tables that this baseline does not consume.

## Next milestone

Use the notebook to inspect idle candidates and duration anomalies. Document
an intervention policy and evidence limitations, implement low/point/high
reclaim and cost-if-wrong, and test primary attribution before exporting a real
`idle-interactive` opportunity. Other opportunity modules remain unimplemented.
Keep the shared API unchanged; review any required field change with Persons
2 and 5.
