from __future__ import annotations

import os
from pathlib import Path

import pytest

import wepppy.weppcloud.user_preferences as preferences_module
from wepppy.weppcloud.user_preferences import (
    AccountPreferenceSnapshot,
    PreferenceValidationError,
    UnitizerPresentationMutationError,
    UnitizerPresentationView,
    UserPreferenceValues,
    WbtBoundaryPolicySnapshotError,
    build_wbt_boundary_policy_snapshot,
    cleanup_new_run_directory,
    resolve_account_preferences,
    resolve_unitizer_presentation_for_user,
    validate_creation_values,
    validate_preference_values,
    validate_wbt_boundary_policy_snapshot,
)
from wepppy.nodb.core import Ron, Watershed
from wepppy.nodb.unitizer import Unitizer

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("explicit", ("true", "false"))
def test_creation_units_are_controlled_only_by_explicit_input(explicit: str) -> None:
    resolved = validate_creation_values({"unitizer:is_english": explicit})
    assert resolved["unitizer:is_english"] == explicit


def test_explicit_creation_units_are_persisted_in_new_run_state(tmp_path) -> None:
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
        validate_creation_values({"unitizer:is_english": invalid})


def test_service_and_mcp_claims_do_not_resolve_an_account() -> None:
    assert resolve_account_preferences({"token_class": "service", "sub": "7"}) is None
    assert resolve_account_preferences({"token_class": "mcp", "sub": "7"}) is None


@pytest.mark.parametrize(
    ("claims", "expected_class", "expected_user_id"),
    (
        (None, None, None),
        ({}, None, None),
        ({"token_class": "session"}, None, None),
        ({"token_class": "user", "sub": "7"}, "user", 7),
        ({"token_class": "session", "user_id": 9}, "session", 9),
    ),
)
def test_account_preference_identity_matrix(
    monkeypatch,
    claims,
    expected_class,
    expected_user_id,
) -> None:
    monkeypatch.setattr(
        preferences_module,
        "_load_active_user_preferences_locked",
        lambda _user_id: UserPreferenceValues("si", "error"),
    )

    resolved = resolve_account_preferences(claims)

    if expected_class is None:
        assert resolved is None
    else:
        assert resolved is not None
        assert resolved.actor_token_class == expected_class
        assert resolved.user_id == expected_user_id


@pytest.mark.parametrize(
    "claims",
    (
        {"token_class": "user"},
        {"token_class": "user", "sub": True},
        {"token_class": "session", "user_id": "0"},
        {"token_class": "unknown", "sub": "7"},
    ),
)
def test_account_preference_identity_fails_closed(monkeypatch, claims) -> None:
    monkeypatch.setattr(
        preferences_module,
        "_load_active_user_preferences_locked",
        lambda _user_id: UserPreferenceValues(),
    )

    with pytest.raises(preferences_module.PreferenceIdentityError):
        resolve_account_preferences(claims)


@pytest.mark.parametrize(
    ("unit_system", "expected_english"),
    (("si", False), ("english", True)),
)
def test_non_auto_units_create_immutable_request_local_view(
    unit_system: str,
    expected_english: bool,
) -> None:
    durable = object.__new__(Unitizer)
    durable.__dict__ = {
        "_preferences": {
            unit_class: next(iter(options))
            for unit_class, options in preferences_module.precisions.items()
        },
        "_lock": object(),
    }
    durable_preferences = dict(durable.preferences)

    view = UnitizerPresentationView.from_unitizer(durable, unit_system)

    assert view is not durable
    assert view.is_english is expected_english
    assert durable.preferences == durable_preferences
    assert view.__dict__["_lock"] is durable.__dict__["_lock"]
    with pytest.raises(UnitizerPresentationMutationError):
        view.set_preferences({"distance": "km"})
    for attribute in ("readonly", "public", "DEBUG", "VERBOSE"):
        with pytest.raises(UnitizerPresentationMutationError):
            setattr(view, attribute, True)
    assert durable.preferences == durable_preferences


def test_auto_units_return_exact_durable_unitizer(monkeypatch) -> None:
    durable = object.__new__(Unitizer)
    durable.__dict__ = {"_preferences": {}}
    monkeypatch.setattr(Unitizer, "getInstance", lambda _wd: durable)
    monkeypatch.setattr(
        preferences_module,
        "_load_active_user_preferences_locked",
        lambda _user_id: UserPreferenceValues("config", "warn"),
    )

    assert resolve_unitizer_presentation_for_user("/run", 7) is durable


