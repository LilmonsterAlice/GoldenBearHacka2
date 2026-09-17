PRICE_PER_GPU_HOUR = 2.50
PRICE_BOOK_VERSION = "2026-Q3"


def gpu_hours_to_usd(gpu_hours: float) -> float:
    """Convert GPU-hours to estimated USD cost."""
    return gpu_hours * PRICE_PER_GPU_HOUR