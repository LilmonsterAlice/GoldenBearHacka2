import json

import pytest

from backend.config import STAGE1_MOCK


@pytest.fixture
def payload():
    return json.loads(STAGE1_MOCK.read_text(encoding="utf-8"))


@pytest.fixture
def write_snapshot(tmp_path):
    def write(payload):
        path = tmp_path / "analysis.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path
    return write