def test_wbt_snapshot_binds_initiating_user_without_mutating_project_policy() -> None:
    account = AccountPreferenceSnapshot(
        actor_token_class="user",
        user_id=7,
        preferences=UserPreferenceValues("si", "error"),
    )

    snapshot = build_wbt_boundary_policy_snapshot("shared-run", "warn", account)

    assert snapshot.actor_user_id == 7
    assert snapshot.config_policy == "warn"
    assert snapshot.effective_policy == "error"
    assert snapshot.source == "user_preference"
    assert validate_wbt_boundary_policy_snapshot(
        snapshot.to_meta(),
        snapshot.to_argument(),
        expected_runid="shared-run",
    ) == snapshot


@pytest.mark.parametrize("config_policy", ("warn", "error"))
def test_two_auto_users_resolve_same_unchanged_config_policy(
    config_policy: str,
) -> None:
    snapshots = [
        build_wbt_boundary_policy_snapshot(
            "shared-run",
            config_policy,
            AccountPreferenceSnapshot(
                actor_token_class="user",
                user_id=user_id,
                preferences=UserPreferenceValues("config", "config"),
            ),
        )
        for user_id in (17, 18)
    ]

    assert [snapshot.actor_user_id for snapshot in snapshots] == [17, 18]
    assert {
        (snapshot.config_policy, snapshot.effective_policy, snapshot.source)
        for snapshot in snapshots
    } == {(config_policy, config_policy, "project_config")}


@pytest.mark.parametrize(
    "mutation",
    (
        lambda value: value.update({"extra": True}),
        lambda value: value.update({"schema_version": True}),
        lambda value: value.update({"actor_user_id": True}),
        lambda value: value.update({"runid": "other-run"}),
        lambda value: value.update({"effective_policy": "stop"}),
    ),
)
def test_wbt_snapshot_rejects_malformed_private_metadata(mutation) -> None:
    account = AccountPreferenceSnapshot(
        actor_token_class="session",
        user_id=9,
        preferences=UserPreferenceValues("config", "warn"),
    )
    snapshot = build_wbt_boundary_policy_snapshot("shared-run", "error", account)
    raw_meta = snapshot.to_meta()
    mutation(raw_meta)

    with pytest.raises(WbtBoundaryPolicySnapshotError):
        validate_wbt_boundary_policy_snapshot(
            raw_meta,
            snapshot.to_argument(),
            expected_runid="shared-run",
        )


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
    monkeypatch.setattr(
        preferences_module,
        "_delete_failed_run_lock_hash",
        lambda _runid: None,
    )
    monkeypatch.setattr(
        preferences_module,
        "_assert_failed_run_nodb_cache_empty",
        lambda _target: None,
    )
    monkeypatch.setattr(
        preferences_module,
        "_delete_failed_run_wd_cache",
        lambda _runid: None,
    )


def test_failed_run_nodb_cache_postcondition_rejects_remaining_key(
    monkeypatch,
) -> None:
    class RemainingCache:
        def scan_iter(self, *, match, count):
            assert count == 100
            if match.endswith("*"):
                yield b"/wc1/runs/te/test-run/ron.nodb"

    monkeypatch.setattr(
        preferences_module.redis,
        "Redis",
        lambda **_kwargs: RemainingCache(),
    )

    with pytest.raises(RuntimeError, match="NoDb cache remains"):
        preferences_module._assert_failed_run_nodb_cache_empty(
            "/wc1/runs/te/test-run"
        )


