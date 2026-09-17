import math
from types import SimpleNamespace

import pandas as pd
import pytest

from analytics.deduplication import PrimaryLedger
from analytics.opportunities.idle_interactive import build_idle_opportunity
from analytics.pricing import Pricing
from analytics.scenarios import IdlePolicy, idle_hour_scenarios


def data():
    jobs = pd.DataFrame({"id_job": [1, 2, 3, 4], "job_type": ["LLSUB:INTERACTIVE"] * 4,
                         "walltime_sec": [10 * 3600.] * 4, "gpu_count": [2] * 4,
                         "gpu_hours": [20., 20., 20., 20.], "gpu_hours_alloc": [20.] * 4,
                         "sm_util_avg": [0., 0., 0., 0.], "sm_util_max": [0., 30., 0., 0.],
                         "attempts": [1, 1, 2, 1], "state_name": ["COMPLETED", "CANCELLED", "TIMEOUT", "FAILED"],
                         "primary_node": ["node"] * 4})
    cards = pd.DataFrame([{"id_job": job, "gpu_hours": 10., "smutilization_pct_max": 0.}
                          for job in [1, 2, 3, 4] for _ in range(2)])
    findings = [{"id": f"idle-{job}", "detectorId": "rules::idle-interactive-session",
                 "metadata": {"job_id": job, "synthetic": job == 4}} for job in [1, 2, 3, 4]]
    findings += [{"id": "other-1", "detectorId": "rules::gpu-not-needed",
                  "metadata": {"job_id": 1, "synthetic": False, "impact_gpu_hours": 999}}]
    return SimpleNamespace(jobs=jobs, gpus=cards, findings=findings)


def test_scenario_is_bounded_by_both_budgets_and_retains_grace():
    assert idle_hour_scenarios(18., 20., 2, IdlePolicy()) == {"low": 0., "point": 5., "high": 10.}
    assert idle_hour_scenarios(30., 20., 2, IdlePolicy())["high"] == 12.
    assert idle_hour_scenarios(5., 5., 2, IdlePolicy())["high"] == 0.


def test_evidence_selection_and_no_finding_impact_addition():
    opportunity, records, diagnostics = build_idle_opportunity(data(), Pricing(2, "test"), 80.)
    assert opportunity["job_count"] == 1
    assert opportunity["jobs"] == [{"job_id": 1}]
    assert opportunity["gpu_hours_low"] == 0
    assert opportunity["gpu_hours_high"] == 12
    assert opportunity["savings_usd_high"] == 24
    assert opportunity["capacity_percent_high"] == 15
    assert records[0]["state"] == "COMPLETED"  # outcome alone does not decide reclaim
    assert [f["id"] for f in records[0]["findings"]] == ["idle-1", "other-1"]
    assert diagnostics["scenarios_gpu_hours"]["point"] == 6
    assert {x["job_id"] for x in diagnostics["exclusions"]} == {2, 3, 4}
    assert opportunity["confidence"] is None
    assert opportunity["cost_if_wrong"]["usd_high"] is None
    assert opportunity["cost_if_wrong"]["reversible"] is False


def test_duplicate_findings_do_not_duplicate_allocation():
    sample = data()
    sample.findings.append({**sample.findings[0], "id": "second-idle-1"})
    result, records, details = build_idle_opportunity(sample, Pricing(), 80.)
    assert result["gpu_hours_high"] == 12
    assert len(records) == len(details["primary_ledger"]) == 1


def test_requeue_and_allocation_disagreement_are_excluded():
    sample = data()
    sample.jobs.loc[0, "gpu_hours"] = 50.
    result, _, diagnostics = build_idle_opportunity(sample, Pricing(), 110.)
    assert result["job_count"] == 0
    assert result["gpu_hours_high"] == 0
    assert "measured_allocated_hours_disagree" in diagnostics["exclusions"][0]["reasons"]


def test_card_peak_disagreement_is_excluded():
    sample = data()
    sample.gpus.loc[0, "smutilization_pct_max"] = 30.
    result, _, _ = build_idle_opportunity(sample, Pricing(), 80.)
    assert result["job_count"] == 0


def test_longer_retention_reduces_reclaim():
    high = build_idle_opportunity(data(), Pricing(), 80., IdlePolicy(8))[0]
    assert high["gpu_hours_high"] == 4


def test_whole_job_primary_ownership_prevents_future_overlap():
    ledger = PrimaryLedger()
    ledger.assign(1, "idle-interactive", 20., {"low": 0., "point": 6., "high": 12.})
    with pytest.raises(ValueError, match="Duplicate primary"):
        ledger.assign(1, "gpu-not-needed", 20., {"low": 0., "point": 5., "high": 10.})


@pytest.mark.parametrize("scenarios", [
    {"low": 0., "point": 21., "high": 21.},
    {"low": 0., "point": 10., "high": 5.},
    {"low": 0., "point": 5., "high": math.inf},
])
def test_primary_allocation_cannot_exceed_budget(scenarios):
    with pytest.raises(ValueError):
        PrimaryLedger().assign(1, "idle-interactive", 20., scenarios)


@pytest.mark.parametrize("policy", [{"retained_hours": 0}, {"point_realization": 1.1},
                                  {"point_realization": math.nan}, {"max_hours_ratio_difference": .5}])
def test_invalid_policy_rejected(policy):
    with pytest.raises(ValueError):
        IdlePolicy(**policy)
