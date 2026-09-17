"""Idle-session diagnostics and bounded, assumption-based policy scenarios."""

from dataclasses import asdict
import math

import pandas as pd

from analytics.deduplication import PrimaryLedger
from analytics.outcomes import percent
from analytics.scenarios import IdlePolicy, idle_hour_scenarios


def idle_candidates(jobs):
    required = {"job_type", "walltime_sec", "sm_util_avg", "gpu_hours", "id_job"}
    if not required.issubset(jobs.columns):
        raise ValueError(f"Missing idle-session columns: {sorted(required - set(jobs.columns))}")
    eligible = (jobs.job_type.eq("LLSUB:INTERACTIVE") &
                jobs.walltime_sec.gt(4 * 3600) & jobs.sm_util_avg.lt(5))
    return jobs.loc[eligible].sort_values(["gpu_hours", "id_job"], ascending=[False, True]).copy()


def nullable(value):
    return None if pd.isna(value) else value


def build_idle_opportunity(data, pricing, total_hours, policy=IdlePolicy(), ledger=None):
    ledger = ledger if ledger is not None else PrimaryLedger()
    candidates = idle_candidates(data.jobs)
    evidence = {}
    for finding in data.findings:
        metadata = finding.get("metadata") or {}
        if metadata.get("job_id") is not None:
            evidence.setdefault(int(metadata["job_id"]), []).append(finding)
    candidate_cards = data.gpus[data.gpus.id_job.isin(candidates.id_job)]
    card_groups = {int(job_id): cards for job_id, cards in candidate_cards.groupby("id_job")}
    exclusions, records, allocations = [], [], []
    for _, job in candidates.iterrows():
        job_id = int(job.id_job)
        findings = evidence.get(job_id, [])
        supporting = [f for f in findings if f.get("detectorId") == "rules::idle-interactive-session"
                      and (f.get("metadata") or {}).get("synthetic") is False]
        reasons = []
        if not supporting:
            reasons.append("no_non_synthetic_idle_finding")
        if pd.isna(job.sm_util_max) or job.sm_util_max != 0 or job.sm_util_avg != 0:
            reasons.append("nonzero_or_unknown_compute_peak_or_mean")
        if pd.isna(job.attempts) or job.attempts != 1:
            reasons.append("multiple_or_unknown_attempts")
        hours = [job.gpu_hours, job.gpu_hours_alloc, job.walltime_sec, job.gpu_count]
        if any(pd.isna(x) or not math.isfinite(float(x)) or x <= 0 for x in hours):
            reasons.append("invalid_allocation_measurements")
        else:
            derived = float(job.gpu_count * job.walltime_sec / 3600)
            if not math.isclose(derived, job.gpu_hours_alloc, rel_tol=1e-9, abs_tol=1e-6):
                reasons.append("inconsistent_final_walltime_allocation")
            if abs(job.gpu_hours / job.gpu_hours_alloc - 1) > policy.max_hours_ratio_difference:
                reasons.append("measured_allocated_hours_disagree")
        cards = card_groups.get(job_id)
        if cards is None or len(cards) != job.gpu_count:
            reasons.append("missing_or_incomplete_card_evidence")
        elif (cards.smutilization_pct_max.isna().any() or cards.smutilization_pct_max.ne(0).any()):
            reasons.append("nonzero_or_unknown_card_compute_peak")
        elif (cards.gpu_hours.isna().any() or
              any(not math.isfinite(float(x)) or x < 0 for x in cards.gpu_hours)):
            reasons.append("invalid_card_consumption")
        elif pd.notna(job.walltime_sec) and (cards.gpu_hours > job.walltime_sec / 3600 * (1 + policy.max_hours_ratio_difference)).any():
            reasons.append("card_consumption_exceeds_final_walltime_tolerance")
        if reasons:
            exclusions.append({"job_id": job_id, "reasons": reasons})
            continue
        scenarios = idle_hour_scenarios(job.gpu_hours, job.gpu_hours_alloc, int(job.gpu_count), policy)
        if scenarios["high"] <= 0:
            exclusions.append({"job_id": job_id, "reasons": ["no_budget_after_retained_hours"]})
            continue
        # Retain every upstream finding. Only the allocation ledger contributes hours.
        allocation = {"modeled_elapsed_start_sec": policy.retained_hours * 3600,
                      "modeled_elapsed_end_sec": float(job.walltime_sec), "gpu_count": int(job.gpu_count),
                      "supporting_finding_ids": [f["id"] for f in findings],
                      "window_basis": "hypothetical session cap; not an observed idle interval"}
        ledger.assign(job_id, "idle-interactive", min(job.gpu_hours, job.gpu_hours_alloc), scenarios, **allocation)
        allocations.append({"job_id": job_id, **scenarios})
        records.append({"job_id": job_id, "state": nullable(job.state_name), "gpu_count": int(job.gpu_count),
                        "gpu_hours": float(job.gpu_hours), "cost_usd": pricing.cost(job.gpu_hours),
                        "sm_util_avg": float(job.sm_util_avg), "sm_util_max": float(job.sm_util_max),
                        "walltime_hours": float(job.walltime_sec / 3600),
                        "primary_node": nullable(job.primary_node), "findings": findings})
    totals = {key: math.fsum(row[key] for row in allocations) for key in ("low", "point", "high")}
    ranking = {a["job_id"]: a["high"] for a in allocations}
    records.sort(key=lambda row: (-ranking[row["job_id"]], row["job_id"]))
    replay_hours = math.fsum(row["gpu_hours"] for row in records)
    point_text = f"Point assumes {policy.point_realization:.0%} of modeled reclaim is realized; this is an uncalibrated policy assumption."
    method = (f"For each eligible job, high=max(0,min(measured GPU-hours, final-walltime allocation GPU-hours)-"
              f"GPU count*{policy.retained_hours:g} retained hours). Low=0 because reclaim is not guaranteed. "
              f"{point_text} Point={totals['point']:.2f} GPU-hours (${pricing.cost(totals['point']):.2f} at "
              f"${pricing.rate:g}/GPU-hour). This is a session-cap proxy, not a time-resolved idle-timeout simulation.")
    opportunity = {"id": "idle-interactive", "title": "Zero-compute interactive sessions: modeled reclaim",
                   "action": "Pilot warnings and opt-out session limits; validate legitimate CPU-only work before termination.",
                   "owner": "Platform Operations", "savings_usd_low": pricing.cost(totals["low"]),
                   "savings_usd_high": pricing.cost(totals["high"]), "gpu_hours_low": totals["low"],
                   "gpu_hours_high": totals["high"], "capacity_percent_low": percent(totals["low"], total_hours),
                   "capacity_percent_high": percent(totals["high"], total_hours), "confidence": None,
                   "risk_level": "medium", "job_count": len(records), "method": method,
                   "basis": "Official idle findings plus zero mean/peak SM on jobs and zero peak on every card, one attempt, valid allocation measurements, and measured/allocated agreement within the documented tolerance. Final state does not decide eligibility.",
                   "caveats": ["These are assumption-based sample resource-value scenarios, not verified cash savings or statistical confidence intervals.",
                               "Zero observed GPU compute can coexist with legitimate CPU-only interactive work; it does not justify automatic termination.",
                               "No time-resolved activity or exact idle onset is available. The retained-hours model is a session-cap proxy.",
                               point_text, "Numerical recoverability confidence and actual business cost if wrong are unknown.",
                               "Supporting findings overlap and are not added. Historical findings describe this sample, not a current queue of live sessions."],
                   "cost_if_wrong": {"description": "Terminating a legitimate session can lose unsaved state, require replay, and delay users. False-positive frequency, engineer time, and business losses are unknown; actual USD downside is null. Producer metadata provides hypothetical one-replay sensitivity, not a measured loss bound.",
                                     "usd_low": None, "usd_high": None, "reversible": False,
                                     "mitigation": "Start warning-only; offer opt-out and extensions, verify checkpoints, review CPU-only work, pilot a small cohort, and disable enforcement on useful-work interruption. Disabling policy does not restore unsaved work."},
                   "jobs": [{"job_id": row["job_id"]} for row in records]}
    diagnostics = {"policy": asdict(policy), "candidate_count": len(candidates), "modeled_job_count": len(records),
                   "exclusions": exclusions, "scenarios_gpu_hours": totals,
                   "scenarios_usd": {key: pricing.cost(value) for key, value in totals.items()},
                   "scenario_interpretation": "Low=zero guaranteed reclaim; point=assumed realization; high=all modeled budget reclaimed. These are not confidence intervals.",
                   "replay_sensitivity": [{"assumed_replay_fraction": fraction,
                                           "gpu_hours": replay_hours * fraction,
                                           "resource_value_usd": pricing.cost(replay_hours * fraction)}
                                          for fraction in (0., .01, .05, .1, 1.)],
                   "replay_basis": "Assume the stated fraction of eligible measured consumption must be replayed once at identical GPU cost; consumption-weighted fractions, not measured false-positive job rates. Excludes engineer time, CPU-only work loss and business loss.",
                   "primary_ledger": ledger.records()}
    return opportunity, records, diagnostics
