# CutScope analysis method

## Source and scope

The input is the official prepared `jobs.parquet` (one row per job),
`gpus.parquet` (one row per physical GPU per job), and `findings.json` from the
MantisGrid generator. No data or generated output is committed. The four-month
sample is not a measure of full-cluster utilization or annual savings.

The baseline uses the measured `jobs.gpu_hours`, not `gpu_count * walltime_sec`.
Outcome percentages are GPU-hour-weighted. The configurable price defaults to
$2.50 per GPU-hour, labeled `2026-Q3`. A changed price is labeled
`custom-rate` unless an explicit version is supplied.

## Opportunity eligibility

A finding is a candidate only when its detector ID, `metadata.job_id`,
`impact_kind=unused_capacity`, and `synthetic=false` are present. We verify it
against raw telemetry before assigning savings:

| Opportunity | Required raw evidence | Intervention |
| --- | --- | --- |
| Idle interactive | Interactive; >4 hours; mean SM <5% | Warning and idle timeout |
| GPU not needed | Completed; >1 GPU-hour; mean and max SM both 0 | Pilot CPU placement |
| Slow cancel | Cancelled; >4 hours; mean SM <5% | Alert/liveness review |
| GPU imbalance | At least 2 measured card rows; >1 hour; busiest >=20% SM; spread >30 points | Profile before resizing |

For imbalance, verification reads `gpus.parquet`. A job average alone is
insufficient. Missing utilization does not mean zero utilization. Each candidate
GPU-hour estimate is the smaller of finding `impact_gpu_hours` and measured job
`gpu_hours`. This caps rounded or inconsistent findings and avoids counting
capacity beyond the measured job. It does not prove the interval was recoverable.

## Deduplication and scenarios

Primary ownership priority is idle interactive, GPU not needed, slow cancel,
then GPU imbalance. A job is assigned only once. Its other findings stay on its
job evidence record. This job-level method is conservative for overlapping
findings but cannot split independent idle intervals within one job. The
`metadata.audit` field reports finding counts, excluded overlaps, rejected
telemetry checks, and assigned candidate GPU-hours.

The policy recovery fractions below are **illustrative interventions**, not
observed or statistically estimated savings. Low is zero because adoption and
recoverability have not been measured. Point values are internal scenario
metadata; the backend API displays low/high.

| Opportunity | Low | Point | High |
| --- | ---: | ---: | ---: |
| Idle interactive | 0% | 10% | 25% |
| GPU not needed | 0% | 20% | 50% |
| Slow cancel | 0% | 10% | 25% |
| GPU imbalance | 0% | 5% | 20% |

For each opportunity: `scenario GPU-hours = assigned candidate GPU-hours ×
recovery fraction`; `USD = scenario GPU-hours × price per GPU-hour`;
`capacity_percent = scenario GPU-hours / total measured GPU-hours × 100`.
Confidence values (0.5–0.7) are qualitative judgment scores for the
intervention, not calibrated probabilities. They must not be interpreted as
confidence intervals.

`cost_if_wrong.usd_low/high` are `null`: the dataset has no observed cost of
wrong intervention, reruns, or lost progress. Each opportunity records a
specific failure mode and rollback plan. A pilot should measure those costs
before converting the scenario into a budget commitment.

## Reproduce and inspect

From the team repository root:

```bash
.venv/bin/python -m analytics.build_analysis \
  --data-dir "/absolute/path/to/hackathon-2026-official/track-2/data" \
  --with-opportunities
.venv/bin/python -m pytest analytics/tests -q
```

The output is `generated/analysis.json`, with `summary`, `opportunities`,
`jobs`, and `metadata`. Each opportunity's `jobs` references resolve to a job
record that includes the original MantisGrid finding payloads. The builder
writes JSON atomically and does not mutate the source files.

## Shared constraints from the main branch

CANCELLED is not automatically waste. `lost`, `consumed`, `degraded`, and
`unused_capacity` are different impact kinds and must not be summed as one
savings pool. The current four opportunities use only `unused_capacity`.

Hardware analysis is outside this four-opportunity snapshot. If added later,
use attempt history (`hit_node_failure`, `nodefail_nodes`) rather than the final
job state or final placement alone. Any new opportunity must preserve the
one-primary-opportunity-per-job-hour rule and document its own counterfactual.
