import json

import pandas as pd
import pytest

from analytics.config import DataPaths, PROJECT_ROOT
from analytics.load_data import load_findings, load_gpus, load_jobs


def test_data_directory_loads_existing_prepared_file(local_data, jobs):
    pd.testing.assert_frame_equal(load_jobs(data_dir=local_data), jobs)


def test_environment_works_without_moving_downloads(local_data, jobs, monkeypatch):
    monkeypatch.setenv("CUTSCOPE_DATA_DIR", str(local_data))
    pd.testing.assert_frame_equal(load_jobs(), jobs)


def test_explicit_file_overrides_environment(local_data, jobs, tmp_path, monkeypatch):
    path = tmp_path / "custom.parquet"
    jobs.to_parquet(path, index=False)
    monkeypatch.setenv("CUTSCOPE_JOBS_PATH", str(tmp_path / "missing.parquet"))
    pd.testing.assert_frame_equal(load_jobs(path), jobs)


def test_individual_file_env_and_flat_directory(tmp_path, jobs, monkeypatch):
    jobs.to_parquet(tmp_path / "jobs.parquet", index=False)
    assert DataPaths.resolve(data_dir=tmp_path).jobs == tmp_path / "jobs.parquet"
    monkeypatch.setenv("CUTSCOPE_JOBS_PATH", str(tmp_path / "jobs.parquet"))
    pd.testing.assert_frame_equal(load_jobs(), jobs)


def test_paths_do_not_depend_on_working_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert DataPaths.resolve(data_dir="data").jobs == PROJECT_ROOT / "data/prepped/jobs.parquet"


def test_missing_file_explains_local_setting(tmp_path):
    with pytest.raises(FileNotFoundError, match="CUTSCOPE_JOBS_PATH"):
        load_jobs(data_dir=tmp_path)


def test_optional_gpus_and_findings_do_not_block_summary(local_data):
    assert len(load_jobs(data_dir=local_data)) == 2
    with pytest.raises(FileNotFoundError, match="CUTSCOPE_GPUS_PATH"):
        load_gpus(data_dir=local_data)


@pytest.mark.parametrize("payload", [[{"id": "finding-1"}], {"findings": [{"id": "finding-1"}], "version": 1}])
def test_findings_preserve_json_layout(tmp_path, payload):
    path = tmp_path / "findings.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    assert load_findings(path) == payload


def test_gpu_loader_respects_explicit_path(tmp_path):
    path = tmp_path / "gpus.parquet"
    frame = pd.DataFrame({"card_id": [1]})
    frame.to_parquet(path, index=False)
    pd.testing.assert_frame_equal(load_gpus(path), frame)
