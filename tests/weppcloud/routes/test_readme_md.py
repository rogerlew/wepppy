from __future__ import annotations

import importlib
from pathlib import Path
from types import SimpleNamespace

import pytest

pytest.importorskip("flask")
from flask import Flask

pytestmark = pytest.mark.routes


class _FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.hashes: dict[str, dict[str, str]] = {}

    def get(self, key: str):
        return self.values.get(key)

    def set(self, key: str, value: str, nx: bool = False, **_kwargs):
        if nx and key in self.values:
            return False
        if _kwargs.get("xx") and key not in self.values:
            return False
        self.values[key] = value
        return True

    def delete(self, key: str):
        self.values.pop(key, None)

    def eval(self, _script: str, _numkeys: int, key: str, owner: str):
        if self.values.get(key) == owner:
            self.delete(key)
            return 1
        return 0

    def pipeline(self):
        return self

    def hset(self, key: str, mapping: dict[str, str]):
        self.hashes.setdefault(key, {}).update(mapping)
        return self

    def hgetall(self, key: str):
        return dict(self.hashes.get(key, {}))

    def expire(self, _key: str, _ttl: int):
        return self

    def execute(self):
        return []


@pytest.fixture()
def readme_module():
    return importlib.reload(importlib.import_module("wepppy.weppcloud.routes.readme_md.readme_md"))


