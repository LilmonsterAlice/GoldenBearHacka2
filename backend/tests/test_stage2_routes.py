from copy import deepcopy

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend.config import Settings
from backend.main import create_app
from backend.models import ErrorResponse, JobDetail, OpportunityDetail, OpportunityList


@pytest.fixture
def client(payload, write_snapshot):
    with TestClient(create_app(Settings("mock", write_snapshot(payload)))) as test_client:
        yield test_client


def test_full_drilldown_preserves_stored_values_and_evidence(client, payload):
    summary = client.get("/api/summary").json()
    listed = client.get("/api/opportunities")
    OpportunityList.model_validate(listed.json())
    card = listed.json()["opportunities"][0]
    response = client.get(f"/api/opportunities/{card['id']}")
    assert response.status_code == 200
    detail = response.json()
    OpportunityDetail.model_validate(detail)
    assert detail["jobs_pagination"] == {"total": 2, "offset": 0, "limit": 20}
    for field, value in card.items():
        assert detail[field] == value
    stored = payload["opportunities"][0]
    for field in ("method", "basis", "caveats", "cost_if_wrong"):
        assert detail[field] == stored[field]
    assert detail["jobs"] == [123, 124]
    assert all(type(job_id) is int for job_id in detail["jobs"])
    job_response = client.get(f"/api/jobs/{detail['jobs'][0]}")
    assert job_response.status_code == 200
    job = job_response.json()
    JobDetail.model_validate(job)
    for field, value in payload["jobs"][0].items():
        assert job[field] == value
    assert job["findings"][0]["raw_evidence"]
    for record in (card, detail, job):
        assert record["price_per_gpu_hour"] == summary["price_per_gpu_hour"]
        assert record["price_book_version"] == summary["price_book_version"]


@pytest.mark.parametrize("invalid_jobs", [[{"job_id": 123}], ["123"], [123.0], [True], [-1]])
def test_detail_response_model_requires_integer_job_ids(client, invalid_jobs):
    detail = client.get("/api/opportunities/idle-interactive").json()
    detail["jobs"] = invalid_jobs
    with pytest.raises(ValidationError):
        OpportunityDetail.model_validate(detail)


@pytest.mark.parametrize("offset,limit,expected", [
    (0, 1, [123]), (1, 1, [124]), (2, 1, []), (999, 100, []),
])
def test_pagination_is_stable_and_retains_full_count(client, offset, limit, expected):
    response = client.get("/api/opportunities/idle-interactive", params={"offset": offset, "limit": limit})
    assert response.status_code == 200
    detail = response.json()
    assert detail["jobs"] == expected
    assert detail["jobs_pagination"] == {"total": 2, "offset": offset, "limit": limit}
    assert detail["job_count"] == 2
    assert len(client.get("/api/opportunities/idle-interactive").json()["jobs"]) == 2


def test_ranked_order_is_preserved_without_numeric_recalculation(payload, write_snapshot):
    second = deepcopy(payload["opportunities"][0])
    second.update(id="ranked-second", savings_usd_low=0, savings_usd_high=None, confidence=None)
    payload["opportunities"].append(second)
    payload["opportunities"][0]["savings_usd_high"] = 987.654
    payload["jobs"][0]["cost_usd"] = 321.123
    payload["jobs"][0]["sm_util_avg"] = 0
    with TestClient(create_app(Settings("mock", write_snapshot(payload)))) as client:
        cards = client.get("/api/opportunities").json()["opportunities"]
        assert [card["id"] for card in cards] == ["idle-interactive", "ranked-second"]
        assert cards[0]["savings_usd_high"] == 987.654
        assert cards[1]["savings_usd_low"] == 0
        assert cards[1]["savings_usd_high"] is None
        assert cards[1]["confidence"] is None
        first_job = client.get("/api/jobs/123").json()
        assert first_job["cost_usd"] == 321.123
        assert first_job["sm_util_avg"] == 0
        second_job = client.get("/api/jobs/124").json()
        assert second_job["sm_util_avg"] is None
        assert second_job["sm_util_max"] is None


def test_empty_opportunity_is_valid(payload, write_snapshot):
    payload["opportunities"][0].update(jobs=[], job_count=0)
    with TestClient(create_app(Settings("mock", write_snapshot(payload)))) as client:
        response = client.get("/api/opportunities/idle-interactive")
        assert response.status_code == 200
        assert response.json()["jobs"] == []
        assert response.json()["jobs_pagination"]["total"] == 0


@pytest.mark.parametrize("path,code", [
    ("/api/opportunities/unknown", "OPPORTUNITY_NOT_FOUND"),
    ("/api/jobs/999", "JOB_NOT_FOUND"),
    ("/api/unknown", "NOT_FOUND"),
])
def test_not_found_uses_error_envelope(client, path, code):
    response = client.get(path)
    assert response.status_code == 404
    assert ErrorResponse.model_validate(response.json()).error.code == code
    assert response.json()["error"]["retryable"] is False
    assert response.headers["X-Analysis-Mode"] == "mock"


@pytest.mark.parametrize("path", [
    "/api/opportunities/idle-interactive?offset=-1",
    "/api/opportunities/idle-interactive?offset=secret-invalid-value",
    "/api/opportunities/idle-interactive?limit=0",
    "/api/opportunities/idle-interactive?limit=101",
    "/api/opportunities/idle-interactive?limit=1.5",
    "/api/jobs/not-an-integer",
    "/api/jobs/-1",
])
def test_invalid_request_uses_sanitized_error_envelope(client, path):
    response = client.get(path)
    assert response.status_code == 422
    error = ErrorResponse.model_validate(response.json()).error
    assert error.code == "VALIDATION_ERROR"
    assert error.retryable is False
    assert "secret-invalid-value" not in response.text
    assert "detail" not in response.json()


def test_method_not_allowed_preserves_allow_header(client):
    response = client.post("/api/jobs/123")
    assert response.status_code == 405
    assert response.json()["error"]["code"] == "METHOD_NOT_ALLOWED"
    assert "GET" in response.headers["allow"]


def test_unexpected_failure_is_sanitized_and_has_cors(client, monkeypatch):
    store = client.app.state.analysis_store

    def fail(job_id):
        raise RuntimeError("private-dataset-path-and-secret")

    monkeypatch.setattr(store, "get_job", fail)
    response = client.get("/api/jobs/123", headers={"Origin": "http://localhost:3000"})
    assert response.status_code == 500
    assert response.json() == {"error": {
        "code": "INTERNAL_ERROR", "message": "Unexpected backend failure", "retryable": False,
    }}
    assert "private-dataset" not in response.text
    assert response.headers["X-Analysis-Mode"] == "mock"
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert client.get("/api/summary").status_code == 200


def test_openapi_documents_success_and_error_models(client):
    schema = client.get("/openapi.json").json()
    for path in ("/api/opportunities", "/api/opportunities/{id}", "/api/jobs/{job_id}"):
        responses = schema["paths"][path]["get"]["responses"]
        for status in ("404", "422", "500"):
            assert responses[status]["content"]["application/json"]["schema"]["$ref"].endswith("/ErrorResponse")
    parameters = schema["paths"]["/api/opportunities/{id}"]["get"]["parameters"]
    query = {parameter["name"]: parameter["schema"] for parameter in parameters if parameter["in"] == "query"}
    assert query["offset"]["minimum"] == 0
    assert query["limit"]["default"] == 20
    assert query["limit"]["maximum"] == 100
    jobs = schema["components"]["schemas"]["OpportunityDetail"]["properties"]["jobs"]
    assert jobs["type"] == "array"
    assert jobs["items"]["type"] == "integer"
