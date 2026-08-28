from __future__ import annotations

import configparser
import hashlib
import json
import logging
from pathlib import Path

import pytest

import wepppy.nodb.base as base
from wepppy.nodb.project_config_reader import (
    PROJECT_CONFIG_READER_FLAG,
    ProjectConfigAuthorityError,
    ProjectConfigSchemaError,
    load_project_config,
    project_config_reader_enabled,
)

pytestmark = pytest.mark.unit


def _write_defaults(path: Path, source: str = "shared") -> None:
    path.write_text(
        f"[values]\nsource = {source}\ndefault_only = retained\n"
        "[nodb]\nmods = []\n",
        encoding="utf-8",
    )


def _write_config(
    path: Path,
    *,
    source: str = "project",
    flattened: str | None = "true",
    schema_version: str = "1",
    resolver_version: str = "1",
) -> None:
    marker = ""
    if flattened is not None:
        marker = (
            "[config]\n"
            f"schema_version = {schema_version}\n"
            f"flattened = {flattened}\n"
            f"resolver_version = {resolver_version}\n"
        )
    path.write_text(
        marker + f"[values]\nsource = {source}\n[nodb]\nmods = []\n",
        encoding="utf-8",
    )


def _manifest_payload(config_path: Path, **updates: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": 1,
        "resolver_version": 1,
        "source_kind": "preset",
        "source_preset": config_path.stem,
        "source_revision": "abc123",
        "resolved_at": "2026-08-26T18:15:00Z",
        "parent_chain": [
            {"kind": "defaults", "id": "shared-defaults", "revision": "abc123"},
            {"kind": "preset", "id": config_path.stem, "revision": "abc123"},
        ],
        "selections": {"overrides": {}},
        "config": {
            "filename": config_path.name,
            "sha256": hashlib.sha256(config_path.read_bytes()).hexdigest(),
        },
        "amendments": [],
    }
    payload.update(updates)
    return payload


def _write_manifest(root: Path, config_path: Path, **updates: object) -> Path:
    path = root / "config-manifest.json"
    path.write_text(json.dumps(_manifest_payload(config_path, **updates)), encoding="utf-8")
    return path


def _load(
    root: Path,
    shared: Path,
    *,
    token: str = "preset",
    parent_wd: Path | None = None,
):
    return load_project_config(
        wd=root,
        config_token=token,
        parent_wd=parent_wd,
        config_dir=shared,
        defaults_resolver=lambda wd=None: str(Path(wd or root) / "_defaults.cfg")
        if (Path(wd or root) / "_defaults.cfg").exists()
        else str(shared / "_defaults.cfg"),
        parser_factory=base.CaseSensitiveRawConfigParser,
        run_id="fixture-run",
    )


