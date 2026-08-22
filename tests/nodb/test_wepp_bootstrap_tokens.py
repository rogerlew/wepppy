from __future__ import annotations

from pathlib import Path
import subprocess

import pytest

from wepppy.nodb.core.wepp import BOOTSTRAP_JWT_EXPIRES_SECONDS, Wepp
from wepppy.nodb.core import wepp_bootstrap_service
from wepppy.nodb.core.wepp_bootstrap_service import WeppBootstrapService
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


def test_optimize_bootstrap_repository_uses_wepppy_cpu_budget(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_root = tmp_path / "ab-run"
    run_root.mkdir()
    wepp = _make_detached_wepp(run_root)
    wepp.logger = type("Logger", (), {"info": lambda *args: None})()
    calls: list[list[str]] = []
    service = WeppBootstrapService()

    monkeypatch.setattr(wepp_bootstrap_service, "NCPU", 12)
    monkeypatch.setattr(service, "run_git", lambda _wepp, args: calls.append(args))

    service.optimize_bootstrap_repository(wepp)

    assert calls == [
        [
            "-c",
            "pack.threads=12",
            "-c",
            "repack.writeBitmaps=true",
            "gc",
        ]
    ]


def test_optimize_bootstrap_repository_preserves_ref_and_content(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_root = tmp_path / "ab-run"
    run_root.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=run_root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=run_root, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=run_root, check=True)
    tracked = run_root / "wepp" / "runs" / "input.run"
    tracked.parent.mkdir(parents=True)
    tracked.write_text("input\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=run_root, check=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=run_root, check=True, capture_output=True)

    wepp = _make_detached_wepp(run_root)
    wepp.logger = type("Logger", (), {"info": lambda *args: None})()
    service = WeppBootstrapService()
    before_sha = service.run_git(wepp, ["rev-parse", "HEAD"]).stdout.strip()

    monkeypatch.setattr(wepp_bootstrap_service, "NCPU", 2)
    service.optimize_bootstrap_repository(wepp)

    assert service.run_git(wepp, ["rev-parse", "HEAD"]).stdout.strip() == before_sha
    assert tracked.read_text(encoding="utf-8") == "input\n"
    assert list((run_root / ".git" / "objects" / "pack").glob("*.pack"))
    assert list((run_root / ".git" / "objects" / "pack").glob("*.bitmap"))


def test_init_bootstrap_does_not_enable_when_maintenance_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_root = tmp_path / "ab-run"
    run_root.mkdir()
    wepp = _make_detached_wepp(run_root)
    wepp.bootstrap_enabled = False
    wepp.logger = type("Logger", (), {"info": lambda *args: None})()
    wepp._bootstrap_repo_exists = lambda: True
    wepp._bootstrap_git_dir = lambda: str(run_root / ".git")
    service = WeppBootstrapService()

    monkeypatch.setattr(service, "run_git", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(service, "write_bootstrap_gitignore", lambda _wepp: None)
    monkeypatch.setattr(service, "install_bootstrap_hook", lambda _wepp: None)
    monkeypatch.setattr(
        service,
        "optimize_bootstrap_repository",
        lambda _wepp: (_ for _ in ()).throw(RuntimeError("maintenance failed")),
    )

    with pytest.raises(RuntimeError, match="maintenance failed"):
        service.init_bootstrap(wepp)

    assert wepp.bootstrap_enabled is False
