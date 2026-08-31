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
        assert parsed["capabilities"]["climate_datasets"]
        assert parsed["capabilities"]["soil_builders"] == [
            "gridded",
            "single_mukey",
            "single_database",
        ]
        assert parsed["capabilities"]["landuse_datasets"]
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


def test_schema_v1_preset_projection_requires_exact_canonical_replay(
    tmp_path: Path,
) -> None:
    candidate = snapshot.resolve_preset_snapshot(
        "eu-disturbed",
        {},
        source_revision="descriptive-only",
        resolved_at=FIXED_TIME,
    )
    snapshot.materialize_preset_snapshot(tmp_path, candidate)

    assert snapshot.resolve_preset_locale_projection(
        tmp_path,
        "eu-disturbed.cfg",
    ) == "europe"

    manifest_path = tmp_path / "config-manifest.json"
    manifest = json.loads(manifest_path.read_bytes())
    manifest["source_revision"] = "changed-descriptive-provenance"
    manifest_path.write_text(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    assert snapshot.resolve_preset_locale_projection(
        tmp_path,
        "eu-disturbed.cfg",
    ) == "europe"


def test_schema_v1_preset_projection_replays_typed_boolean_overrides(
    tmp_path: Path,
) -> None:
    candidate = snapshot.resolve_preset_snapshot(
        "disturbed9002",
        {"unitizer:is_english": "false", "nodb:apply_nodir": "true"},
        source_revision="descriptive-only",
        resolved_at=FIXED_TIME,
    )
    snapshot.materialize_preset_snapshot(tmp_path, candidate)

    assert snapshot.resolve_preset_locale_projection(
        tmp_path,
        "disturbed9002.cfg",
    ) == "continental-us"


@pytest.mark.parametrize("forged_value", ["false", ["false"]])
def test_schema_v1_preset_projection_rejects_forged_override_value_types(
    tmp_path: Path,
    forged_value: object,
) -> None:
    candidate = snapshot.resolve_preset_snapshot(
        "disturbed9002",
        {"unitizer:is_english": "false"},
        source_revision="descriptive-only",
        resolved_at=FIXED_TIME,
    )
    _config_path, manifest_path = snapshot.materialize_preset_snapshot(
        tmp_path,
        candidate,
    )
    manifest = json.loads(manifest_path.read_bytes())
    manifest["selections"]["overrides"]["unitizer.is_english"]["value"] = forged_value
    manifest_path.write_text(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )

    assert snapshot.resolve_preset_locale_projection(
        tmp_path,
        "disturbed9002.cfg",
    ) is None


def test_schema_v1_preset_projection_rejects_drift_and_self_asserted_forgery(
    tmp_path: Path,
) -> None:
    candidate = snapshot.resolve_preset_snapshot(
        "eu-disturbed",
        {},
        source_revision="test-revision",
        resolved_at=FIXED_TIME,
    )
    config_path, manifest_path = snapshot.materialize_preset_snapshot(tmp_path, candidate)
    original_manifest = json.loads(manifest_path.read_bytes())

    parent_drift = dict(original_manifest)
    parent_drift["parent_chain"] = [
        dict(parent) for parent in original_manifest["parent_chain"]
    ]
    parent_drift["parent_chain"][1]["revision"] = "0" * 64
    manifest_path.write_text(
        json.dumps(parent_drift, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    assert snapshot.resolve_preset_locale_projection(tmp_path, "eu-disturbed.cfg") is None

    forged_bytes = config_path.read_bytes().replace(b'["eu"]', b'["us"]')
    config_path.write_bytes(forged_bytes)
    forged_manifest = dict(original_manifest)
    forged_manifest["config"] = dict(original_manifest["config"])
    forged_manifest["config"]["sha256"] = hashlib.sha256(forged_bytes).hexdigest()
    manifest_path.write_text(
        json.dumps(forged_manifest, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    assert snapshot.resolve_preset_locale_projection(tmp_path, "eu-disturbed.cfg") is None


def test_schema_v1_preset_projection_rechecks_the_replayed_config_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = snapshot.resolve_preset_snapshot(
        "eu-disturbed",
        {},
        source_revision="test-revision",
        resolved_at=FIXED_TIME,
    )
    config_path, _manifest_path = snapshot.materialize_preset_snapshot(
        tmp_path,
        candidate,
    )
    original_read_bytes = Path.read_bytes
    config_reads = 0

    def swapping_read_bytes(path: Path) -> bytes:
        nonlocal config_reads
        if path == config_path:
            config_reads += 1
            if config_reads > 1:
                return candidate.config_bytes.replace(b'["eu"]', b'["us"]')
        return original_read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", swapping_read_bytes)

    assert snapshot.resolve_preset_locale_projection(
        tmp_path,
        "eu-disturbed.cfg",
    ) is None
    assert config_reads == 2


def test_schema_v1_preset_projection_fails_when_policy_corpus_is_unavailable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = snapshot.resolve_preset_snapshot(
        "eu-disturbed",
        {},
        source_revision="test-revision",
        resolved_at=FIXED_TIME,
    )
    snapshot.materialize_preset_snapshot(tmp_path, candidate)

    def unavailable():
        raise snapshot.PresetPolicyError("policy corpus unavailable")

    monkeypatch.setattr(snapshot, "load_preset_policies", unavailable)
    with pytest.raises(snapshot.PresetPolicyError, match="unavailable"):
        snapshot.resolve_preset_locale_projection(tmp_path, "eu-disturbed.cfg")


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