@pytest.fixture
def roots(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "fixture-run"
    shared = tmp_path / "shared"
    root.mkdir()
    shared.mkdir()
    _write_defaults(shared / "_defaults.cfg")
    _write_config(shared / "preset.cfg", source="shared-preset", flattened=None)
    return root, shared


@pytest.mark.parametrize(
    ("value", "expected"),
    [(None, False), ("0", False), ("false", False), ("1", True), ("YES", True)],
)
def test_reader_flag_is_explicit_and_default_off(value: str | None, expected: bool) -> None:
    environ = {} if value is None else {PROJECT_CONFIG_READER_FLAG: value}
    assert project_config_reader_enabled(environ) is expected


def test_reader_flag_rejects_ambiguous_value() -> None:
    with pytest.raises(ValueError, match=PROJECT_CONFIG_READER_FLAG):
        project_config_reader_enabled({PROJECT_CONFIG_READER_FLAG: "maybe"})


def test_flattened_config_loads_alone_and_preserves_stable_token(
    roots: tuple[Path, Path],
) -> None:
    root, shared = roots
    config = root / "preset.cfg"
    _write_config(config)
    _write_manifest(root, config)

    result = _load(root, shared, token="preset?values:source=query-override")

    assert result.parser.get("values", "source") == "project"
    assert not result.parser.has_option("values", "default_only")
    assert result.status.mode == "flattened"
    assert result.status.config_filename == "preset.cfg"
    assert result.status.manifest_valid is True
    assert result.status.updates_enabled is True
    assert result.status.warnings == ()


@pytest.mark.parametrize(
    ("token", "source_kind", "source_preset"),
    [
        ("config", "builder", None),
        ("disturbed9002_wbt", "preset", "disturbed9002_wbt"),
    ],
    ids=["builder-config-filename", "named-preset-basename"],
)
def test_manifest_v1_accepts_builder_preset_and_copied_fork_provenance(
    roots: tuple[Path, Path],
    token: str,
    source_kind: str,
    source_preset: str | None,
) -> None:
    root, shared = roots
    config = root / f"{token}.cfg"
    _write_config(config)
    _write_manifest(
        root,
        config,
        source_kind=source_kind,
        source_preset=source_preset,
    )

    result = _load(root, shared, token=token)

    assert result.status.config_filename == config.name
    assert result.status.manifest_valid is True
    assert result.status.updates_enabled is True


def test_copied_fork_pair_retains_manifest_v1_provenance(
    roots: tuple[Path, Path], tmp_path: Path
) -> None:
    source_root, shared = roots
    source_config = source_root / "preset.cfg"
    _write_config(source_config)
    source_manifest = _write_manifest(source_root, source_config)
    fork_root = tmp_path / "fork-run"
    fork_root.mkdir()
    fork_config = fork_root / source_config.name
    fork_config.write_bytes(source_config.read_bytes())
    (fork_root / "config-manifest.json").write_bytes(source_manifest.read_bytes())

    result = _load(fork_root, shared)

    assert result.status.manifest_valid is True
    assert result.status.updates_enabled is True
    assert result.parser.get("values", "source") == "project"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("resolver_version", 2),
        ("source_kind", ""),
        ("source_kind", "unknown"),
        ("source_revision", None),
        ("resolved_at", "not-a-timestamp"),
        ("parent_chain", []),
        ("selections", []),
        ("amendments", {}),
    ],
)
def test_manifest_v1_rejects_missing_or_malformed_common_fields(
    roots: tuple[Path, Path], field: str, value: object
) -> None:
    root, shared = roots
    config = root / "preset.cfg"
    _write_config(config)
    _write_manifest(root, config, **{field: value})

    result = _load(root, shared)

    assert result.status.manifest_valid is False
    assert result.status.updates_enabled is False
    assert result.status.warnings[0].code == "manifest_invalid"


@pytest.mark.parametrize(
    ("flattened", "schema", "resolver"),
    [("not-bool", "1", "1"), ("true", "2", "1"), ("true", "1", "2"), ("true", "x", "1")],
)
def test_recognized_flattened_schema_fails_without_shared_fallback(
    roots: tuple[Path, Path], flattened: str, schema: str, resolver: str
) -> None:
    root, shared = roots
    _write_config(
        root / "preset.cfg",
        flattened=flattened,
        schema_version=schema,
        resolver_version=resolver,
    )

    with pytest.raises(ProjectConfigSchemaError):
        _load(root, shared)


def test_malformed_flattened_candidate_fails_without_shared_fallback(
    roots: tuple[Path, Path],
) -> None:
    root, shared = roots
    (root / "preset.cfg").write_text("not-an-ini\n", encoding="utf-8")

    with pytest.raises(configparser.MissingSectionHeaderError):
        _load(root, shared)


def test_enabled_legacy_reader_preserves_missing_file_exception(
    roots: tuple[Path, Path]
) -> None:
    root, shared = roots
    (shared / "preset.cfg").unlink()

    with pytest.raises(FileNotFoundError) as exc_info:
        _load(root, shared)

    assert Path(exc_info.value.filename) == shared / "preset.cfg"


def test_enabled_legacy_reader_preserves_malformed_override_exception(
    roots: tuple[Path, Path]
) -> None:
    root, shared = roots

    with pytest.raises(ValueError):
        _load(root, shared, token="preset?values:source=a=b")


def test_legacy_reader_rejects_locale_override_before_config_load(
    roots: tuple[Path, Path]
) -> None:
    root, shared = roots

    with pytest.raises(
        ProjectConfigAuthorityError,
        match="may not set general.locales",
    ):
        _load(root, shared, token='preset?general:locales=["eu"]')


