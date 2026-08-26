from __future__ import annotations

from datetime import datetime, timezone
import json

import pytest

from wepppy.nodb.config_builder.resolver import BuilderConstraintError
from wepppy.nodb.config_builder.snapshot import builder_writer_enabled, parse_builder_selections, resolve_builder_candidate
from wepppy.project_config_serialization import parse_config_text
from wepppy.nodb.base import CaseSensitiveRawConfigParser
from wepppy.nodb.project_config_reader import load_project_config
from wepppy.nodb.project_config_snapshot import materialize_preset_snapshot

pytestmark = pytest.mark.unit


def _payload(**updates):
    payload = {"locale": "continental-us", "dem": "usgs-ned13-2022", "delineation_backend": "wbt", "watershed_representation": "single-ofe", "soil": "ssurgo-gnatsgso-2025", "landuse": "nlcd-2019", "climate": "vanilla_cligen", "mods": []}
    payload.update(updates)
    return payload


def test_builder_flag_is_strict_and_default_off() -> None:
    assert not builder_writer_enabled({})
    assert builder_writer_enabled({"WEPPPY_PROJECT_CONFIG_BUILDER_WRITER_ENABLED": "yes"})
    with pytest.raises(ValueError):
        builder_writer_enabled({"WEPPPY_PROJECT_CONFIG_BUILDER_WRITER_ENABLED": "maybe"})


def test_builder_candidate_has_fixed_token_manifest_and_review() -> None:
    candidate = resolve_builder_candidate(parse_builder_selections(_payload()), resolved_at=datetime(2026, 8, 26, tzinfo=timezone.utc))
    config = parse_config_text(candidate.artifact.config_bytes.decode())
    manifest = json.loads(candidate.artifact.manifest_bytes)
    assert candidate.artifact.config_filename == "config.cfg"
    assert config["general"]["cellsize"] == 10
    assert manifest["source_kind"] == "builder"
    assert manifest["source_preset"] is None
    assert manifest["selections"]["cellsize_source"] == "dem_default"
    assert manifest["config"]["filename"] == "config.cfg"
    assert manifest["source_revision"] == "dev"


def test_builder_pair_reopens_without_shared_fallback(tmp_path, monkeypatch) -> None:
    candidate = resolve_builder_candidate(parse_builder_selections(_payload()))
    materialize_preset_snapshot(tmp_path, candidate.artifact)
    monkeypatch.setenv("WEPPPY_PROJECT_CONFIG_READER_ENABLED", "1")
    result = load_project_config(
        wd=tmp_path,
        config_token="config",
        parent_wd=None,
        config_dir=tmp_path / "missing",
        defaults_resolver=lambda _wd=None: str(tmp_path / "missing-defaults.cfg"),
        parser_factory=CaseSensitiveRawConfigParser,
        run_id="builder-fixture",
    )
    assert result.status.mode == "flattened"
    assert result.status.manifest_valid is True


def test_payload_rejects_unknown_fields_and_invalid_cellsize() -> None:
    with pytest.raises(BuilderConstraintError) as unknown:
        parse_builder_selections(_payload(config="evil"))
    assert unknown.value.code == "unknown_field"
    with pytest.raises(BuilderConstraintError) as invalid:
        resolve_builder_candidate(parse_builder_selections(_payload(cellsize_override=17)))
    assert invalid.value.field == "cellsize_override"
