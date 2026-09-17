import pandas as pd

from analytics.opportunities.idle_interactive import find_idle_interactive_jobs


def test_original_idle_candidate_thresholds_exclude_unknown_values():
    jobs = pd.DataFrame({
        "job_type": ["LLSUB:INTERACTIVE"] * 5 + ["BATCH"],
        "walltime_sec": [3600, 7200, 3599, 7200, None, 7200],
        "sm_util_avg": [5, 6, 0, None, 0, 0],
    })
    original = jobs.copy(deep=True)
    selected = find_idle_interactive_jobs(jobs)
    assert list(selected.index) == [0]
    assert selected.iloc[0]["walltime_hours"] == 1
    pd.testing.assert_frame_equal(jobs, original)


def test_person1_can_refine_thresholds_and_job_type():
    jobs = pd.DataFrame({"job_type": ["CUSTOM"], "walltime_sec": [1800], "sm_util_avg": [8]})
    selected = find_idle_interactive_jobs(jobs, interactive_job_type="CUSTOM", max_sm_util_avg=10, min_walltime_hours=0.5)
    assert len(selected) == 1
