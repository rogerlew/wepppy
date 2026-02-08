from __future__ import annotations

from pathlib import Path

import pytest

from wepppy.nodb.core.wepp import BOOTSTRAP_JWT_EXPIRES_SECONDS, Wepp
from wepppy.weppcloud.utils import auth_tokens

pytestmark = pytest.mark.unit


def _make_detached_wepp(wd: Path) -> Wepp:
    wepp = object.__new__(Wepp)
    wepp.wd = str(wd)
    return wepp


def test_mint_bootstrap_jwt_uses_six_month_expiry(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    run_root = tmp_path / "ab-run"
    run_root.mkdir()
    wepp = _make_detached_wepp(run_root)

    monkeypatch.setenv("EXTERNAL_HOST", "wepp.cloud")
    monkeypatch.delenv("OAUTH_REDIRECT_HOST", raising=False)

    captured: dict[str, object] = {}

    def _issue_token(
        subject: str,
        *,
        audience: str | None = None,
        expires_in: int = 0,
        extra_claims: dict[str, str] | None = None,
    ) -> dict[str, str]:
        captured["subject"] = subject
        captured["audience"] = audience
        captured["expires_in"] = expires_in
        captured["extra_claims"] = extra_claims or {}
        return {"token": "signed-jwt"}

    monkeypatch.setattr(auth_tokens, "issue_token", _issue_token)

    clone_url = wepp.mint_bootstrap_jwt("user@example.com", "42")

    assert captured["subject"] == "user@example.com"
    assert captured["audience"] == "wepp.cloud"
    assert captured["expires_in"] == BOOTSTRAP_JWT_EXPIRES_SECONDS
    assert captured["extra_claims"] == {"runid": "ab-run"}
    assert clone_url == "https://42:signed-jwt@wepp.cloud/git/ab/ab-run/.git"


def test_install_bootstrap_hook_uses_source_root_env(tmp_path: Path) -> None:
    run_root = tmp_path / "ab-run"
    git_dir = run_root / ".git"
    git_dir.mkdir(parents=True)
    wepp = _make_detached_wepp(run_root)

    wepp._install_bootstrap_hook()

    hook_path = git_dir / "hooks" / "pre-receive"
    hook_text = hook_path.read_text(encoding="utf-8")

    assert "WEPPPY_SOURCE_ROOT" in hook_text
    assert "/workdir/wepppy" not in hook_text
