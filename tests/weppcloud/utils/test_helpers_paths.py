import types

import pytest

from wepppy.weppcloud.utils import helpers


pytestmark = pytest.mark.unit


def _disable_redis_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    """Avoid touching real Redis during path resolution tests."""
    monkeypatch.setattr(helpers, "redis_wd_cache_client", None)


def test_get_wd_prefers_primary_when_both_exist(monkeypatch: pytest.MonkeyPatch) -> None:
    _disable_redis_cache(monkeypatch)
    runid = "ab-newrun"

    def fake_exists(path: str) -> bool:
        if path == "/wc1/runs/ab/ab-newrun":
            return True
        if path == "/geodata/weppcloud_runs/ab-newrun":
            return True
        return False

    monkeypatch.setattr(helpers, "_exists", fake_exists)

    resolved = helpers.get_wd(runid, prefer_active=False)

    assert resolved == "/wc1/runs/ab/ab-newrun"


def test_batch_runs_use_wc1_batch(monkeypatch: pytest.MonkeyPatch) -> None:
    _disable_redis_cache(monkeypatch)
    dummy_app = types.SimpleNamespace(config={})
    monkeypatch.setattr(helpers, "current_app", dummy_app)

    resolved = helpers.get_batch_run_wd("demo-batch", "demo-run")

    assert resolved == "/wc1/batch/demo-batch/runs/demo-run"


def test_get_wd_falls_back_to_legacy_when_primary_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    _disable_redis_cache(monkeypatch)
    runid = "cd-legacy"

    def fake_exists(path: str) -> bool:
        if path == "/wc1/runs/cd/cd-legacy":
            return False
        if path == "/geodata/weppcloud_runs/cd-legacy":
            return True
        return False

    monkeypatch.setattr(helpers, "_exists", fake_exists)

    resolved = helpers.get_wd(runid, prefer_active=False)

    assert resolved == "/geodata/weppcloud_runs/cd-legacy"


def test_get_primary_wd_always_points_to_wc1(monkeypatch: pytest.MonkeyPatch) -> None:
    _disable_redis_cache(monkeypatch)
    runid = "ef-new"
    assert helpers.get_primary_wd(runid) == "/wc1/runs/ef/ef-new"
