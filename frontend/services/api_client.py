from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

"""Product API transport. Responses are returned without analytical changes."""
import os
from typing import Optional
from urllib.parse import quote

import requests

DEFAULT_API_BASE_URL = "http://localhost:8001"


def _api_base_url() -> str:
    return (os.environ.get("API_BASE_URL", "").strip() or DEFAULT_API_BASE_URL).rstrip("/")


def get_api_base_url() -> str:
    """Compatibility alias for existing callers."""
    return _api_base_url()


def _request(method: str, path: str, **kwargs):
    response = requests.request(
        method,
        f"{_api_base_url()}{path}",
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


class ChatAPIError(RuntimeError):
    """Raised when chat cannot return a usable response."""


def post_chat(
    question: str,
    *,
    opportunity_id: str | None = None,
    job_id: int | None = None,
    timeout: float = 30.0,
) -> dict[str, Any]:
    """Send one question to POST /api/chat and return its JSON response."""
    payload: dict[str, Any] = {"question": question}
    if opportunity_id is not None:
        payload["opportunity_id"] = opportunity_id
    if job_id is not None:
        payload["job_id"] = job_id

    request = Request(
        f"{_api_base_url()}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(request, timeout=timeout) as response:
            body = json.load(response)
    except HTTPError as exc:
        try:
            detail = json.load(exc)
            message = detail.get("error", {}).get("message", "Chat request failed")
        except (json.JSONDecodeError, AttributeError):
            message = "Chat request failed"
        raise ChatAPIError(f"Backend returned HTTP {exc.code}: {message}") from exc
    except (URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        raise ChatAPIError("Backend chat API is unavailable") from exc

    required_fields = {
        "answer",
        "evidence",
        "risk",
        "recommendation",
        "confidence",
        "finding_ids",
        "job_ids",
        "caveats",
    }
    if not isinstance(body, dict) or not required_fields.issubset(body):
        raise ChatAPIError("Backend returned an invalid chat response")
    return body
