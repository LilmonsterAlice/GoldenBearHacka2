# Analysis Method — Shared Invariants

Person 1 owns the detailed formulas and inclusion/exclusion methodology. This
file begins with the non-negotiable rules agreed by the team:

1. CANCELLED is a scenario decision, not automatic waste.
2. Finding `impact_gpu_hours` overlaps and must not be naively summed.
3. `lost`, `consumed`, `degraded`, and `unused_capacity` are distinct concepts.
4. A physical job-hour may enter at most one primary savings opportunity.
5. A job may retain multiple supporting finding IDs without duplicate pricing.
6. Cost analysis uses GPU-hour weighting rather than row weighting.
7. Card imbalance is calculated from `gpus.parquet`, not job-level averages.
8. Hardware analysis uses attempt history, `hit_node_failure`, and
   `nodefail_nodes`, not final state/placement alone.
9. Savings outputs include low/point/high, confidence, basis, and caveats.
10. Every result describes the four-month workload sample.

## First method to document

`idle-interactive-session`: Person 1 will add its exact inclusion rules,
deduplication priority, interval interpretation, and cost-if-wrong assumptions.

## analytics2 baseline v1

The fresh pipeline reads the official `track-2/data/prepped/jobs.parquet`,
`gpus.parquet`, and `synthetic/findings.json` in place. It consumes neither the
previous analytics branch nor any generated output from it. Notebook and batch
execution import the same deterministic Python functions.

### Source verification and grain

Parquet sources are checked using the official column-value SHA-256 algorithm;
findings use a byte SHA-256. A supplied checksum mismatch stops loading.
Missing manifests are marked unknown, rather than called verified.

Jobs are one row per `id_job`, preserving final scheduler information and
attempt-history fields. GPU rows are one physical card per job keyed by
`(Node, gpu_id, id_job)`; they are summaries, not timestamped utilization.
The build rejects duplicate or unresolved allocation keys, incorrect card
counts, and job/card measured-hour disagreements.

### Baseline formulas

- Sample hours: sum the official measured `jobs.gpu_hours`, derived from DCGM.
- Outcome hours: sum that same field within each final `state_name`.
- Scenario resource value: measured GPU-hours multiplied by the configured
  USD/GPU-hour. Default rate is 2.50, labeled `cutscope-assumption-v1`; this is
  not a verified provider price book or a claim of realizable cash savings.
- Outcome and capacity percentages: 100 times cohort measured hours divided by
  all measured hours in the workload sample. These are not fleet utilization.
- Completed percentage: completed measured GPU-hours divided by all measured
  GPU-hours, on the 0–100 scale; it is not the share of job records completed.
- SM utilization: sum(job-average SM percent times measured GPU-hours) divided
  by hours with observed SM measurements. Report their coverage separately.

Unknown states are retained. Cancellation is an outcome, not a waste label.
Missing measured hours make the affected aggregate unknown; they do not become
zero. An absent completed cohort has zero completed hours when the other
measurements are known. A zero total has undefined percentages (`null`).

`gpu_hours_alloc` is a separate scheduler final-walltime comparison. It is not
substituted for measured consumption. Report its known subtotal and missing
count separately from the complete aggregate. Requeues can mix attempts; card
duration disagreement is diagnostic and does not trigger a silent replacement
of the official measured-hour basis. The duration audit uses a stated one-second
tolerance and compares to final scheduler walltime. Investigate mismatches before
using card durations in a policy model.

### Candidate diagnostics and idle eligibility

Recompute the published idle rule exactly: `job_type == LLSUB:INTERACTIVE`,
`walltime_sec > 14400`, and `sm_util_avg < 5`. Missing qualifying measurements
do not satisfy eligibility. Candidate jobs retain their measurements and all
supporting findings for inspection. The notebook checks the candidate ID set
against the official idle findings.

Diagnostic cohorts are distinct matched job IDs from explicitly non-synthetic
findings for the four target rules. Historical and active findings are retained;
active counts are shown separately. Synthetic or unknown-origin findings are
not silently included as real candidate evidence. Cohort GPU-hours are the
jobs' full measured consumption, NOT recoverable hours or rule impact. In
particular, imbalance cohort totals include busy cards. Pairwise job overlap
is reported; no additive opportunity savings total is generated.

### Current limits and next stage

The first snapshot is summary-only with candidate diagnostics in producer
metadata. Opportunities and job drill-down exports remain empty. Low/point/high
savings, confidence scores, cost-if-wrong, and primary interval attribution are
not implemented. The summary tables cannot locate an exact idle start or
support a timestamped timeout simulation. Those models require explicit policy
assumptions and a documented evidence basis before any opportunity is exported.

No shared API fields or endpoints are changed by this baseline. Producer-only
information stays in metadata. Point estimates will need metadata storage or an
agreed contract extension when the scenario implementation begins.
