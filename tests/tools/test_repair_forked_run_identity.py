from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import runpy

import pytest


pytestmark = pytest.mark.unit


def _module() -> dict[str, object]:
    repo_root = Path(__file__).resolve().parents[2]
    return runpy.run_path(str(repo_root / "tools/repair_forked_run_identity.py"))


def _write_nodb(path: Path, *, run_group=None, group_name=None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "py/object": "example.Controller",
        "py/state": {
            "_run_group": run_group,
            "_group_name": group_name,
            "wd": str(path.parent),
            "preserved": [1, 2, 3],
        },
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def _state(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))["py/state"]


def _write_batch_metadata(path: Path, batch_name: str) -> None:
    path.write_text(
        json.dumps(
            {
                "runid": f"batch;;{batch_name};;WA-10",
                "batch_name": batch_name,
                "status": "success",
            }
        ),
        encoding="utf-8",
    )


def test_dry_run_plan_is_non_mutating(tmp_path: Path) -> None:
    module = _module()
    build_repair_plan = module["build_repair_plan"]

    run_root = tmp_path / "interactive-run"
    run_root.mkdir()
    ash_path = run_root / "ash.nodb"
    _write_nodb(ash_path, run_group="batch", group_name="example-batch")
    metadata_path = run_root / "run_metadata.json"
    _write_batch_metadata(metadata_path, "example-batch")
    original_ash = ash_path.read_bytes()
    original_metadata = metadata_path.read_bytes()

    plan = build_repair_plan(
        run_root=run_root,
        runid="interactive-run",
        expected_batch_name="example-batch",
    )

    assert plan.batch_name == "example-batch"
    assert [repair.path.name for repair in plan.controller_repairs] == ["ash.nodb"]
    assert plan.metadata_repair is not None
    assert ash_path.read_bytes() == original_ash
    assert metadata_path.read_bytes() == original_metadata
    assert not (run_root / "_repair_backups").exists()


def test_apply_repairs_roots_backs_up_metadata_and_ignores_pups(
    tmp_path: Path,
) -> None:
    module = _module()
    build_repair_plan = module["build_repair_plan"]
    apply_repair_plan = module["apply_repair_plan"]

    run_root = tmp_path / "interactive-run"
    run_root.mkdir()
    for filename in ("ash.nodb", "ron.nodb"):
        _write_nodb(
            run_root / filename,
            run_group="batch",
            group_name="example-batch",
        )
    _write_nodb(run_root / "omni.nodb", run_group=None, group_name=None)
    child_path = run_root / "_pups" / "child" / "ash.nodb"
    _write_nodb(child_path, run_group="batch", group_name="child-batch")
    child_before = child_path.read_bytes()
    metadata_path = run_root / "run_metadata.json"
    _write_batch_metadata(metadata_path, "example-batch")
    metadata_before = metadata_path.read_bytes()

    cache_calls: list[tuple[str, Path, tuple[Path, ...]]] = []

    def _clear_cache(
        runid: str,
        path: Path,
        controller_paths: tuple[Path, ...],
    ) -> list[str]:
        cache_calls.append((runid, path, controller_paths))
        return ["ash.nodb", "ron.nodb"]

    plan = build_repair_plan(
        run_root=run_root,
        runid="interactive-run",
        expected_batch_name="example-batch",
    )
    result = apply_repair_plan(
        plan,
        clear_cache=True,
        cache_clearer=_clear_cache,
        now=datetime(2026, 7, 16, 17, 30, tzinfo=timezone.utc),
    )

    assert result.backup_dir == (
        run_root / "_repair_backups" / "forked_batch_identity_20260716T173000Z"
    )
    assert set(result.changed_controllers) == {Path("ash.nodb"), Path("ron.nodb")}
    assert result.removed_metadata is True
    assert result.cleared_cache_entries == ("ash.nodb", "ron.nodb")
    assert cache_calls == [
        (
            "interactive-run",
            run_root.resolve(),
            (run_root.resolve() / "ash.nodb", run_root.resolve() / "ron.nodb"),
        )
    ]
    for filename in ("ash.nodb", "ron.nodb", "omni.nodb"):
        assert _state(run_root / filename)["_run_group"] is None
        assert _state(run_root / filename)["_group_name"] is None
    assert child_path.read_bytes() == child_before
    assert not metadata_path.exists()
    assert (result.backup_dir / "run_metadata.json").read_bytes() == metadata_before
    manifest = json.loads((result.backup_dir / "manifest.json").read_text())
    assert manifest["status"] == "complete"
    assert manifest["batch_name"] == "example-batch"


