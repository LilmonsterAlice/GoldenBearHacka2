"""Grounded Copilot service with Featherless generation and safe fallback."""

import json

from backend.models import ChatResponse
from backend.services.chat_adapter import ChatContext
from backend.services.context_builder import (
    IdleInteractiveContext,
    build_idle_interactive_context,
)
from backend.services.featherless_client import FeatherlessClient, FeatherlessError
from backend.services.grounding import grounded_references, validate_generated_claims


GPU_SYSTEM_PROMPT = """You are a helpful assistant embedded in the CutScope dashboard.
The application has already classified this question as GPU-related. Set
gpu_related=true. Answer using only the supplied stored analysis
and evidence, focusing on recoverability, evidence, and the cost if the policy is
wrong. Never invent a number, job, finding, cause, or savings claim. Distinguish
observations from recommendations. Low utilization alone does not prove waste, and
CANCELLED does not mean failed.
Return exactly one JSON object with four fields:
{"answer":"...","risk":"...","recommendation":"...","gpu_related":true}
Do not use Markdown fences or add other fields."""


GENERAL_SYSTEM_PROMPT = """You are a helpful general assistant embedded in the
CutScope dashboard. The application has already classified this question as not GPU-related.
Answer the user's actual question normally. Do not mention GPUs,
Idle Interactive, recoverability, dashboard evidence, or savings unless the user
asks about them. Set gpu_related=false. Set risk and recommendation to concise
values appropriate to the question, or "Not applicable" when they do not apply.
Return exactly one JSON object with four fields:
{"answer":"...","risk":"...","recommendation":"...","gpu_related":false}
Do not use Markdown fences or add other fields."""


CAPABILITY_SYSTEM_PROMPT = """You are the AI Copilot for CutScope, a dashboard
that helps a CFO investigate GPU-cluster capacity and spending. The user is asking
what this project can do. Briefly explain that you can:
- explain potentially recoverable GPU capacity and dollar/GPU-hour ranges;
- summarize the stored evidence behind findings and relevant jobs;
- explain recommendations, confidence, caveats, and the cost if a policy is wrong;
- help evaluate warning-first, reversible GPU policies.
Do not claim that savings are guaranteed or invent current results. Do not describe
yourself as a generic assistant or mention unrelated abilities such as reminders.
Set gpu_related=false because this is a product introduction, not an analytical
claim requiring evidence. Set risk and recommendation to "Not applicable".
Return exactly one JSON object with four fields:
{"answer":"...","risk":"Not applicable","recommendation":"Not applicable","gpu_related":false}
Do not use Markdown fences or add other fields."""


def _money_range(low: float | None, high: float | None) -> str:
    if low is None or high is None:
        return "an unavailable dollar range"
    return f"${low:,.0f}–${high:,.0f}"


def _hours_range(low: float | None, high: float | None) -> str:
    if low is None or high is None:
        return "an unavailable GPU-hour range"
    return f"{low:,.0f}–{high:,.0f} GPU-hours"


def _is_greeting(question: str) -> bool:
    return question.casefold().strip(" .!?") in {"hello", "hi", "hey", "你好", "嗨"}


def _is_capability_question(question: str) -> bool:
    normalized = question.casefold().strip(" .!?")
    phrases = {
        "what can you do",
        "what do you do",
        "how can you help",
        "help",
        "你能做什么",
        "你可以做什么",
        "你能帮我什么",
    }
    return any(phrase in normalized for phrase in phrases)


def _looks_in_scope(question: str) -> bool:
    normalized = question.casefold()
    gpu_terms = {
        "gpu", "cuda", "vram", "accelerator", "idle interactive", "gpu-hour",
        "cluster capacity", "gpu capacity", "gpu cost", "gpu saving",
        "utilization", "allocation", "idle timeout", "recover", "recoverable capacity",
    }
    preset_followups = {
        "what could go wrong if we enforce an idle timeout",
        "what evidence supports this recommendation",
    }
    return any(term in normalized for term in gpu_terms) or any(
        phrase in normalized for phrase in preset_followups
    )


