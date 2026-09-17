import math

import pandas as pd
import pytest

from analytics.outcomes import build_summary, weighted_utilization
from analytics.pricing import Pricing
from analytics.opportunities.idle_interactive import idle_candidates
from analytics.exploration import findings_table


def jobs():
    return pd.DataFrame({"id_job": [1, 2, 3], "gpu_hours": [10., 80., 10.],
                         "state_name": ["COMPLETED", "CANCELLED", "UNDECODED_11"],
                         "sm_util_avg": [100., 0., None]})


def test_outcome_accounting_does_not_call_cancelled_waste():
    summary = build_summary(jobs(), Pricing(2, "test-rate"))
    assert summary["total_cost_usd"] == 200
    assert summary["completed_percent"] == 10
    assert sum(x["gpu_hours"] for x in summary["outcomes"]) == 100
    assert sum(x["jobs"] for x in summary["outcomes"]) == 3
    assert {x["name"] for x in summary["outcomes"]} == {"COMPLETED", "CANCELLED", "UNDECODED_11"}


def test_missing_consumption_is_unknown_not_zero():
    frame = jobs()
    frame.loc[1, "gpu_hours"] = math.nan
    summary = build_summary(frame)
    assert summary["total_gpu_hours"] is None
    cancelled = next(x for x in summary["outcomes"] if x["name"] == "CANCELLED")
    assert cancelled["gpu_hours"] is None and cancelled["cost_usd"] is None


def test_weighting_and_missing_coverage():
    result = weighted_utilization(jobs())
    assert result["sm_util_gpu_hour_weighted"] == pytest.approx(1000 / 90)
    assert result["coverage_percent"] == 90


@pytest.mark.parametrize("value", [-1, math.inf])
def test_invalid_consumption_rejected(value):
    frame = jobs()
    frame.loc[0, "gpu_hours"] = value
    with pytest.raises(ValueError):
        build_summary(frame)


def test_duplicate_job_rejected():
    frame = jobs()
    frame.loc[1, "id_job"] = 1
    with pytest.raises(ValueError):
        build_summary(frame)


def test_idle_thresholds_and_unknowns():
    frame = pd.DataFrame({"id_job": range(6), "gpu_hours": [8.] * 6,
                          "job_type": ["LLSUB:INTERACTIVE"] * 5 + ["OTHER"],
                          "walltime_sec": [5*3600, 4*3600, 5*3600, None, 5*3600, 5*3600],
                          "sm_util_avg": [0., 0., 5., 0., None, 0.]})
    assert idle_candidates(frame).id_job.tolist() == [0]


def test_finding_ids_do_not_lose_integer_precision():
    large = 2**53 + 1
    frame = findings_table([{"id": "a", "metadata": {"job_id": large}}, {"id": "b"}])
    assert int(frame.loc[0, "job_id"]) == large
    assert pd.isna(frame.loc[1, "job_id"])
