"""Resolve per-computer data paths without copying official data into Git."""

from dataclasses import dataclass
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def project_path(value: str | Path) -> Path:
    path = Path(value).expanduser()
    return (path if path.is_absolute() else PROJECT_ROOT / path).resolve()


def _resolve(explicit, variable: str, root: Path, candidates: tuple[str, ...]) -> Path:
    configured = explicit if explicit is not None else os.environ.get(variable)
    if configured is not None:
        if not str(configured).strip():
            raise ValueError(f"{variable} cannot be empty")
        return project_path(configured)
    for relative in candidates:
        candidate = root / relative
        if candidate.is_file():
            return candidate
    return root / candidates[0]


@dataclass(frozen=True)
class DataPaths:
    jobs: Path
    gpus: Path
    findings: Path

    @classmethod
    def resolve(cls, *, data_dir=None, jobs_path=None, gpus_path=None, findings_path=None):
        configured = data_dir if data_dir is not None else os.environ.get("CUTSCOPE_DATA_DIR", PROJECT_ROOT / "data")
        if not str(configured).strip():
            raise ValueError("CUTSCOPE_DATA_DIR cannot be empty")
        root = project_path(configured)
        return cls(
            _resolve(jobs_path, "CUTSCOPE_JOBS_PATH", root, ("prepped/jobs.parquet", "jobs.parquet", "processed/jobs.parquet")),
            _resolve(gpus_path, "CUTSCOPE_GPUS_PATH", root, ("prepped/gpus.parquet", "gpus.parquet", "processed/gpus.parquet")),
            _resolve(findings_path, "CUTSCOPE_FINDINGS_PATH", root, ("findings.json", "synthetic/findings.json")),
        )
