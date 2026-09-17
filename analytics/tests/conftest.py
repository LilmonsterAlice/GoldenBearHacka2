import pandas as pd
import pytest


@pytest.fixture(autouse=True)
def isolate_data_env(monkeypatch):
    for name in ("CUTSCOPE_DATA_DIR", "CUTSCOPE_JOBS_PATH", "CUTSCOPE_GPUS_PATH", "CUTSCOPE_FINDINGS_PATH"):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def jobs():
    return pd.DataFrame({"id_job": [1, 2], "state_name": ["COMPLETED", "CANCELLED"], "gpu_hours": [8.0, 2.0]})


@pytest.fixture
def local_data(tmp_path, jobs):
    root = tmp_path / "official data"
    (root / "prepped").mkdir(parents=True)
    jobs.to_parquet(root / "prepped/jobs.parquet", index=False)
    return root
