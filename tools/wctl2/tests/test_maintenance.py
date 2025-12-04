from __future__ import annotations

import pytest

from tools.wctl2.commands import maintenance
from tools.wctl2.context import CLIContext


pytestmark = pytest.mark.unit


def test_resolve_runtime_uid_gid_prefers_env_values(temp_project, monkeypatch: pytest.MonkeyPatch) -> None:
    context = CLIContext.from_environ(project_dir=str(temp_project))

    def _fail_lookup(_name: str) -> str:
        raise AssertionError("Lookup should not be used when env supplies UID/GID")

    monkeypatch.setattr(maintenance, "_lookup_user_uid", _fail_lookup)
    monkeypatch.setattr(maintenance, "_lookup_group_gid", _fail_lookup)

    uid, gid = maintenance._resolve_runtime_uid_gid(context)

    assert uid == "1000"
    assert gid == "993"


def test_resolve_runtime_uid_gid_falls_back_to_rogers_ids(temp_project, monkeypatch: pytest.MonkeyPatch) -> None:
    context = CLIContext.from_environ(project_dir=str(temp_project))

    monkeypatch.setattr(context, "env_value", lambda key, default=None: None)
    monkeypatch.setattr(maintenance, "_lookup_user_uid", lambda username: "1100")
    monkeypatch.setattr(maintenance, "_lookup_group_gid", lambda group: "2200")

    uid, gid = maintenance._resolve_runtime_uid_gid(context)

    assert uid == "1100"
    assert gid == "2200"


def test_resolve_runtime_uid_gid_defaults_when_lookup_missing(temp_project, monkeypatch: pytest.MonkeyPatch) -> None:
    context = CLIContext.from_environ(project_dir=str(temp_project))

    monkeypatch.setattr(context, "env_value", lambda key, default=None: None)
    monkeypatch.setattr(maintenance, "_lookup_user_uid", lambda username: None)
    monkeypatch.setattr(maintenance, "_lookup_group_gid", lambda group: None)

    uid, gid = maintenance._resolve_runtime_uid_gid(context)

    assert uid == "1000"
    assert gid == "993"
