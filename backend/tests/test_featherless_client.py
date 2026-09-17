import pytest

from backend.services.featherless_client import _parse_json_object


def test_parse_json_object_accepts_code_fence():
    assert _parse_json_object('```json\n{"answer": "ok"}\n```') == {"answer": "ok"}


def test_parse_json_object_accepts_brief_model_preamble():
    assert _parse_json_object('Result:\n{"answer": "ok"}\nDone.') == {"answer": "ok"}


def test_parse_json_object_rejects_non_object():
    with pytest.raises(ValueError):
        _parse_json_object('["not", "an", "object"]')
