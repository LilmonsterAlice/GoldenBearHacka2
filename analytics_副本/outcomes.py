import pandas as pd

from analytics.pricing import gpu_hours_to_usd


def calculate_outcomes(jobs: pd.DataFrame) -> list[dict]:
    """
    Calculate GPU usage and cost by final job outcome.

    This is descriptive only:
    FAILED, CANCELLED, or TIMEOUT jobs are not automatically
    considered recoverable waste.
    """

    total_gpu_hours = jobs["gpu_hours"].sum()

    grouped = (
        jobs.groupby("state_name", dropna=False)
        .agg(
            jobs=("id_job", "count"),
            gpu_hours=("gpu_hours", "sum"),
        )
        .reset_index()
    )

    grouped["cost_usd"] = grouped["gpu_hours"].apply(
        gpu_hours_to_usd
    )

    grouped["capacity_percent"] = (
        grouped["gpu_hours"] / total_gpu_hours * 100
    )

    outcomes = []

    for _, row in grouped.iterrows():
        outcomes.append(
            {
                "name": str(row["state_name"]),
                "jobs": int(row["jobs"]),
                "gpu_hours": float(row["gpu_hours"]),
                "cost_usd": float(row["cost_usd"]),
                "capacity_percent": float(row["capacity_percent"]),
            }
        )

    return outcomes