"""Product API transport. Responses are returned without analytical changes."""
import os
from typing import Optional
from urllib.parse import quote

import requests

DEFAULT_API_BASE_URL = "http://localhost:8001"


def get_api_base_url() -> str:
    return (os.environ.get("API_BASE_URL", "").strip() or DEFAULT_API_BASE_URL).rstrip("/")


def _request(method: str, path: str, **kwargs):
    response = requests.request(
        method,
        f"{get_api_base_url()}{path}",
        timeout=(5, 30),
        **kwargs,
    )
    response.raise_for_status()
    return response.json()


def get_summary():
    return _request("GET", "/api/summary")


def get_opportunities():
    return _request("GET", "/api/opportunities")


def get_opportunity(opportunity_id: str):
    return _request("GET", f"/api/opportunities/{quote(str(opportunity_id), safe='')}")


def get_job(job_id: int):
    return _request("GET", f"/api/jobs/{quote(str(job_id), safe='')}")


def query_copilot(question: str, opportunity_id: Optional[str] = None, job_id: Optional[int] = None):
    return _request("POST", "/api/chat", json={
        "question": question,
        "opportunity_id": opportunity_id,
        "job_id": job_id,
    })
