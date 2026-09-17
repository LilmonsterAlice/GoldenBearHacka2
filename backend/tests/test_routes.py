import pytest
from fastapi.testclient import TestClient

from backend.config import Settings, STAGE1_MOCK
from backend.main import create_app
from backend.services.analysis_store import AnalysisLoadError


def test_summary_preserves_numbers_nulls_and_zero(payload, write_snapshot):
    payload["summary"]["total_cost_usd"] = 123.456  # No backend recomputation.
    payload["summary"]["completed_percent"] = None
    payload["summary"]["outcomes"][0]["jobs"] = 0
    with TestClient(create_app(Settings("mock", write_snapshot(payload)))) as client:
        response = client.get("/api/summary")
        assert response.status_code == 200
        assert response.json() == payload["summary"]
        assert response.headers["X-Analysis-Mode"] == "mock"


def test_snapshot_is_not_reread_per_request(payload, write_snapshot):
    path = write_snapshot(payload)
    with TestClient(create_app(Settings("mock", path))) as client:
        original = client.get("/api/summary").json()
        path.write_text("{broken", encoding="utf-8")
        assert client.get("/api/summary").json() == original


def test_docs_and_openapi():
    with TestClient(create_app(Settings("mock", STAGE1_MOCK))) as client:
        assert client.get("/docs").status_code == 200
        schema = client.get("/openapi.json").json()
        assert set(schema["paths"]) == {
            "/api/summary", "/api/opportunities", "/api/opportunities/{id}", "/api/jobs/{job_id}",
        }
        assert schema["paths"]["/api/summary"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith("/Summary")


def test_cors_only_allows_configured_origin():
    settings = Settings("mock", STAGE1_MOCK, ("http://localhost:3000",))
    with TestClient(create_app(settings)) as client:
        for origin, status in [("http://localhost:3000", 200), ("https://unexpected.example", 400)]:
            response = client.options("/api/summary", headers={
                "Origin": origin, "Access-Control-Request-Method": "GET",
            })
            assert response.status_code == status
            assert "access-control-allow-credentials" not in response.headers
        response = client.get("/api/summary", headers={"Origin": "http://localhost:3000"})
        assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_real_mode_missing_file_fails_startup(tmp_path):
    with pytest.raises(AnalysisLoadError):
        with TestClient(create_app(Settings("real", tmp_path / "missing.json"))):
            pass


def test_real_mode_header(payload, write_snapshot):
    payload["summary"]["scope_caveat"] = "Four-month workload sample"
    with TestClient(create_app(Settings("real", write_snapshot(payload)))) as client:
        assert client.get("/api/summary").headers["X-Analysis-Mode"] == "real"


def test_settings_modes_and_path_resolution(monkeypatch):
    monkeypatch.setenv("ANALYSIS_MODE", "real")
    monkeypatch.delenv("ANALYSIS_PATH", raising=False)
    assert Settings.from_env().analysis_path.name == "analysis.json"
    assert Settings.from_env().analysis_path.parent.name == "generated"
    with pytest.raises(ValueError, match="mock fixture"):
        Settings("real", STAGE1_MOCK)
    with pytest.raises(ValueError, match="mock or real"):
        Settings("invalid", STAGE1_MOCK)
    monkeypatch.setenv("ANALYSIS_MODE", "mock")
    monkeypatch.setenv("ANALYSIS_PATH", "backend/fixtures/analysis.stage1.mock.json")
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000, http://127.0.0.1:3000")
    assert Settings.from_env().analysis_path == STAGE1_MOCK
    assert len(Settings.from_env().cors_origins) == 2
