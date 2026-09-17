"""GPU-hour-weighted baseline. Preserve unknown outcomes and measurements."""

import numpy as np
import pandas as pd

from analytics.pricing import Pricing


def validate_jobs(jobs):
    required = {"id_job", "gpu_hours", "state_name"}
    if not required.issubset(jobs.columns):
        raise ValueError(f"Missing job columns: {sorted(required - set(jobs.columns))}")
    if jobs.id_job.isna().any() or jobs.id_job.duplicated().any():
        raise ValueError("Job IDs must be present and unique")
    known = jobs.gpu_hours.dropna()
    if not np.isfinite(known).all() or (known < 0).any():
        raise ValueError("Measured GPU-hours must be finite and nonnegative")


def measured_total(hours):
    # An incomplete cohort must not silently become an apparently complete sum.
    return None if hours.isna().any() else float(hours.sum())


def percent(value, total):
    return None if value is None or total is None or total <= 0 else 100 * value / total


def build_summary(jobs, pricing=Pricing()):
    validate_jobs(jobs)
    total = measured_total(jobs.gpu_hours)
    outcomes = []
    for state, cohort in jobs.groupby("state_name", dropna=False, sort=True):
        hours = measured_total(cohort.gpu_hours)
        outcomes.append({"name": "UNKNOWN" if pd.isna(state) else str(state),
                         "jobs": len(cohort), "gpu_hours": hours,
                         "cost_usd": pricing.cost(hours), "capacity_percent": percent(hours, total)})
    completed = next((x["gpu_hours"] for x in outcomes if x["name"] == "COMPLETED"), 0.0)
    return {"total_gpu_hours": total, "total_cost_usd": pricing.cost(total),
            "price_per_gpu_hour": pricing.rate, "price_book_version": pricing.version,
            "completed_percent": percent(completed, total), "outcomes": outcomes,
            "scope_caveat": "Four-month workload sample; percentages are shares of sampled measured GPU-hours, not fleet utilization. USD is scenario resource value, not verified billing or cash savings."}


def weighted_utilization(jobs):
    """Weight only observed SM values and return their GPU-hour coverage."""
    valid = jobs.sm_util_avg.notna() & jobs.gpu_hours.notna()
    hours = float(jobs.loc[valid, "gpu_hours"].sum())
    total = measured_total(jobs.gpu_hours)
    return {"sm_util_gpu_hour_weighted": float((jobs.loc[valid, "sm_util_avg"] *
            jobs.loc[valid, "gpu_hours"]).sum() / hours) if hours > 0 else None,
            "observed_gpu_hours": hours, "coverage_percent": percent(hours, total)}
