"""Explicit snapshot selection; paths resolve relative to the repository root."""

from dataclasses import dataclass
import os
import math
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
STAGE1_MOCK = PROJECT_ROOT / "backend/fixtures/analysis.stage1.mock.json"


@dataclass(frozen=True)
class Settings:
    analysis_mode: str
    analysis_path: Path
    cors_origins: tuple[str, ...] = ("http://localhost:3000",)
    chat_service: str | None = None
    chat_timeout_seconds: float = 20.0

    def __post_init__(self) -> None:
        if self.analysis_mode not in {"mock", "real"}:
            raise ValueError("ANALYSIS_MODE must be mock or real")
        if not math.isfinite(self.chat_timeout_seconds) or self.chat_timeout_seconds <= 0:
            raise ValueError("CHAT_TIMEOUT_SECONDS must be finite and greater than zero")
        path = Path(self.analysis_path).expanduser()
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        path = path.resolve()
        if self.analysis_mode == "real" and (
            path == STAGE1_MOCK.resolve()
            or "fixtures" in path.parts
            or path.name.endswith(".mock.json")
        ):
            raise ValueError("Real mode cannot use a mock fixture path")
        object.__setattr__(self, "analysis_path", path)

    @classmethod
    def from_env(cls) -> "Settings":
        mode = os.environ.get("ANALYSIS_MODE", "mock")
        default = STAGE1_MOCK if mode == "mock" else PROJECT_ROOT / "generated/analysis.json"
        configured = os.environ.get("ANALYSIS_PATH")
        if configured is not None and not configured.strip():
            raise ValueError("ANALYSIS_PATH cannot be empty")
        origins = tuple(
            origin.strip()
            for origin in os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",")
            if origin.strip()
        )
        service = os.environ.get("CHAT_SERVICE", "").strip() or None
        try:
            timeout = float(os.environ.get("CHAT_TIMEOUT_SECONDS", "20"))
        except ValueError as exc:
            raise ValueError("CHAT_TIMEOUT_SECONDS must be a number") from exc
        return cls(mode, Path(configured) if configured else default, origins, service, timeout)
