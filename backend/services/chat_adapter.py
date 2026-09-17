"""Person 2's HTTP/service boundary; AI generation and grounding belong to Person 4."""

import asyncio
from dataclasses import dataclass
import importlib
import inspect
import json
import logging
from typing import Any, Protocol

from pydantic import ValidationError

from backend.errors import APIError
from backend.models import ChatRequest, ChatResponse, Summary
from backend.services.analysis_store import AnalysisStore

logger = logging.getLogger(__name__)


class AnalysisReader(Protocol):
    def get_summary(self) -> Summary: ...
    def get_pricing(self) -> dict[str, Any]: ...
    def list_opportunities(self) -> list[dict[str, Any]]: ...
    def get_opportunity(self, opportunity_id: str) -> dict[str, Any] | None: ...
    def get_job(self, job_id: int) -> dict[str, Any] | None: ...


class ReadOnlyAnalysis:
    """Expose defensive-copy lookups, not snapshot reload or replacement."""

    def __init__(self, store: AnalysisStore):
        self._store = store

    def get_summary(self) -> Summary:
        return self._store.get_summary()

    def get_pricing(self) -> dict[str, Any]:
        return self._store.get_pricing()

    def list_opportunities(self) -> list[dict[str, Any]]:
        return self._store.list_opportunities()

    def get_opportunity(self, opportunity_id: str) -> dict[str, Any] | None:
        return self._store.get_opportunity(opportunity_id)

    def get_job(self, job_id: int) -> dict[str, Any] | None:
        return self._store.get_job(job_id)


@dataclass(frozen=True)
class ChatContext:
    summary: Summary
    opportunity: dict[str, Any] | None
    job: dict[str, Any] | None
    analysis_mode: str
    analysis: AnalysisReader


class ChatService(Protocol):
    async def __call__(self, *, question: str, context: ChatContext) -> ChatResponse | dict[str, Any]: ...


def is_async_service(service) -> bool:
    return inspect.iscoroutinefunction(service) or inspect.iscoroutinefunction(getattr(service, "__call__", None))


def load_chat_service(target: str | None) -> ChatService | None:
    """Optional configured Person 4 export. Import failure never disables read APIs."""
    if target is None:
        return None
    try:
        module_name, export = target.split(":")
        if not module_name or not export or "." in export:
            raise ValueError("Expected module:callable")
        service = getattr(importlib.import_module(module_name), export)
        if not is_async_service(service):
            raise TypeError("Chat service must be async")
        return service
    except Exception as exc:
        logger.warning("Chat service unavailable during loading (%s)", type(exc).__name__)
        return None


def resolve_context(store: AnalysisStore, request: ChatRequest, mode: str) -> ChatContext:
    opportunity = store.get_opportunity(request.opportunity_id) if request.opportunity_id is not None else None
    if request.opportunity_id is not None and opportunity is None:
        raise APIError(404, "OPPORTUNITY_NOT_FOUND", "Opportunity not found")
    job = store.get_job(request.job_id) if request.job_id is not None else None
    if request.job_id is not None and job is None:
        raise APIError(404, "JOB_NOT_FOUND", "Job not found")
    if opportunity is not None and job is not None:
        if job["job_id"] not in {reference["job_id"] for reference in opportunity["jobs"]}:
            raise APIError(422, "JOB_OPPORTUNITY_MISMATCH", "Job does not belong to the selected opportunity")
    return ChatContext(store.get_summary(), opportunity, job, mode, ReadOnlyAnalysis(store))


def unavailable_response(context: ChatContext, reason: str) -> ChatResponse:
    """Transport fallback only: makes no analytical or financial recommendation."""
    caveats = [reason, context.summary.scope_caveat]
    if context.analysis_mode == "mock":
        caveats.append("The selected analysis is synthetic development data, not verified evidence.")
    return ChatResponse(
        answer="cannot_determine: AI Copilot could not provide an evidence-grounded answer.",
        evidence=[],
        risk="cannot_determine",
        recommendation="Review the stored analysis and evidence; no AI recommendation is available.",
        confidence=None,
        finding_ids=[],
        job_ids=[],
        caveats=caveats,
    )


async def answer_with_service(
    service: ChatService | None, question: str, context: ChatContext, timeout: float,
) -> ChatResponse:
    if service is None or not is_async_service(service):
        return unavailable_response(context, "No compatible AI service is configured.")
    try:
        result = await asyncio.wait_for(service(question=question, context=context), timeout=timeout)
        # Revalidate model instances too, including ones built with model_construct.
        if isinstance(result, ChatResponse):
            result = result.model_dump()
        response = ChatResponse.model_validate(result)
        # Evidence is opaque, but must still be finite, JSON-serializable data.
        json.dumps(response.model_dump(), allow_nan=False)
        # This is a basic reference check, not Person 4's evidence-grounding layer.
        if any(context.analysis.get_job(job_id) is None for job_id in response.job_ids):
            raise ValueError("Unknown cited job")
        allowed = None
        if context.opportunity is not None:
            allowed = {reference["job_id"] for reference in context.opportunity["jobs"]}
        elif context.job is not None:
            allowed = {context.job["job_id"]}
        if allowed is not None and not set(response.job_ids).issubset(allowed):
            raise ValueError("Cited job outside selected context")
        # Preserve authoritative caveats even if a service forgets to include them.
        caveats = list(response.caveats)
        required = [context.summary.scope_caveat]
        if context.opportunity is not None:
            required.extend(context.opportunity["caveats"])
        if context.analysis_mode == "mock":
            required.append("The selected analysis is synthetic development data, not verified evidence.")
        for caveat in required:
            if caveat not in caveats:
                caveats.append(caveat)
        return response.model_copy(update={"caveats": caveats}, deep=True)
    except asyncio.TimeoutError:
        return unavailable_response(context, "The AI service timed out.")
    except (ValidationError, ValueError, TypeError):
        return unavailable_response(context, "The AI service returned an invalid response or job reference.")
    except Exception as exc:
        logger.warning("Chat service call failed (%s)", type(exc).__name__)
        return unavailable_response(context, "The AI service is unavailable or failed.")
