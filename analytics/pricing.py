"""Explicit scenario pricing; this is not a verified cloud bill."""

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class Pricing:
    rate: float = 2.5
    version: str = "cutscope-assumption-v1"

    def __post_init__(self):
        if not math.isfinite(self.rate) or self.rate < 0:
            raise ValueError("Price must be finite and nonnegative")
        if not self.version.strip():
            raise ValueError("A pricing version is required")

    def cost(self, hours):
        return None if hours is None else float(hours) * self.rate
