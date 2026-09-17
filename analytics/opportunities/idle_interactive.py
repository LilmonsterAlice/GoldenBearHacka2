"""Identify interactive sessions matching the official idle-session rule."""

import math
import pandas as pd

MAX_SM_UTIL_AVG = 5.0
MIN_WALLTIME_HOURS = 4.0


def find_idle_interactive_jobs(
    jobs: pd.DataFrame, *, max_sm_util_avg: float = MAX_SM_UTIL_AVG,
    min_walltime_hours: float = MIN_WALLTIME_HOURS,
    interactive_job_type: str = "LLSUB:INTERACTIVE",
) -> pd.DataFrame:
    required = {"job_type", "walltime_sec", "sm_util_avg"}
    missing = required - set(jobs.columns)
    if missing:
        raise ValueError("Idle candidate detection is missing columns: " + ", ".join(sorted(missing)))
    if not math.isfinite(max_sm_util_avg) or not 0 <= max_sm_util_avg <= 100:
        raise ValueError("Utilization threshold must be from 0 to 100")
    if not math.isfinite(min_walltime_hours) or min_walltime_hours < 0:
        raise ValueError("Minimum walltime must be finite and nonnegative")
    interactive = jobs.loc[jobs["job_type"] == interactive_job_type].copy()
    interactive["walltime_hours"] = pd.to_numeric(interactive["walltime_sec"], errors="raise") / 3600
    utilization = pd.to_numeric(interactive["sm_util_avg"], errors="raise")
    return interactive.loc[
        utilization.ge(0) & utilization.lt(max_sm_util_avg)
        & interactive["walltime_hours"].gt(min_walltime_hours)
        & interactive["walltime_hours"].map(lambda value: pd.notna(value) and math.isfinite(float(value)))
    ].copy()
