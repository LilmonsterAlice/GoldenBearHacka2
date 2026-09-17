"""Load a snapshot once and return defensive copies to consumers."""

from copy import deepcopy
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from backend.models import AnalysisSnapshot, Summary


class AnalysisLoadError(RuntimeError):
    """Startup cannot proceed with the configured snapshot."""


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
    def load(cls, path: Path) -> "AnalysisStore":
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise AnalysisLoadError(
                f"Cannot read analysis snapshot at {path}. Check ANALYSIS_PATH and file access."
            ) from exc
        try:
            snapshot = AnalysisSnapshot.model_validate_json(content)
        except ValidationError as exc:
            # Locations/types are actionable without logging raw dataset values.
            issues = "; ".join(
                f"{'.'.join(map(str, issue['loc'])) or 'root'}: {issue['type']}"
                for issue in exc.errors(include_input=False)
            )
            raise AnalysisLoadError(f"Invalid analysis snapshot at {path}: {issues}") from exc
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

    def get_opportunity(self, opportunity_id: str) -> dict[str, Any] | None:
        return deepcopy(self._opportunities.get(opportunity_id))

    def get_job(self, job_id: int) -> dict[str, Any] | None:
        return deepcopy(self._jobs.get(job_id))
