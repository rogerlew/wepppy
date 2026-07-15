from __future__ import annotations

from types import SimpleNamespace

import pytest

from wepppy.wepp.interchange import _rust_interchange as native


pytestmark = pytest.mark.unit


def test_required_native_module_and_symbols_are_returned(monkeypatch: pytest.MonkeyPatch) -> None:
    module = SimpleNamespace(writer=lambda: None)
    monkeypatch.setattr(native, "_import_wepppyo3_interchange", lambda: module)

    assert native.require_wepppyo3_interchange("test writer", "writer") is module


def test_native_import_failure_has_stable_error_and_cause(monkeypatch: pytest.MonkeyPatch) -> None:
    cause = ImportError("extension unavailable")

    def fail_import():
        raise cause

    monkeypatch.setattr(native, "_import_wepppyo3_interchange", fail_import)

    with pytest.raises(native.WeppInterchangeUnavailableError, match="test writer") as raised:
        native.require_wepppyo3_interchange("test writer", "writer")

    assert raised.value.__cause__ is cause


def test_missing_native_symbol_names_release_skew(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(native, "_import_wepppyo3_interchange", lambda: SimpleNamespace())

    with pytest.raises(
        native.WeppInterchangeUnavailableError,
        match="missing native API: writer",
    ) as raised:
        native.require_wepppyo3_interchange("test writer", "writer")

    assert isinstance(raised.value.__cause__, AttributeError)


def test_native_execution_failure_has_stable_error_and_cause(monkeypatch: pytest.MonkeyPatch) -> None:
    cause = ValueError("bad WEPP row")

    def fail_writer() -> None:
        raise cause

    module = SimpleNamespace(writer=fail_writer)
    monkeypatch.setattr(native, "_import_wepppyo3_interchange", lambda: module)

    with pytest.raises(native.WeppInterchangeExecutionError, match="test writer") as raised:
        native.call_wepppyo3_interchange("test writer", "writer")

    assert raised.value.__cause__ is cause


def test_complete_required_api_can_be_preflighted(monkeypatch: pytest.MonkeyPatch) -> None:
    module = SimpleNamespace(
        **{name: (lambda: None) for name in native.REQUIRED_WEPPPYO3_INTERCHANGE_API}
    )
    monkeypatch.setattr(native, "_import_wepppyo3_interchange", lambda: module)

    assert (
        native.require_wepppyo3_interchange(
            "production interchange",
            *native.REQUIRED_WEPPPYO3_INTERCHANGE_API,
        )
        is module
    )
