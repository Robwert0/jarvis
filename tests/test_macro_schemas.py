import pytest
from pydantic import ValidationError

from app import schemas


def test_accepts_bare_string_and_object_entries():
    m = schemas.MacroCreate(name="work", apps=["chrome", {"app": "code", "args": ["--new-window"]}])
    dumped = m.model_dump()
    assert dumped["apps"][0] == "chrome"
    assert dumped["apps"][1] == {"app": "code", "args": ["--new-window"]}


def test_rejects_non_string_non_object_entry():
    with pytest.raises(ValidationError):
        schemas.MacroCreate(name="work", apps=[123])


def test_rejects_object_entry_missing_app():
    with pytest.raises(ValidationError):
        schemas.MacroCreate(name="work", apps=[{"args": ["--x"]}])


def test_rejects_empty_apps():
    with pytest.raises(ValidationError):
        schemas.MacroCreate(name="work", apps=[])


def test_rejects_empty_name():
    with pytest.raises(ValidationError):
        schemas.MacroCreate(name="", apps=["chrome"])
