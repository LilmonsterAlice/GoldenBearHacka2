"""Read teammates' existing official files; no download or prep side effects."""

import json
from pathlib import Path

import pandas as pd

from analytics.config import DataPaths, project_path


def _file(path: Path, label: str, setting: str) -> Path:
    if not path.is_file():
        raise FileNotFoundError(
            f"{label} file not found: {path}. Set CUTSCOPE_DATA_DIR or {setting} "
            "to your existing official data; see analytics/README.md."
        )
    return path


def load_jobs(path: str | Path | None = None, *, data_dir=None) -> pd.DataFrame:
    selected = project_path(path) if path is not None else DataPaths.resolve(data_dir=data_dir).jobs
    return pd.read_parquet(_file(selected, "Jobs", "CUTSCOPE_JOBS_PATH"), engine="pyarrow")


def load_gpus(path: str | Path | None = None, *, data_dir=None) -> pd.DataFrame:
    selected = project_path(path) if path is not None else DataPaths.resolve(data_dir=data_dir).gpus
    return pd.read_parquet(_file(selected, "GPU telemetry", "CUTSCOPE_GPUS_PATH"), engine="pyarrow")


def load_findings(path: str | Path | None = None, *, data_dir=None) -> list | dict:
    """Preserve list/envelope JSON; do not assume a flat pandas table."""
    selected = project_path(path) if path is not None else DataPaths.resolve(data_dir=data_dir).findings
    with _file(selected, "Findings", "CUTSCOPE_FINDINGS_PATH").open(encoding="utf-8") as stream:
        result = json.load(stream)
    if not isinstance(result, (list, dict)):
        raise ValueError("Findings JSON must be a list or object")
    return result
