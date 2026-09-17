"""Identify cancelled idle jobs matching the official slow-cancel rule."""

import math
import pandas as pd

MIN_WALLTIME_HOURS = 4.0
MAX_SM_UTIL_AVG = 5.0


def find_slow_cancel_candidates(
    jobs: pd.DataFrame, *, min_walltime_hours: float = MIN_WALLTIME_HOURS,
    max_sm_util_avg: float = MAX_SM_UTIL_AVG,
) -> pd.DataFrame:
    required = {"state_name", "walltime_sec", "sm_util_avg"}
    missing = required - set(jobs.columns)
    if missing:
        raise ValueError("Slow-cancel detection is missing columns: " + ", ".join(sorted(missing)))
    if not math.isfinite(min_walltime_hours) or min_walltime_hours < 0:
        raise ValueError("Minimum walltime must be finite and nonnegative")
    if not math.isfinite(max_sm_util_avg) or not 0 <= max_sm_util_avg <= 100:
        raise ValueError("Utilization threshold must be from 0 to 100")
    cancelled = jobs.loc[jobs["state_name"].eq("CANCELLED")].copy()
    cancelled["walltime_hours"] = pd.to_numeric(cancelled["walltime_sec"], errors="raise") / 3600
    utilization = pd.to_numeric(cancelled["sm_util_avg"], errors="raise")
    return cancelled.loc[
        cancelled["walltime_hours"].gt(min_walltime_hours)
        & cancelled["walltime_hours"].map(lambda value: pd.notna(value) and math.isfinite(float(value)))
        & utilization.ge(0) & utilization.lt(max_sm_util_avg)
    ].copy()
