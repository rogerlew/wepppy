#!/usr/bin/env python3
"""Repair Batch Runner identity copied into an interactive project fork."""

from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
from typing import Any


RUNID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
BACKUP_ROOT_NAME = "_repair_backups"
BACKUP_PREFIX = "forked_batch_identity_"


class RepairError(RuntimeError):
    """Raised when the requested repair is unsafe or internally inconsistent."""


@dataclass(frozen=True)
class ControllerRepair:
    path: Path
    original_text: str
    repaired_text: str
    batch_name: str


@dataclass(frozen=True)
class MetadataRepair:
    path: Path
    original_text: str
    batch_name: str


@dataclass(frozen=True)
class RepairPlan:
    run_root: Path
    runid: str
    batch_name: str | None
    controller_repairs: tuple[ControllerRepair, ...]
    metadata_repair: MetadataRepair | None

    @property
    def has_changes(self) -> bool:
        return bool(self.controller_repairs or self.metadata_repair is not None)


@dataclass(frozen=True)
class ApplyResult:
    backup_dir: Path | None
    changed_controllers: tuple[Path, ...]
    removed_metadata: bool
    cleared_cache_entries: tuple[str, ...]


@dataclass(frozen=True)
class CacheRetryResult:
    backup_dir: Path
    cleared_cache_entries: tuple[str, ...]
    already_complete: bool


CacheClearer = Callable[[str, Path, Sequence[Path]], Sequence[object]]


def _read_json_mapping(path: Path) -> tuple[str, dict[str, Any]]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RepairError(f"Cannot read {path}: {exc}") from exc

    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RepairError(f"Invalid JSON in {path}: {exc}") from exc

    if not isinstance(payload, dict):
        raise RepairError(f"Expected a JSON object in {path}")
    return text, payload


def _controller_state(payload: dict[str, Any], path: Path) -> dict[str, Any]:
    state = payload.get("py/state", payload)
    if not isinstance(state, dict):
        raise RepairError(f"Expected object-valued py/state in {path}")
    return state


def _render_like_source(payload: Mapping[str, Any], original_text: str) -> str:
    rendered = json.dumps(payload, ensure_ascii=False)
    if original_text.endswith("\n"):
        rendered += "\n"
    return rendered


def _metadata_batch_name(payload: Mapping[str, Any], path: Path) -> str | None:
    raw_batch_name = payload.get("batch_name")
    if raw_batch_name is not None:
        if not isinstance(raw_batch_name, str) or not raw_batch_name.strip():
            raise RepairError(f"Invalid batch_name in {path}")

    raw_runid = payload.get("runid")
    if raw_runid is not None and not isinstance(raw_runid, str):
        raise RepairError(f"Invalid runid in {path}")
    encoded_batch_name: str | None = None
    if isinstance(raw_runid, str) and raw_runid.startswith("batch;;"):
        parts = raw_runid.split(";;")
        if len(parts) != 3 or not parts[1] or not parts[2]:
            raise RepairError(f"Malformed batch runid in {path}: {raw_runid!r}")
        encoded_batch_name = parts[1]

    has_batch_name = raw_batch_name is not None
    has_batch_runid = encoded_batch_name is not None
    if has_batch_name != has_batch_runid:
        raise RepairError(f"Incomplete batch identity in {path}")
    if (
        isinstance(raw_batch_name, str)
        and encoded_batch_name is not None
        and raw_batch_name != encoded_batch_name
    ):
        raise RepairError(
            f"Conflicting batch names in {path}: "
            f"{sorted((raw_batch_name, encoded_batch_name))!r}"
        )
    return encoded_batch_name


def _validate_run_root(run_root: Path, runid: str) -> Path:
    if not RUNID_PATTERN.fullmatch(runid):
        raise RepairError(f"Invalid primary run ID: {runid!r}")

    try:
        resolved = run_root.resolve(strict=True)
    except OSError as exc:
        raise RepairError(f"Cannot resolve run root {run_root}: {exc}") from exc

    if not resolved.is_dir():
        raise RepairError(f"Run root is not a directory: {resolved}")
    if resolved.name != runid:
        raise RepairError(
            f"Run root basename {resolved.name!r} does not match --runid {runid!r}"
        )
    return resolved


