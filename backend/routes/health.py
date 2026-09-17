from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/health", include_in_schema=False)
def health(request: Request) -> dict[str, str]:
    """Readiness means the configured snapshot loaded; AI availability is independent."""
    return {"status": "ready", "analysis_mode": request.app.state.settings.analysis_mode}
