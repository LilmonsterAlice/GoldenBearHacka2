import pytest

from backend.services.context_builder import route_opportunity_id


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("Why are idle interactive sessions recoverable?", "idle-interactive"),
        ("Which successful workloads do not need a GPU?", "gpu-not-needed"),
        ("Why is slow cancellation expensive?", "slow-cancel"),
        ("Show the per-card GPU imbalance", "gpu-imbalance"),
        ("What is the capital of France?", None),
        ("Compare idle interactive sessions with GPU imbalance", None),
    ],
)
def test_route_opportunity_id(question, expected):
    assert route_opportunity_id(question) == expected