def test_enabled_legacy_reader_preserves_absolute_config_path(
    roots: tuple[Path, Path], tmp_path: Path
) -> None:
    root, shared = roots
    external = tmp_path / "external-legacy.cfg"
    _write_config(external, source="absolute", flattened=None)

    result = _load(root, shared, token=str(external))

    assert result.status.mode == "legacy"
    assert result.parser.get("values", "source") == "absolute"


def test_unmarked_local_config_retains_defaults_layering_and_overrides(
    roots: tuple[Path, Path],
) -> None:
    root, shared = roots
    _write_defaults(root / "_defaults.cfg", "local-default")
    _write_config(root / "preset.cfg", source="local-preset", flattened=None)

    result = _load(root, shared, token="preset?values:source=query")

    assert result.status.mode == "legacy"
    assert result.parser.get("values", "source") == "query"
    assert result.parser.get("values", "default_only") == "retained"


@pytest.mark.parametrize(
    ("manifest_state", "warning_code"),
    [
        ("missing", "manifest_missing"),
        ("malformed", "manifest_unsafe_or_malformed"),
        ("wrong_filename", "manifest_invalid"),
        ("newer", "manifest_schema_newer"),
        ("secret", "manifest_unsafe_or_malformed"),
    ],
)
def test_invalid_manifest_degrades_without_shared_fallback_or_mutation(
    roots: tuple[Path, Path], manifest_state: str, warning_code: str
) -> None:
    root, shared = roots
    config = root / "preset.cfg"
    _write_config(config)
    manifest = root / "config-manifest.json"
    if manifest_state == "malformed":
        manifest.write_text("{broken", encoding="utf-8")
    elif manifest_state == "wrong_filename":
        payload = _manifest_payload(config)
        payload["config"] = dict(payload["config"], filename="other.cfg")
        manifest.write_text(json.dumps(payload), encoding="utf-8")
    elif manifest_state == "newer":
        _write_manifest(root, config, schema_version=2)
    elif manifest_state == "secret":
        _write_manifest(root, config, bearer_token="redacted-fixture-value")

    before = {path.name: path.read_bytes() for path in root.iterdir()}
    result = _load(root, shared)
    after = {path.name: path.read_bytes() for path in root.iterdir()}

    assert result.parser.get("values", "source") == "project"
    assert result.status.manifest_valid is False
    assert result.status.updates_enabled is False
    assert [warning.code for warning in result.status.warnings] == [warning_code]
    assert before == after


def test_digest_mismatch_is_structured_warning_only_and_updates_remain_enabled(
    roots: tuple[Path, Path], caplog: pytest.LogCaptureFixture
) -> None:
    root, shared = roots
    config = root / "preset.cfg"
    _write_config(config)
    manifest = _write_manifest(root, config)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    declared = "0" * 64
    payload["config"]["sha256"] = declared
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    controller = object.__new__(base.NoDbBase)
    controller.wd = str(root)
    controller._config = "preset"

    with caplog.at_level(logging.WARNING), pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setenv(PROJECT_CONFIG_READER_FLAG, "1")
        monkeypatch.setattr(base, "_config_dir", str(shared))
        monkeypatch.setattr(base, "_default_config", str(shared / "_defaults.cfg"))
        first = controller._configparser
        second = controller._configparser

    status = controller.project_config_status
    warning = status.warnings[0]
    assert first.get("values", "source") == second.get("values", "source") == "project"
    assert status.manifest_valid is True
    assert status.updates_enabled is True
    assert warning.code == "config_digest_mismatch"
    assert warning.run_id == "fixture-run"
    assert warning.config_filename == "preset.cfg"
    assert warning.declared_digest == declared
    assert warning.observed_digest == hashlib.sha256(config.read_bytes()).hexdigest()
    records = [record for record in caplog.records if "project_config_warning" in record.message]
    assert len(records) == 1
    assert "[values]" not in records[0].getMessage()


