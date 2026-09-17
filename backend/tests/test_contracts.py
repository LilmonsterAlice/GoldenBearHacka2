import pytest
from pydantic import ValidationError

from backend.models import AnalysisSnapshot


@pytest.mark.parametrize("field,value", [
    ("total_gpu_hours", -1),
    ("total_cost_usd", float("nan")),
    ("price_per_gpu_hour", float("inf")),
    ("completed_percent", 101),
    ("completed_percent", -0.1),
    ("total_cost_usd", "250"),
    ("total_gpu_hours", True),
])
def test_rejects_invalid_summary_measurements(payload, field, value):
    payload["summary"][field] = value
    with pytest.raises(ValidationError):
        AnalysisSnapshot.model_validate(payload)


def test_missing_is_not_implicitly_null(payload):
    del payload["summary"]["total_gpu_hours"]
    with pytest.raises(ValidationError):
        AnalysisSnapshot.model_validate(payload)


@pytest.mark.parametrize("field,value", [("jobs", 1.5), ("jobs", True), ("capacity_percent", 101)])
def test_rejects_invalid_outcomes(payload, field, value):
    payload["summary"]["outcomes"][0][field] = value
    with pytest.raises(ValidationError):
        AnalysisSnapshot.model_validate(payload)


def test_unknown_summary_fields_are_rejected(payload):
    payload["summary"]["totalCost"] = 250
    with pytest.raises(ValidationError):
        AnalysisSnapshot.model_validate(payload)


@pytest.mark.parametrize("field,value", [
    ("confidence", 1.01),
    ("confidence", -0.01),
    ("savings_usd_low", 26),
    ("gpu_hours_low", 11),
    ("capacity_percent_low", 11),
    ("capacity_percent_high", 101),
])
def test_opportunity_bounds_and_ranges(payload, field, value):
    payload["opportunities"][0][field] = value
    with pytest.raises(ValidationError):
        AnalysisSnapshot.model_validate(payload)


def test_cost_if_wrong_range(payload):
    payload["opportunities"][0]["cost_if_wrong"]["usd_low"] = 6
    with pytest.raises(ValidationError):
        AnalysisSnapshot.model_validate(payload)


@pytest.mark.parametrize("field,value", [("gpu_count", 1.5), ("gpu_hours", -1), ("sm_util_avg", 101)])
def test_job_measurement_validation(payload, field, value):
    payload["jobs"][0][field] = value
    with pytest.raises(ValidationError):
        AnalysisSnapshot.model_validate(payload)
