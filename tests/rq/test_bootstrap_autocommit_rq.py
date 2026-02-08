from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace

import pytest

import wepppy.rq.swat_rq as swat_rq
import wepppy.rq.wepp_rq as wepp_rq

pytestmark = pytest.mark.unit


def _stub_log_complete_dependencies(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(wepp_rq, "get_current_job", lambda: SimpleNamespace(id="job-1"))
    monkeypatch.setattr(wepp_rq, "get_wd", lambda runid: "/tmp/run")
    monkeypatch.setattr(wepp_rq.StatusMessenger, "publish", lambda channel, message: None)
    monkeypatch.setattr(
        wepp_rq.RedisPrep,
        "getInstance",
        lambda wd: SimpleNamespace(timestamp=lambda task: None),
    )
    monkeypatch.setattr(
        wepp_rq.Ron,
        "getInstance",
        lambda wd: SimpleNamespace(name="", scenario="", config_stem="cfg"),
    )
    monkeypatch.setattr(wepp_rq, "send_discord_message", None)


def _stub_rq_queue(monkeypatch: pytest.MonkeyPatch, module) -> list[dict[str, object]]:
    calls: list[dict[str, object]] = []

    class DummyQueue:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def enqueue_call(
            self,
            func,
            args=(),
            kwargs=None,
            timeout=None,
            depends_on=None,
        ):
            job = SimpleNamespace(id=f"job-{len(calls) + 1}")
            calls.append(
                {
                    "func": func,
                    "args": args,
                    "kwargs": kwargs,
                    "timeout": timeout,
                    "depends_on": depends_on,
                    "job": job,
                }
            )
            return job

    class DummyRedis:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(module, "Queue", DummyQueue)
    monkeypatch.setattr(module.redis, "Redis", lambda **kwargs: DummyRedis())
    monkeypatch.setattr(module, "redis_connection_kwargs", lambda _db: {})
    return calls


def _make_parent_job() -> SimpleNamespace:
    job = SimpleNamespace(id="parent-job", meta={})
    job.save = lambda: None  # type: ignore[attr-defined]
    return job


class DummyRedis:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_log_complete_skips_autocommit_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_log_complete_dependencies(monkeypatch)

    def _unexpected_get_instance(_wd: str):
        raise AssertionError("Wepp.getInstance should not be called when auto-commit is disabled")

    monkeypatch.setattr(wepp_rq.Wepp, "getInstance", _unexpected_get_instance)

    wepp_rq._log_complete_rq("ab-run")


def test_log_complete_autocommits_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_log_complete_dependencies(monkeypatch)
    stages: list[str] = []
    released_tokens: list[str] = []
    monkeypatch.setattr(
        wepp_rq.Wepp,
        "getInstance",
        lambda wd: SimpleNamespace(
            bootstrap_commit_inputs=lambda stage: stages.append(stage),
            logger=SimpleNamespace(warning=lambda *args, **kwargs: None),
        ),
    )
    monkeypatch.setattr(wepp_rq, "redis_connection_kwargs", lambda _db: {})
    monkeypatch.setattr(wepp_rq.redis, "Redis", lambda **kwargs: DummyRedis())
    monkeypatch.setattr(
        wepp_rq,
        "acquire_bootstrap_git_lock",
        lambda *args, **kwargs: SimpleNamespace(token="lock-1"),
    )
    monkeypatch.setattr(
        wepp_rq,
        "release_bootstrap_git_lock",
        lambda _redis_conn, *, runid, token: released_tokens.append(token) or True,
    )

    wepp_rq._log_complete_rq(
        "ab-run",
        auto_commit_inputs=True,
        commit_stage="WEPP pipeline",
    )

    assert stages == ["WEPP pipeline"]
    assert released_tokens == ["lock-1"]


def test_log_complete_skips_autocommit_when_git_lock_busy(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_log_complete_dependencies(monkeypatch)
    stages: list[str] = []
    warnings: list[str] = []
    monkeypatch.setattr(
        wepp_rq.Wepp,
        "getInstance",
        lambda wd: SimpleNamespace(
            bootstrap_commit_inputs=lambda stage: stages.append(stage),
            logger=SimpleNamespace(warning=lambda message, *_args: warnings.append(str(message))),
        ),
    )
    monkeypatch.setattr(wepp_rq, "redis_connection_kwargs", lambda _db: {})
    monkeypatch.setattr(wepp_rq.redis, "Redis", lambda **kwargs: DummyRedis())
    monkeypatch.setattr(wepp_rq, "acquire_bootstrap_git_lock", lambda *args, **kwargs: None)

    wepp_rq._log_complete_rq(
        "ab-run",
        auto_commit_inputs=True,
        commit_stage="WEPP pipeline",
    )

    assert stages == []
    assert warnings
    assert "bootstrap lock busy" in warnings[-1].lower()


def test_standard_watershed_enqueue_sets_autocommit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(wepp_rq.StatusMessenger, "publish", lambda channel, message: None)
    monkeypatch.setattr(wepp_rq, "get_current_job", _make_parent_job)
    monkeypatch.setattr(wepp_rq, "get_wd", lambda runid: "/tmp/run")
    monkeypatch.setattr(
        wepp_rq.Wepp,
        "getInstance",
        lambda wd: SimpleNamespace(
            islocked=lambda: False,
            ensure_bootstrap_main=lambda: None,
            run_wepp_watershed=False,
            logger=SimpleNamespace(info=lambda *args, **kwargs: None),
        ),
    )
    calls = _stub_rq_queue(monkeypatch, wepp_rq)

    wepp_rq.run_wepp_watershed_rq("ab-run")

    assert len(calls) == 1
    assert calls[0]["func"] is wepp_rq._log_complete_rq
    assert calls[0]["kwargs"] == {
        "auto_commit_inputs": True,
        "commit_stage": "WEPP watershed pipeline",
    }


def test_noprep_watershed_enqueue_keeps_autocommit_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(wepp_rq.StatusMessenger, "publish", lambda channel, message: None)
    monkeypatch.setattr(wepp_rq, "get_current_job", _make_parent_job)
    monkeypatch.setattr(wepp_rq, "get_wd", lambda runid: "/tmp/run")
    monkeypatch.setattr(
        wepp_rq.Wepp,
        "getInstance",
        lambda wd: SimpleNamespace(
            islocked=lambda: False,
            run_wepp_watershed=False,
            logger=SimpleNamespace(info=lambda *args, **kwargs: None),
        ),
    )
    calls = _stub_rq_queue(monkeypatch, wepp_rq)

    wepp_rq.run_wepp_watershed_noprep_rq("ab-run")

    assert len(calls) == 1
    assert calls[0]["func"] is wepp_rq._log_complete_rq
    assert calls[0]["kwargs"] is None


def test_build_swat_inputs_autocommits(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(swat_rq.StatusMessenger, "publish", lambda channel, message: None)
    monkeypatch.setattr(swat_rq, "get_current_job", lambda: SimpleNamespace(id="job-2"))
    monkeypatch.setattr(swat_rq, "get_wd", lambda runid: "/tmp/run")

    built: list[str] = []
    commit_stages: list[str] = []

    swat_module = ModuleType("wepppy.nodb.mods.swat")

    class DummySwatController:
        def build_inputs(self) -> None:
            built.append("built")

    class DummySwat:
        @staticmethod
        def getInstance(wd: str) -> DummySwatController:
            return DummySwatController()

    swat_module.Swat = DummySwat  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "wepppy.nodb.mods.swat", swat_module)
    released_tokens: list[str] = []
    monkeypatch.setattr(
        swat_rq.Wepp,
        "getInstance",
        lambda wd: SimpleNamespace(
            bootstrap_commit_inputs=lambda stage: commit_stages.append(stage),
            logger=SimpleNamespace(warning=lambda *args, **kwargs: None),
        ),
    )
    monkeypatch.setattr(swat_rq, "redis_connection_kwargs", lambda _db: {})
    monkeypatch.setattr(swat_rq.redis, "Redis", lambda **kwargs: DummyRedis())
    monkeypatch.setattr(
        swat_rq,
        "acquire_bootstrap_git_lock",
        lambda *args, **kwargs: SimpleNamespace(token="lock-1"),
    )
    monkeypatch.setattr(
        swat_rq,
        "release_bootstrap_git_lock",
        lambda _redis_conn, *, runid, token: released_tokens.append(token) or True,
    )

    swat_rq._build_swat_inputs_rq("ab-run")

    assert built == ["built"]
    assert commit_stages == ["SWAT inputs"]
    assert released_tokens == ["lock-1"]