def build_repair_plan(
    *,
    run_root: Path,
    runid: str,
    expected_batch_name: str | None = None,
) -> RepairPlan:
    """Inspect one primary run and return a fully validated repair plan."""
    resolved_root = _validate_run_root(run_root, runid)
    if expected_batch_name is not None and not expected_batch_name.strip():
        raise RepairError("--expected-batch-name cannot be empty")

    nodb_paths = sorted(resolved_root.glob("*.nodb"))
    if not nodb_paths:
        raise RepairError(f"No root .nodb files found in {resolved_root}")

    controller_repairs: list[ControllerRepair] = []
    observed_batch_names: set[str] = set()

    for path in nodb_paths:
        if path.is_symlink() or not path.is_file():
            raise RepairError(f"Root NoDb path must be a regular non-symlink file: {path}")

        original_text, payload = _read_json_mapping(path)
        state = _controller_state(payload, path)
        run_group = state.get("_run_group")
        group_name = state.get("_group_name")

        if run_group is None:
            if group_name not in (None, ""):
                raise RepairError(
                    f"Inconsistent group identity in {path}: run_group is null but "
                    f"group_name is {group_name!r}"
                )
            continue

        if run_group != "batch":
            raise RepairError(
                f"Refusing to normalize non-batch run_group {run_group!r} in {path}"
            )
        if not isinstance(group_name, str) or not group_name.strip():
            raise RepairError(f"Batch controller lacks a valid group_name in {path}")
        if expected_batch_name is not None and group_name != expected_batch_name:
            raise RepairError(
                f"Batch name mismatch in {path}: expected {expected_batch_name!r}, "
                f"found {group_name!r}"
            )

        observed_batch_names.add(group_name)
        state["_run_group"] = None
        state["_group_name"] = None
        controller_repairs.append(
            ControllerRepair(
                path=path,
                original_text=original_text,
                repaired_text=_render_like_source(payload, original_text),
                batch_name=group_name,
            )
        )

    metadata_repair: MetadataRepair | None = None
    metadata_path = resolved_root / "run_metadata.json"
    if metadata_path.exists():
        if metadata_path.is_symlink() or not metadata_path.is_file():
            raise RepairError(
                f"run_metadata.json must be a regular non-symlink file: {metadata_path}"
            )
        original_text, metadata_payload = _read_json_mapping(metadata_path)
        metadata_batch_name = _metadata_batch_name(metadata_payload, metadata_path)
        if metadata_batch_name is not None:
            if (
                expected_batch_name is not None
                and metadata_batch_name != expected_batch_name
            ):
                raise RepairError(
                    f"Batch name mismatch in {metadata_path}: expected "
                    f"{expected_batch_name!r}, found {metadata_batch_name!r}"
                )
            observed_batch_names.add(metadata_batch_name)
            metadata_repair = MetadataRepair(
                path=metadata_path,
                original_text=original_text,
                batch_name=metadata_batch_name,
            )

    if len(observed_batch_names) > 1:
        raise RepairError(
            f"Conflicting batch names across run state: {sorted(observed_batch_names)!r}"
        )

    detected_batch_name = next(iter(observed_batch_names), None)
    return RepairPlan(
        run_root=resolved_root,
        runid=runid,
        batch_name=detected_batch_name,
        controller_repairs=tuple(controller_repairs),
        metadata_repair=metadata_repair,
    )


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _atomic_write_text(
    path: Path,
    text: str,
    *,
    mode_source: Path | None = None,
) -> None:
    source_stat = (mode_source or path).stat()
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temp_path = Path(temp_name)
    try:
        os.fchmod(fd, source_stat.st_mode & 0o7777)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_path, path)
    except OSError:
        try:
            os.close(fd)
        except OSError:
            pass
        temp_path.unlink(missing_ok=True)
        raise


