from __future__ import annotations

from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from configparser import RawConfigParser
import hashlib
import json
from pathlib import Path

import pytest

from wepppy.nodb.project_config_snapshot import (
    materialize_preset_snapshot,
    resolve_preset_snapshot,
)
from wepppy.nodb.config_builder.snapshot import resolve_builder_candidate
from wepppy.nodb.config_builder.schema import BuilderSelections
from wepppy.nodb.project_config_update import (
    JOURNAL_NAME,
    StaleConfigPreviewError,
    apply_project_config_update,
    preview_project_config_update,
    project_config_update_enabled,
    recover_project_config_update,
    ConfigUpdateUnavailableError,
)
from wepppy.nodb.project_config_reader import load_project_config
from wepppy.project_config_serialization import parse_config_text, serialize_config

pytestmark = pytest.mark.unit


def _old_preset_project(tmp_path: Path) -> tuple[Path, tuple[str, str]]:
    candidate = resolve_preset_snapshot(
        "disturbed9002_wbt",
        {},
        source_revision="deployment-a",
        resolved_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
    )
    materialize_preset_snapshot(tmp_path, candidate)
    config_path = tmp_path / candidate.config_filename
    config = parse_config_text(config_path.read_text(encoding="utf-8"))
    target = ("unitizer", "is_english")
    assert target[0] in config and target[1] in config[target[0]]
    del config[target[0]][target[1]]
    if not config[target[0]]:
        del config[target[0]]
    old_bytes = serialize_config(config)
    config_path.write_bytes(old_bytes)
    manifest_path = tmp_path / "config-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["config"]["sha256"] = hashlib.sha256(old_bytes).hexdigest()
    manifest_path.write_text(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    return config_path, target


def _snapshot(root: Path) -> dict[str, tuple[bytes, int]]:
    return {
        path.name: (path.read_bytes(), path.stat().st_mtime_ns)
        for path in root.iterdir()
        if path.is_file() and path.name in {"config-manifest.json", "disturbed9002_wbt.cfg"}
    }


def test_update_flag_is_strict_and_default_off() -> None:
    assert project_config_update_enabled({}) is False
    assert project_config_update_enabled({"WEPPPY_PROJECT_CONFIG_UPDATE_ENABLED": "true"}) is True
    with pytest.raises(ValueError, match="strict boolean"):
        project_config_update_enabled({"WEPPPY_PROJECT_CONFIG_UPDATE_ENABLED": "sometimes"})


def test_preview_is_read_only_and_lists_complete_registered_delta(tmp_path: Path) -> None:
    _config_path, target = _old_preset_project(tmp_path)
    before = _snapshot(tmp_path)

    preview = preview_project_config_update(tmp_path)

    assert preview.available is True
    assert preview.preview_id and preview.preview_id.startswith("pcu1-")
    assert [(item.section, item.option) for item in preview.additions] == [target]
    assert preview.additions[0].source_id in {"shared-defaults", "disturbed9002_wbt"}
    assert _snapshot(tmp_path) == before
    assert not (tmp_path / ".config-amendment.lock").exists()


def test_apply_adds_missing_value_preserves_existing_and_records_provenance(tmp_path: Path) -> None:
    config_path, target = _old_preset_project(tmp_path)
    before = parse_config_text(config_path.read_text(encoding="utf-8"))
    preview = preview_project_config_update(tmp_path)

    result = apply_project_config_update(
        tmp_path,
        preview.preview_id or "",
        trigger_section=target[0],
        trigger_option=target[1],
        application_revision="worker-revision-a",
        resolved_at=datetime(2026, 8, 26, tzinfo=timezone.utc),
    )

    after = parse_config_text(config_path.read_text(encoding="utf-8"))
    for section, options in before.items():
        for option, value in options.items():
            assert after[section][option] == value
    assert target[1] in after[target[0]]
    manifest = json.loads((tmp_path / "config-manifest.json").read_text(encoding="utf-8"))
    amendment = manifest["amendments"][-1]
    assert result.sequence == amendment["sequence"] == 1
    assert amendment["application_revision"] == "worker-revision-a"
    assert amendment["reason"] == "missing_registered_attribute_merge"
    assert amendment["additions"][0]["source_revision"]
    assert manifest["config"]["sha256"] == result.resulting_digest
    assert not (tmp_path / JOURNAL_NAME).exists()
    assert preview_project_config_update(tmp_path).available is False


def test_digest_mismatch_is_recorded_from_actual_config_not_blocked(tmp_path: Path) -> None:
    config_path, target = _old_preset_project(tmp_path)
    manifest_path = tmp_path / "config-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["config"]["sha256"] = "0" * 64
    manifest_path.write_text(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    actual_prior = hashlib.sha256(config_path.read_bytes()).hexdigest()
    preview = preview_project_config_update(tmp_path)

    result = apply_project_config_update(
        tmp_path, preview.preview_id or "", trigger_section=target[0],
        trigger_option=target[1], application_revision="worker-revision-a",
    )

    amended = json.loads(manifest_path.read_text(encoding="utf-8"))["amendments"][-1]
    assert result.prior_digest == amended["prior_sha256"] == actual_prior
    assert amended["resulting_sha256"] == result.resulting_digest


def test_stale_preview_rejects_without_mutation(tmp_path: Path) -> None:
    config_path, target = _old_preset_project(tmp_path)
    preview = preview_project_config_update(tmp_path)
    config = parse_config_text(config_path.read_text(encoding="utf-8"))
    config.setdefault("user", {})["retained"] = "value"
    config_path.write_bytes(serialize_config(config))
    before = _snapshot(tmp_path)

    with pytest.raises(StaleConfigPreviewError):
        apply_project_config_update(
            tmp_path, preview.preview_id or "", trigger_section=target[0],
            trigger_option=target[1], application_revision="worker-revision-a",
        )

    assert _snapshot(tmp_path) == before


def test_arbitrary_trigger_rejects_complete_batch_without_mutation(tmp_path: Path) -> None:
    _config_path, _target = _old_preset_project(tmp_path)
    preview = preview_project_config_update(tmp_path)
    before = _snapshot(tmp_path)
    with pytest.raises(ConfigUpdateUnavailableError, match="Trigger"):
        apply_project_config_update(
            tmp_path, preview.preview_id or "", trigger_section="misspelled",
            trigger_option="attribute", application_revision="worker-revision-a",
        )
    assert _snapshot(tmp_path) == before


def test_builder_preview_uses_only_recorded_active_component_chain(tmp_path: Path) -> None:
    selections = BuilderSelections(
        locale="continental-us", dem="usgs-ned13-2022", delineation_backend="wbt",
        watershed_representation="single-ofe", soil="ssurgo-gnatsgso-2025",
        landuse="nlcd-2019", climate="vanilla_cligen",
    )
    candidate = resolve_builder_candidate(
        selections, resolved_at=datetime(2026, 8, 1, tzinfo=timezone.utc)
    )
    materialize_preset_snapshot(tmp_path, candidate.artifact)
    config_path = tmp_path / "config.cfg"
    config = parse_config_text(config_path.read_text(encoding="utf-8"))
    owned = sorted(
        (key, writer) for key, writer in candidate.resolved.effective_writers.items()
        if writer not in {"shared-defaults", "resolver-v1", "selection:cellsize", "selection:mods"}
    )
    (section, option), expected_writer = owned[0]
    del config[section][option]
    old_bytes = serialize_config(config)
    config_path.write_bytes(old_bytes)
    manifest_path = tmp_path / "config-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["config"]["sha256"] = hashlib.sha256(old_bytes).hexdigest()
    manifest_path.write_text(json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")

    preview = preview_project_config_update(tmp_path)

    addition = next(item for item in preview.additions if (item.section, item.option) == (section, option))
    assert addition.source_id == expected_writer


def test_invalid_recorded_chain_produces_no_preview_or_write(tmp_path: Path) -> None:
    _old_preset_project(tmp_path)
    manifest_path = tmp_path / "config-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["parent_chain"][1]["id"] = "unregistered-preset"
    manifest_path.write_text(json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    before = _snapshot(tmp_path)
    with pytest.raises(ConfigUpdateUnavailableError, match="parent chain"):
        preview_project_config_update(tmp_path)
    assert _snapshot(tmp_path) == before


def test_concurrent_applies_produce_one_amendment(tmp_path: Path) -> None:
    _config_path, target = _old_preset_project(tmp_path)
    preview = preview_project_config_update(tmp_path)

    def apply_once():
        return apply_project_config_update(
            tmp_path, preview.preview_id or "", trigger_section=target[0],
            trigger_option=target[1], application_revision="worker-revision-a",
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(apply_once) for _index in range(2)]
    outcomes = []
    for future in futures:
        try:
            outcomes.append(future.result())
        except ConfigUpdateUnavailableError:
            outcomes.append(None)
    assert sum(item is not None for item in outcomes) == 1
    manifest = json.loads((tmp_path / "config-manifest.json").read_text(encoding="utf-8"))
    assert len(manifest["amendments"]) == 1


def test_reader_recovers_interrupted_replacement_before_serving(tmp_path: Path) -> None:
    _config_path, target = _old_preset_project(tmp_path)
    preview = preview_project_config_update(tmp_path)

    def fail_after_config(stage: str) -> None:
        if stage == "config_replaced":
            raise RuntimeError("worker stopped")

    with pytest.raises(RuntimeError, match="worker stopped"):
        apply_project_config_update(
            tmp_path, preview.preview_id or "", trigger_section=target[0],
            trigger_option=target[1], application_revision="worker-revision-a",
            fault_hook=fail_after_config,
        )

    result = load_project_config(
        wd=tmp_path, config_token="disturbed9002_wbt", parent_wd=None,
        config_dir=tmp_path, defaults_resolver=lambda _wd: str(tmp_path / "unused.cfg"),
        parser_factory=RawConfigParser, run_id="run-1",
    )

    assert result.parser.has_option(target[0], target[1])
    assert result.status.updates_enabled is True
    assert not (tmp_path / JOURNAL_NAME).exists()


@pytest.mark.parametrize(
    ("stage", "expected_applied"),
    [("journal_committed", False), ("config_replaced", True), ("manifest_replaced", True)],
)
def test_crash_recovery_returns_one_consistent_pair(
    tmp_path: Path, stage: str, expected_applied: bool,
) -> None:
    config_path, target = _old_preset_project(tmp_path)
    preview = preview_project_config_update(tmp_path)

    def fail_at(current: str) -> None:
        if current == stage:
            raise RuntimeError(f"fault at {stage}")

    with pytest.raises(RuntimeError, match="fault at"):
        apply_project_config_update(
            tmp_path, preview.preview_id or "", trigger_section=target[0],
            trigger_option=target[1], application_revision="worker-revision-a",
            fault_hook=fail_at,
        )
    assert (tmp_path / JOURNAL_NAME).exists()

    assert recover_project_config_update(tmp_path) is True

    config = parse_config_text(config_path.read_text(encoding="utf-8"))
    manifest = json.loads((tmp_path / "config-manifest.json").read_text(encoding="utf-8"))
    assert (target[0] in config and target[1] in config[target[0]]) is expected_applied
    assert bool(manifest["amendments"]) is expected_applied
    assert manifest["config"]["sha256"] == hashlib.sha256(config_path.read_bytes()).hexdigest()
    assert not (tmp_path / JOURNAL_NAME).exists()
