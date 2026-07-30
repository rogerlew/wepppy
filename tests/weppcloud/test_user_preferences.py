from __future__ import annotations

import itertools
import os
from pathlib import Path

import pytest

import wepppy.weppcloud.user_preferences as preferences_module
from wepppy.weppcloud.user_preferences import (
    CreationPreferenceSnapshot,
    PreferenceValidationError,
    UserPreferenceValues,
    apply_creation_preference_overrides,
    cleanup_new_run_directory,
    resolve_creation_preferences,
    validate_preference_values,
)
from wepppy.nodb.core import Ron, Watershed
from wepppy.nodb.unitizer import Unitizer

pytestmark = pytest.mark.unit


def _snapshot(unit: str, boundary: str) -> CreationPreferenceSnapshot:
    return CreationPreferenceSnapshot(
        user_id=7,
        email="user@example.com",
        preferences=UserPreferenceValues(unit, boundary),
    )


@pytest.mark.parametrize(
    ("unit", "boundary"),
    itertools.product(
        ("config", "si", "english"),
        ("config", "warn", "error"),
    ),
)
def test_creation_preference_cartesian_resolution(unit: str, boundary: str) -> None:
    resolved = apply_creation_preference_overrides({}, _snapshot(unit, boundary))

    expected_unit = {"si": "false", "english": "true"}.get(unit)
    if expected_unit is None:
        assert "unitizer:is_english" not in resolved
    else:
        assert resolved["unitizer:is_english"] == expected_unit

    if boundary == "config":
        assert "watershed.wbt:boundary_touch_behavior" not in resolved
    else:
        assert resolved["watershed.wbt:boundary_touch_behavior"] == boundary


@pytest.mark.parametrize("explicit", ("true", "false"))
@pytest.mark.parametrize("unit", ("config", "si", "english"))
def test_explicit_unit_override_wins_account_preference(
    explicit: str,
    unit: str,
) -> None:
    resolved = apply_creation_preference_overrides(
        {"unitizer:is_english": explicit},
        _snapshot(unit, "config"),
    )

    assert resolved["unitizer:is_english"] == explicit


def test_effective_preferences_are_persisted_in_new_run_state(tmp_path) -> None:
    run_dir = tmp_path / "preference-snapshot"
    run_dir.mkdir()

    Ron(
        str(run_dir),
        (
            "disturbed9002_wbt.cfg?"
            "unitizer:is_english=false&"
            "watershed.wbt:boundary_touch_behavior=error"
        ),
    )

    assert Unitizer.getInstance(str(run_dir)).is_english is False
    assert (
        Watershed.getInstance(str(run_dir)).wbt_boundary_touch_behavior
        == "error"
    )


@pytest.mark.parametrize("invalid", ("1", "yes", "TRUE", " false ", "garbage"))
def test_invalid_explicit_unit_override_fails_closed(invalid: str) -> None:
    with pytest.raises(PreferenceValidationError):
        apply_creation_preference_overrides(
            {"unitizer:is_english": invalid},
            _snapshot("config", "config"),
        )


def test_service_and_mcp_claims_do_not_resolve_an_account() -> None:
    assert resolve_creation_preferences({"token_class": "service", "sub": "7"}) is None
    assert resolve_creation_preferences({"token_class": "mcp", "sub": "7"}) is None


@pytest.mark.parametrize(
    ("unit", "boundary"),
    (("", "warn"), ("metric", "warn"), ("si", ""), ("si", "stop")),
)
def test_submitted_preferences_require_exact_tokens(unit: str, boundary: str) -> None:
    with pytest.raises(PreferenceValidationError):
        validate_preference_values(unit, boundary)


def _configure_test_runs_root(monkeypatch, tmp_path: Path) -> None:
    from wepppy.weppcloud.utils import helpers

    monkeypatch.setattr(helpers, "PRIMARY_RUNS_ROOT", str(tmp_path))
    monkeypatch.setattr(helpers, "LEGACY_RUNS_ROOT", str(tmp_path / "legacy"))
    monkeypatch.setattr(helpers, "redis_wd_cache_client", None)


def test_cleanup_new_run_directory_removes_only_canonical_directory(
    monkeypatch,
    tmp_path,
) -> None:
    _configure_test_runs_root(monkeypatch, tmp_path)
    runid = "safe-cleanup"
    target = tmp_path / runid[:2] / runid
    target.mkdir(parents=True)
    (target / "ron.nodb").write_text("fixture", encoding="utf-8")

    cleanup_new_run_directory(runid, str(target))

    assert not target.exists()


def test_cleanup_new_run_directory_rejects_top_level_symlink(
    monkeypatch,
    tmp_path,
) -> None:
    _configure_test_runs_root(monkeypatch, tmp_path)
    runid = "symlink-run"
    sibling = tmp_path / "si" / "sibling"
    sibling.mkdir(parents=True)
    target = tmp_path / runid[:2] / runid
    target.parent.mkdir(parents=True, exist_ok=True)
    target.symlink_to(sibling, target_is_directory=True)

    with pytest.raises(ValueError, match="symlink"):
        cleanup_new_run_directory(runid, str(target))

    assert sibling.is_dir()


def test_cleanup_new_run_directory_rejects_symlink_replacement_race(
    monkeypatch,
    tmp_path,
) -> None:
    _configure_test_runs_root(monkeypatch, tmp_path)
    runid = "race-cleanup"
    sibling = tmp_path / "ra" / "sibling"
    sibling.mkdir(parents=True)
    (sibling / "keep").write_text("safe", encoding="utf-8")
    target = tmp_path / runid[:2] / runid
    target.mkdir(parents=True)
    original_rmtree = preferences_module.shutil.rmtree

    def replace_then_remove(path):
        os.rmdir(path)
        Path(path).symlink_to(sibling, target_is_directory=True)
        original_rmtree(path)

    monkeypatch.setattr(preferences_module.shutil, "rmtree", replace_then_remove)

    with pytest.raises(OSError):
        cleanup_new_run_directory(runid, str(target))

    assert (sibling / "keep").read_text(encoding="utf-8") == "safe"


def test_cleanup_new_run_directory_rejects_mismatch_and_runs_root(
    monkeypatch,
    tmp_path,
) -> None:
    _configure_test_runs_root(monkeypatch, tmp_path)
    runid = "mismatch-run"
    target = tmp_path / runid[:2] / runid
    target.mkdir(parents=True)

    with pytest.raises(ValueError, match="unexpected"):
        cleanup_new_run_directory(runid, str(tmp_path / "other"))
    with pytest.raises(ValueError, match="unexpected"):
        cleanup_new_run_directory(runid, str(tmp_path))

    assert target.is_dir()
