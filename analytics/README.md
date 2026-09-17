# Analytics: Person 1's workspace in the team repository

These scripts bring Person 1's summary/outcome calculations and idle-interactive
candidate detector from `origin/analytics` (`d114ae3`, formerly uploaded under
`analytics_副本/`) into the proper importable `analytics/` package. Continue
notebook-derived work here; the official starter repository is not a runtime
dependency. Only analytics files were changed.

Implemented: configurable local file loading, descriptive summary/outcomes,
four evidence-backed opportunities, scenario ranges, job-level deduplication,
cost-if-wrong descriptions, job/finding evidence, CLI, atomic backend-compatible
JSON, and tests. Full analysis requires `--with-opportunities`.

## Setup after pulling

From the team repository root, use Python 3.11 or newer and a virtual environment.
On macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r analytics/requirements-dev.txt
```

If your existing `.venv` uses an older Python, create it with an installed
Python 3.11+ executable instead. On Windows, activate `.venv\Scripts\Activate.ps1`
in PowerShell, then use the same `python -m ...` commands.
`requirements.txt` contains runtime pandas and the pyarrow parquet engine;
`requirements-dev.txt` adds pytest. No backend/frontend packages are required
for building analytics. Tested with Python 3.13.5, pandas 3.0.5, pyarrow 25.0.1.

## Use the official data already on your computer

Keep using the files you downloaded. Do not copy datasets, secrets, or generated
outputs into a commit. Each teammate sets their own paths; no absolute personal
path is baked into the code.

Option A: supply the existing official **data directory**, not notebook directory:

```bash
python -m analytics.build_analysis --data-dir "/absolute/path/to/official-repo/data" --check-data
python -m analytics.build_analysis --data-dir "/absolute/path/to/official-repo/data"
```

Option B: supply the exact prepared jobs file wherever it is stored:

```bash
python -m analytics.build_analysis --jobs-path "/absolute/path/to/jobs.parquet" --check-data
python -m analytics.build_analysis --jobs-path "/absolute/path/to/jobs.parquet"
```

Option C: set per-computer environment variables, then use the short command:

```bash
export CUTSCOPE_DATA_DIR="/absolute/path/to/official-repo/data"
python -m analytics.build_analysis --check-data
python -m analytics.build_analysis
```

PowerShell equivalent: `$env:CUTSCOPE_DATA_DIR = "C:\path\to\official-repo\data"`.
Environment variables are read at invocation; `.env` files are not automatically
loaded, committed, or shared.

| Setting | Meaning |
| --- | --- |
| `CUTSCOPE_DATA_DIR` / `--data-dir` | Data directory; defaults to team repo `data/` |
| `CUTSCOPE_JOBS_PATH` / `--jobs-path` | Exact jobs parquet path; overrides directory lookup |
| `CUTSCOPE_GPUS_PATH` | Exact GPU telemetry parquet path for future card analysis |
| `CUTSCOPE_FINDINGS_PATH` | Exact findings JSON path |
| `--output` | JSON destination; defaults to team repo `generated/analysis.json` |
| `--price-per-gpu-hour` | Default Person 1 rate 2.50; nonnegative finite override |
| `--price-book-version` | Explicit pricing label; changed rate otherwise gets `custom-rate` |

Explicit function/CLI paths override per-file environment variables, which
override directory discovery. Under the chosen directory, parquet lookup checks
`prepped/jobs.parquet`, `jobs.parquet`, then `processed/jobs.parquet` (same for
GPUs). Findings lookup checks `findings.json`, then `synthetic/findings.json`.
These are filename/layout conveniences, not proof of source authenticity.
Absolute paths and `~` are supported; relative paths resolve from the team
repository root, independent of your shell's working directory.

Direct execution is also supported:

```bash
python /absolute/path/to/GoldenBearHacka2/analytics/build_analysis.py --jobs-path "/absolute/path/to/jobs.parquet"
```

## Input contract and adapting starter-notebook work

Loaders preserve the input table's columns; they do not run the official prep
pipeline, download data, invent units, or discard attempts.

Person 1's current summary expects a **prepared job-level table** with:

- `id_job`: nonmissing unique job identifier (one row per job).
- `state_name`: nonmissing final outcome name, including `COMPLETED` where present.
- `gpu_hours`: finite nonnegative allocated GPU-hours; missing hours are rejected
  rather than silently treated as zero.

Idle-candidate detection additionally uses `job_type`, `walltime_sec` (seconds),
and `sm_util_avg` (0–100). Its official-rule defaults are `LLSUB:INTERACTIVE`,
more than four hours, and average utilization below 5%. Unknown measurements
are excluded, not set to zero. Thresholds and the interactive type label can
be refined through function arguments.

If your notebook/raw download uses different columns or units, put an explicit
mapping/preparation step in `load_data.py` or a new module inside `analytics/`
after checking the actual schema. Do not guess whether a duration is milliseconds
or seconds, infer GPU-hours from utilization, or multiply an already allocated
GPU-hours column again. The CLI explains missing columns and missing paths.

Use in a notebook/kernel started at the team repository root:

```python
from analytics.load_data import load_jobs, load_gpus, load_findings
from analytics.build_analysis import build_summary
from analytics.opportunities.idle_interactive import find_idle_interactive_jobs

