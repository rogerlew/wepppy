from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil

import pytest

import wepppy.nodb.project_config_snapshot as snapshot
from wepppy.nodb.project_config_reader import load_project_config
from wepppy.nodb.base import CaseSensitiveRawConfigParser
from wepppy.project_config_sanitization import scan_path
from wepppy.project_config_serialization import parse_config_text

pytestmark = pytest.mark.unit

FIXED_TIME = datetime(2026, 8, 26, 20, 0, tzinfo=timezone.utc)


def test_writer_flag_is_strict_and_default_off() -> None:
    assert snapshot.preset_writer_enabled({}) is False
    assert snapshot.preset_writer_enabled({snapshot.PRESET_WRITER_FLAG: "YES"}) is True
    with pytest.raises(ValueError, match=snapshot.PRESET_WRITER_FLAG):
        snapshot.preset_writer_enabled({snapshot.PRESET_WRITER_FLAG: "maybe"})


def test_policy_corpus_explicitly_covers_every_named_preset() -> None:
    policies = snapshot.load_preset_policies()
    config_ids = {
        path.stem
        for path in snapshot.CONFIGS_ROOT.glob("*.cfg")
        if path.stem != "_defaults"
    }

    assert set(policies) == config_ids
    assert len(policies) == 128
    assert all(policy.overrides for policy in policies.values())


def test_every_named_preset_resolves_complete_canonical_safe_bytes() -> None:
    policies = snapshot.load_preset_policies()

    for preset_id in policies:
        candidate = snapshot.resolve_preset_snapshot(
            preset_id,
            {},
            source_revision="test-revision",
            resolved_at=FIXED_TIME,
            policies=policies,
        )
        parsed = parse_config_text(candidate.config_bytes.decode("utf-8"))
        manifest = json.loads(candidate.manifest_bytes)
        assert parsed["config"] == {
            "flattened": True,
            "resolver_version": 1,
            "schema_version": 1,
        }
        assert manifest["source_preset"] == preset_id
        assert manifest["config"]["filename"] == f"{preset_id}.cfg"
        assert manifest["config"]["sha256"] == hashlib.sha256(candidate.config_bytes).hexdigest()


def test_override_is_typed_materialized_and_recorded_after_parent_chain() -> None:
    candidate = snapshot.resolve_preset_snapshot(
        "disturbed9002",
        {
            "general:dem_db": "ned1/2016",
            "unitizer:is_english": "true",
            "nodb:apply_nodir": "false",
        },
        source_revision="test-revision",
        resolved_at=FIXED_TIME,
    )
    config = parse_config_text(candidate.config_bytes.decode())
    manifest = json.loads(candidate.manifest_bytes)

    assert config["general"]["dem_db"] == "ned1/2016"
    assert config["unitizer"]["is_english"] is True
    assert manifest["selections"]["overrides"]["unitizer.is_english"] == {
        "source": "query",
        "value": True,
    }
    assert [parent["kind"] for parent in manifest["parent_chain"]] == [
        "defaults",
        "preset",
    ]


@pytest.mark.parametrize(
    "overrides",
    [
        {"api_token": "secret"},
        {"unitizer:is_english": "yes"},
        {"general:dem_db": "arbitrary/path"},
        {"watershed:delineation_backend": "tau"},
    ],
)
def test_unknown_or_unsupported_overrides_fail_closed(overrides: dict[str, str]) -> None:
    with pytest.raises(snapshot.PresetSnapshotError):
        snapshot.resolve_preset_snapshot(
            "disturbed9002",
            overrides,
            source_revision="test-revision",
        )


def test_snapshot_bytes_are_independent_from_later_shared_source_changes(tmp_path: Path) -> None:
    configs = tmp_path / "configs"
    shutil.copytree(snapshot.CONFIGS_ROOT, configs, symlinks=True)
    policies = snapshot.load_preset_policies(configs_root=configs)
    candidate = snapshot.resolve_preset_snapshot(
        "disturbed9002",
        {},
        source_revision="test-revision",
        resolved_at=FIXED_TIME,
        configs_root=configs,
        policies=policies,
    )
    before = candidate.config_bytes

    (configs / "disturbed9002.cfg").write_text("[general]\ndem_db = \"changed\"\n", encoding="utf-8")
    assert candidate.config_bytes == before


def test_materialized_pair_reopens_through_wp02_reader_without_shared_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_root = tmp_path / "run"
    run_root.mkdir()
    candidate = snapshot.resolve_preset_snapshot(
        "disturbed9002",
        {},
        source_revision="test-revision",
        resolved_at=FIXED_TIME,
    )
    config_path, manifest_path = snapshot.materialize_preset_snapshot(run_root, candidate)
    monkeypatch.setenv("WEPPPY_PROJECT_CONFIG_READER_ENABLED", "1")

    result = load_project_config(
        wd=run_root,
        config_token="disturbed9002",
        parent_wd=None,
        config_dir=tmp_path / "missing-shared",
        defaults_resolver=lambda _wd=None: str(tmp_path / "missing-defaults.cfg"),
        parser_factory=CaseSensitiveRawConfigParser,
        run_id="fixture-run",
    )

    assert result.status.mode == "flattened"
    assert result.status.manifest_valid is True
    assert result.status.warnings == ()
    assert config_path.read_bytes() == candidate.config_bytes
    assert manifest_path.read_bytes() == candidate.manifest_bytes
    assert scan_path(run_root) == ()


def test_materializer_refuses_overwrite_and_cleans_partial_pair(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    candidate = snapshot.resolve_preset_snapshot(
        "disturbed9002",
        {},
        source_revision="test-revision",
        resolved_at=FIXED_TIME,
    )
    real_replace = os.replace
    calls = 0

    def fail_second_replace(source: str | Path, target: str | Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("injected manifest replace failure")
        real_replace(source, target)

    monkeypatch.setattr(snapshot.os, "replace", fail_second_replace)
    with pytest.raises(snapshot.PresetSnapshotError):
        snapshot.materialize_preset_snapshot(tmp_path, candidate)

    assert not (tmp_path / "disturbed9002.cfg").exists()
    assert not (tmp_path / "config-manifest.json").exists()
    assert list(tmp_path.iterdir()) == []

    monkeypatch.setattr(snapshot.os, "replace", real_replace)
    (tmp_path / "disturbed9002.cfg").write_text("existing", encoding="utf-8")
    with pytest.raises(snapshot.PresetSnapshotError, match="already exist"):
        snapshot.materialize_preset_snapshot(tmp_path, candidate)
