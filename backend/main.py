from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import Settings
from backend.errors import error_response, register_error_handlers
from backend.routes.jobs import router as jobs_router
from backend.routes.opportunities import router as opportunities_router
from backend.routes.summary import router
from backend.services.analysis_store import AnalysisStore

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    configured = settings if settings is not None else Settings.from_env()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        selected = configured
        app.state.analysis_store = AnalysisStore.load(selected.analysis_path)
        app.state.settings = selected
        if selected.analysis_mode == "mock":
            logger.warning("MOCK MODE: serving synthetic analysis from %s", selected.analysis_path)
        try:
            yield
        finally:
            del app.state.analysis_store

    app = FastAPI(
        title="CutScope Product API",
        version="0.2.0",
        description="Stored summary, opportunities, and job evidence. Default development data is synthetic.",
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
        allow_methods=["GET"],
        allow_headers=["Content-Type"],
        expose_headers=["X-Analysis-Mode"],
    )
    register_error_handlers(app)
    app.include_router(router)
    app.include_router(opportunities_router)
    app.include_router(jobs_router)
    return app


app = create_app()
