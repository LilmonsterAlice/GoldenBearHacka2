import asyncio
from copy import deepcopy
from dataclasses import replace
import sys
from types import ModuleType

import pytest
from fastapi.testclient import TestClient

from backend.config import Settings
from backend.main import create_app
from backend.models import ChatResponse
from backend.services.chat_adapter import load_chat_service


@pytest.fixture
def settings(payload, write_snapshot):
    return Settings("mock", write_snapshot(payload))


@pytest.fixture
def grounded_result(payload):
    opportunity = payload["opportunities"][0]
    finding = payload["jobs"][0]["findings"][0]
    return {
        "answer": opportunity["basis"],
        "evidence": [deepcopy(finding)],
        "risk": opportunity["cost_if_wrong"]["description"],
        "recommendation": opportunity["action"],
        "confidence": opportunity["confidence"],
        "finding_ids": [finding["finding_id"]],
        "job_ids": [123],
        "caveats": [],
    }


def assert_fallback(response):
    assert response.status_code == 200
    body = response.json()
    ChatResponse.model_validate(body)
    assert body["answer"].startswith("cannot_determine")
    assert body["confidence"] is None
    assert body["evidence"] == []
    assert body["finding_ids"] == []
    assert body["job_ids"] == []
    assert body["caveats"]
    return body


def assert_reads_work(client):
    for path in ("/api/summary", "/api/opportunities", "/api/opportunities/idle-interactive", "/api/jobs/123"):
        assert client.get(path).status_code == 200


def test_default_unavailable_service_preserves_dashboard(settings):
    with TestClient(create_app(settings)) as client:
        body = assert_fallback(client.post("/api/chat", json={
            "question": "Why is this recoverable?", "opportunity_id": "idle-interactive", "job_id": None,
        }))
        assert "No compatible AI service" in body["caveats"][0]
        assert_reads_work(client)


@pytest.mark.parametrize("question", [
    "Why is this recoverable?", "What is the cost if we are wrong?", "What evidence supports this?",
])
def test_stub_service_receives_authoritative_context_and_preserves_response(settings, grounded_result, payload, question):
    received = []

    async def service(*, question, context):
        received.append((question, context))
        assert context.summary.model_dump() == payload["summary"]
        assert context.opportunity == payload["opportunities"][0]
        assert context.job == payload["jobs"][0]
        assert context.analysis.get_job(124) == payload["jobs"][1]
        assert context.analysis_mode == "mock"
        # Mutating service-owned copies cannot change the source snapshot.
        context.job["cost_usd"] = 999
        context.analysis.get_job(123)["findings"].clear()
        return grounded_result

    with TestClient(create_app(settings, chat_service=service)) as client:
        response = client.post("/api/chat", json={
            "question": "  " + question + "  ", "opportunity_id": "idle-interactive", "job_id": 123,
        })
        assert response.status_code == 200
        body = response.json()
        for field, value in grounded_result.items():
            if field != "caveats":
                assert body[field] == value
        assert all(caveat in body["caveats"] for caveat in payload["opportunities"][0]["caveats"])
        assert payload["summary"]["scope_caveat"] in body["caveats"]
        assert received[0][0] == question
        assert client.get("/api/jobs/123").json()["cost_usd"] == payload["jobs"][0]["cost_usd"]


@pytest.mark.parametrize("selection", [{}, {"job_id": 123}, {"opportunity_id": "idle-interactive"}])
def test_valid_selection_variants(settings, grounded_result, selection):
    async def service(*, question, context):
        assert (context.job is not None) == ("job_id" in selection)
        assert (context.opportunity is not None) == ("opportunity_id" in selection)
        return ChatResponse.model_validate(grounded_result)

    with TestClient(create_app(settings, chat_service=service)) as client:
        assert client.post("/api/chat", json={"question": "Explain this", **selection}).status_code == 200


@pytest.mark.parametrize("body,status,code", [
    ({"question": "Explain", "opportunity_id": "unknown"}, 404, "OPPORTUNITY_NOT_FOUND"),
    ({"question": "Explain", "job_id": 999}, 404, "JOB_NOT_FOUND"),
    ({"question": ""}, 422, "VALIDATION_ERROR"),
    ({"question": "   "}, 422, "VALIDATION_ERROR"),
    ({"question": "a" * 4001}, 422, "VALIDATION_ERROR"),
    ({"question": 123}, 422, "VALIDATION_ERROR"),
    ({"job_id": 123}, 422, "VALIDATION_ERROR"),
    ({"question": "Explain", "job_id": "123"}, 422, "VALIDATION_ERROR"),
    ({"question": "Explain", "job_id": True}, 422, "VALIDATION_ERROR"),
    ({"question": "Explain", "raw_telemetry": {"cost_usd": 123456}}, 422, "VALIDATION_ERROR"),
])
def test_bad_requests_never_call_service(settings, body, status, code):
    async def service(**kwargs):
        pytest.fail("Invalid client input must not reach AI")

    with TestClient(create_app(settings, chat_service=service)) as client:
        response = client.post("/api/chat", json=body)
        assert response.status_code == status
        assert response.json()["error"]["code"] == code


def test_malformed_json_is_client_error(settings):
    with TestClient(create_app(settings)) as client:
        response = client.post("/api/chat", content="{broken", headers={"Content-Type": "application/json"})
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_unrelated_job_is_rejected(payload, write_snapshot):
    unrelated = deepcopy(payload["jobs"][1])
    unrelated["job_id"] = 125
    payload["jobs"].append(unrelated)

    async def service(**kwargs):
        pytest.fail("Mismatched job must not reach AI")

    with TestClient(create_app(Settings("mock", write_snapshot(payload)), chat_service=service)) as client:
        response = client.post("/api/chat", json={
            "question": "Explain", "opportunity_id": "idle-interactive", "job_id": 125,
        })
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "JOB_OPPORTUNITY_MISMATCH"


