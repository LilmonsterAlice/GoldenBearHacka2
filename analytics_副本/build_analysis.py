import json
from pathlib import Path

from analytics.load_data import load_jobs
from analytics.outcomes import calculate_outcomes
from analytics.pricing import (
    PRICE_PER_GPU_HOUR,
    PRICE_BOOK_VERSION,
    gpu_hours_to_usd,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = PROJECT_ROOT / "generated" / "analysis.json"


def build_summary(jobs):
    total_gpu_hours = float(jobs["gpu_hours"].sum())
    total_cost_usd = gpu_hours_to_usd(total_gpu_hours)

    outcomes = calculate_outcomes(jobs)

    completed = next(
        outcome
        for outcome in outcomes
        if outcome["name"] == "COMPLETED"
    )

    return {
        "total_gpu_hours": total_gpu_hours,
        "total_cost_usd": total_cost_usd,
        "price_per_gpu_hour": PRICE_PER_GPU_HOUR,
        "price_book_version": PRICE_BOOK_VERSION,
        "completed_percent": completed["capacity_percent"],
        "outcomes": outcomes,
        "scope_caveat": "Four-month workload sample",
    }


def build_analysis():
    jobs = load_jobs()

    analysis = {
        "summary": build_summary(jobs),
        "opportunities": [],
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_PATH, "w") as f:
        json.dump(analysis, f, indent=2)

    return analysis


if __name__ == "__main__":
    build_analysis()
    print(f"Analysis written to: {OUTPUT_PATH}")