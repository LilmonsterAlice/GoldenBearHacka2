"""Deterministic first-slice Copilot service.

This module intentionally does not call an external LLM yet. It explains only
the authoritative stored Idle Interactive record and clearly discloses mock
analysis. The async boundary matches the backend adapter so a real provider can
replace the response generation later without changing the HTTP contract.
"""

from backend.models import ChatResponse
from backend.services.chat_adapter import ChatContext
from backend.services.context_builder import build_idle_interactive_context
from backend.services.grounding import grounded_references


def _money_range(low: float | None, high: float | None) -> str:
    if low is None or high is None:
        return "an unavailable dollar range"
    return f"${low:,.0f}–${high:,.0f}"


def _hours_range(low: float | None, high: float | None) -> str:
    if low is None or high is None:
        return "an unavailable GPU-hour range"
    return f"{low:,.0f}–{high:,.0f} GPU-hours"


async def answer_chat(*, question: str, context: ChatContext) -> ChatResponse:
    """Answer the three Idle Interactive question families from stored data."""
    selected = build_idle_interactive_context(context)
    if selected is None:
        return ChatResponse(
            answer="cannot_determine: No Idle Interactive opportunity is available in the selected analysis.",
            evidence=[],
            risk="cannot_determine",
            recommendation="Select the Idle Interactive opportunity and try again.",
            confidence=None,
            finding_ids=[],
            job_ids=[],
            caveats=[context.summary.scope_caveat],
        )

    opportunity = selected.opportunity
    evidence, finding_ids, job_ids = grounded_references(selected)
    savings = _money_range(
        opportunity.get("savings_usd_low"),
        opportunity.get("savings_usd_high"),
    )
    gpu_hours = _hours_range(
        opportunity.get("gpu_hours_low"),
        opportunity.get("gpu_hours_high"),
    )
    downside = opportunity.get("cost_if_wrong", {})
    downside_range = _money_range(downside.get("usd_low"), downside.get("usd_high"))
    normalized = question.casefold()

    if any(term in normalized for term in ("wrong", "risk", "downside", "cost")):
        answer = (
            f"The stored scenario estimates a {downside_range} cost if the policy is wrong. "
            f"The main risk is that an idle timeout interrupts useful interactive work. "
            f"This is reversible: {downside.get('mitigation') or 'pilot the policy and roll it back if needed.'}"
        )
    elif any(term in normalized for term in ("evidence", "support", "finding", "job")):
        if evidence:
            answer = (
                f"The stored analysis links this opportunity to {len(opportunity.get('jobs', []))} jobs, "
                f"but only {len(evidence)} stored finding currently provides descriptive evidence. "
                "That finding reports low-utilization samples and explicitly says this alone does not "
                "prove the work was unnecessary."
            )
        else:
            answer = (
                "cannot_determine: The selected Idle Interactive record has no grounded finding evidence."
            )
    else:
        answer = (
            f"The stored Idle Interactive scenario treats {gpu_hours}, worth {savings}, as a range to "
            "investigate—not guaranteed savings. Capacity may be recoverable when a reserved interactive "
            "allocation remains open while little GPU compute is observed. Low utilization alone is not "
            "proof of waste, so the recommendation is a warning-first pilot with an opt-out."
        )

    caveats = list(opportunity.get("caveats", []))
    if selected.scope_caveat not in caveats:
        caveats.append(selected.scope_caveat)
    if selected.analysis_mode == "mock":
        caveats.append(
            "This deterministic response uses synthetic development data and is not a verified savings claim."
        )

    return ChatResponse(
        answer=answer,
        evidence=evidence,
        risk=downside.get("description") or "Useful interactive work could be interrupted.",
        recommendation=opportunity.get("action") or "Review the evidence before taking action.",
        confidence=opportunity.get("confidence"),
        finding_ids=finding_ids,
        job_ids=job_ids,
        caveats=caveats,
    )