def test_timeout_cancels_service_and_leaves_reads_operational(settings):
    cancelled = []

    async def service(**kwargs):
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.append(True)

    with TestClient(create_app(replace(settings, chat_timeout_seconds=0.01), chat_service=service)) as client:
        response = client.post("/api/chat", json={"question": "Explain"})
        body = assert_fallback(response)
        assert "timed out" in body["caveats"][0]
        assert cancelled == [True]
        assert_reads_work(client)


def test_service_exception_is_sanitized(settings):
    async def service(**kwargs):
        raise RuntimeError("private-key-and-upstream-payload")

    with TestClient(create_app(settings, chat_service=service)) as client:
        response = client.post("/api/chat", json={"question": "Explain"})
        assert_fallback(response)
        assert "private-key" not in response.text
        assert_reads_work(client)


@pytest.mark.parametrize("change", ["missing_field", "confidence", "unknown_job", "nonfinite_evidence", "unserializable_evidence", "constructed_model"])
def test_invalid_service_result_is_not_exposed(settings, grounded_result, change):
    async def service(**kwargs):
        result = deepcopy(grounded_result)
        if change == "missing_field":
            del result["caveats"]
        elif change == "confidence":
            result["confidence"] = 2
        elif change == "unknown_job":
            result["job_ids"] = [999]
        elif change == "nonfinite_evidence":
            result["evidence"] = [{"value": float("nan")}]
        elif change == "unserializable_evidence":
            result["evidence"] = [{"value": object()}]
        else:
            result["confidence"] = 2
            return ChatResponse.model_construct(**result)
        return result

    with TestClient(create_app(settings, chat_service=service)) as client:
        assert_fallback(client.post("/api/chat", json={"question": "Explain", "job_id": 123}))
        assert_reads_work(client)


def test_service_cannot_cite_job_outside_selected_scope(settings, grounded_result):
    async def service(**kwargs):
        return {**grounded_result, "job_ids": [124]}

    with TestClient(create_app(settings, chat_service=service)) as client:
        assert_fallback(client.post("/api/chat", json={"question": "Explain", "job_id": 123}))


def test_imported_service_integration_uses_configured_export(settings, grounded_result, monkeypatch):
    module = ModuleType("test_person4_copilot")

    async def answer_chat(*, question, context):
        return grounded_result

    module.answer_chat = answer_chat
    monkeypatch.setitem(sys.modules, module.__name__, module)
    with TestClient(create_app(replace(settings, chat_service="test_person4_copilot:answer_chat"))) as client:
        response = client.post("/api/chat", json={"question": "Explain", "opportunity_id": "idle-interactive"})
        assert response.json()["answer"] == grounded_result["answer"]


@pytest.mark.parametrize("target", ["missing_person4_module:answer_chat", "invalid-target"])
def test_unloadable_optional_service_does_not_disable_backend(settings, target):
    with TestClient(create_app(replace(settings, chat_service=target))) as client:
        assert_fallback(client.post("/api/chat", json={"question": "Explain"}))
        assert_reads_work(client)


def test_sync_services_are_never_called(settings):
    def sync_service(**kwargs):
        pytest.fail("Blocking sync AI code must not run on the event loop")

    with TestClient(create_app(settings, chat_service=sync_service)) as client:
        assert_fallback(client.post("/api/chat", json={"question": "Explain"}))


def test_loader_rejects_sync_export(monkeypatch):
    module = ModuleType("test_sync_copilot")
    module.answer_chat = lambda **kwargs: {}
    monkeypatch.setitem(sys.modules, module.__name__, module)
    assert load_chat_service("test_sync_copilot:answer_chat") is None


def test_chat_cors_and_swagger(settings):
    with TestClient(create_app(settings)) as client:
        preflight = client.options("/api/chat", headers={
            "Origin": "http://localhost:3000", "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        })
        assert preflight.status_code == 200
        response = client.post("/api/chat", json={"question": "Explain"}, headers={"Origin": "http://localhost:3000"})
        assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
        assert response.headers["X-Analysis-Mode"] == "mock"
        schema = client.get("/openapi.json").json()
        route = schema["paths"]["/api/chat"]["post"]
        assert route["requestBody"]["content"]["application/json"]["schema"]["$ref"].endswith("/ChatRequest")
        assert route["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith("/ChatResponse")
        for status in ("404", "422", "500"):
            assert route["responses"][status]["content"]["application/json"]["schema"]["$ref"].endswith("/ErrorResponse")


@pytest.mark.parametrize("value", ["0", "-1", "nan", "inf", "not-a-number"])
def test_invalid_timeout_setting(monkeypatch, value):
    monkeypatch.setenv("CHAT_TIMEOUT_SECONDS", value)
    with pytest.raises(ValueError, match="CHAT_TIMEOUT_SECONDS"):
        Settings.from_env()


def test_chat_env_settings(monkeypatch):
    monkeypatch.setenv("CHAT_SERVICE", "backend.services.llm:answer_chat")
    monkeypatch.setenv("CHAT_TIMEOUT_SECONDS", "3.5")
    settings = Settings.from_env()
    assert settings.chat_service == "backend.services.llm:answer_chat"
    assert settings.chat_timeout_seconds == 3.5
