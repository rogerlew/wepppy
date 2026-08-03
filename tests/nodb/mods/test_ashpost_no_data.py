from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path

import pytest

import wepppy.nodb.mods.ash_transport.ashpost as ashpost_module


pytestmark = pytest.mark.unit


def test_run_post_treats_no_data_as_success_and_updates_catalog(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    ashpost = object.__new__(ashpost_module.AshPost)
    ashpost.wd = str(tmp_path)
    ashpost._return_periods = {2: {}}
    ashpost._cum_return_periods = {2: {}}
    ashpost._burn_class_return_periods = {1: {}}
    (tmp_path / "ash" / "post").mkdir(parents=True)

    @contextmanager
    def noop_lock():
        yield ashpost

    ashpost.locked = noop_lock
    monkeypatch.setattr(ashpost_module, "remove_incompatible_outputs", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(ashpost_module, "watershed_daily_aggregated", lambda *_args, **_kwargs: None)

    def fail_if_called(*_args, **_kwargs) -> None:
        raise AssertionError("no-data AshPost must not publish normal dataset metadata")

    monkeypatch.setattr(ashpost_module, "write_version_manifest", fail_if_called)
    monkeypatch.setattr(ashpost_module, "generate_ashpost_documentation", fail_if_called)

    catalog_calls: list[tuple[str, str]] = []
    monkeypatch.setattr(
        ashpost_module,
        "update_catalog_entry",
        lambda wd, key: catalog_calls.append((wd, key)),
    )

    ashpost.run_post()

    assert ashpost.return_periods is None
    assert ashpost.cum_return_periods is None
    assert ashpost.burn_class_return_periods is None
    assert catalog_calls == [(str(tmp_path), "ash")]
