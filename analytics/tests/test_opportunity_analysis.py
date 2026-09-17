import pandas as pd
import pytest

from analytics.opportunity_analysis import build_opportunities


def finding(job_id, detector, impact):
    return {
        "id": f"finding-{job_id}-{detector}",
        "detectorId": detector,
        "metadata": {"job_id": job_id, "synthetic": False,
                     "impact_kind": "unused_capacity", "impact_gpu_hours": impact},
    }


def test_overlap_is_assigned_once_and_keeps_supporting_findings():
    jobs = pd.DataFrame({
        "id_job": [1, 2, 3], "gpu_hours": [10.0, 8.0, 20.0],
        "gpu_count": [1, 1, 2], "walltime_sec": [36000, 28800, 36000],
        "job_type": ["LLSUB:INTERACTIVE", "OTHER", "OTHER"],
        "state_name": ["COMPLETED", "CANCELLED", "COMPLETED"],
        "sm_util_avg": [0.0, 2.0, 25.0], "sm_util_max": [0.0, 3.0, 50.0],
        "primary_node": ["n1", "n2", "n3"],
    })
    gpus = pd.DataFrame({
        "id_job": [1, 2, 3, 3], "smutilization_pct_avg": [0, 2, 0, 50],
        "gpu_hours": [10, 8, 10, 10],
    })
    findings = [
        finding(1, "rules::idle-interactive-session", 10),
        finding(1, "rules::gpu-not-needed", 10),
        finding(2, "rules::slow-cancel-of-idle-job", 8),
        finding(3, "rules::gpu-imbalance", 10),
    ]
    records, evidence, meta = build_opportunities(
        jobs, gpus, findings, price_per_gpu_hour=2.5, total_gpu_hours=38,
    )
    assert [record["job_count"] for record in records] == [1, 0, 1, 1]
    assert meta["audit"]["gpu-not-needed"]["overlap_jobs_excluded"] == 1
    assert sum(item["candidate_gpu_hours"] for item in meta["audit"].values()) == 28
    assert len(evidence) == 3
    assert len(evidence[0]["findings"]) == 2
    assert records[0]["savings_usd_high"] == 6.25
    assert records[0]["cost_if_wrong"]["usd_high"] is None


def test_missing_or_unverified_evidence_cannot_create_savings():
    jobs = pd.DataFrame({
        "id_job": [1], "gpu_hours": [10.0], "gpu_count": [1],
        "walltime_sec": [36000], "job_type": ["LLSUB:INTERACTIVE"],
        "state_name": ["CANCELLED"], "sm_util_avg": [None],
        "sm_util_max": [None], "primary_node": ["n1"],
    })
    gpus = pd.DataFrame({"id_job": [1], "smutilization_pct_avg": [None], "gpu_hours": [10]})
    records, evidence, meta = build_opportunities(
        jobs, gpus, [finding(1, "rules::idle-interactive-session", 10)],
        price_per_gpu_hour=2.5, total_gpu_hours=10,
    )
    assert records[0]["job_count"] == 0
    assert evidence == []
    assert meta["audit"]["idle-interactive"]["failed_telemetry_check"] == 1
