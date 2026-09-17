"""Load a snapshot once and return defensive copies to consumers."""

from copy import deepcopy
import json
import math
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from backend.models import AnalysisSnapshot, OpportunitySummary, Summary


class AnalysisLoadError(RuntimeError):
    """Startup cannot proceed with the configured snapshot."""


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON object key")
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError("Non-finite JSON number")


def _finite_json(value):
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("Non-finite JSON number")
    if isinstance(value, dict):
        for item in value.values():
            _finite_json(item)
    elif isinstance(value, list):
        for item in value:
            _finite_json(item)


class AnalysisStore:
    def __init__(self, snapshot: AnalysisSnapshot):
        self._summary = snapshot.summary.model_copy(deep=True)
        self._opportunities = self._index(
            [record.model_dump() for record in snapshot.opportunities], "id", str
        )
        self._jobs = self._index([record.model_dump() for record in snapshot.jobs], "job_id", int)
        for opportunity in self._opportunities.values():
            references = [reference["job_id"] for reference in opportunity["jobs"]]
            if len(references) != len(set(references)):
                raise AnalysisLoadError(f"Duplicate job references in opportunity {opportunity['id']}")
            if opportunity["job_count"] != len(references):
                raise AnalysisLoadError(f"job_count mismatch in opportunity {opportunity['id']}")
            if any(job_id not in self._jobs for job_id in references):
                raise AnalysisLoadError(f"Unknown job reference in opportunity {opportunity['id']}")

    @staticmethod
    def _index(records: list[dict[str, Any]], field: str, kind: type) -> dict:
        indexed = {}
        for record in records:
            identifier = record.get(field)
            if type(identifier) is not kind or (kind is str and not identifier.strip()):
                raise AnalysisLoadError(f"Each record requires a valid {field} ({kind.__name__})")
            if kind is int and identifier < 0:
                raise AnalysisLoadError(f"{field} cannot be negative")
            if identifier in indexed:
                raise AnalysisLoadError(f"Duplicate {field}: {identifier}")
            indexed[identifier] = deepcopy(record)
        return indexed

    @classmethod
    def load(cls, path: Path, *, mode: str | None = None) -> "AnalysisStore":
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise AnalysisLoadError(
                f"Cannot read analysis snapshot at {path}. Check ANALYSIS_PATH and file access."
            ) from exc
        try:
            data = json.loads(content, object_pairs_hook=_unique_object, parse_constant=_reject_constant)
            _finite_json(data)
        except (ValueError, RecursionError) as exc:
            raise AnalysisLoadError(
                f"Invalid analysis snapshot at {path}: invalid, duplicate-key, or non-finite JSON"
            ) from exc
        try:
            snapshot = AnalysisSnapshot.model_validate(data)
        except ValidationError as exc:
            # Locations/types are actionable without logging raw dataset values.
            issues = "; ".join(
                f"{'.'.join(map(str, issue['loc'])) or 'root'}: {issue['type']}"
                for issue in exc.errors(include_input=False)
            )
            raise AnalysisLoadError(f"Invalid analysis snapshot at {path}: {issues}") from exc
        if mode == "real":
            version = snapshot.summary.price_book_version.strip().lower()
            caveat = snapshot.summary.scope_caveat.strip().lower()
            if version in {"mock", "synthetic"} or version.startswith(("mock-", "mock_", "synthetic-", "synthetic_")) or caveat.startswith((
                "synthetic development fixture", "synthetic fixture", "synthetic data",
                "mock development fixture", "mock fixture", "mock data",
            )):
                raise AnalysisLoadError("Real mode cannot serve a snapshot explicitly labeled mock or synthetic")
        return cls(snapshot)

    def get_summary(self) -> Summary:
        return self._summary.model_copy(deep=True)

    def get_pricing(self) -> dict[str, Any]:
        return {
            "price_per_gpu_hour": self._summary.price_per_gpu_hour,
            "price_book_version": self._summary.price_book_version,
        }

    def list_opportunities(self) -> list[dict[str, Any]]:
        return deepcopy(list(self._opportunities.values()))

    def list_opportunity_cards(self) -> list[dict[str, Any]]:
        fields = OpportunitySummary.model_fields
        return [deepcopy({key: record[key] for key in fields}) for record in self._opportunities.values()]

    def get_opportunity_page(self, opportunity_id: str, offset: int, limit: int) -> dict[str, Any] | None:
        if offset < 0 or not 1 <= limit <= 100:
            raise ValueError("Invalid opportunity pagination")
        source = self._opportunities.get(opportunity_id)
        if source is None:
            return None
        # Copy metadata and the requested page, not the complete affected-job list.
        record = deepcopy({key: value for key, value in source.items() if key != "jobs"})
        record["jobs"] = deepcopy(source["jobs"][offset:offset + limit])
        record["jobs_pagination"] = {"total": len(source["jobs"]), "offset": offset, "limit": limit}
        return record

    def snapshot_counts(self) -> dict[str, int]:
        return {"outcomes": len(self._summary.outcomes), "opportunities": len(self._opportunities), "jobs": len(self._jobs)}

    def get_opportunity(self, opportunity_id: str) -> dict[str, Any] | None:
        return deepcopy(self._opportunities.get(opportunity_id))

    def get_job(self, job_id: int) -> dict[str, Any] | None:
        return deepcopy(self._jobs.get(job_id))
