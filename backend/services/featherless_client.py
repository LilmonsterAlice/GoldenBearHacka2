"""Async Featherless.ai client using its OpenAI-compatible chat endpoint."""

import json
import os
from typing import Any

import httpx


class FeatherlessError(RuntimeError):
    """Sanitized provider error; never includes keys or raw provider payloads."""


class FeatherlessClient:
    def __init__(self) -> None:
        self.api_key = os.environ.get("FEATHERLESS_API_KEY", "").strip()
        self.base_url = os.environ.get(
            "FEATHERLESS_BASE_URL", "https://api.featherless.ai/v1"
        ).rstrip("/")
        self.model = os.environ.get(
            "FEATHERLESS_MODEL", "Qwen/Qwen2.5-7B-Instruct"
        ).strip()
        try:
            self.timeout = float(os.environ.get("FEATHERLESS_TIMEOUT_SECONDS", "20"))
        except ValueError as exc:
            raise FeatherlessError("Invalid Featherless timeout configuration") from exc

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.model and self.timeout > 0)

    async def generate_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> dict[str, Any]:
        if not self.configured:
            raise FeatherlessError("Featherless is not configured")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/LilmonsterAlice/GoldenBearHacka2",
            "X-Title": "CutScope",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.1,
            "max_tokens": 700,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                body = response.json()
            content = body["choices"][0]["message"]["content"]
            if not isinstance(content, str) or not content.strip():
                raise ValueError("Empty completion")
            return _parse_json_object(content)
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise FeatherlessError("Featherless returned no usable completion") from exc


def _parse_json_object(content: str) -> dict[str, Any]:
    """Accept a JSON object, including one wrapped in a Markdown code fence."""
    text = content.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    start = text.find("{")
    if start < 0:
        raise ValueError("Completion contains no JSON object")
    value, _ = json.JSONDecoder().raw_decode(text[start:])
    if not isinstance(value, dict):
        raise ValueError("Completion must be a JSON object")
    return value
