from __future__ import annotations

from types import SimpleNamespace

import pytest

import wepppy.weppcloud.routes.fork_console.fork_console as fork_console_module


pytestmark = pytest.mark.routes


@pytest.mark.parametrize(
    ("args", "expected_undisturbify", "expected_skip"),
    [
        ({}, False, False),
        ({"undisturbify": "YES", "skip_wepp_runs_output": "1"}, True, True),
        ({"undisturbify": "false", "skip_wepp_runs_output": "off"}, False, False),
    ],
)
def test_fork_console_route_propagates_query_defaults_and_authenticated_token(
    monkeypatch: pytest.MonkeyPatch,
    args: dict[str, str],
    expected_undisturbify: bool,
    expected_skip: bool,
) -> None:
    monkeypatch.setattr(fork_console_module, "authorize", lambda runid, config: None)
    monkeypatch.setattr(fork_console_module, "request", SimpleNamespace(args=args))
    monkeypatch.setattr(
        fork_console_module,
        "current_user",
        SimpleNamespace(is_authenticated=True),
    )
    monkeypatch.setattr(
        fork_console_module,
        "current_app",
        SimpleNamespace(
            config={
                "CAP_BASE_URL": "/cap/",
                "CAP_ASSET_BASE_URL": "/cap/assets/",
                "CAP_SITE_KEY": "site-key",
            },
            logger=SimpleNamespace(exception=lambda *args, **kwargs: None),
        ),
    )
    monkeypatch.setattr(fork_console_module, "_issue_rq_engine_token", lambda: "rq-token")
    monkeypatch.setattr(
        fork_console_module,
        "render_template",
        lambda template, **context: {"template": template, **context},
    )

    context = fork_console_module.rq_fork_console("source-run", "cfg")

    assert context == {
        "template": "rq-fork-console.htm",
        "runid": "source-run",
        "config": "cfg",
        "undisturbify": expected_undisturbify,
        "skip_wepp_runs_output": expected_skip,
        "cap_base_url": "/cap",
        "cap_asset_base_url": "/cap/assets",
        "cap_site_key": "site-key",
        "rq_engine_token": "rq-token",
    }


def test_fork_console_route_anonymous_context_has_no_bearer_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(fork_console_module, "authorize", lambda runid, config: None)
    monkeypatch.setattr(fork_console_module, "request", SimpleNamespace(args={}))
    monkeypatch.setattr(
        fork_console_module,
        "current_user",
        SimpleNamespace(is_authenticated=False),
    )
    monkeypatch.setattr(
        fork_console_module,
        "current_app",
        SimpleNamespace(
            config={
                "CAP_BASE_URL": "/cap",
                "CAP_ASSET_BASE_URL": "/cap/assets",
                "CAP_SITE_KEY": "site-key",
            },
            logger=SimpleNamespace(exception=lambda *args, **kwargs: None),
        ),
    )
    monkeypatch.setattr(
        fork_console_module,
        "_issue_rq_engine_token",
        lambda: pytest.fail("anonymous route must not mint a bearer token"),
    )
    monkeypatch.setattr(
        fork_console_module,
        "render_template",
        lambda template, **context: context,
    )

    context = fork_console_module.rq_fork_console("public-run", "cfg")

    assert context["rq_engine_token"] is None
    assert context["undisturbify"] is False
    assert context["skip_wepp_runs_output"] is False
