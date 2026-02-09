import os
from pathlib import Path

import pytest

from wepppy.microservices.browse.security import (
    PATH_SECURITY_FORBIDDEN_HIDDEN,
    PATH_SECURITY_FORBIDDEN_RECORDER,
    PATH_SECURITY_INVALID_PATH,
    PATH_SECURITY_OUTSIDE_ALLOWED_ROOTS,
    derive_allowed_symlink_roots,
    path_security_detail,
    validate_raw_subpath,
    validate_resolved_path_against_roots,
    validate_resolved_target,
)

pytestmark = pytest.mark.unit


def test_path_security_detail_messages() -> None:
    assert path_security_detail(PATH_SECURITY_FORBIDDEN_RECORDER) == (
        "Access to recorder log artifacts is forbidden."
    )
    assert path_security_detail(PATH_SECURITY_FORBIDDEN_HIDDEN) == (
        "Access to hidden paths is forbidden."
    )
    assert path_security_detail(PATH_SECURITY_OUTSIDE_ALLOWED_ROOTS) == "Invalid path."
    assert path_security_detail(PATH_SECURITY_INVALID_PATH) == "Invalid path."


@pytest.mark.parametrize(
    ("raw_path", "expected_code"),
    [
        ("_logs/profile.events.jsonl", PATH_SECURITY_FORBIDDEN_RECORDER),
        ("_LoGs\\PROFILE.EVENTS.JSONL", PATH_SECURITY_FORBIDDEN_RECORDER),
        ("wepp/.secret", PATH_SECURITY_FORBIDDEN_HIDDEN),
        (".secret", PATH_SECURITY_FORBIDDEN_HIDDEN),
        ("normal/path.txt", None),
    ],
)
def test_validate_raw_subpath(raw_path: str, expected_code: str | None) -> None:
    assert validate_raw_subpath(raw_path) == expected_code


def test_derive_allowed_symlink_roots_runs_layout(tmp_path: Path) -> None:
    group_root = tmp_path / "batch"
    run_root = group_root / "runs" / "1001"
    run_root.mkdir(parents=True)

    roots = derive_allowed_symlink_roots(run_root)

    assert run_root.resolve() in roots
    assert group_root.resolve() in roots


def test_derive_allowed_symlink_roots_omni_layout(tmp_path: Path) -> None:
    parent_run_root = tmp_path / "runs" / "ab" / "run-1"
    scenario_root = parent_run_root / "_pups" / "omni" / "scenarios" / "scenario-a"
    scenario_root.mkdir(parents=True)

    roots = derive_allowed_symlink_roots(scenario_root)

    assert scenario_root.resolve() in roots
    assert parent_run_root.resolve() in roots


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="symlink not supported")
def test_validate_resolved_target_allows_parent_maps_symlink_for_runs_layout(tmp_path: Path) -> None:
    group_root = tmp_path / "group"
    run_root = group_root / "runs" / "1001"
    run_root.mkdir(parents=True)
    (group_root / "maps").mkdir(parents=True)

    os.symlink("../../maps", run_root / "maps_link")

    assert validate_resolved_target(run_root, run_root / "maps_link") is None


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="symlink not supported")
def test_validate_resolved_target_blocks_symlink_outside_allowed_roots(tmp_path: Path) -> None:
    run_root = tmp_path / "run"
    outside_root = tmp_path / "outside"
    run_root.mkdir()
    outside_root.mkdir()

    os.symlink(str(outside_root), run_root / "external")

    assert (
        validate_resolved_target(run_root, run_root / "external")
        == PATH_SECURITY_OUTSIDE_ALLOWED_ROOTS
    )


def test_validate_resolved_target_blocks_restricted_and_hidden_segments(tmp_path: Path) -> None:
    run_root = tmp_path / "run"
    run_root.mkdir()
    restricted_target = run_root / "_logs"
    hidden_target = run_root / ".private"
    restricted_target.mkdir()
    hidden_target.mkdir()

    assert (
        validate_resolved_target(run_root, restricted_target)
        == PATH_SECURITY_FORBIDDEN_RECORDER
    )
    assert (
        validate_resolved_target(run_root, hidden_target) == PATH_SECURITY_FORBIDDEN_HIDDEN
    )


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="symlink not supported")
def test_validate_resolved_target_marks_symlink_loop_invalid(tmp_path: Path) -> None:
    run_root = tmp_path / "run"
    run_root.mkdir()

    os.symlink("loop", run_root / "loop")

    assert validate_resolved_target(run_root, run_root / "loop") == PATH_SECURITY_INVALID_PATH


def test_validate_resolved_path_against_roots_requires_candidate_within_roots(tmp_path: Path) -> None:
    root = tmp_path / "root"
    other = tmp_path / "other"
    root.mkdir()
    other.mkdir()

    assert (
        validate_resolved_path_against_roots(other, (root,))
        == PATH_SECURITY_OUTSIDE_ALLOWED_ROOTS
    )
