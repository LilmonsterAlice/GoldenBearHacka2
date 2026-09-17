import math

PRICE_PER_GPU_HOUR = 2.50
PRICE_BOOK_VERSION = "2026-Q3"


def validate_price(price: float) -> float:
    price = float(price)
    if not math.isfinite(price) or price < 0:
        raise ValueError("GPU-hour price must be finite and nonnegative")
    return price


def gpu_hours_to_usd(gpu_hours: float, price_per_gpu_hour: float = PRICE_PER_GPU_HOUR) -> float:
    """Person 1's original conversion; rate is explicit and configurable."""
    hours = float(gpu_hours)
    if not math.isfinite(hours) or hours < 0:
        raise ValueError("GPU-hours must be finite and nonnegative")
    result = hours * validate_price(price_per_gpu_hour)
    if not math.isfinite(result):
        raise ValueError("Cost exceeds finite numeric range")
    return result
