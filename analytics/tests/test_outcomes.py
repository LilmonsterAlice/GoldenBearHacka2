import pytest

from analytics.build_analysis import build_summary
from analytics.outcomes import calculate_outcomes


def test_summary_and_outcomes_are_gpu_hour_weighted(jobs):
    summary = build_summary(jobs)
    assert summary["total_gpu_hours"] == 10
    assert summary["total_cost_usd"] == 25
    assert summary["completed_percent"] == 80
    completed = next(outcome for outcome in summary["outcomes"] if outcome["name"] == "COMPLETED")
    assert completed["capacity_percent"] == 80  # Not the row average of 50%.
    assert sum(outcome["cost_usd"] for outcome in summary["outcomes"]) == 25


def test_no_completed_jobs_is_a_valid_summary(jobs):
    assert build_summary(jobs.iloc[1:])["completed_percent"] == 0


def test_empty_sample_and_zero_hours_have_unknown_percentages(jobs):
    summary = build_summary(jobs.iloc[:0])
    assert summary["total_gpu_hours"] == 0
    assert summary["outcomes"] == []
    assert summary["completed_percent"] is None
    zero = build_summary(jobs.assign(gpu_hours=0))
    assert zero["completed_percent"] is None
    assert all(outcome["capacity_percent"] is None for outcome in zero["outcomes"])


@pytest.mark.parametrize("bad", [None, float("nan"), float("inf"), -1])
def test_invalid_gpu_hours_are_not_silently_zero(jobs, bad):
    jobs.loc[0, "gpu_hours"] = bad
    with pytest.raises(ValueError):
        build_summary(jobs)


def test_duplicate_job_rows_require_deliberate_analytics_handling(jobs):
    jobs.loc[1, "id_job"] = 1
    with pytest.raises(ValueError, match="deduplicate attempts"):
        calculate_outcomes(jobs)


def test_custom_price_has_explicit_provenance(jobs):
    summary = build_summary(jobs, price_per_gpu_hour=3)
    assert summary["total_cost_usd"] == 30
    assert summary["price_per_gpu_hour"] == 3
    assert summary["price_book_version"] == "custom-rate"


def test_missing_columns_report_prepared_schema(jobs):
    with pytest.raises(ValueError, match="gpu_hours"):
        build_summary(jobs.drop(columns=["gpu_hours"]))
