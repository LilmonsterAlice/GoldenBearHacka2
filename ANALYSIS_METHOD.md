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

## First opportunity

`idle-interactive-session`: baseline identification and the v2 policy model are
documented below. The API opportunity ID remains `idle-interactive`.

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

## analytics2 idle policy model v2

### Inclusion and exclusion

Start with the 906 recomputed official idle candidates. Require a matching
explicitly non-synthetic idle finding; zero job SM mean and peak; zero peak on
every physical GPU; exactly one scheduler attempt; positive finite measured
hours, final-walltime allocation hours, walltime and GPU count; complete card
counts and valid card consumption. Scheduler allocation must equal
`gpu_count * walltime_sec / 3600`. Measured/scheduler discrepancy must be within
10%; each card's measured hours must not exceed final walltime by more than 10%.
The tolerance can be tightened, but not widened above 10%.

Final state is not an inclusion rule: useful CPU-only work may complete with
zero GPU compute. This cohort is a policy-review target, not proof of abandonment.
Missing qualifying evidence is excluded with a recorded reason; multiple
exclusion reasons can apply to the same job.

### Policy scenarios

Default retained period `G=4` hours and point realization `R=0.5` are explicit
uncalibrated assumptions. For job measured hours `M`, scheduler allocation
hours `A`, and GPU count `N`:

```text
high  = max(0, min(M, A) - N * G)
point = R * high
low   = 0
```

Only jobs with positive high budget enter the affected-reference list. Sum
these allocation budgets, never finding impacts. Low is zero because actual
reclaim is not guaranteed. High assumes every modeled budget is reclaimed;
point assumes half by default. These are not confidence intervals, empirically
calibrated forecasts, or provider-bill savings. USD is resource value at the
snapshot rate. Numeric confidence remains null: upstream detector confidence
in a symptom does not measure recoverability probability.

The retained period defines a hypothetical session-cap window after `G` hours
from session start, not an observed idle interval. The dataset does not reveal
an idle onset or permit a timestamped idle-timeout simulation. The assumed
realization fraction represents opt-outs, legitimate work, and policy adoption
collectively; none of those factors is measured here. Warning-only pilots and
review of legitimate CPU work must precede enforcement.

### Primary attribution and evidence

The ledger records one primary `idle-interactive` owner per eligible job, its
allocation budget, modeled elapsed window, low/point/high hours and supporting
finding IDs. Entire-job ownership is conservative: future opportunities on
that same job must remain supporting evidence unless a reviewed method can
demonstrate disjoint physical allocations. A duplicate primary assignment or
scenario exceeding its job budget raises an error. No observed timestamped
physical interval is claimed from the modeled window.

Retain all original job findings, including overlapping GPU-not-needed and
slow-cancel evidence. They do not create extra priced hours. Affected jobs are
ordered by high modeled budget descending, then ID; every reference resolves
to an exported full job record. Price job evidence using its original measured
consumption, so evidence cost and modeled reclaim cost remain distinct.

### Cost if wrong and rollback

Actual cost-if-wrong low/high USD remains null because interruption frequency,
CPU work loss, engineer time and business consequences are unmeasured. Producer
metadata shows an explicitly hypothetical sensitivity: replay 0%, 1%, 5%, 10%
or 100% of eligible measured consumption once, at identical GPU cost. Fractions
are consumption-weighted, not observed false-positive job rates. This is not a
business-loss bound, and GPU-only replay can miss the main harm to CPU work.

Start warning-only, provide extensions and opt-outs, review useful CPU-only
work, check checkpoint persistence, pilot a small cohort, and disable enforcement
when legitimate work is interrupted. `reversible=false` reflects that rolling
back the policy cannot restore unsaved session state. Medium risk is a qualitative
policy judgment, not an empirically estimated loss rate.

### Integration

The existing API fields now contain low/high modeled values, null actual confidence
and downside USD, method/basis/caveats, complete job references and findings.
Structured point values, policy parameters, exclusions, replay sensitivity and
the ledger live in file-only metadata; method text also states the point
assumption and result. No shared API fields or endpoints have changed.

## analytics2 CPU-placement model v3

Recompute `rules::gpu-not-needed`: final state COMPLETED, job-average and peak
SM exactly zero, and measured GPU-hours >1. Check the official finding ID set
in notebook 03. Require matching explicitly non-synthetic evidence, exactly one
attempt, complete zero-peak cards, positive valid allocation measurements,
scheduler formula agreement and measured/scheduler discrepancy within 10%.
Exclude cards whose measured consumption exceeds final walltime by more than
10%. Unknown qualifying evidence is excluded with a recorded reason.

Idle-interactive receives primary ownership first to preserve the prior stage.
Any job already owned by it is excluded entirely from GPU-not-needed reclaim;
supporting GPU-not-needed findings remain on the idle job. Allocation ownership
is independent of display order. Rank the two cards by descending gross high
GPU resource value; equal unknown confidence and medium qualitative risk do
not establish a ranking by net benefit.

For each additional eligible job, high=min(measured hours, scheduler allocation
hours), point=high times the configured realization fraction (default 50%), and
low=0 guaranteed reclaim. The whole allocation is modeled as moved to CPU
placement. This is not proof of portability or successful migration. Jobs may
initialize CUDA or hold GPU memory while reporting zero compute. Report GPU
memory observations and validate dependencies and output equivalence in a pilot.

API monetary fields retain the existing interpretation of gross freed-GPU
resource value at the snapshot rate; method/title/caveats explicitly identify
this as gross. Net benefit remains unknown by default. Optional producer
metadata models total incremental CPU placement cost as observed job walltime
times a positive assumed CPU runtime multiplier times a nonnegative incremental
USD/job-hour rate. This is a total job rate, not USD/core-hour, and should cover
only additional cost relative to baseline. Full-adoption net=gross GPU value
minus this cost; point scales both by realization; low means no migration and
zero incremental cost. Negative net outcomes are retained. Full adoption is an
adoption scenario, not an upper bound on net benefit. Migration effort, CPU queue
constraints, engineer time and business loss remain unpriced.

Actual numeric confidence and cost-if-wrong USD remain null. Preserve original
GPU requests and checkpoints, validate representative outputs and runtimes, and
stop the pilot on regressions. `reversible=false` reflects that a request rollback
cannot undo missed deadlines or already lost work. No enforcement or placement
change is performed by the analytics code.

Two opportunities now share one primary ledger, complete unique job evidence,
and low/high public values. Structured point/net scenarios, CPU assumptions and
exclusions remain file-only metadata. No shared API fields or endpoints change.