def _default_cache_clearer(
    runid: str,
    run_root: Path,
    controller_paths: Sequence[Path],
) -> Sequence[object]:
    from wepppy.nodb.base import clear_nodb_file_cache
    from wepppy.weppcloud.utils.helpers import get_wd

    resolved_runtime_root = Path(get_wd(runid)).resolve(strict=True)
    if resolved_runtime_root != run_root:
        raise RepairError(
            f"Runtime path mismatch for {runid!r}: {resolved_runtime_root} != {run_root}"
        )
    cleared: list[object] = []
    for controller_path in controller_paths:
        relative_path = controller_path.relative_to(run_root)
        if len(relative_path.parts) != 1 or relative_path.suffix != ".nodb":
            raise RepairError(
                f"Cache-clear scope must be one root NoDb file: {relative_path}"
            )
        cleared.extend(
            clear_nodb_file_cache(runid, pup_relpath=str(relative_path))
        )
    return cleared


def _create_backup(plan: RepairPlan, *, now: datetime) -> Path:
    backup_parent = plan.run_root / BACKUP_ROOT_NAME
    if os.path.lexists(backup_parent) and backup_parent.is_symlink():
        raise RepairError(f"Backup parent cannot be a symlink: {backup_parent}")
    backup_parent.mkdir(mode=0o750, exist_ok=True)
    if backup_parent.resolve() != backup_parent:
        raise RepairError(f"Backup parent did not resolve to itself: {backup_parent}")

    stamp = now.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_dir = backup_parent / f"{BACKUP_PREFIX}{stamp}"
    try:
        backup_dir.mkdir(mode=0o750)
    except FileExistsError as exc:
        raise RepairError(f"Backup directory already exists: {backup_dir}") from exc

    for repair in plan.controller_repairs:
        shutil.copy2(repair.path, backup_dir / repair.path.name)
    if plan.metadata_repair is not None:
        shutil.copy2(
            plan.metadata_repair.path,
            backup_dir / plan.metadata_repair.path.name,
        )

    manifest = {
        "status": "prepared",
        "created_at": now.astimezone(timezone.utc).isoformat(),
        "run_root": str(plan.run_root),
        "runid": plan.runid,
        "batch_name": plan.batch_name,
        "controller_repairs": [
            {
                "filename": repair.path.name,
                "before_sha256": _sha256_text(repair.original_text),
                "after_sha256": _sha256_text(repair.repaired_text),
            }
            for repair in plan.controller_repairs
        ],
        "removed_run_metadata": plan.metadata_repair is not None,
    }
    (backup_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return backup_dir


def _assert_plan_is_current(plan: RepairPlan) -> None:
    for repair in plan.controller_repairs:
        try:
            current_text = repair.path.read_text(encoding="utf-8")
        except OSError as exc:
            raise RepairError(f"Cannot revalidate {repair.path}: {exc}") from exc
        if current_text != repair.original_text:
            raise RepairError(
                f"Repair plan is stale; controller changed after inspection: {repair.path}"
            )

    if plan.metadata_repair is not None:
        try:
            current_metadata = plan.metadata_repair.path.read_text(encoding="utf-8")
        except OSError as exc:
            raise RepairError(
                f"Cannot revalidate {plan.metadata_repair.path}: {exc}"
            ) from exc
        if current_metadata != plan.metadata_repair.original_text:
            raise RepairError(
                "Repair plan is stale; run_metadata.json changed after inspection"
            )


def _restore_written_files(
    *,
    written_controllers: Sequence[ControllerRepair],
    metadata_repair: MetadataRepair | None,
    metadata_removed: bool,
    backup_dir: Path,
) -> None:
    conflicts: list[str] = []
    for repair in reversed(written_controllers):
        try:
            current_text = repair.path.read_text(encoding="utf-8")
        except OSError as exc:
            conflicts.append(f"{repair.path}: cannot verify rollback target ({exc})")
            continue
        if current_text != repair.repaired_text:
            conflicts.append(f"{repair.path}: changed after repair write")
            continue
        backup_path = backup_dir / repair.path.name
        try:
            backup_text = backup_path.read_text(encoding="utf-8")
        except OSError as exc:
            conflicts.append(f"{repair.path}: cannot read backup ({exc})")
            continue
        if backup_text != repair.original_text:
            conflicts.append(f"{repair.path}: backup content failed verification")
            continue
        try:
            _atomic_write_text(repair.path, backup_text)
        except OSError as exc:
            conflicts.append(f"{repair.path}: atomic restore failed ({exc})")

    if metadata_removed and metadata_repair is not None:
        if metadata_repair.path.exists() or metadata_repair.path.is_symlink():
            conflicts.append(
                f"{metadata_repair.path}: recreated after repair metadata removal"
            )
        else:
            backup_path = backup_dir / metadata_repair.path.name
            try:
                backup_text = backup_path.read_text(encoding="utf-8")
            except OSError as exc:
                conflicts.append(
                    f"{metadata_repair.path}: cannot read backup ({exc})"
                )
            else:
                if backup_text != metadata_repair.original_text:
                    conflicts.append(
                        f"{metadata_repair.path}: backup content failed verification"
                    )
                else:
                    try:
                        _atomic_write_text(
                            metadata_repair.path,
                            backup_text,
                            mode_source=backup_path,
                        )
                    except OSError as exc:
                        conflicts.append(
                            f"{metadata_repair.path}: atomic restore failed ({exc})"
                        )

    if conflicts:
        raise RepairError("Rollback requires manual recovery: " + "; ".join(conflicts))


def _complete_manifest(
    manifest_path: Path,
    manifest: dict[str, Any],
    *,
    cleared_cache_entries: Sequence[str],
) -> None:
    manifest["status"] = "complete"
    manifest["completed_at"] = datetime.now(timezone.utc).isoformat()
    manifest["cleared_cache_entries"] = list(cleared_cache_entries)
    _atomic_write_text(
        manifest_path,
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
    )


def apply_repair_plan(
    plan: RepairPlan,
    *,
    clear_cache: bool,
    cache_clearer: CacheClearer | None = None,
    now: datetime | None = None,
) -> ApplyResult:
    """Apply a validated plan with backup, rollback, verification, and cache clear."""
    if not plan.has_changes:
        return ApplyResult(
            backup_dir=None,
            changed_controllers=(),
            removed_metadata=False,
            cleared_cache_entries=(),
        )

    _assert_plan_is_current(plan)
    effective_now = now or datetime.now(timezone.utc)
    backup_dir = _create_backup(plan, now=effective_now)
    written_controllers: list[ControllerRepair] = []
    metadata_removed = False
    try:
        for repair in plan.controller_repairs:
            try:
                current_text = repair.path.read_text(encoding="utf-8")
            except OSError as exc:
                raise RepairError(f"Cannot revalidate {repair.path}: {exc}") from exc
            if current_text != repair.original_text:
                raise RepairError(
                    f"Repair plan became stale before write: {repair.path}"
                )
            _atomic_write_text(repair.path, repair.repaired_text)
            written_controllers.append(repair)
        if plan.metadata_repair is not None:
            try:
                current_metadata = plan.metadata_repair.path.read_text(
                    encoding="utf-8"
                )
            except OSError as exc:
                raise RepairError(
                    f"Cannot revalidate {plan.metadata_repair.path}: {exc}"
                ) from exc
            if current_metadata != plan.metadata_repair.original_text:
                raise RepairError(
                    "Repair plan became stale before run_metadata.json removal"
                )
            plan.metadata_repair.path.unlink()
            metadata_removed = True

        verification = build_repair_plan(
            run_root=plan.run_root,
            runid=plan.runid,
            expected_batch_name=plan.batch_name,
        )
        if verification.has_changes:
            raise RepairError("Post-write verification still found active batch identity")
    except (OSError, RepairError) as exc:
        try:
            _restore_written_files(
                written_controllers=written_controllers,
                metadata_repair=plan.metadata_repair,
                metadata_removed=metadata_removed,
                backup_dir=backup_dir,
            )
        except RepairError as rollback_exc:
            raise RepairError(f"{exc}; {rollback_exc}") from rollback_exc
        raise

    cleared: tuple[str, ...] = ()
    if clear_cache:
        clearer = cache_clearer or _default_cache_clearer
        changed_paths = tuple(repair.path for repair in plan.controller_repairs)
        cleared = tuple(
            str(path)
            for path in clearer(plan.runid, plan.run_root, changed_paths)
        )

    manifest_path = backup_dir / "manifest.json"
    _manifest_text, manifest = _read_json_mapping(manifest_path)
    _complete_manifest(
        manifest_path,
        manifest,
        cleared_cache_entries=cleared,
    )

    return ApplyResult(
        backup_dir=backup_dir,
        changed_controllers=tuple(
            repair.path.relative_to(plan.run_root) for repair in plan.controller_repairs
        ),
        removed_metadata=plan.metadata_repair is not None,
        cleared_cache_entries=cleared,
    )


def retry_cache_clear_from_backup(
    *,
    run_root: Path,
    runid: str,
    backup_dir: Path,
    expected_batch_name: str | None = None,
    cache_clearer: CacheClearer | None = None,
) -> CacheRetryResult:
    """Retry only cache invalidation for an applied repair with a prepared manifest."""
    resolved_root = _validate_run_root(run_root, runid)
    expected_parent = resolved_root / BACKUP_ROOT_NAME
    if not os.path.lexists(expected_parent):
        raise RepairError(f"Backup parent does not exist: {expected_parent}")
    if expected_parent.is_symlink() or not expected_parent.is_dir():
        raise RepairError(
            f"Backup parent must be a regular non-symlink directory: {expected_parent}"
        )
    try:
        resolved_parent = expected_parent.resolve(strict=True)
    except OSError as exc:
        raise RepairError(f"Cannot resolve backup parent {expected_parent}: {exc}") from exc
    if resolved_parent != expected_parent:
        raise RepairError(f"Backup parent escapes the run root: {expected_parent}")

    lexical_backup = Path(os.path.abspath(os.fspath(backup_dir)))
    if lexical_backup.parent != expected_parent:
        raise RepairError(
            f"Backup must be one direct child of {expected_parent}: {lexical_backup}"
        )
    if lexical_backup.is_symlink():
        raise RepairError(f"Backup directory cannot be a symlink: {lexical_backup}")
    try:
        resolved_backup = lexical_backup.resolve(strict=True)
    except OSError as exc:
        raise RepairError(f"Cannot resolve backup directory {lexical_backup}: {exc}") from exc

    if (
        resolved_backup.parent != resolved_parent
        or resolved_backup != lexical_backup
        or not resolved_backup.name.startswith(BACKUP_PREFIX)
        or not resolved_backup.is_dir()
    ):
        raise RepairError(
            f"Backup must be one {BACKUP_PREFIX}* directory under {resolved_parent}"
        )

    manifest_path = resolved_backup / "manifest.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise RepairError(f"Backup manifest must be a regular non-symlink file: {manifest_path}")
    _manifest_text, manifest = _read_json_mapping(manifest_path)

    if manifest.get("run_root") != str(resolved_root):
        raise RepairError("Backup manifest run_root does not match the requested run")
    if manifest.get("runid") != runid:
        raise RepairError("Backup manifest runid does not match --runid")
    manifest_batch_name = manifest.get("batch_name")
    if expected_batch_name is not None and manifest_batch_name != expected_batch_name:
        raise RepairError(
            f"Backup manifest batch name mismatch: expected {expected_batch_name!r}, "
            f"found {manifest_batch_name!r}"
        )

    status = manifest.get("status")
    if status == "complete":
        prior_entries = manifest.get("cleared_cache_entries", [])
        if not isinstance(prior_entries, list) or not all(
            isinstance(entry, str) for entry in prior_entries
        ):
            raise RepairError("Completed backup manifest has invalid cache entry records")
        return CacheRetryResult(
            backup_dir=resolved_backup,
            cleared_cache_entries=tuple(prior_entries),
            already_complete=True,
        )
    if status != "prepared":
        raise RepairError(f"Backup manifest is not retryable: status={status!r}")

    current_plan = build_repair_plan(
        run_root=resolved_root,
        runid=runid,
        expected_batch_name=expected_batch_name,
    )
    if current_plan.has_changes:
        raise RepairError(
            "Cache-only retry requires the file repair to be fully applied first"
        )

    raw_repairs = manifest.get("controller_repairs")
    if not isinstance(raw_repairs, list) or not raw_repairs:
        raise RepairError("Backup manifest has no controller repair records")

    controller_paths: list[Path] = []
    for record in raw_repairs:
        if not isinstance(record, dict):
            raise RepairError("Backup manifest contains an invalid controller record")
        filename = record.get("filename")
        after_sha256 = record.get("after_sha256")
        if (
            not isinstance(filename, str)
            or Path(filename).name != filename
            or Path(filename).suffix != ".nodb"
            or not isinstance(after_sha256, str)
        ):
            raise RepairError("Backup manifest contains an unsafe controller record")
        controller_path = resolved_root / filename
        if controller_path.is_symlink() or not controller_path.is_file():
            raise RepairError(
                f"Repaired controller must be a regular non-symlink file: {controller_path}"
            )
        try:
            current_text = controller_path.read_text(encoding="utf-8")
        except OSError as exc:
            raise RepairError(f"Cannot verify repaired controller {controller_path}: {exc}") from exc
        if _sha256_text(current_text) != after_sha256:
            raise RepairError(
                f"Repaired controller changed since backup preparation: {controller_path}"
            )
        controller_paths.append(controller_path)

    clearer = cache_clearer or _default_cache_clearer
    cleared = tuple(
        str(path)
        for path in clearer(runid, resolved_root, tuple(controller_paths))
    )
    _complete_manifest(
        manifest_path,
        manifest,
        cleared_cache_entries=cleared,
    )
    return CacheRetryResult(
        backup_dir=resolved_backup,
        cleared_cache_entries=cleared,
        already_complete=False,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_root", type=Path, help="Explicit primary run directory")
    parser.add_argument("--runid", required=True, help="Expected primary run ID")
    parser.add_argument(
        "--expected-batch-name",
        help="Fail unless every copied batch marker has this exact group name",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Create backups and apply the repair; default is dry-run",
    )
    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="After apply, clear NoDb Redis cache entries for --runid",
    )
    parser.add_argument(
        "--retry-cache-from",
        type=Path,
        help=(
            "Retry cache invalidation from an explicit prepared backup manifest; "
            "cannot be combined with --apply or --clear-cache"
        ),
    )
    return parser


def _print_plan(plan: RepairPlan, *, apply: bool) -> None:
    mode = "APPLY" if apply else "DRY-RUN"
    print(f"[{mode}] run_root={plan.run_root}")
    print(f"runid={plan.runid} batch_name={plan.batch_name or '<none>'}")
    print(f"controllers_to_clear={len(plan.controller_repairs)}")
    for repair in plan.controller_repairs:
        print(f"  {repair.path.name}")
    print(f"remove_batch_run_metadata={plan.metadata_repair is not None}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.clear_cache and not args.apply:
        parser.error("--clear-cache requires --apply")
    if args.retry_cache_from is not None and (args.apply or args.clear_cache):
        parser.error("--retry-cache-from cannot be combined with --apply or --clear-cache")

    try:
        if args.retry_cache_from is not None:
            retry_result = retry_cache_clear_from_backup(
                run_root=args.run_root,
                runid=args.runid,
                backup_dir=args.retry_cache_from,
                expected_batch_name=args.expected_batch_name,
            )
            print(f"backup_dir={retry_result.backup_dir}")
            print(f"cache_entries_cleared={len(retry_result.cleared_cache_entries)}")
            print(f"already_complete={retry_result.already_complete}")
            return 0

        plan = build_repair_plan(
            run_root=args.run_root,
            runid=args.runid,
            expected_batch_name=args.expected_batch_name,
        )
        _print_plan(plan, apply=bool(args.apply))
        if not args.apply:
            return 0

        result = apply_repair_plan(plan, clear_cache=bool(args.clear_cache))
    except (OSError, RepairError, RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if result.backup_dir is None:
        print("No active copied batch identity found; no changes made.")
        return 0

    print(f"backup_dir={result.backup_dir}")
    print(f"controllers_cleared={len(result.changed_controllers)}")
    print(f"batch_run_metadata_removed={result.removed_metadata}")
    print(f"cache_entries_cleared={len(result.cleared_cache_entries)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
