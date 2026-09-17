"""Build evidence-backed, mutually exclusive opportunity estimates.

The findings select candidates; prepared telemetry verifies each candidate. The
recovery fractions are policy scenarios, not observed savings.
"""

from collections import defaultdict
import math

import pandas as pd

from analytics.pricing import gpu_hours_to_usd


POLICIES = (
    ("idle-interactive", "rules::idle-interactive-session", "Idle interactive sessions", "Warn and time out idle interactive allocations", "Platform Operations", 0.0, 0.25, 0.10, 0.60, "medium"),
    ("gpu-not-needed", "rules::gpu-not-needed", "GPU not needed", "Review successful CPU-only workloads for CPU placement", "Workload Owners", 0.0, 0.50, 0.20, 0.70, "medium"),
    ("slow-cancel", "rules::slow-cancel-of-idle-job", "Slow cancellation of idle jobs", "Alert owners and add a liveness review before cancellation", "Platform Operations", 0.0, 0.25, 0.10, 0.50, "medium"),
    ("gpu-imbalance", "rules::gpu-imbalance", "GPU card imbalance", "Profile per-card work distribution before resizing", "Workload Owners", 0.0, 0.20, 0.05, 0.50, "high"),
)

WRONG_ACTION = {
    "idle-interactive": ("An idle timeout could terminate a useful interactive session and force a rerun.", "Warn first, permit an extension, pilot on a small group, and roll back if retries or complaints rise."),
    "gpu-not-needed": ("Moving a job to CPU placement could slow it or fail if an unobserved GPU dependency exists.", "Canary selected jobs on CPU nodes and compare completion time and success before changing defaults."),
    "slow-cancel": ("A premature cancellation could destroy useful progress or interrupt a hung job that might recover.", "Send alerts first, require owner confirmation, and measure retry and completion rates."),
    "gpu-imbalance": ("Removing a GPU could extend runtime or break distributed jobs.", "Profile and benchmark representative jobs before resizing; restore the prior allocation on regression."),
}


def _number(value):
    if value is None or pd.isna(value):
        return None
    result = float(value)
    return result if math.isfinite(result) else None


def _valid(row, rule, cards):
    hours = _number(row.gpu_hours)
    wall = _number(row.walltime_sec)
    avg = _number(row.sm_util_avg)
    peak = _number(row.sm_util_max)
    if hours is None or hours <= 0 or wall is None or wall < 0:
        return False
    if rule == "rules::idle-interactive-session":
        return row.job_type == "LLSUB:INTERACTIVE" and wall > 4 * 3600 and avg is not None and 0 <= avg < 5
    if rule == "rules::gpu-not-needed":
        return row.state_name == "COMPLETED" and hours > 1 and avg == 0 and peak == 0
    if rule == "rules::slow-cancel-of-idle-job":
        return row.state_name == "CANCELLED" and wall > 4 * 3600 and avg is not None and 0 <= avg < 5
    if rule == "rules::gpu-imbalance":
        measures = cards.get(int(row.id_job), [])
        return (wall > 3600 and len(measures) >= 2 and max(measures) >= 20
                and max(measures) - min(measures) > 30)
    return False


def _cards_by_job(gpus):
    required = {"id_job", "smutilization_pct_avg", "gpu_hours"}
    if not required <= set(gpus.columns):
        raise ValueError("GPU telemetry missing: " + ", ".join(sorted(required - set(gpus.columns))))
    cards = defaultdict(list)
    for job_id, sm, hours in gpus[["id_job", "smutilization_pct_avg", "gpu_hours"]].itertuples(index=False, name=None):
        sm, hours = _number(sm), _number(hours)
        if sm is not None and 0 <= sm <= 100 and hours is not None and hours >= 0:
            cards[int(job_id)].append(sm)
    return cards


def _nullable(value):
    result = _number(value)
    return result if result is not None and result >= 0 else None


