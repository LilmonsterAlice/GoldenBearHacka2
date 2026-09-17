from types import SimpleNamespace
import math

import pandas as pd
import pytest

from analytics.deduplication import PrimaryLedger
from analytics.opportunities.gpu_not_needed import gpu_not_needed_candidates, build_gpu_not_needed_opportunity
from analytics.scenarios import CpuPlacementPolicy
from analytics.pricing import Pricing


def data():
    jobs = pd.DataFrame({"id_job": [1, 2, 3], "state_name": ["COMPLETED", "COMPLETED", "FAILED"],
                         "sm_util_avg": [0.] * 3, "sm_util_max": [0.] * 3,
                         "gpu_hours": [10.] * 3, "gpu_hours_alloc": [10.] * 3,
                         "walltime_sec": [36000.] * 3, "gpu_count": [1] * 3,
                         "attempts": [1] * 3, "primary_node": ["node"] * 3,
                         "max_gpu_mem_used": [0., 1000., 0.]})
    cards = pd.DataFrame({"id_job": [1, 2, 3], "gpu_hours": [10.] * 3,
                          "smutilization_pct_max": [0.] * 3})
    findings = [{"id": str(job), "detectorId": "rules::gpu-not-needed",
                 "metadata": {"job_id": job, "synthetic": False, "impact_gpu_hours": 9999}}
                for job in [1, 2, 3]]
    return SimpleNamespace(jobs=jobs, gpus=cards, findings=findings)


def test_success_is_required_not_just_zero_compute():
    assert gpu_not_needed_candidates(data().jobs).id_job.tolist() == [1, 2]


def test_primary_overlap_is_excluded_and_gpu_memory_is_flagged():
    ledger = PrimaryLedger()
    ledger.assign(1, "idle-interactive", 10., {"low": 0., "point": 3., "high": 6.})
    opportunity, jobs, details = build_gpu_not_needed_opportunity(data(), Pricing(2, "test"), 30., ledger=ledger)
    assert opportunity["jobs"] == [{"job_id": 2}]
    assert jobs[0]["gpu_hours"] == 10
    assert opportunity["gpu_hours_high"] == 10  # no adding finding impact
    assert opportunity["savings_usd_high"] == 20
    assert details["net_benefit_usd"] is None
    assert details["candidate_jobs_with_nonzero_gpu_memory"] == 1
    assert details["exclusions"] == [{"job_id": 1, "reasons": ["already_primary:idle-interactive"]}]
    assert len(ledger.records()) == 2


def test_incremental_cpu_cost_can_make_net_benefit_negative():
    opportunity, _, details = build_gpu_not_needed_opportunity(data(), Pricing(2, "test"), 30.,
                                                              CpuPlacementPolicy(.5, 3., 2.))
    assert details["incremental_cpu_cost_usd_high_adoption"] == 120
    assert details["net_benefit_usd"] == {"low": 0., "point": -40., "high_adoption": -80.}
    assert opportunity["savings_usd_high"] == 40  # gross value stays distinct
    assert opportunity["confidence"] is None
    assert opportunity["cost_if_wrong"]["usd_high"] is None


def test_missing_card_evidence_or_requeues_are_excluded():
    sample = data()
    sample.gpus = sample.gpus[sample.gpus.id_job.ne(1)]
    sample.jobs.loc[1, "attempts"] = 2
    opportunity, _, details = build_gpu_not_needed_opportunity(sample, Pricing(), 30.)
    assert opportunity["job_count"] == 0
    assert details["modeled_job_count"] == 0
    assert len(details["exclusions"]) == 2


@pytest.mark.parametrize("change", [{"point_realization": math.nan}, {"point_realization": 2},
                                    {"incremental_cpu_cost_per_job_hour": -1},
                                    {"cpu_runtime_multiplier": 0}])
def test_invalid_cpu_assumptions_rejected(change):
    with pytest.raises(ValueError):
        CpuPlacementPolicy(**change)