def _deterministic_text(
    question: str,
    selected: IdleInteractiveContext,
    evidence: list[dict],
) -> tuple[str, str, str, bool]:
    opportunity = selected.opportunity
    savings = _money_range(
        opportunity.get("savings_usd_low"), opportunity.get("savings_usd_high")
    )
    gpu_hours = _hours_range(
        opportunity.get("gpu_hours_low"), opportunity.get("gpu_hours_high")
    )
    downside = opportunity.get("cost_if_wrong", {})
    downside_range = _money_range(downside.get("usd_low"), downside.get("usd_high"))
    normalized = question.casefold()

    if _is_greeting(question):
        answer = "Hello! How can I help?"
        risk = "Not applicable."
        recommendation = "Ask a question whenever you are ready."
        return answer, risk, recommendation, False
    if _is_capability_question(question):
        answer = (
            "I can answer general questions and explain this dashboard's GPU "
            "capacity, evidence, savings ranges, and policy risks."
        )
        risk = "Not applicable."
        recommendation = "Ask a general question or a question about the GPU analysis."
        return answer, risk, recommendation, False
    if not _looks_in_scope(question):
        answer = (
            "The LLM provider is unavailable, so I cannot answer this general "
            "question right now."
        )
        risk = "Not applicable."
        recommendation = "Try the question again when the LLM provider is available."
        return answer, risk, recommendation, False
    if any(term in normalized for term in ("wrong", "risk", "downside", "cost")):
        answer = (
            f"The stored scenario estimates a {downside_range} cost if the policy is wrong. "
            "The main risk is that an idle timeout interrupts useful interactive work. "
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
            answer = "cannot_determine: The selected opportunity has no grounded finding evidence."
    else:
        answer = (
            f"The stored Idle Interactive scenario treats {gpu_hours}, worth {savings}, as a range to "
            "investigate—not guaranteed savings. Capacity may be recoverable when a reserved interactive "
            "allocation remains open while little GPU compute is observed. Low utilization alone is not "
            "proof of waste, so the recommendation is a warning-first pilot with an opt-out."
        )

    risk = downside.get("description") or "Useful interactive work could be interrupted."
    recommendation = opportunity.get("action") or "Review the evidence before taking action."
    return answer, risk, recommendation, True


async def answer_chat(*, question: str, context: ChatContext) -> ChatResponse:
    """Generate language with Featherless while keeping citations authoritative."""
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
    answer, risk, recommendation, _ = _deterministic_text(
        question, selected, evidence
    )
    gpu_related = _looks_in_scope(question)
    client = FeatherlessClient()
    generation_caveat = "No Featherless key was configured; a deterministic grounded response was used."

    if client.configured:
        if _is_capability_question(question):
            provider_context = {"question": question, "product": "CutScope"}
            system_prompt = CAPABILITY_SYSTEM_PROMPT
        elif gpu_related:
            provider_context = {
                "question": question,
                "analysis_mode": selected.analysis_mode,
                "opportunity": opportunity,
                "evidence": evidence,
            }
            system_prompt = GPU_SYSTEM_PROMPT
        else:
            provider_context = {"question": question}
            system_prompt = GENERAL_SYSTEM_PROMPT
        try:
            generated = await client.generate_json(
                system_prompt=system_prompt,
                user_prompt=json.dumps(provider_context, sort_keys=True),
            )
            # Routing is owned by the application, not by generation influenced by context.
            generated["gpu_related"] = gpu_related
            answer, risk, recommendation, gpu_related = validate_generated_claims(
                generated, selected
            )
            if gpu_related:
                generation_caveat = (
                    f"Answer wording was generated by Featherless model {client.model} "
                    "from the cited stored context."
                )
            else:
                generation_caveat = (
                    f"Answer was generated by Featherless model {client.model}."
                )
        except (FeatherlessError, ValueError):
            generation_caveat = (
                "Featherless was unavailable or returned an ungrounded response; "
                "a deterministic grounded response was used."
            )

    caveats = list(opportunity.get("caveats", [])) if gpu_related else []
    route_caveats = (
        (selected.scope_caveat, generation_caveat)
        if gpu_related
        else (generation_caveat,)
    )
    for caveat in route_caveats:
        if caveat not in caveats:
            caveats.append(caveat)

    return ChatResponse(
        answer=answer,
        evidence=evidence if gpu_related else [],
        risk=risk,
        recommendation=recommendation,
        confidence=opportunity.get("confidence") if gpu_related else None,
        finding_ids=finding_ids if gpu_related else [],
        job_ids=job_ids if gpu_related else [],
        caveats=caveats,
    )
