"""Transparent policy assumptions, not statistical confidence intervals."""

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class IdlePolicy:
    retained_hours: float = 4.0
    point_realization: float = 0.5
    max_hours_ratio_difference: float = 0.1

    def __post_init__(self):
        if not math.isfinite(self.retained_hours) or self.retained_hours < 4:
            raise ValueError("Retained hours must be finite and at least the four-hour detector threshold")
        if not math.isfinite(self.point_realization) or not 0 <= self.point_realization <= 1:
            raise ValueError("Point realization must be between zero and one")
        if not math.isfinite(self.max_hours_ratio_difference) or not 0 <= self.max_hours_ratio_difference <= .1:
            raise ValueError("Hour discrepancy tolerance must be between zero and 10%")


def idle_hour_scenarios(measured_hours, allocated_hours, gpu_count, policy):
    """Cap the model to both measured and final-walltime allocation budgets."""
    values = (measured_hours, allocated_hours, gpu_count)
    if not all(math.isfinite(float(x)) for x in values) or min(values) < 0 or gpu_count <= 0:
        raise ValueError("Scenario requires valid consumption and positive GPU count")
    high = max(0., min(float(measured_hours), float(allocated_hours)) - gpu_count * policy.retained_hours)
    return {"low": 0., "point": high * policy.point_realization, "high": high}
