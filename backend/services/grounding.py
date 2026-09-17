"""Ground citations against the authoritative context selected by the backend."""

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
