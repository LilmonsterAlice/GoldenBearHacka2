from fastapi.testclient import TestClient

from backend.application import create_app
from backend.config import Settings, STAGE1_MOCK


def test_readiness_works_without_ai_and_preserves_five_product_endpoints():
    with TestClient(create_app(Settings("mock", STAGE1_MOCK))) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ready", "analysis_mode": "mock"}
        assert "/health" not in client.get("/openapi.json").json()["paths"]
        assert len(client.get("/openapi.json").json()["paths"]) == 5


def test_ai_import_failure_does_not_make_backend_unready():
    settings = Settings("mock", STAGE1_MOCK, chat_service="missing_person4_service:answer_chat")
    with TestClient(create_app(settings)) as client:
        assert client.get("/health").status_code == 200
        assert client.post("/api/chat", json={"question": "Explain"}).json()["answer"].startswith("cannot_determine")