@pytest.fixture()
def readme_client(readme_module, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    run_root = tmp_path / "run"
    run_root.mkdir()
    ctx = SimpleNamespace(
        runid="run-1",
        config="cfg",
        run_root=run_root,
        active_root=run_root,
        pup_root=None,
        pup_relpath=None,
    )
    ron = SimpleNamespace(readonly=False, name="Initial", scenario="Base")

    app = Flask(__name__)
    app.config.update(TESTING=True, SECRET_KEY="readme-test", WTF_CSRF_ENABLED=False)
    app.register_blueprint(readme_module.readme_bp)

    monkeypatch.setattr(readme_module, "authorize", lambda runid, config: None)
    monkeypatch.setattr(readme_module, "load_run_context", lambda runid, config: ctx)
    monkeypatch.setattr(readme_module.Ron, "getInstance", lambda wd: ron)
    monkeypatch.setattr(readme_module, "_can_edit", lambda runid: True)
    fake_redis = _FakeRedis()
    monkeypatch.setattr(readme_module, "redis_readme_client", fake_redis)
    scope = readme_module._editor_scope(ctx)
    readme_module._record_editor_session("run-1", "cfg", scope, "a" * 32, ron)

    with app.test_client() as client:
        yield client, readme_module, run_root, ron


def test_save_requires_confirmed_editor_authority(
    readme_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, module, run_root, _ron = readme_client
    monkeypatch.setattr(module, "_can_edit", lambda runid: False)

    response = client.post(
        "/runs/run-1/cfg/readme/save",
        json={"markdown": "# denied", "uuid": "a" * 32, "revision": 1},
    )

    assert response.status_code == 403
    assert not (run_root / "README.md").exists()


def test_editor_requires_confirmed_editor_authority(
    readme_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, module, _run_root, _ron = readme_client
    monkeypatch.setattr(module, "_can_edit", lambda runid: False)

    response = client.get("/runs/run-1/cfg/readme-editor")

    assert response.status_code == 403


def test_save_rejects_readonly_before_write(readme_client) -> None:
    client, _module, run_root, ron = readme_client
    ron.readonly = True

    response = client.post(
        "/runs/run-1/cfg/readme/save",
        json={"markdown": "# denied", "uuid": "a" * 32, "revision": 1},
    )

    assert response.status_code == 409
    assert not (run_root / "README.md").exists()


def test_save_lock_mismatch_returns_conflict_and_preserves_file(
    readme_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, module, run_root, _ron = readme_client
    readme_path = run_root / "README.md"
    readme_path.write_text("# original", encoding="utf-8")
    monkeypatch.setattr(module, "_session_has_lock", lambda *args: False)

    response = client.post(
        "/runs/run-1/cfg/readme/save",
        json={"markdown": "# stale", "uuid": "b" * 32, "revision": 1},
    )

    assert response.status_code == 409
    assert response.get_json()["invalidated"] is True
    assert readme_path.read_text(encoding="utf-8") == "# original"


def test_save_persists_fixed_readme_and_returns_ron_update(
    readme_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, module, run_root, ron = readme_client
    monkeypatch.setattr(module, "_session_has_lock", lambda *args: True)
    monkeypatch.setattr(
        module,
        "_get_editor_state",
        lambda *args: {"ron_name": "Old", "ron_scenario": "Old scenario"},
    )
    ron.name = "Updated"
    ron.scenario = "Updated scenario"

    response = client.post(
        "/runs/run-1/cfg/readme/save",
        json={"markdown": "# persisted", "uuid": "a" * 32, "revision": 1},
    )

    assert response.status_code == 200
    assert response.get_json() == {
        "ronUpdate": {"name": "Updated", "scenario": "Updated scenario"}
    }
    assert (run_root / "README.md").read_text(encoding="utf-8") == "# persisted"

    raw = client.get(
        "/runs/run-1/cfg/readme/raw",
        headers={"X-Readme-Client": "a" * 32},
    )
    assert raw.get_json()["markdown"] == "# persisted"


def test_late_older_save_revision_cannot_overwrite_newer_text(readme_client) -> None:
    client, _module, run_root, _ron = readme_client

    newer = client.post(
        "/runs/run-1/cfg/readme/save",
        json={"markdown": "# newer", "uuid": "a" * 32, "revision": 2},
    )
    older = client.post(
        "/runs/run-1/cfg/readme/save",
        json={"markdown": "# older", "uuid": "a" * 32, "revision": 1},
    )

    assert newer.status_code == 200
    assert older.status_code == 409
    assert older.get_json()["reason"] == "stale_revision"
    assert (run_root / "README.md").read_text(encoding="utf-8") == "# newer"


def test_save_fails_closed_when_redis_coordination_is_unavailable(
    readme_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, module, run_root, _ron = readme_client
    monkeypatch.setattr(module, "redis_readme_client", None)

    response = client.post(
        "/runs/run-1/cfg/readme/save",
        json={"markdown": "# denied", "uuid": "a" * 32, "revision": 1},
    )

    assert response.status_code == 503
    assert not (run_root / "README.md").exists()


@pytest.mark.parametrize(
    "uuid_value",
    [None, "", "not-hex", "a" * 31, "a" * 33, "A" * 32],
)
def test_save_rejects_invalid_uuid_without_creating_redis_state(
    readme_client,
    uuid_value,
) -> None:
    client, module, run_root, _ron = readme_client
    hashes_before = dict(module.redis_readme_client.hashes)

    response = client.post(
        "/runs/run-1/cfg/readme/save",
        json={"markdown": "# denied", "uuid": uuid_value, "revision": 1},
    )

    assert response.status_code == 400
    assert module.redis_readme_client.hashes == hashes_before
    assert not (run_root / "README.md").exists()


@pytest.mark.parametrize("revision", [0, -1, True, 9_007_199_254_740_992])
def test_save_rejects_invalid_revision(readme_client, revision) -> None:
    client, _module, run_root, _ron = readme_client

    response = client.post(
        "/runs/run-1/cfg/readme/save",
        json={"markdown": "# denied", "uuid": "a" * 32, "revision": revision},
    )

    assert response.status_code == 400
    assert not (run_root / "README.md").exists()


@pytest.mark.parametrize("endpoint", ["save", "preview"])
@pytest.mark.parametrize("body", [[], "markdown", None])
def test_mutations_reject_non_object_json(readme_client, endpoint, body) -> None:
    client, _module, _run_root, _ron = readme_client

    response = client.post(f"/runs/run-1/cfg/readme/{endpoint}", json=body)

    assert response.status_code == 400


def test_preview_rejects_markdown_over_one_mib(readme_client) -> None:
    client, _module, _run_root, _ron = readme_client

    response = client.post(
        "/runs/run-1/cfg/readme/preview",
        json={"markdown": "x" * (1_048_576 + 1)},
    )

    assert response.status_code == 413


def test_preview_rejects_oversized_json_before_parsing(readme_client) -> None:
    client, _module, _run_root, _ron = readme_client

    response = client.post(
        "/runs/run-1/cfg/readme/preview",
        json={"markdown": "x" * 1_052_673},
    )

    assert response.status_code == 413


@pytest.mark.parametrize(
    "source",
    [
        "{{ 'x' * 2097152 }}",
        "{{ '%2097152s' % 'x' }}",
        "{{ 'x'|center(2097152) }}",
        "{{ range(4096)|join('x' * 1024) }}",
    ],
)
def test_markdown_template_blocks_compact_expansion(readme_module, source) -> None:
    context = {
        "runid": "run-1",
        "config": "cfg",
        "ron": SimpleNamespace(name="", scenario="", mods=[]),
        "run_record": None,
        "nodb": {},
    }

    html = readme_module._render_markdown(source, context)

    assert "README template failed to render" in html
    assert len(html.encode("utf-8")) <= readme_module.README_MAX_BYTES


def test_default_template_does_not_re_evaluate_config_as_jinja(
    readme_module,
    tmp_path: Path,
) -> None:
    ctx = SimpleNamespace(
        runid="run-1",
        config="{{ 'x' * 2097152 }}",
        active_root=tmp_path,
    )
    context = {
        "runid": ctx.runid,
        "config": ctx.config,
        "ron": SimpleNamespace(name="", scenario="", mods=[]),
        "run_record": None,
        "nodb": {},
    }

    source = readme_module._load_markdown(ctx)
    html = readme_module._render_markdown(source, context)

    assert len(html.encode("utf-8")) <= readme_module.README_MAX_BYTES
    assert "run-1" in html
    assert "{{ 'x' * 2097152 }}" in html
    assert "unknown" in html
    assert "Not set" in html
    assert "README template failed to render" not in html
    assert not (tmp_path / "README.md").exists()


def test_missing_readme_view_and_raw_do_not_create_file(
    readme_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, module, run_root, ron = readme_client
    monkeypatch.setattr(
        module,
        "_template_context",
        lambda ctx: {
            "runid": ctx.runid,
            "config": ctx.config,
            "ron": ron,
            "run_record": None,
            "nodb": {},
        },
    )
    monkeypatch.setattr(module, "render_template", lambda *args, **kwargs: "viewer")

    raw = client.get("/runs/run-1/cfg/readme/raw")
    viewer = client.get("/runs/run-1/cfg/README")

    assert raw.status_code == 200
    assert raw.get_json()["markdown"]
    assert viewer.status_code == 200
    assert not (run_root / "README.md").exists()


def test_raw_reports_stale_editor_lock(
    readme_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, module, run_root, _ron = readme_client
    (run_root / "README.md").write_text("# value", encoding="utf-8")
    monkeypatch.setattr(module, "_session_has_lock", lambda *args: False)

    response = client.get(
        "/runs/run-1/cfg/readme/raw",
        headers={"X-Readme-Client": "b" * 32},
    )

    assert response.status_code == 200
    assert response.get_json() == {"markdown": "# value", "locked_out": True}


def test_readme_target_rejects_symlink_escape(
    readme_client,
    tmp_path: Path,
) -> None:
    client, _module, run_root, _ron = readme_client
    outside = tmp_path / "outside.md"
    outside.write_text("outside", encoding="utf-8")
    (run_root / "README.md").symlink_to(outside)

    response = client.post(
        "/runs/run-1/cfg/readme/save",
        json={"markdown": "escaped", "uuid": "a" * 32, "revision": 1},
    )

    assert response.status_code == 400
    assert outside.read_text(encoding="utf-8") == "outside"


def test_markdown_renderer_omits_active_html_and_javascript(readme_module) -> None:
    context = {
        "runid": "run-1",
        "config": "cfg",
        "ron": SimpleNamespace(name="", scenario="", mods=[]),
        "run_record": None,
        "nodb": {},
    }

    html = readme_module._render_markdown(
        "<script>alert(1)</script>\n\n[x](javascript:alert(2))",
        context,
    )

    assert "<script" not in html
    assert "javascript:" not in html


def test_editor_lock_keys_are_scoped_per_active_run_root(
    readme_module,
    tmp_path: Path,
) -> None:
    base_root = tmp_path / "run"
    pup_root = base_root / "_pups" / "omni" / "scenarios" / "1"
    pup_root.mkdir(parents=True)
    base_ctx = SimpleNamespace(active_root=base_root, pup_relpath=None)
    pup_ctx = SimpleNamespace(active_root=pup_root, pup_relpath="omni/scenarios/1")

    assert readme_module._editor_lock_key(
        "run-1", "cfg", readme_module._editor_scope(base_ctx)
    ) != readme_module._editor_lock_key(
        "run-1", "cfg", readme_module._editor_scope(pup_ctx)
    )
    assert readme_module._editor_lock_key(
        "run-1", "cfg-a", readme_module._editor_scope(base_ctx)
    ) == readme_module._editor_lock_key(
        "run-1", "cfg-b", readme_module._editor_scope(base_ctx)
    )


def test_route_aliases_share_one_active_root_lock(
    readme_module,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    child_root = tmp_path / "_pups" / "omni" / "scenarios" / "one"
    child_root.mkdir(parents=True)
    legacy_ctx = SimpleNamespace(active_root=child_root, pup_relpath="omni/scenarios/one")
    composite_ctx = SimpleNamespace(active_root=child_root, pup_relpath=None)
    fake_redis = _FakeRedis()
    monkeypatch.setattr(readme_module, "redis_readme_client", fake_redis)
    ron = SimpleNamespace(name="", scenario="")
    scope = readme_module._editor_scope(legacy_ctx)
    assert scope == readme_module._editor_scope(composite_ctx)

    readme_module._record_editor_session(
        "run-1", "cfg-a", scope, "a" * 32, ron
    )

    assert readme_module._session_has_lock(
        "run-1;;omni;;one", "cfg-b", scope, "a" * 32
    ) is True
    assert readme_module._session_has_lock(
        "run-1;;omni;;one", "cfg-b", scope, "b" * 32
    ) is False


@pytest.mark.parametrize(
    ("route_runid", "query"),
    [
        ("run-1", "?pup=omni/scenarios/scenario-1"),
        ("run-1;;omni;;scenario-1", ""),
    ],
)
def test_legacy_and_composite_omni_urls_share_parent_owner_and_active_root_lock(
    readme_client,
    monkeypatch: pytest.MonkeyPatch,
    route_runid: str,
    query: str,
) -> None:
    client, module, run_root, ron = readme_client
    child_root = run_root / "_pups" / "omni" / "scenarios" / "scenario-1"
    child_root.mkdir(parents=True)
    ctx = SimpleNamespace(
        runid=route_runid,
        config="cfg",
        run_root=run_root if ";;" not in route_runid else child_root,
        active_root=child_root,
        pup_root=child_root if ";;" not in route_runid else None,
        pup_relpath="omni/scenarios/scenario-1" if ";;" not in route_runid else None,
    )
    monkeypatch.setattr(module, "load_run_context", lambda runid, config: ctx)
    identity_runid, scope = module._editor_identity(route_runid, ctx)
    assert identity_runid == "run-1"
    omni_uuid = "c" * 32
    module._record_editor_session(identity_runid, "cfg", scope, omni_uuid, ron)

    response = client.post(
        f"/runs/{route_runid}/cfg/readme/save{query}",
        json={"markdown": "# child", "uuid": omni_uuid, "revision": 1},
    )

    assert response.status_code == 200
    assert (child_root / "README.md").read_text(encoding="utf-8") == "# child"


def test_record_editor_session_invalidates_previous_client(
    readme_module,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_redis = _FakeRedis()
    monkeypatch.setattr(readme_module, "redis_readme_client", fake_redis)
    ron = SimpleNamespace(name="Name", scenario="Scenario")
    scope = "scope"

    first_uuid = "1" * 32
    second_uuid = "2" * 32
    readme_module._record_editor_session("run-1", "cfg", scope, first_uuid, ron)
    readme_module._record_editor_session("run-1", "cfg", scope, second_uuid, ron)

    assert readme_module._session_has_lock("run-1", "cfg", scope, second_uuid) is True
    assert readme_module._session_has_lock("run-1", "cfg", scope, first_uuid) is False
    first_key = readme_module._editor_client_key("run-1", "cfg", scope, first_uuid)
    assert fake_redis.hashes[first_key]["status"] == "stale"