@pytest.mark.parametrize(
    ("run_group", "group_name", "expected_message"),
    [
        ("culvert", "group-1", "non-batch run_group"),
        (None, "orphaned-name", "Inconsistent group identity"),
        ("batch", "wrong-batch", "Batch name mismatch"),
    ],
)
def test_validation_rejects_unsafe_identity_before_writing(
    tmp_path: Path,
    run_group: str | None,
    group_name: str,
    expected_message: str,
) -> None:
    module = _module()
    build_repair_plan = module["build_repair_plan"]
    RepairError = module["RepairError"]

    run_root = tmp_path / "interactive-run"
    run_root.mkdir()
    _write_nodb(
        run_root / "ash.nodb",
        run_group=run_group,
        group_name=group_name,
    )
    before = (run_root / "ash.nodb").read_bytes()

    with pytest.raises(RepairError, match=expected_message):
        build_repair_plan(
            run_root=run_root,
            runid="interactive-run",
            expected_batch_name="expected-batch",
        )

    assert (run_root / "ash.nodb").read_bytes() == before
    assert not (run_root / "_repair_backups").exists()


def test_repair_is_idempotent_without_second_backup(tmp_path: Path) -> None:
    module = _module()
    build_repair_plan = module["build_repair_plan"]
    apply_repair_plan = module["apply_repair_plan"]

    run_root = tmp_path / "interactive-run"
    run_root.mkdir()
    _write_nodb(
        run_root / "ash.nodb",
        run_group="batch",
        group_name="example-batch",
    )

    first_plan = build_repair_plan(
        run_root=run_root,
        runid="interactive-run",
        expected_batch_name="example-batch",
    )
    first_result = apply_repair_plan(
        first_plan,
        clear_cache=False,
        now=datetime(2026, 7, 16, 17, 31, tzinfo=timezone.utc),
    )
    second_plan = build_repair_plan(
        run_root=run_root,
        runid="interactive-run",
        expected_batch_name="example-batch",
    )
    second_result = apply_repair_plan(
        second_plan,
        clear_cache=False,
        now=datetime(2026, 7, 16, 17, 32, tzinfo=timezone.utc),
    )

    assert first_result.backup_dir is not None
    assert second_plan.has_changes is False
    assert second_result.backup_dir is None
    backups = list((run_root / "_repair_backups").iterdir())
    assert backups == [first_result.backup_dir]


