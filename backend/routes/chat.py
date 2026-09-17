from fastapi import APIRouter, Request

from backend.errors import ERROR_RESPONSES
from backend.models import ChatRequest, ChatResponse
from backend.services.chat_adapter import answer_with_service, resolve_context

router = APIRouter(prefix="/api", tags=["chat"], responses=ERROR_RESPONSES)


@router.post("/chat", response_model=ChatResponse)
async def chat(body: ChatRequest, request: Request) -> ChatResponse:
    state = request.app.state
    context = resolve_context(state.analysis_store, body, state.settings.analysis_mode)
    return await answer_with_service(
        state.chat_service, body.question, context, state.settings.chat_timeout_seconds,
    )
