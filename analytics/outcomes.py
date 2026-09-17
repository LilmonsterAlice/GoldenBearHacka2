"""Descriptive GPU-hour-weighted outcomes, not recoverable-waste estimates."""

import math

import pandas as pd

from analytics.pricing import PRICE_PER_GPU_HOUR, gpu_hours_to_usd, validate_price


def validate_summary_jobs(jobs: pd.DataFrame) -> pd.DataFrame:
    required = {"id_job", "state_name", "gpu_hours"}
    missing = required - set(jobs.columns)
    if missing:
        raise ValueError(
            "Jobs table is missing columns: " + ", ".join(sorted(missing))
            + ". This module expects the prepared job-level table used by Person 1; "
            "finish official preparation or adapt analytics/load_data.py for your notebook schema."
        )
    result = jobs.copy()
    if result["id_job"].isna().any() or result["id_job"].duplicated().any():
        raise ValueError("Prepared jobs must have nonmissing unique id_job values; do not silently deduplicate attempts")
    if not result["state_name"].map(lambda value: isinstance(value, str) and bool(value.strip())).all():
        raise ValueError("state_name must contain nonmissing outcome names")
    result["gpu_hours"] = pd.to_numeric(result["gpu_hours"], errors="raise")
    if not result["gpu_hours"].map(lambda value: pd.notna(value) and math.isfinite(float(value)) and value >= 0).all():
        raise ValueError("gpu_hours must be finite, nonnegative, and nonmissing; missing measurements are not zero")
    if not math.isfinite(float(result["gpu_hours"].sum())):
        raise ValueError("Total GPU-hours exceeds finite numeric range")
    return result


def calculate_outcomes(jobs: pd.DataFrame, price_per_gpu_hour: float = PRICE_PER_GPU_HOUR) -> list[dict]:
    """FAILED/CANCELLED/TIMEOUT describe outcomes; they are not automatic waste."""
    jobs = validate_summary_jobs(jobs)
    price = validate_price(price_per_gpu_hour)
    total_gpu_hours = float(jobs["gpu_hours"].sum())
    grouped = jobs.groupby("state_name", sort=True).agg(jobs=("id_job", "size"), gpu_hours=("gpu_hours", "sum"))
    return [
        {
            "name": state,
            "jobs": int(row["jobs"]),
            "gpu_hours": float(row["gpu_hours"]),
            "cost_usd": gpu_hours_to_usd(row["gpu_hours"], price),
            "capacity_percent": float(row["gpu_hours"]) / total_gpu_hours * 100 if total_gpu_hours > 0 else None,
        }
        for state, row in grouped.iterrows()
    ]
