"""Build the small, authoritative context used by the first Copilot slice."""

from dataclasses import dataclass
from typing import Any

from backend.services.chat_adapter import ChatContext


IDLE_INTERACTIVE_ID = "idle-interactive"


@dataclass(frozen=True)
class IdleInteractiveContext:
    opportunity: dict[str, Any]
    jobs: tuple[dict[str, Any], ...]
    evidence: tuple[dict[str, Any], ...]
    analysis_mode: str
    scope_caveat: str


def build_idle_interactive_context(context: ChatContext) -> IdleInteractiveContext | None:
    """Select stored Idle Interactive evidence without inventing telemetry."""
    opportunity = context.opportunity
    if opportunity is None:
        opportunity = context.analysis.get_opportunity(IDLE_INTERACTIVE_ID)
    if opportunity is None or opportunity.get("id") != IDLE_INTERACTIVE_ID:
        return None

    allowed_job_ids = {reference["job_id"] for reference in opportunity.get("jobs", [])}
    if context.job is not None:
        candidate_jobs = [context.job]
    else:
        candidate_jobs = [
            job
            for job_id in sorted(allowed_job_ids)
            if (job := context.analysis.get_job(job_id)) is not None
        ]

    jobs = tuple(job for job in candidate_jobs if job.get("job_id") in allowed_job_ids)
    evidence: list[dict[str, Any]] = []
    for job in jobs:
        for finding in job.get("findings", []):
            finding_id = finding.get("finding_id")
            description = finding.get("description")
            if not isinstance(finding_id, str) or not finding_id.strip():
                continue
            if not isinstance(description, str) or not description.strip():
                continue
            evidence.append(
                {
                    "source": finding.get("source", "stored analysis"),
                    "job_id": job["job_id"],
                    "finding_id": finding_id,
                    "description": description,
                    "fact_or_judgment": finding.get("fact_or_judgment", "unknown"),
                }
            )

    return IdleInteractiveContext(
        opportunity=opportunity,
        jobs=jobs,
        evidence=tuple(evidence),
        analysis_mode=context.analysis_mode,
        scope_caveat=context.summary.scope_caveat,
    )
