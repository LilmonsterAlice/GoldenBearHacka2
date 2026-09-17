import pandas as pd

from analytics.opportunities.gpu_not_needed import find_gpu_not_needed_candidates
from analytics.opportunities.idle_interactive import find_idle_interactive_jobs
from analytics.opportunities.slow_cancel import find_slow_cancel_candidates


def test_idle_rule_requires_long_interactive_and_measured_low_utilization():
    jobs = pd.DataFrame({
        "job_type": ["LLSUB:INTERACTIVE"] * 5 + ["BATCH"],
        "walltime_sec": [5 * 3600, 4 * 3600, 6 * 3600, 6 * 3600, None, 6 * 3600],
        "sm_util_avg": [4.9, 0, 5, None, 0, 0],
    })
    original = jobs.copy(deep=True)
    selected = find_idle_interactive_jobs(jobs)
    assert list(selected.index) == [0]
    assert selected.iloc[0]["walltime_hours"] == 5
    pd.testing.assert_frame_equal(jobs, original)


def test_idle_rule_threshold_can_be_refined():
    jobs = pd.DataFrame({"job_type": ["CUSTOM"], "walltime_sec": [2 * 3600], "sm_util_avg": [8]})
    selected = find_idle_interactive_jobs(jobs, interactive_job_type="CUSTOM", max_sm_util_avg=10, min_walltime_hours=1)
    assert len(selected) == 1


def test_gpu_not_needed_requires_success_and_zero_peak():
    jobs = pd.DataFrame({
        "state_name": ["COMPLETED", "FAILED", "COMPLETED", "COMPLETED", "COMPLETED"],
        "gpu_hours": [2, 2, 2, 1, 2],
        "sm_util_avg": [0, 0, 0, 0, None],
        "sm_util_max": [0, 0, 1, 0, 0],
    })
    original = jobs.copy(deep=True)
    assert list(find_gpu_not_needed_candidates(jobs).index) == [0]
    pd.testing.assert_frame_equal(jobs, original)


def test_slow_cancel_requires_long_idle_cancelled_job():
    jobs = pd.DataFrame({
        "state_name": ["CANCELLED", "CANCELLED", "CANCELLED", "COMPLETED", "CANCELLED"],
        "walltime_sec": [5 * 3600, 4 * 3600, 6 * 3600, 6 * 3600, 6 * 3600],
        "sm_util_avg": [4, 0, 5, 0, None],
    })
    original = jobs.copy(deep=True)
    selected = find_slow_cancel_candidates(jobs)
    assert list(selected.index) == [0]
    assert selected.iloc[0]["walltime_hours"] == 5
    pd.testing.assert_frame_equal(jobs, original)
