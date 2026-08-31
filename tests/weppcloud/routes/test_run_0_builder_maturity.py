from __future__ import annotations

from types import SimpleNamespace
import importlib

import pytest

run0_module = importlib.import_module("wepppy.weppcloud.routes.run_0.run_0_bp")

pytestmark = [pytest.mark.routes, pytest.mark.unit]


def test_builder_manifest_for_reserved_config_token_is_preview(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(run0_module, "project_config_manifest_source_kind", lambda *_args, **_kwargs: "builder")

    assert run0_module._resolve_run_config_maturity_label("config", "/wc1/runs/aa/example", "example", None) == "Preview"


def test_nonbuilder_or_other_token_does_not_invent_preview(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(run0_module, "project_config_manifest_source_kind", lambda *_args, **_kwargs: None)
    stable = SimpleNamespace(maturity="stable")

    assert run0_module._resolve_run_config_maturity_label("config", "/wc1/runs/aa/example", "example", None) is None
    assert run0_module._resolve_run_config_maturity_label("disturbed9002", "/wc1/runs/aa/example", "example", stable) == "Stable"
