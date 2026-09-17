"""Identify completed jobs matching the official GPU-not-needed rule."""

import pandas as pd


def find_gpu_not_needed_candidates(jobs: pd.DataFrame) -> pd.DataFrame:
    required = {"state_name", "gpu_hours", "sm_util_avg", "sm_util_max"}
    missing = required - set(jobs.columns)
    if missing:
        raise ValueError("GPU-not-needed detection is missing columns: " + ", ".join(sorted(missing)))
    hours = pd.to_numeric(jobs["gpu_hours"], errors="raise")
    avg = pd.to_numeric(jobs["sm_util_avg"], errors="raise")
    peak = pd.to_numeric(jobs["sm_util_max"], errors="raise")
    return jobs.loc[
        jobs["state_name"].eq("COMPLETED") & hours.gt(1)
        & avg.eq(0) & peak.eq(0)
    ].copy()
