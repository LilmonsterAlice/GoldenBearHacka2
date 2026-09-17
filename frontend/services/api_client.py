"""Small HTTP client for the CutScope backend API."""

import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class ChatAPIError(RuntimeError):
    """Raised when the chat API cannot return a usable response."""


def _api_base_url() -> str:
    return os.environ.get("API_BASE_URL", "http://localhost:8001").rstrip("/")


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