def test_apply_rolls_back_all_files_after_partial_write(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _module()
    build_repair_plan = module["build_repair_plan"]
    apply_repair_plan = module["apply_repair_plan"]
    real_atomic_write = module["_atomic_write_text"]

    run_root = tmp_path / "interactive-run"
    run_root.mkdir()
    paths = [run_root / "ash.nodb", run_root / "ron.nodb"]
    for path in paths:
        _write_nodb(path, run_group="batch", group_name="example-batch")
    before = {path.name: path.read_bytes() for path in paths}
    metadata_path = run_root / "run_metadata.json"
    _write_batch_metadata(metadata_path, "example-batch")
    metadata_before = metadata_path.read_bytes()

    calls = 0

    def _fail_second_write(path: Path, text: str) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("simulated write failure")
        real_atomic_write(path, text)

    monkeypatch.setitem(
        apply_repair_plan.__globals__,
        "_atomic_write_text",
        _fail_second_write,
    )
    plan = build_repair_plan(
        run_root=run_root,
        runid="interactive-run",
        expected_batch_name="example-batch",
    )

    with pytest.raises(OSError, match="simulated write failure"):
        apply_repair_plan(
            plan,
            clear_cache=False,
            now=datetime(2026, 7, 16, 17, 33, tzinfo=timezone.utc),
        )

    assert {path.name: path.read_bytes() for path in paths} == before
    assert metadata_path.read_bytes() == metadata_before


def test_rollback_restore_failure_preserves_valid_published_json(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _module()
    build_repair_plan = module["build_repair_plan"]
    apply_repair_plan = module["apply_repair_plan"]
    RepairError = module["RepairError"]
    real_atomic_write = module["_atomic_write_text"]

    run_root = tmp_path / "interactive-run"
    run_root.mkdir()
    paths = [run_root / "ash.nodb", run_root / "ron.nodb"]
    for path in paths:
        _write_nodb(path, run_group="batch", group_name="example-batch")

    calls = 0

    def _fail_forward_and_rollback(
        path: Path,
        text: str,
        *,
        mode_source: Path | None = None,
    ) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("simulated forward write failure")
        if calls == 3:
            raise OSError("simulated rollback write failure")
        real_atomic_write(path, text, mode_source=mode_source)

    monkeypatch.setitem(
        apply_repair_plan.__globals__,
        "_atomic_write_text",
        _fail_forward_and_rollback,
    )
    plan = build_repair_plan(
        run_root=run_root,
        runid="interactive-run",
        expected_batch_name="example-batch",
    )

    with pytest.raises(RepairError, match="atomic restore failed"):
        apply_repair_plan(
            plan,
            clear_cache=False,
            now=datetime(2026, 7, 16, 17, 33, 30, tzinfo=timezone.utc),
        )

    first_state = _state(paths[0])
    assert first_state["_run_group"] is None
    assert first_state["_group_name"] is None
    backup_path = (
        run_root
        / "_repair_backups"
        / "forked_batch_identity_20260716T173330Z"
        / paths[0].name
    )
    backup_state = _state(backup_path)
    assert backup_state["_run_group"] == "batch"
    assert backup_state["_group_name"] == "example-batch"


def test_malformed_root_nodb_fails_before_backup(tmp_path: Path) -> None:
    module = _module()
    build_repair_plan = module["build_repair_plan"]
    RepairError = module["RepairError"]

    run_root = tmp_path / "interactive-run"
    run_root.mkdir()
    (run_root / "ash.nodb").write_text("{not-json", encoding="utf-8")

    with pytest.raises(RepairError, match="Invalid JSON"):
        build_repair_plan(run_root=run_root, runid="interactive-run")

    assert not (run_root / "_repair_backups").exists()


@pytest.mark.parametrize(
    "metadata_payload",
    [
        {"runid": "batch;;example-batch;;WA-10"},
        {"batch_name": "example-batch"},
        {"runid": "ordinary-run", "batch_name": "example-batch"},
    ],
)
def test_repair_rejects_incomplete_batch_metadata(
    tmp_path: Path,
    metadata_payload: dict[str, str],
) -> None:
    module = _module()
    build_repair_plan = module["build_repair_plan"]
    RepairError = module["RepairError"]

    run_root = tmp_path / "interactive-run"
    run_root.mkdir()
    _write_nodb(
        run_root / "ash.nodb",
        run_group="batch",
        group_name="example-batch",
    )
    metadata_path = run_root / "run_metadata.json"
    metadata_path.write_text(json.dumps(metadata_payload), encoding="utf-8")
    controller_before = (run_root / "ash.nodb").read_bytes()
    metadata_before = metadata_path.read_bytes()

    with pytest.raises(RepairError, match="Incomplete batch identity"):
        build_repair_plan(
            run_root=run_root,
            runid="interactive-run",
            expected_batch_name="example-batch",
        )

    assert (run_root / "ash.nodb").read_bytes() == controller_before
    assert metadata_path.read_bytes() == metadata_before
    assert not (run_root / "_repair_backups").exists()


def test_stale_plan_rejects_intervening_controller_change_before_backup(
    tmp_path: Path,
) -> None:
    module = _module()
    build_repair_plan = module["build_repair_plan"]
    apply_repair_plan = module["apply_repair_plan"]
    RepairError = module["RepairError"]

    run_root = tmp_path / "interactive-run"
    run_root.mkdir()
    controller_path = run_root / "ash.nodb"
    _write_nodb(
        controller_path,
        run_group="batch",
        group_name="example-batch",
    )
    plan = build_repair_plan(
        run_root=run_root,
        runid="interactive-run",
        expected_batch_name="example-batch",
    )
    payload = json.loads(controller_path.read_text(encoding="utf-8"))
    payload["py/state"]["preserved"] = ["concurrent", "update"]
    controller_path.write_text(json.dumps(payload), encoding="utf-8")
    intervening_text = controller_path.read_text(encoding="utf-8")

    with pytest.raises(RepairError, match="plan is stale"):
        apply_repair_plan(plan, clear_cache=False)

    assert controller_path.read_text(encoding="utf-8") == intervening_text
    assert not (run_root / "_repair_backups").exists()


def test_cache_failure_can_be_retried_from_prepared_backup(tmp_path: Path) -> None:
    module = _module()
    build_repair_plan = module["build_repair_plan"]
    apply_repair_plan = module["apply_repair_plan"]
    retry_cache_clear_from_backup = module["retry_cache_clear_from_backup"]

    run_root = tmp_path / "interactive-run"
    run_root.mkdir()
    controller_path = run_root / "ash.nodb"
    _write_nodb(
        controller_path,
        run_group="batch",
        group_name="example-batch",
    )
    plan = build_repair_plan(
        run_root=run_root,
        runid="interactive-run",
        expected_batch_name="example-batch",
    )
    backup_dir = (
        run_root / "_repair_backups" / "forked_batch_identity_20260716T173400Z"
    )

    def _fail_cache(
        _runid: str,
        _run_root: Path,
        _controller_paths: tuple[Path, ...],
    ) -> list[str]:
        raise RuntimeError("redis unavailable")

    with pytest.raises(RuntimeError, match="redis unavailable"):
        apply_repair_plan(
            plan,
            clear_cache=True,
            cache_clearer=_fail_cache,
            now=datetime(2026, 7, 16, 17, 34, tzinfo=timezone.utc),
        )

    assert _state(controller_path)["_run_group"] is None
    prepared_manifest = json.loads((backup_dir / "manifest.json").read_text())
    assert prepared_manifest["status"] == "prepared"

    retry_calls: list[tuple[str, Path, tuple[Path, ...]]] = []

    def _retry_cache(
        runid: str,
        root: Path,
        controller_paths: tuple[Path, ...],
    ) -> list[str]:
        retry_calls.append((runid, root, controller_paths))
        return ["ash.nodb"]

    result = retry_cache_clear_from_backup(
        run_root=run_root,
        runid="interactive-run",
        backup_dir=backup_dir,
        expected_batch_name="example-batch",
        cache_clearer=_retry_cache,
    )

    assert result.already_complete is False
    assert result.cleared_cache_entries == ("ash.nodb",)
    assert retry_calls == [
        (
            "interactive-run",
            run_root.resolve(),
            (run_root.resolve() / "ash.nodb",),
        )
    ]
    completed_manifest = json.loads((backup_dir / "manifest.json").read_text())
    assert completed_manifest["status"] == "complete"

    repeated = retry_cache_clear_from_backup(
        run_root=run_root,
        runid="interactive-run",
        backup_dir=backup_dir,
        expected_batch_name="example-batch",
        cache_clearer=_fail_cache,
    )
    assert repeated.already_complete is True
    assert repeated.cleared_cache_entries == ("ash.nodb",)


def test_cache_retry_rejects_symlinked_backup_parent(tmp_path: Path) -> None:
    module = _module()
    retry_cache_clear_from_backup = module["retry_cache_clear_from_backup"]
    RepairError = module["RepairError"]

    run_root = tmp_path / "interactive-run"
    run_root.mkdir()
    _write_nodb(run_root / "ash.nodb", run_group=None, group_name=None)
    external_parent = tmp_path / "external-backups"
    backup_name = "forked_batch_identity_20260716T173400Z"
    (external_parent / backup_name).mkdir(parents=True)
    (run_root / "_repair_backups").symlink_to(external_parent, target_is_directory=True)

    with pytest.raises(RepairError, match="Backup parent must be a regular non-symlink"):
        retry_cache_clear_from_backup(
            run_root=run_root,
            runid="interactive-run",
            backup_dir=run_root / "_repair_backups" / backup_name,
        )


def test_default_cache_clearer_scopes_each_changed_root_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _module()
    default_cache_clearer = module["_default_cache_clearer"]

    from wepppy.nodb import base as nodb_base
    from wepppy.weppcloud.utils import helpers

    run_root = tmp_path / "interactive-run"
    run_root.mkdir()
    calls: list[tuple[str, str]] = []

    monkeypatch.setattr(helpers, "get_wd", lambda _runid: str(run_root))
    monkeypatch.setattr(
        nodb_base,
        "clear_nodb_file_cache",
        lambda runid, *, pup_relpath: calls.append((runid, pup_relpath))
        or [Path(pup_relpath)],
    )

    cleared = default_cache_clearer(
        "interactive-run",
        run_root.resolve(),
        (run_root / "ash.nodb", run_root / "ron.nodb"),
    )

    assert calls == [
        ("interactive-run", "ash.nodb"),
        ("interactive-run", "ron.nodb"),
    ]
    assert cleared == [Path("ash.nodb"), Path("ron.nodb")]
