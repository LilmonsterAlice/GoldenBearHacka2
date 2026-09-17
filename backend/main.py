"""Uvicorn entry point; application factory is also available for isolated checks."""

from backend.application import create_app

app = create_app()
