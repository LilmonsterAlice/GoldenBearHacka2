from copy import deepcopy
import json

import pytest
from fastapi.testclient import TestClient

from backend.config import Settings
from backend.main import create_app
from backend.services.analysis_store import AnalysisLoadError, AnalysisStore
from backend.validate_analysis import main


@pytest.fixture
def contract_payload(payload):
    """Contract test input only; not Person 1's output or verified official data."""
    payload["summary"]["price_book_version"] = "contract-test-price-book"
    payload["summary"]["scope_caveat"] = "Four-month workload sample; contract test input only"
    return payload


def test_cli_schema_exports_current_input_contract(capsys):
    assert main(["--schema"]) == 0
    schema = json.loads(capsys.readouterr().out)
    assert set(schema["required"]) == {"summary", "opportunities", "jobs"}
    assert "metadata" in schema["properties"]


def test_cli_mock_validation_is_read_only(write_snapshot, payload, capsys):
    path = write_snapshot(payload)
    original = path.read_bytes()
    assert main([str(path), "--mode", "mock", "--check-api"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["valid"] is True
    assert report["counts"] == {"outcomes": 2, "opportunities": 1, "jobs": 2}
    assert report["api_requests_checked"] == 7
    assert path.read_bytes() == original


def test_cli_real_mode_contract_checks_without_official_data(write_snapshot, contract_payload, capsys):
    path = write_snapshot(contract_payload)
    assert main([str(path), "--check-api"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["mode"] == "real"
    assert "not analytical" in report["verification_scope"]


def test_summary_only_is_supported_before_opportunities_are_ready(contract_payload, write_snapshot, capsys):
    contract_payload.update(opportunities=[], jobs=[], metadata={"producer_version": "work-in-progress"})
    path = write_snapshot(contract_payload)
    assert main([str(path), "--check-api"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["counts"]["opportunities"] == 0
    assert report["api_requests_checked"] == 2
    with TestClient(create_app(Settings("real", path))) as client:
        assert client.get("/api/summary").json() == contract_payload["summary"]
        assert client.get("/api/opportunities").json() == {"opportunities": []}
        assert "metadata" not in client.get("/api/summary").json()


@pytest.mark.parametrize("marker", ["price_book_version", "scope_caveat"])
def test_real_mode_rejects_mock_content_even_when_renamed(payload, contract_payload, write_snapshot, marker):
    # contract_payload shares the base fixture; use explicit known labels here.
    contract_payload["summary"][marker] = "synthetic-stage1" if marker == "price_book_version" else "SYNTHETIC development fixture; not real data"
    path = write_snapshot(contract_payload)
    with pytest.raises(AnalysisLoadError, match="explicitly labeled"):
        AnalysisStore.load(path, mode="real")
    with pytest.raises(AnalysisLoadError, match="explicitly labeled"):
        with TestClient(create_app(Settings("real", path))):
            pass


def test_cli_missing_or_invalid_input_has_nonzero_exit(tmp_path, capsys):
    assert main([str(tmp_path / "missing.json")]) == 1
    assert "ANALYSIS_PATH" in capsys.readouterr().err
    path = tmp_path / "analysis.json"
    path.write_text("{}", encoding="utf-8")
    assert main([str(path)]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "Invalid analysis snapshot" in captured.err


def test_cli_respects_analysis_path_but_ignores_ai_settings(contract_payload, write_snapshot, monkeypatch, capsys):
    path = write_snapshot(contract_payload)
    monkeypatch.setenv("ANALYSIS_PATH", str(path))
    monkeypatch.setenv("CHAT_TIMEOUT_SECONDS", "invalid-ai-setting")
    assert main(["--check-api"]) == 0
    assert json.loads(capsys.readouterr().out)["valid"] is True


@pytest.mark.parametrize("content", [
    '{"summary": {}, "summary": {}}',
    '{"evidence": NaN}',
    '{"evidence": Infinity}',
    '{"evidence": 1e999}',
])
def test_duplicate_keys_and_nonfinite_json_are_rejected(tmp_path, content):
    path = tmp_path / "analysis.json"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(AnalysisLoadError, match="duplicate-key, or non-finite"):
        AnalysisStore.load(path)


def test_nonfinite_nested_finding_is_rejected(payload, write_snapshot):
    payload["jobs"][0]["findings"][0]["raw_evidence"][0]["sm_util_percent"] = float("nan")
    with pytest.raises(AnalysisLoadError, match="non-finite"):
        AnalysisStore.load(write_snapshot(payload))


def test_routes_do_not_copy_full_opportunity_records(payload, write_snapshot, monkeypatch):
    with TestClient(create_app(Settings("mock", write_snapshot(payload)))) as client:
        def fail(*args):
            pytest.fail("List/page requests must not use full-record copy methods")
        store = client.app.state.analysis_store
        monkeypatch.setattr(store, "list_opportunities", fail)
        monkeypatch.setattr(store, "get_opportunity", fail)
        assert client.get("/api/opportunities").status_code == 200
        response = client.get("/api/opportunities/idle-interactive?limit=1")
        assert response.status_code == 200
        assert response.json()["jobs"] == [{"job_id": 123}]


def test_large_reference_list_is_paged_without_mutating_source(payload, write_snapshot):
    job_template = deepcopy(payload["jobs"][1])
    payload["jobs"] = [{**deepcopy(job_template), "job_id": job_id} for job_id in range(2000)]
    payload["opportunities"][0].update(jobs=[{"job_id": job_id} for job_id in range(2000)], job_count=2000)
    store = AnalysisStore.load(write_snapshot(payload))
    page = store.get_opportunity_page("idle-interactive", 1999, 20)
    assert page["jobs"] == [{"job_id": 1999}]
    assert page["jobs_pagination"]["total"] == 2000
    page["jobs"][0]["job_id"] = -1
    assert store.get_opportunity_page("idle-interactive", 1999, 20)["jobs"] == [{"job_id": 1999}]
    assert "jobs" not in store.list_opportunity_cards()[0]