def build_opportunities(jobs, gpus, findings, *, price_per_gpu_hour, total_gpu_hours):
    if not isinstance(findings, list) or not findings:
        raise ValueError("Full analysis needs a nonempty findings JSON list")
    required = {"id_job", "gpu_hours", "gpu_count", "walltime_sec", "job_type", "state_name", "sm_util_avg", "sm_util_max", "primary_node"}
    if not required <= set(jobs.columns):
        raise ValueError("Jobs missing: " + ", ".join(sorted(required - set(jobs.columns))))
    indexed_jobs = jobs.set_index("id_job", drop=False)
    cards = _cards_by_job(gpus)
    related = defaultdict(list)
    by_rule = defaultdict(list)
    for finding in findings:
        if not isinstance(finding, dict):
            continue
        meta = finding.get("metadata") or {}
        job_id = meta.get("job_id")
        if type(job_id) is not int or job_id not in indexed_jobs.index:
            continue
        related[job_id].append(finding)
        if meta.get("synthetic") is False and meta.get("impact_kind") == "unused_capacity":
            by_rule[finding.get("detectorId")].append(finding)

    claimed = set()
    records = []
    evidence_jobs = {}
    point_estimates = {}
    audit = {}
    for oid, rule, title, action, owner, low_rate, high_rate, point_rate, confidence, risk in POLICIES:
        selected = []
        candidate_hours = 0.0
        overlap = 0
        rejected = 0
        for finding in by_rule[rule]:
            jid = finding["metadata"]["job_id"]
            if jid in claimed:
                overlap += 1
                continue
            row = indexed_jobs.loc[jid]
            if not _valid(row, rule, cards):
                rejected += 1
                continue
            raw_hours = _number(row.gpu_hours)
            impact = _number(finding["metadata"].get("impact_gpu_hours"))
            if impact is None or impact <= 0:
                rejected += 1
                continue
            eligible = min(raw_hours, impact)
            if eligible <= 0:
                continue
            claimed.add(jid)
            candidate_hours += eligible
            selected.append(jid)
            if jid not in evidence_jobs:
                evidence_jobs[jid] = {
                    "job_id": jid,
                    "state": row.state_name,
                    "gpu_count": int(row.gpu_count) if _nullable(row.gpu_count) is not None else None,
                    "gpu_hours": raw_hours,
                    "cost_usd": gpu_hours_to_usd(raw_hours, price_per_gpu_hour),
                    "sm_util_avg": _nullable(row.sm_util_avg),
                    "sm_util_max": _nullable(row.sm_util_max),
                    "walltime_hours": _nullable(row.walltime_sec / 3600),
                    "primary_node": row.primary_node if isinstance(row.primary_node, str) else None,
                    "findings": related[jid],
                }
        selected.sort()
        low_hours, high_hours = candidate_hours * low_rate, candidate_hours * high_rate
        basis = (f"{len(selected)} distinct verified jobs; {candidate_hours:.3f} candidate GPU-hours "
                 f"capped by measured job GPU-hours; recovery assumptions {low_rate:.0%}–{high_rate:.0%}.")
        caveats = [
            "Four-month workload sample; no cluster-wide annualization.",
            "Recoverable fractions are policy assumptions, not measured outcomes.",
            "Job-level allocation prevents overlap across opportunities; within-job idle intervals are unavailable.",
        ]
        if oid == "gpu-imbalance":
            caveats.append("Per-card averages verify imbalance but cannot prove work can run on fewer GPUs.")
        record = {
            "id": oid, "title": title, "action": action, "owner": owner,
            "savings_usd_low": gpu_hours_to_usd(low_hours, price_per_gpu_hour),
            "savings_usd_high": gpu_hours_to_usd(high_hours, price_per_gpu_hour),
            "gpu_hours_low": low_hours, "gpu_hours_high": high_hours,
            "capacity_percent_low": low_hours / total_gpu_hours * 100 if total_gpu_hours > 0 else None,
            "capacity_percent_high": high_hours / total_gpu_hours * 100 if total_gpu_hours > 0 else None,
            "confidence": confidence, "risk_level": risk, "job_count": len(selected),
            "method": "Match a MantisGrid detector to raw telemetry, assign each job to its first eligible opportunity, cap impact by measured GPU-hours, then apply scenario recovery fractions.",
            "basis": basis, "caveats": caveats,
            "cost_if_wrong": {
                "description": WRONG_ACTION[oid][0] + " This dataset does not measure the counterfactual cost.",
                "usd_low": None, "usd_high": None, "reversible": True,
                "mitigation": WRONG_ACTION[oid][1],
            },
            "jobs": [{"job_id": jid} for jid in selected],
        }
        records.append(record)
        point_estimates[oid] = {
            "recovery_fraction": point_rate,
            "gpu_hours": candidate_hours * point_rate,
            "usd": gpu_hours_to_usd(candidate_hours * point_rate, price_per_gpu_hour),
        }
        audit[oid] = {"candidate_gpu_hours": candidate_hours, "overlap_jobs_excluded": overlap,
                      "failed_telemetry_check": rejected, "finding_count": len(by_rule[rule])}
    return records, [evidence_jobs[jid] for jid in sorted(evidence_jobs)], {"point_scenarios": point_estimates, "audit": audit}
