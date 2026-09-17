import pytest
from fastapi.testclient import TestClient

from backend.config import Settings
from backend.main import create_app
from backend.services.chat_adapter import load_chat_service
from backend.services.llm import answer_chat


@pytest.fixture
def client(payload, write_snapshot):
    settings = Settings("mock", write_snapshot(payload))
    with TestClient(create_app(settings, chat_service=answer_chat)) as test_client:
        yield test_client


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("Why is idle interactive capacity recoverable?", "4–10 GPU-hours"),
        ("What could go wrong if we enforce an idle timeout?", "$0–$5"),
        ("What evidence supports this recommendation?", "only 1 stored finding"),
    ],
)
def test_idle_interactive_presets_are_grounded(client, question, expected):
    response = client.post(
        "/api/chat",
        json={"question": question, "opportunity_id": "idle-interactive"},
    )

    assert response.status_code == 200
    body = response.json()
    assert expected in body["answer"]
    assert body["confidence"] == 0.7
    assert body["finding_ids"] == ["synthetic-idle-123"]
    assert body["job_ids"] == [123]
    assert body["evidence"][0]["job_id"] == 123
    assert any("synthetic" in caveat.lower() for caveat in body["caveats"])


def test_idle_interactive_answer_does_not_claim_verified_savings(client):
    response = client.post(
        "/api/chat",
        json={
            "question": "Why is idle interactive capacity recoverable?",
            "opportunity_id": "idle-interactive",
        },
    )

    answer = response.json()["answer"]
    assert "not guaranteed savings" in answer
    assert "Low utilization alone is not proof of waste" in answer


def test_answer_chat_is_loadable_from_compose_configuration():
    assert load_chat_service("backend.services.llm:answer_chat") is answer_chat
