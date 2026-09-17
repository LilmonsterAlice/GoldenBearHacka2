from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import Settings
from backend.errors import error_response, register_error_handlers
from backend.routes.chat import router as chat_router
from backend.routes.jobs import router as jobs_router
from backend.routes.opportunities import router as opportunities_router
from backend.routes.summary import router
from backend.services.analysis_store import AnalysisStore
from backend.services.chat_adapter import ChatService, load_chat_service

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None, *, chat_service: ChatService | None = None) -> FastAPI:
    configured = settings if settings is not None else Settings.from_env()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        selected = configured
        app.state.analysis_store = AnalysisStore.load(selected.analysis_path, mode=selected.analysis_mode)
        app.state.settings = selected
        app.state.chat_service = chat_service if chat_service is not None else load_chat_service(selected.chat_service)
        if selected.analysis_mode == "mock":
            logger.warning("MOCK MODE: serving synthetic analysis from %s", selected.analysis_path)
        try:
            yield
        finally:
            del app.state.analysis_store
            del app.state.chat_service

    app = FastAPI(
        title="CutScope Product API",
        version="0.3.0",
        description="Stored analysis and optional AI Copilot. Default development data is synthetic.",
        lifespan=lifespan,
    )
    @app.middleware("http")
    async def identify_data_mode(request, call_next):
        try:
            response = await call_next(request)
        except Exception as exc:
            logger.error("Unhandled backend failure (%s)", type(exc).__name__)
            response = error_response(500, "INTERNAL_ERROR", "Unexpected backend failure")
        response.headers["X-Analysis-Mode"] = request.app.state.settings.analysis_mode
        return response

    # CORS wraps error responses as well as successful requests.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(configured.cors_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
        expose_headers=["X-Analysis-Mode"],
    )
    register_error_handlers(app)
    app.include_router(router)
    app.include_router(opportunities_router)
    app.include_router(jobs_router)
    app.include_router(chat_router)
    return app

