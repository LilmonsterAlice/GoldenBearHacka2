from copy import deepcopy

import pytest

from backend.models import AnalysisSnapshot
from backend.services.analysis_store import AnalysisLoadError, AnalysisStore


@pytest.mark.parametrize("content", ["", "{broken", "{}"])
def test_invalid_file_has_actionable_error(tmp_path, content):
    path = tmp_path / "analysis.json"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(AnalysisLoadError, match="Invalid analysis snapshot"):
        AnalysisStore.load(path)


def test_missing_file_does_not_fallback(tmp_path):
    with pytest.raises(AnalysisLoadError, match="ANALYSIS_PATH"):
        AnalysisStore.load(tmp_path / "missing.json")


@pytest.mark.parametrize("collection,records", [
    ("opportunities", [{"id": "idle-interactive"}, {"id": "idle-interactive"}]),
    ("jobs", [{"job_id": 1}, {"job_id": 1}]),
    ("jobs", [{"job_id": True}]),
    ("jobs", [{"job_id": "1"}]),
    ("opportunities", [{"id": ""}]),
])
def test_record_id_integrity(payload, write_snapshot, collection, records):
    payload[collection] = records
    with pytest.raises(AnalysisLoadError):
        AnalysisStore.load(write_snapshot(payload))


def test_lookups_preserve_order_and_cannot_mutate_store(payload):
    template = payload["opportunities"][0]
    payload["opportunities"] = [deepcopy(template), deepcopy(template)]
    payload["opportunities"][0].update(id="second", caveats=[])
    payload["opportunities"][1]["id"] = "first"
    payload["jobs"][0]["findings"] = []
    source = AnalysisSnapshot.model_validate(payload)
    store = AnalysisStore(source)
    source.summary.outcomes.clear()
    store.get_summary().outcomes.clear()
    store.get_job(123)["findings"].append("injected")
    store.get_opportunity("second")["caveats"].append("injected")
    assert len(store.get_summary().outcomes) == 2
    assert store.get_job(123)["findings"] == []
    assert store.get_opportunity("second")["caveats"] == []
    assert [item["id"] for item in store.list_opportunities()] == ["second", "first"]
    assert store.get_job(999) is None
    assert store.get_opportunity("missing") is None


@pytest.mark.parametrize("change,message", [
    ("duplicate_opportunity", "Duplicate id"),
    ("duplicate_job", "Duplicate job_id"),
    ("duplicate_reference", "Duplicate job references"),
    ("missing_job", "Unknown job reference"),
    ("wrong_count", "job_count mismatch"),
])
def test_full_snapshot_integrity(payload, write_snapshot, change, message):
    opportunity = payload["opportunities"][0]
    if change == "duplicate_opportunity":
        payload["opportunities"].append(deepcopy(opportunity))
    elif change == "duplicate_job":
        payload["jobs"].append(deepcopy(payload["jobs"][0]))
    elif change == "duplicate_reference":
        opportunity["jobs"][1] = deepcopy(opportunity["jobs"][0])
    elif change == "missing_job":
        opportunity["jobs"][0]["job_id"] = 999
    else:
        opportunity["job_count"] = 999
    with pytest.raises(AnalysisLoadError, match=message):
        AnalysisStore.load(write_snapshot(payload))
