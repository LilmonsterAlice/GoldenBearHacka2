"""Audits and candidate diagnostics, without recoverable-savings claims."""

from itertools import combinations

import numpy as np
import pandas as pd

from analytics.outcomes import measured_total, percent, validate_jobs, weighted_utilization

RULES = ("idle-interactive-session", "gpu-not-needed", "slow-cancel-of-idle-job", "gpu-imbalance")


def schema_table(frame):
    return pd.DataFrame({"dtype": frame.dtypes.astype(str), "missing": frame.isna().sum(),
                         "missing_percent": 100 * frame.isna().mean()}).rename_axis("column")


def findings_table(findings):
    rows = []
    for finding in findings:
        metadata = finding.get("metadata") or {}
        rows.append({"finding_id": finding.get("id"), "detector_id": finding.get("detectorId"),
                     "job_id": metadata.get("job_id"), "synthetic": metadata.get("synthetic"),
                     "impact_kind": metadata.get("impact_kind"),
                     "impact_scope": metadata.get("impact_scope"), "is_active": finding.get("isActive")})
    # Nullable integers avoid turning 64-bit job identifiers into floating-point IDs.
    frame = pd.DataFrame(rows, columns=["finding_id", "detector_id", "job_id", "synthetic",
                                       "impact_kind", "impact_scope", "is_active"])
    frame["job_id"] = pd.array([row["job_id"] for row in rows], dtype="Int64")
    return frame


def audit_data(data):
    jobs, gpus = data.jobs, data.gpus
    validate_jobs(jobs)
    finding_frame = findings_table(data.findings)
    card_hours = gpus.groupby("id_job").gpu_hours.sum(min_count=1)
    compared = jobs.set_index("id_job").gpu_hours.to_frame("job_hours").join(card_hours.rename("card_hours"))
    card_counts = gpus.groupby("id_job").size().reindex(jobs.id_job, fill_value=0).to_numpy()
    duration = gpus[["id_job", "totalexecutiontime_sec"]].merge(
        jobs[["id_job", "walltime_sec"]], on="id_job", how="left", validate="many_to_one")
    job_refs = finding_frame.job_id.dropna()
    return {"job_count": len(jobs), "gpu_row_count": len(gpus),
            "user_count": int(jobs.id_user.nunique()), "node_count": int(gpus.Node.nunique()),
            "finding_count": len(data.findings),
            "synthetic_finding_count": int(finding_frame.synthetic.eq(True).sum()),
            "unknown_synthetic_flag_count": int(finding_frame.synthetic.isna().sum()),
            "duplicate_gpu_keys": int(gpus.duplicated(["Node", "gpu_id", "id_job"]).sum()),
            "orphan_gpu_rows": int((~gpus.id_job.isin(jobs.id_job)).sum()),
            "unmatched_job_findings": int((~job_refs.isin(jobs.id_job)).sum()),
            "gpu_count_mismatch_jobs": int((card_counts != jobs.gpu_count.to_numpy()).sum()),
            "job_card_hours_mismatch_jobs": int((~np.isclose(compared.job_hours, compared.card_hours,
                                                              rtol=1e-9, atol=1e-6, equal_nan=False)).sum()),
            "measured_gpu_hours": measured_total(jobs.gpu_hours),
            "allocated_gpu_hours_comparison": measured_total(jobs.gpu_hours_alloc),
            "allocated_gpu_hours_known_subtotal": float(jobs.gpu_hours_alloc.sum()),
            "missing_allocated_gpu_hours_jobs": int(jobs.gpu_hours_alloc.isna().sum()),
            "missing_measured_gpu_hours_jobs": int(jobs.gpu_hours.isna().sum()),
            "invalid_card_hours_rows": int((gpus.gpu_hours.isna() | ~np.isfinite(gpus.gpu_hours) |
                                              (gpus.gpu_hours < 0)).sum()),
            "card_duration_over_final_walltime_by_over_1s_rows": int(((duration.totalexecutiontime_sec - duration.walltime_sec) > 1).sum()),
            "card_duration_comparison_tolerance_seconds": 1,
            "jobs_with_measured_allocated_difference_over_10pct": int(((jobs.gpu_hours_ratio - 1).abs() > .1).sum()),
            "requeued_jobs": int((jobs.attempts > 1).sum()),
            "jobs_hitting_node_failure": int(jobs.hit_node_failure.sum()),
            "final_node_fail_jobs": int(jobs.state_name.eq("NODE_FAIL").sum()),
            "timestamp_basis": "seconds from arbitrary origin; no calendar conversion applied",
            **weighted_utilization(jobs)}


def candidate_diagnostics(data):
    frame = findings_table(data.findings)
    total = measured_total(data.jobs.gpu_hours)
    rows, sets = [], {}
    for rule in RULES:
        selected = frame[frame.detector_id.eq("rules::" + rule) & frame.synthetic.eq(False)]
        ids = set(int(x) for x in selected.job_id.dropna())
        sets[rule] = ids
        jobs = data.jobs[data.jobs.id_job.isin(ids)]
        hours = measured_total(jobs.gpu_hours)
        rows.append({"rule": rule, "findings": len(selected), "matched_jobs": len(jobs),
                     "cohort_gpu_hours": hours, "cohort_share_percent": percent(hours, total),
                     "active_findings": int(selected.is_active.eq(True).sum())})
    overlap = [{"rule_a": a, "rule_b": b, "shared_jobs": len(sets[a] & sets[b])}
               for a, b in combinations(RULES, 2)]
    return pd.DataFrame(rows), pd.DataFrame(overlap)
