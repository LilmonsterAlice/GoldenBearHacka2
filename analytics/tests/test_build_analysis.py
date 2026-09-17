import json
from pathlib import Path
import subprocess
import sys

import pytest

from analytics.build_analysis import build_analysis, main, write_analysis
from analytics.config import PROJECT_ROOT


def test_build_from_local_parquet_has_backend_summary_only_shape(local_data, tmp_path):
    source = local_data / "prepped/jobs.parquet"
    original = source.read_bytes()
    output = tmp_path / "generated/analysis.json"
    result = build_analysis(data_dir=local_data, output_path=output)
    assert json.loads(output.read_text()) == result
    assert result["jobs"] == []
    assert result["opportunities"] == []
    assert result["metadata"]["stage"] == "summary-only"
    assert source.read_bytes() == original


def test_check_data_does_not_write_output(local_data, tmp_path, capsys):
    output = tmp_path / "analysis.json"
    assert main(["--data-dir", str(local_data), "--check-data", "--output", str(output)]) == 0
    assert not output.exists()
    assert "No output written" in capsys.readouterr().out


def test_direct_script_runs_from_another_directory(local_data, tmp_path):
    output = tmp_path / "analysis.json"
    result = subprocess.run([
        sys.executable, str(PROJECT_ROOT / "analytics/build_analysis.py"),
        "--data-dir", str(local_data), "--output", str(output),
    ], cwd=tmp_path, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    assert json.loads(output.read_text())["summary"]["total_gpu_hours"] == 10


def test_missing_input_fails_clearly_without_writing(tmp_path, capsys):
    output = tmp_path / "analysis.json"
    assert main(["--jobs-path", str(tmp_path / "missing.parquet"), "--output", str(output)]) == 1
    assert not output.exists()
    assert "CUTSCOPE_JOBS_PATH" in capsys.readouterr().err


def test_invalid_price_does_not_replace_existing_snapshot(local_data, tmp_path):
    output = tmp_path / "analysis.json"
    output.write_text("previous snapshot", encoding="utf-8")
    with pytest.raises(ValueError):
        build_analysis(data_dir=local_data, output_path=output, price_per_gpu_hour=-1)
    assert output.read_text() == "previous snapshot"


def test_nonfinite_json_is_not_written(tmp_path):
    output = tmp_path / "analysis.json"
    with pytest.raises(ValueError):
        write_analysis({"value": float("nan")}, output)
    assert not output.exists()


def test_source_cannot_be_overwritten(local_data):
    source = local_data / "prepped/jobs.parquet"
    with pytest.raises(ValueError, match="overwrite"):
        build_analysis(jobs_path=source, output_path=source)


def test_matches_backend_models_when_backend_is_available(local_data, tmp_path):
    try:
        from backend.models import AnalysisSnapshot
    except ImportError:
        pytest.skip("Backend models not implemented on this branch; validate after integration")
    output = tmp_path / "analysis.json"
    AnalysisSnapshot.model_validate(build_analysis(data_dir=local_data, output_path=output))
