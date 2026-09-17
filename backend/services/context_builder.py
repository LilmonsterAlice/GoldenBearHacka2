"""Route questions and build small, authoritative Copilot contexts."""

from dataclasses import dataclass
from typing import Any

from backend.services.chat_adapter import ChatContext


OPPORTUNITY_TERMS = {
    "idle-interactive": (
        "idle interactive", "interactive session", "interactive allocation",
        "idle timeout", "recoverable capacity",
    ),
    "gpu-not-needed": (
        "gpu not needed", "doesn't need gpu", "does not need gpu",
        "doesn't need a gpu", "does not need a gpu", "do not need a gpu",
        "do not need gpu", "without gpu",
        "cpu placement", "cpu-only", "cpu only",
    ),
    "slow-cancel": (
        "slow cancel", "slow cancellation", "cancelled job", "canceled job",
        "cancellation", "canceling", "cancelling", "liveness review",
    ),
    "gpu-imbalance": (
        "gpu imbalance", "card imbalance", "per-card", "per card",
        "uneven gpu", "imbalanced gpu", "work distribution",
    ),
}

PRESET_ROUTES = {
    "what could go wrong if we enforce an idle timeout": "idle-interactive",
    "what evidence supports this recommendation": "idle-interactive",
}

MAX_CONTEXT_JOBS = 20
MAX_CONTEXT_EVIDENCE = 20


@dataclass(frozen=True)
class OpportunityContext:
    opportunity: dict[str, Any]
    jobs: tuple[dict[str, Any], ...]
    evidence: tuple[dict[str, Any], ...]
    analysis_mode: str
    scope_caveat: str


def route_opportunity_id(question: str) -> str | None:
    """Return the single opportunity clearly named by a question."""
    normalized = question.casefold()
    for phrase, opportunity_id in PRESET_ROUTES.items():
        if phrase in normalized:
            return opportunity_id
    matches = [
        opportunity_id
        for opportunity_id, terms in OPPORTUNITY_TERMS.items()
        if any(term in normalized for term in terms)
    ]
    return matches[0] if len(matches) == 1 else None


def build_opportunity_context(
    question: str, context: ChatContext
) -> OpportunityContext | None:
    """Select routed stored evidence without inventing telemetry."""
    opportunity = context.opportunity
    if opportunity is None:
        opportunity_id = route_opportunity_id(question)
        opportunity = (
            context.analysis.get_opportunity(opportunity_id)
            if opportunity_id is not None
            else None
        )
    if opportunity is None:
        return None

    allowed_job_ids = {reference["job_id"] for reference in opportunity.get("jobs", [])}
    if context.job is not None:
        candidate_jobs = [context.job]
    else:
        candidate_jobs = [
            job
            for job_id in sorted(allowed_job_ids)[:MAX_CONTEXT_JOBS]
            if (job := context.analysis.get_job(job_id)) is not None
        ]

    jobs = tuple(job for job in candidate_jobs if job.get("job_id") in allowed_job_ids)
    evidence: list[dict[str, Any]] = []
    for job in jobs:
        for finding in job.get("findings", []):
            finding_id = finding.get("finding_id") or finding.get("id")
            description = (
                finding.get("description")
                or finding.get("shortDescription")
                or finding.get("longDescription")
            )
            if not isinstance(finding_id, str) or not finding_id.strip():
                continue
            if not isinstance(description, str) or not description.strip():
                continue
            evidence.append(
                {
                    "source": finding.get("source") or finding.get("detectorId") or "stored analysis",
                    "job_id": job["job_id"],
                    "finding_id": finding_id,
                    "description": description,
                    "fact_or_judgment": finding.get("fact_or_judgment", "unknown"),
                }
            )
            if len(evidence) >= MAX_CONTEXT_EVIDENCE:
                break
        if len(evidence) >= MAX_CONTEXT_EVIDENCE:
            break

    return OpportunityContext(
        opportunity=opportunity,
        jobs=jobs,
        evidence=tuple(evidence),
        analysis_mode=context.analysis_mode,
        scope_caveat=context.summary.scope_caveat,
    )


# Backward-compatible names for existing integrations.
IdleInteractiveContext = OpportunityContext


def build_idle_interactive_context(context: ChatContext) -> OpportunityContext | None:
    return build_opportunity_context("idle interactive", context)
