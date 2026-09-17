"""Successful zero-compute jobs: CPU-placement candidates, not proven portability."""

from dataclasses import asdict
import math

import pandas as pd

from analytics.deduplication import PrimaryLedger
from analytics.outcomes import percent
from analytics.scenarios import CpuPlacementPolicy
from analytics.opportunities.idle_interactive import nullable


def gpu_not_needed_candidates(jobs):
    eligible = (jobs.state_name.eq("COMPLETED") & jobs.sm_util_avg.eq(0) &
                jobs.sm_util_max.eq(0) & jobs.gpu_hours.gt(1))
    return jobs.loc[eligible].sort_values(["gpu_hours", "id_job"], ascending=[False, True]).copy()


def build_gpu_not_needed_opportunity(data, pricing, total_hours, policy=CpuPlacementPolicy(), ledger=None):
    ledger = ledger if ledger is not None else PrimaryLedger()
    candidates = gpu_not_needed_candidates(data.jobs)
    findings_by_job = {}
    for finding in data.findings:
        job_id = (finding.get("metadata") or {}).get("job_id")
        if job_id is not None:
            findings_by_job.setdefault(int(job_id), []).append(finding)
    cards_by_job = {int(job_id): cards for job_id, cards in
                    data.gpus[data.gpus.id_job.isin(candidates.id_job)].groupby("id_job")}
    exclusions, records, budgets = [], [], []
    for _, job in candidates.iterrows():
        job_id = int(job.id_job)
        findings = findings_by_job.get(job_id, [])
        reasons = []
        if not any(f.get("detectorId") == "rules::gpu-not-needed" and
                   (f.get("metadata") or {}).get("synthetic") is False for f in findings):
            reasons.append("no_non_synthetic_gpu_not_needed_finding")
        owner = ledger.owner(job_id)
        if owner is not None:
            reasons.append("already_primary:" + owner)
        if pd.isna(job.attempts) or job.attempts != 1:
            reasons.append("multiple_or_unknown_attempts")
        values = (job.gpu_hours, job.gpu_hours_alloc, job.walltime_sec, job.gpu_count)
        if any(pd.isna(v) or not math.isfinite(float(v)) or v <= 0 for v in values):
            reasons.append("invalid_allocation_measurements")
        else:
            if abs(job.gpu_hours / job.gpu_hours_alloc - 1) > .1:
                reasons.append("measured_allocated_hours_disagree")
            if not math.isclose(job.gpu_hours_alloc, job.gpu_count * job.walltime_sec / 3600,
                                rel_tol=1e-9, abs_tol=1e-6):
                reasons.append("inconsistent_final_walltime_allocation")
        cards = cards_by_job.get(job_id)
        if cards is None or len(cards) != job.gpu_count:
            reasons.append("missing_or_incomplete_card_evidence")
        elif (cards.smutilization_pct_max.isna().any() or cards.smutilization_pct_max.ne(0).any()):
            reasons.append("nonzero_or_unknown_card_compute_peak")
        elif any(pd.isna(v) or not math.isfinite(float(v)) or v < 0 for v in cards.gpu_hours):
            reasons.append("invalid_card_consumption")
        elif pd.notna(job.walltime_sec) and (cards.gpu_hours > job.walltime_sec / 3600 * 1.1).any():
            reasons.append("card_consumption_exceeds_final_walltime_tolerance")
        if reasons:
            exclusions.append({"job_id": job_id, "reasons": reasons})
            continue
        high = float(min(job.gpu_hours, job.gpu_hours_alloc))
        scenarios = {"low": 0., "point": high * policy.point_realization, "high": high}
        ledger.assign(job_id, "gpu-not-needed", high, scenarios,
                      modeled_elapsed_start_sec=0., modeled_elapsed_end_sec=float(job.walltime_sec),
                      gpu_count=int(job.gpu_count), supporting_finding_ids=[f["id"] for f in findings],
                      window_basis="hypothetical CPU placement of the whole job, not measured savings")
        budgets.append({"job_id": job_id, "gpu_hours": scenarios, "walltime_hours": float(job.walltime_sec / 3600)})
        records.append({"job_id": job_id, "state": str(job.state_name), "gpu_count": int(job.gpu_count),
                        "gpu_hours": float(job.gpu_hours), "cost_usd": pricing.cost(job.gpu_hours),
                        "sm_util_avg": 0., "sm_util_max": 0., "walltime_hours": float(job.walltime_sec / 3600),
                        "primary_node": nullable(job.primary_node), "findings": findings})
    rank = {row["job_id"]: row["gpu_hours"]["high"] for row in budgets}
    records.sort(key=lambda row: (-rank[row["job_id"]], row["job_id"]))
    totals = {key: math.fsum(row["gpu_hours"][key] for row in budgets) for key in ("low", "point", "high")}
    gross = {key: pricing.cost(value) for key, value in totals.items()}
    walltime = math.fsum(row["walltime_hours"] for row in budgets)
    cpu_cost = None if policy.incremental_cpu_cost_per_job_hour is None else (
        walltime * policy.cpu_runtime_multiplier * policy.incremental_cpu_cost_per_job_hour)
    net = None if cpu_cost is None else {"low": 0., "point": gross["point"] - cpu_cost * policy.point_realization,
                                        "high_adoption": gross["high"] - cpu_cost}
    # Monetary API fields represent gross freed-GPU resource value, consistent
    # with the idle opportunity. Net monetary benefit is separate and can be negative.
    opportunity = {"id": "gpu-not-needed", "title": "Successful zero-compute jobs: modeled GPU resource value",
                   "action": "Pilot CPU-only placement after validating GPU-memory dependencies and output equivalence.",
                   "owner": "Workload Owners / Platform Operations", "savings_usd_low": gross["low"],
                   "savings_usd_high": gross["high"], "gpu_hours_low": totals["low"], "gpu_hours_high": totals["high"],
                   "capacity_percent_low": percent(totals["low"], total_hours),
                   "capacity_percent_high": percent(totals["high"], total_hours), "confidence": None,
                   "risk_level": "medium", "job_count": len(records),
                   "method": f"High=sum(min(measured GPU-hours, scheduler allocation)) for eligible unowned jobs. Low=0 guaranteed reclaim. Point assumes {policy.point_realization:.0%} realization: {totals['point']:.2f} GPU-hours (${gross['point']:.2f} gross resource value). USD fields are gross GPU resource value, not net savings. Incremental CPU costs are {'unknown' if cpu_cost is None else f'assumed at ${policy.incremental_cpu_cost_per_job_hour:g}/job-hour with runtime multiplier {policy.cpu_runtime_multiplier:g}'}. Idle-interactive retains primary precedence for overlapping jobs.",
                   "basis": "COMPLETED with zero observed mean and peak GPU compute and more than one measured GPU-hour; matching non-synthetic finding, zero card peaks, one attempt, valid consistent allocation, and no existing primary owner.",
                   "caveats": ["Zero compute is observed evidence, not proof of CPU-only portability: CUDA initialization, GPU-memory use, dependencies and output correctness require testing.",
                               "GPU resource value is gross; net benefit is unknown without incremental CPU cost and runtime assumptions. CPU capacity and scheduling delay are unmeasured.",
                               "Point realization is uncalibrated; scenarios are not confidence intervals or verified cash savings.",
                               "Jobs owned by idle-interactive are excluded entirely rather than pricing the same allocation twice.",
                               "Historical sample findings do not establish current live workloads. Numerical recoverability confidence and actual business downside remain unknown."],
                   "cost_if_wrong": {"description": "CPU-only placement may fail due to GPU dependencies, alter outputs, or increase runtime and queue delay. Actual failure frequency and business losses are unknown.",
                                     "usd_low": None, "usd_high": None, "reversible": False,
                                     "mitigation": "Pilot representative jobs, compare outputs and runtimes, inspect memory/dependencies, preserve original GPU request and checkpoints, and roll back placement if outputs or latency regress. Rollback cannot undo missed deadlines or lost work."},
                   "jobs": [{"job_id": row["job_id"]} for row in records]}
    diagnostics = {"policy": asdict(policy), "candidate_count": len(candidates), "modeled_job_count": len(records),
                   "candidate_jobs_with_nonzero_gpu_memory": int(candidates.max_gpu_mem_used.gt(0).sum()),
                   "candidate_jobs_with_unknown_gpu_memory": int(candidates.max_gpu_mem_used.isna().sum()),
                   "exclusions": exclusions, "scenarios_gpu_hours": totals, "gross_resource_value_usd": gross,
                   "incremental_cpu_cost_usd_high_adoption": cpu_cost, "net_benefit_usd": net,
                   "net_basis": "Incremental total CPU placement cost per job-hour times observed walltime times assumed runtime multiplier; scales by realization for point. high_adoption means full adoption, not an upper bound on net benefit. Negative net benefit is retained. Low=do not migrate, with zero modeled cost.",
                   "primary_ledger": [row for row in ledger.records() if row["primary_opportunity_id"] == "gpu-not-needed"]}
    return opportunity, records, diagnostics
