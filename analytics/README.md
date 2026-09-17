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

## Investigate the idle opportunity

```bash
.venv/bin/python -m jupyterlab analytics/notebooks/02_idle_interactive.ipynb
```

This notebook inspects representative sessions, exclusions, primary ownership,
low/point/high modeled reclaim, policy sensitivity, and hypothetical replay
cost. Both notebooks remain output-free source templates.

## Generate the backend snapshot

GPU-not-needed exploration is in `analytics/notebooks/03_gpu_not_needed.ipynb`.
It reproduces the completed zero-compute rule, examines GPU-memory evidence,
excludes jobs already owned by idle-interactive, and explores CPU cost/runtime
sensitivity. The snapshot now includes both opportunities and their full job
records, ranked by gross modeled high GPU resource value.

CPU-placement point realization defaults to 50%. Net benefit remains unknown
unless incremental total CPU cost per job-hour is supplied. For example:

```bash
.venv/bin/python -m analytics.build_analysis --incremental-cpu-cost-per-job-hour 1 --cpu-runtime-multiplier 1.5 --cpu-point-realization 0.5 --output generated/analysis.cpu-sensitivity.json
```

This rate is hypothetical incremental USD/job-hour, not USD/core-hour. It
changes producer-only net scenarios; public monetary fields remain explicitly
gross GPU resource value. Negative modeled net outcomes are retained.

```bash
.venv/bin/python -m analytics.build_analysis
.venv/bin/python -m backend.validate_analysis generated/analysis.json --check-api
```

Optional arguments:

```bash
.venv/bin/python -m analytics.build_analysis --data-dir ~/Desktop/hackathon-2026-official --price 2.50 --price-book-version cutscope-assumption-v1
```

The exporter uses the existing `summary`, `opportunities`, `jobs`, and
`metadata` envelope. It includes `idle-interactive` and `gpu-not-needed`, every
affected job record, and original finding evidence. Point estimates, policy
parameters, exclusions, replay sensitivity and the primary ledger live in
metadata. Backend APIs do not expose that producer metadata; method text also
explains the point estimate and assumption.

Defaults retain four hours per allocation and assume 50% realization for the
point scenario. Low is zero guaranteed reclaim; high assumes all eligible
modeled budget is reclaimed. These are explicit, uncalibrated scenarios, not
measured savings or statistical confidence intervals. Change them with:

```bash
.venv/bin/python -m analytics.build_analysis --idle-retained-hours 8 --idle-point-realization 0.25 --output generated/analysis.sensitivity.json
```

Actual downside dollars and confidence remain null. Hypothetical replay cost
is shown separately; it does not price engineer time or bound business loss.

The default $2.50/GPU-hour is an explicit scenario assumption, not an official
cloud price, verified bill, or cash-savings claim. All headline calculations
use measured DCGM `gpu_hours`. The final-walltime allocation estimate remains
a comparison with a separately labeled known subtotal and missing count.

## Verification

```bash
.venv/bin/python -m pytest analytics/tests -q
.venv/bin/python ~/Desktop/hackathon-2026-official/track-2/scripts/checksum_data.py
```

The loader independently checks the three consumed files using the official
hash algorithm. If the manifest is absent, verification is marked unknown;
a present mismatching hash stops loading. The official command checks all five
files, including resource and edge tables that this baseline does not consume.

## Next milestone

Review the policy with operational feedback and inspect the other opportunities.
Expand slow cancel and card imbalance through the same primary
ledger; whole-job ownership currently prevents overlap conservatively. Their
modules remain unimplemented. No enforcement is deployed by this analysis.
Keep the shared API unchanged; review any required field change with Persons
2 and 5.
