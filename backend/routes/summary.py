from fastapi import APIRouter, Request

from backend.models import Summary
from backend.errors import ERROR_RESPONSES

router = APIRouter(prefix="/api", tags=["summary"], responses=ERROR_RESPONSES)


@router.get("/summary", response_model=Summary)
def get_summary(request: Request) -> Summary:
    """Return authoritative stored figures without recalculation."""
    return request.app.state.analysis_store.get_summary()