def test_facade_flag_off_preserves_legacy_reader(
    roots: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    root, shared = roots
    _write_config(root / "preset.cfg")
    controller = object.__new__(base.NoDbBase)
    controller.wd = str(root)
    controller._config = "preset"
    monkeypatch.delenv(PROJECT_CONFIG_READER_FLAG, raising=False)
    monkeypatch.setattr(base, "_config_dir", str(shared))
    monkeypatch.setattr(base, "_default_config", str(shared / "_defaults.cfg"))
    monkeypatch.setattr(base, "_legacy_default_config", str(shared / "_defaults.toml"))

    parser = controller._configparser

    assert parser.get("values", "source") == "project"
    assert parser.get("values", "default_only") == "retained"
    assert controller.project_config_status.mode == "legacy"


def test_nested_legacy_child_config_retains_precedence(roots: tuple[Path, Path]) -> None:
    parent, shared = roots
    child = parent / "_pups" / "child"
    child.mkdir(parents=True)
    _write_config(parent / "preset.cfg", source="parent", flattened=None)
    _write_config(child / "preset.cfg", source="child", flattened=None)

    result = _load(child, shared, parent_wd=parent)

    assert result.status.mode == "legacy"
    assert result.parser.get("values", "source") == "child"


def test_nested_controller_inherits_validated_parent_flattened_config(
    roots: tuple[Path, Path],
) -> None:
    parent, shared = roots
    child = parent / "_pups" / "child"
    child.mkdir(parents=True)
    config = parent / "preset.cfg"
    _write_config(config, source="parent")
    _write_manifest(parent, config)

    result = _load(child, shared, parent_wd=parent)

    assert result.status.mode == "flattened"
    assert result.status.authority_root == str(parent.resolve())
    assert result.parser.get("values", "source") == "parent"
    assert not (child / "preset.cfg").exists()
    assert not (child / "config-manifest.json").exists()


def test_nested_child_flattened_config_is_rejected(roots: tuple[Path, Path]) -> None:
    parent, shared = roots
    child = parent / "_pups" / "child"
    child.mkdir(parents=True)
    _write_config(child / "preset.cfg")

    with pytest.raises(ProjectConfigAuthorityError, match="cannot own"):
        _load(child, shared, parent_wd=parent)


def test_flattened_config_symlink_cannot_escape_authority_root(
    roots: tuple[Path, Path], tmp_path: Path
) -> None:
    root, shared = roots
    external = tmp_path / "external.cfg"
    _write_config(external)
    (root / "preset.cfg").symlink_to(external)

    with pytest.raises(ProjectConfigAuthorityError, match="direct child"):
        _load(root, shared)


def test_manifest_symlink_escape_degrades_without_reading_as_authority(
    roots: tuple[Path, Path], tmp_path: Path
) -> None:
    root, shared = roots
    config = root / "preset.cfg"
    _write_config(config)
    external_manifest = tmp_path / "external-manifest.json"
    external_manifest.write_text(json.dumps(_manifest_payload(config)), encoding="utf-8")
    (root / "config-manifest.json").symlink_to(external_manifest)

    result = _load(root, shared)

    assert result.parser.get("values", "source") == "project"
    assert result.status.manifest_valid is False
    assert result.status.updates_enabled is False
    assert result.status.warnings[0].code == "manifest_authority_invalid"


@pytest.mark.parametrize("parent_name", ["sibling", "fixture"])
def test_nested_parent_must_be_real_ancestor_not_string_prefix(
    tmp_path: Path, parent_name: str
) -> None:
    parent = tmp_path / parent_name
    child = tmp_path / "fixture-run2" / "_pups" / "child"
    shared = tmp_path / "shared"
    parent.mkdir()
    child.mkdir(parents=True)
    shared.mkdir()
    _write_defaults(shared / "_defaults.cfg")
    _write_config(shared / "preset.cfg", flattened=None)

    with pytest.raises(ProjectConfigAuthorityError, match="does not contain"):
        _load(child, shared, parent_wd=parent)


def test_pup_relpath_uses_path_containment_not_prefix(tmp_path: Path) -> None:
    parent = tmp_path / "run"
    real_child = parent / "_pups" / "child"
    prefix_sibling = tmp_path / "run2" / "_pups" / "child"
    real_child.mkdir(parents=True)
    prefix_sibling.mkdir(parents=True)

    controller = object.__new__(base.NoDbBase)
    controller.parent_wd = str(parent)
    controller.wd = str(real_child)
    assert controller.pup_relpath == str(Path("_pups") / "child")

    controller.wd = str(prefix_sibling)
    assert controller.pup_relpath is None
