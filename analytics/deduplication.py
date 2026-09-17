"""Primary ownership for modeled allocation windows; no finding-impact sums."""

import math


class PrimaryLedger:
    """Conservatively reserve the whole job for one primary opportunity.

    Until attempt/time-resolved telemetry is available, disjoint sub-job windows
    are not inferred. A future opportunity on this job must remain supporting
    evidence or go through an explicitly reviewed interval-allocation method.
    """

    def __init__(self):
        self.rows = {}

    def assign(self, job_id, opportunity_id, budget_hours, scenarios, **details):
        if job_id in self.rows:
            raise ValueError(f"Duplicate primary allocation for job {job_id}")
        if not math.isfinite(budget_hours) or budget_hours < 0:
            raise ValueError("Primary allocation budget must be finite and nonnegative")
        low, point, high = (scenarios[key] for key in ("low", "point", "high"))
        if not all(math.isfinite(value) for value in (low, point, high)) or not 0 <= low <= point <= high <= budget_hours:
            raise ValueError("Scenario allocation must be ordered and within the job budget")
        self.rows[job_id] = {"job_id": int(job_id), "primary_opportunity_id": opportunity_id,
                             "budget_gpu_hours": float(budget_hours), "gpu_hours": scenarios, **details}

    def records(self):
        return [self.rows[key] for key in sorted(self.rows)]

    def owner(self, job_id):
        row = self.rows.get(job_id)
        return None if row is None else row["primary_opportunity_id"]
