"""Ground citations against the authoritative context selected by the backend."""

import json
import re
from typing import Any

from backend.services.context_builder import IdleInteractiveContext


def grounded_references(
    context: IdleInteractiveContext,
) -> tuple[list[dict[str, Any]], list[str], list[int]]:
    """Return evidence and IDs that can be traced to selected stored jobs."""
    allowed_job_ids = {job["job_id"] for job in context.jobs}
    evidence: list[dict[str, Any]] = []
    finding_ids: list[str] = []
    job_ids: list[int] = []

    for item in context.evidence:
        job_id = item.get("job_id")
        finding_id = item.get("finding_id")
        if job_id not in allowed_job_ids or not isinstance(finding_id, str):
            continue
        evidence.append(dict(item))
        if finding_id not in finding_ids:
            finding_ids.append(finding_id)
        if job_id not in job_ids:
            job_ids.append(job_id)

    return evidence, finding_ids, job_ids


def validate_generated_claims(
    generated: dict[str, Any],
    context: IdleInteractiveContext,
) -> tuple[str, str, str, bool]:
    """Reject malformed text or numerical claims absent from stored context."""
    required = ("answer", "risk", "recommendation")
    values: list[str] = []
    for field in required:
        value = generated.get(field)
        if not isinstance(value, str) or not value.strip() or len(value) > 4000:
            raise ValueError(f"Invalid generated {field}")
        values.append(value.strip())

    gpu_related = generated.get("gpu_related")
    if not isinstance(gpu_related, bool):
        raise ValueError("Invalid generated gpu_related flag")

    if gpu_related:
        source = json.dumps(
            {
                "opportunity": context.opportunity,
                "jobs": context.jobs,
                "evidence": context.evidence,
            },
            sort_keys=True,
        )
        allowed_numbers = {
            _normalize_number(token)
            for token in re.findall(r"\d+(?:[.,]\d+)?%?", source)
        }
        generated_numbers = {
            _normalize_number(token)
            for token in re.findall(r"\d+(?:[.,]\d+)?%?", " ".join(values))
        }
        if not generated_numbers.issubset(allowed_numbers):
            raise ValueError("Generated response introduced an unsupported number")

    return values[0], values[1], values[2], gpu_related


def _normalize_number(token: str) -> str:
    number = token.removesuffix("%").replace(",", "")
    return f"{float(number):g}"
