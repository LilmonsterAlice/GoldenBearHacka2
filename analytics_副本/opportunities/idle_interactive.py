import pandas as pd


MAX_SM_UTIL_AVG = 5.0
MIN_WALLTIME_HOURS = 1.0


def find_idle_interactive_jobs(jobs: pd.DataFrame) -> pd.DataFrame:
    """
    Identify long-running interactive jobs with very low average GPU utilization.

    This identifies candidate optimization opportunities only.
    The observed GPU-hours are not assumed to be fully recoverable savings.
    """

    interactive = jobs[
        jobs["job_type"] == "LLSUB:INTERACTIVE"
    ].copy()

    interactive["walltime_hours"] = (
        interactive["walltime_sec"] / 3600
    )

    idle_interactive = interactive[
        (interactive["sm_util_avg"] <= MAX_SM_UTIL_AVG)
        & (interactive["walltime_hours"] >= MIN_WALLTIME_HOURS)
    ].copy()

    return idle_interactive