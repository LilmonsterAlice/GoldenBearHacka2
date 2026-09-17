from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

JOBS_PATH = PROJECT_ROOT / "data" / "prepped" / "jobs.parquet"
GPUS_PATH = PROJECT_ROOT / "data" / "prepped" / "gpus.parquet"
FINDINGS_PATH = PROJECT_ROOT / "data" / "synthetic" / "findings.json"


def load_jobs() -> pd.DataFrame:
    """Load the preprocessed job-level dataset."""
    if not JOBS_PATH.exists():
        raise FileNotFoundError(f"Jobs data not found: {JOBS_PATH}")

    return pd.read_parquet(JOBS_PATH)


def load_gpus() -> pd.DataFrame:
    """Load the preprocessed GPU-level telemetry dataset."""
    if not GPUS_PATH.exists():
        raise FileNotFoundError(f"GPU data not found: {GPUS_PATH}")

    return pd.read_parquet(GPUS_PATH)


def load_findings():
    """Load MantisGrid findings."""
    if not FINDINGS_PATH.exists():
        raise FileNotFoundError(f"Findings data not found: {FINDINGS_PATH}")

    return pd.read_json(FINDINGS_PATH)