jobs = load_jobs(data_dir="/absolute/path/to/official-repo/data")
summary = build_summary(jobs)
candidates = find_idle_interactive_jobs(jobs)
```

Findings are returned as their original JSON list/object, rather than assuming
a flat table. If an existing notebook needs a DataFrame, extract the correct
list from the actual envelope and normalize it explicitly in Person 1's code.
GPUs and findings are not required for the current summary-only builder.

## Output and backend connection

The builder writes:

```text
summary: calculated Summary fields
opportunities: [] until savings modeling is ready
jobs: [] until evidence records are ready
metadata: producer information indicating summary-only stage
```

Missing completed outcomes yield 0% only when measured total GPU-hours are
positive. Empty/zero-hour samples have null percentages, not division-by-zero
NaN. CANCELLED/FAILED/TIMEOUT are descriptive outcomes, not automatic savings.
The scope caveat remains the planned four-month sample; verify actual input
scope in your methodology before submission.

Output uses strict JSON and atomic replacement. Invalid input leaves existing
output unchanged. The source parquet is never modified. Output is readable by
the non-root backend container; root `generated/*` is already ignored by Git.
When using a custom output directory, keep it ignored and never commit it.

When the backend branch is integrated, run its read-only compatibility check:

```bash
python -m backend.validate_analysis generated/analysis.json --check-api
```

Person 5 can then select real mode and mount this file. The current backend
supports summary-only snapshots. Add full opportunities and referenced jobs
incrementally using the backend model/schema draft, coordinating changes with
Person 5. Candidate GPU-hours must not be published as fully recoverable savings.

## Tests and known limitations

```bash
python -m pytest analytics/tests -q
```

Tests use temporary synthetic parquet files, not committed official datasets.
They cover local/env paths, spaces in paths, direct execution from another
directory, read-only source preservation, summary weighting, no completed
jobs, empty/zero-hour data, invalid values, strict output, and idle thresholds.
The backend-model integration test skips if backend models are not available
on the pulled branch; run it again after integration.

Full analysis was verified locally against the official prepared files. The
generated snapshot passed the backend `AnalysisSnapshot` and `AnalysisStore`
checks, including opportunity-to-job references. The current analytics branch
does not contain the backend package, so the in-tree backend integration test
skips until the branches are merged. Do not commit generated analysis or data.

## Full evidence-backed analysis

The summary-only command above remains available. To build the four ranked
opportunities from official prepared data and generated MantisGrid findings:

```bash
python -m analytics.build_analysis \
  --data-dir "/absolute/path/to/hackathon-2026-official/track-2/data" \
  --with-opportunities
```

This requires `prepped/jobs.parquet`, `prepped/gpus.parquet`, and
`synthetic/findings.json`. You can override each with `--jobs-path`,
`--gpus-path`, or `--findings-path`. Read `ANALYSIS_METHOD.md` for the filters,
scenario assumptions, deduplication rule, and caveats. A true API is not needed
to generate this deterministic snapshot; the product backend serves it through
`/api/*` after integration.