def test_cleanup_new_run_directory_removes_only_canonical_directory(
    monkeypatch,
    tmp_path,
) -> None:
    _configure_test_runs_root(monkeypatch, tmp_path)
    runid = "safe-cleanup"
    target = tmp_path / runid[:2] / runid
    target.mkdir(parents=True)
    (target / "ron.nodb").write_text("fixture", encoding="utf-8")
    calls: list[tuple[str, object]] = []
    monkeypatch.setattr(
        preferences_module.NoDbBase,
        "cleanup_run_instances",
        lambda wd: calls.append(("instances", wd)),
    )
    monkeypatch.setattr(
        preferences_module,
        "clear_locks",
        lambda value: calls.append(("locks", value)),
    )
    monkeypatch.setattr(
        preferences_module,
        "clear_nodb_file_cache",
        lambda value: calls.append(("nodb_cache", value)),
    )
    monkeypatch.setattr(
        preferences_module,
        "_delete_failed_run_lock_hash",
        lambda value: calls.append(("lock_hash", value)),
    )
    monkeypatch.setattr(
        preferences_module,
        "_assert_failed_run_nodb_cache_empty",
        lambda value: calls.append(("nodb_postcondition", value)),
    )
    monkeypatch.setattr(
        preferences_module,
        "_delete_failed_run_wd_cache",
        lambda value: calls.append(("wd_cache", value)),
    )

    cleanup_new_run_directory(runid, str(target))

    assert not target.exists()
    assert calls == [
        ("instances", str(target)),
        ("locks", runid),
        ("lock_hash", runid),
        ("nodb_cache", runid),
        ("nodb_postcondition", str(target.resolve())),
        ("wd_cache", runid),
    ]


def test_cleanup_new_run_directory_stops_before_delete_when_cache_purge_fails(
    monkeypatch,
    tmp_path,
) -> None:
    _configure_test_runs_root(monkeypatch, tmp_path)
    runid = "cache-failure"
    target = tmp_path / runid[:2] / runid
    target.mkdir(parents=True)
    monkeypatch.setattr(
        preferences_module.NoDbBase,
        "cleanup_run_instances",
        lambda _wd: 1,
    )
    monkeypatch.setattr(
        preferences_module,
        "clear_locks",
        lambda _runid: (_ for _ in ()).throw(RuntimeError("redis unavailable")),
    )

    with pytest.raises(RuntimeError, match="redis unavailable"):
        cleanup_new_run_directory(runid, str(target))

    assert target.is_dir()


@pytest.mark.parametrize(
    "failure",
    (
        RuntimeError("NoDb cache keys remain"),
        preferences_module.redis.RedisError("redis unavailable"),
    ),
)
def test_cleanup_new_run_directory_stops_on_strict_cache_postcondition_failure(
    monkeypatch,
    tmp_path,
    failure: BaseException,
) -> None:
    _configure_test_runs_root(monkeypatch, tmp_path)
    runid = "strict-cache-failure"
    target = tmp_path / runid[:2] / runid
    target.mkdir(parents=True)
    monkeypatch.setattr(
        preferences_module.NoDbBase,
        "cleanup_run_instances",
        lambda _wd: None,
    )
    monkeypatch.setattr(preferences_module, "clear_locks", lambda _runid: None)
    monkeypatch.setattr(
        preferences_module,
        "_delete_failed_run_lock_hash",
        lambda _runid: None,
    )
    monkeypatch.setattr(
        preferences_module,
        "clear_nodb_file_cache",
        lambda _runid: None,
    )
    monkeypatch.setattr(
        preferences_module,
        "_assert_failed_run_nodb_cache_empty",
        lambda _target: (_ for _ in ()).throw(failure),
    )

    with pytest.raises(type(failure), match=str(failure)):
        cleanup_new_run_directory(runid, str(target))

    assert target.is_dir()


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


def test_unitizer_presentation_adoption_inventory_is_explicit() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    production_files = sorted((repo_root / "wepppy").rglob("*.py"))
    direct_get_instance = {
        path.relative_to(repo_root).as_posix()
        for path in production_files
        if "Unitizer.getInstance(" in path.read_text(encoding="utf-8")
    }
    assert direct_get_instance == {
        "wepppy/nodb/mods/features_export/service.py",
        "wepppy/weppcloud/routes/nodb_api/unitizer_bp.py",
        "wepppy/weppcloud/user_preferences.py",
    }

    explicit_non_overlay = {
        "wepppy/weppcloud/routes/ui_showcase/ui_showcase_bp.py",
    }
    for path in production_files:
        source = path.read_text(encoding="utf-8")
        if "unitizer_nodb=" not in source:
            continue
        relative = path.relative_to(repo_root).as_posix()
        assert (
            "resolve_unitizer_presentation" in source
            or relative in explicit_non_overlay
        ), f"Unitizer presentation lookup lacks a contract disposition: {relative}"
