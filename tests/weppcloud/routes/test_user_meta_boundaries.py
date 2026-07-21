from __future__ import annotations

import pytest

pytest.importorskip("flask")

from wepppy.weppcloud.routes import user as user_routes

pytestmark = pytest.mark.unit


def test_collect_metas_for_runs_skips_missing_and_broken_runs(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    ok_wd = "/tmp/ok"
    missing_wd = "/tmp/missing"
    broken_wd = "/tmp/broken"

    class DummyRon:
        def __init__(self) -> None:
            self.name = "Ok Run"
            self.scenario = "baseline"
            self.readonly = False

    def _load_detached(wd: str):
        if wd == ok_wd:
            return DummyRon()
        if wd == missing_wd:
            raise FileNotFoundError("ron.nodb missing")
        if wd == broken_wd:
            raise RuntimeError("broken ron")
        raise AssertionError(f"unexpected wd: {wd}")

    caplog.set_level("INFO", logger=user_routes.__name__)

    runs = [
        {"runid": "ok-run", "config": "cfg", "owner": "a@b.com", "wd": ok_wd},
        {"runid": "missing-run", "config": "cfg", "owner": "a@b.com", "wd": missing_wd},
        {"runid": "broken-run", "config": "cfg", "owner": "a@b.com", "wd": broken_wd},
    ]

    monkeypatch.setattr(user_routes.Ron, "load_detached", staticmethod(_load_detached))
    metas = user_routes._collect_metas_for_runs(runs)

    assert metas == [
        {
            "name": "Ok Run",
            "scenario": "baseline",
            "readonly": False,
            "owner": "a@b.com",
            "runid": "ok-run",
            "date_created": None,
            "last_modified": None,
            "owner_id": None,
            "config": "cfg",
            "ttl_deletion_at": None,
        }
    ]

    info_messages = [record.getMessage() for record in caplog.records if record.levelname == "INFO"]
    assert any("user._build_meta: ron.nodb missing for runid=missing-run" in msg for msg in info_messages)

    warning_records = [record for record in caplog.records if record.levelname == "WARNING"]
    assert any(
        "user._build_meta: failed to load Ron for runid=broken-run" in record.getMessage()
        for record in warning_records
    )
    assert any(record.exc_info for record in warning_records)


def test_ttl_deletion_at_accepts_only_active_timezone_aware_expirations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        user_routes.run_ttl,
        "read_ttl_state",
        lambda _wd: {
            "policy": user_routes.run_ttl.POLICY_ROLLING,
            "expires_at": "2026-12-31T00:00:00-07:00",
        },
    )

    assert user_routes._ttl_deletion_at("/tmp/run") == "2026-12-31T07:00:00Z"


@pytest.mark.parametrize(
    "state",
    [
        None,
        {},
        {"policy": "disabled", "expires_at": "2026-12-31T00:00:00Z"},
        {"policy": user_routes.run_ttl.POLICY_ROLLING, "expires_at": None},
        {"policy": user_routes.run_ttl.POLICY_ROLLING, "expires_at": "not-a-date"},
        {"policy": user_routes.run_ttl.POLICY_ROLLING, "expires_at": "2026-12-31T00:00:00"},
        {"policy": 1, "expires_at": "2026-12-31T00:00:00Z"},
    ],
)
def test_ttl_deletion_at_falls_back_for_inactive_or_invalid_state(
    monkeypatch: pytest.MonkeyPatch,
    state: object,
) -> None:
    monkeypatch.setattr(user_routes.run_ttl, "read_ttl_state", lambda _wd: state)

    assert user_routes._ttl_deletion_at("/tmp/run") is None


def test_ttl_deletion_at_falls_back_for_expected_reader_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise_invalid_encoding(_wd: str):
        raise UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid start byte")

    monkeypatch.setattr(user_routes.run_ttl, "read_ttl_state", _raise_invalid_encoding)

    assert user_routes._ttl_deletion_at("/tmp/run") is None
