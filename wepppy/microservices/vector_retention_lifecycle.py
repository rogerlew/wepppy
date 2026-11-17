"""Account for retained evidence crossing existing project copy/reset boundaries.

Raw uploads remain opaque. Only bounded, application-owned receipts are read.
The existing run-filesystem ledger and repair obligations remain authoritative.
"""
from __future__ import annotations

from contextlib import ExitStack, contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Iterator, Sequence
import uuid

from . import vector_upload_normalization as retention

_BORROWED: ContextVar[dict[str, Any]] = ContextVar("vector_retention_borrowed", default={})
_TERMINAL = {"accepted", "accepted_recovered", "rejected", "incomplete", "corrupt_attempt"}
_COPY_RECEIPT = "copy-source-receipt.json"


def _error(message: str) -> retention.VectorUploadError:
    return retention.VectorUploadError("vector_retention_quota_exceeded", message, status_code=507)


def _sensitive(path: Path) -> bool:
    parts = path.parts
    return "vector_upload_attempts" in parts or any(
        parts[index:index + 2] == ("archives", "private") for index in range(len(parts) - 1)
    )


def _roots(tree: Path) -> list[Path]:
    if tree.is_symlink():
        raise _error("Retained evidence operation requires a real project path.")
    if not tree.exists():
        return []
    if _sensitive(tree):
        return [tree]
    result = []
    for directory, children, files in os.walk(tree, followlinks=False):
        if "normalization.json" in files:
            # Profile archive exports retain receipts but flatten archives/.
            # Match the ledger scanner's receipt-parent discovery here too.
            result.append(Path(directory))
            children[:] = []
            continue
        for name in files:
            path = Path(directory) / name
            if _sensitive(path):
                raise _error("Retained evidence root must be a directory without symbolic links.")
        for child in list(children):
            path = Path(directory) / child
            if _sensitive(path):
                if path.is_symlink():
                    raise _error("Retained evidence must not contain symbolic links.")
                result.append(path)
                children.remove(child)
            elif path.is_symlink():
                children.remove(child)
    return result


def _reject_linked_evidence(tree: Path) -> None:
    """Reject evidence a following copytree would materialize through model links."""
    for directory, children, _files in os.walk(tree, followlinks=False):
        for name in children:
            link = Path(directory) / name
            if not link.is_symlink():
                continue
            visited = set()
            for linked_dir, linked_children, linked_files in os.walk(link, followlinks=True):
                info = Path(linked_dir).stat()
                identity = (info.st_dev, info.st_ino)
                if identity in visited:
                    linked_children[:] = []
                    continue
                visited.add(identity)
                if "normalization.json" in linked_files or any(
                    _sensitive(Path(linked_dir) / child) for child in linked_children + linked_files
                ):
                    raise _error("Retained evidence must not be copied through symbolic links.")


def _has_evidence(tree: Path) -> bool:
    return any(retention._regular_tree_size(root) for root in _roots(tree))


def has_retained_evidence(tree: Path) -> bool:
    """Classify nested retained roots using the same discovery as accounting."""
    return _has_evidence(Path(tree))


def _read_receipt(path: Path) -> tuple[bytes, dict[str, Any]]:
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    with os.fdopen(descriptor, "rb") as stream:
        raw = stream.read(retention._RECEIPT_ALLOWANCE + 1)
    if len(raw) > retention._RECEIPT_ALLOWANCE:
        raise _error("Retained evidence receipt exceeds its bound.")
    value = retention._strict_json(raw)
    if value.get("schema") != "vector-normalization-v1" or value.get("status") not in _TERMINAL:
        raise _error("Reconcile nonterminal or invalid retained evidence before copying.")
    return raw, value


def _inventory(tree: Path) -> tuple[int, list[Path]]:
    total = 0
    receipts = []
    for root in _roots(tree):
        root_bytes = retention._regular_tree_size(root)
        accounted = 0
        for receipt in root.rglob("normalization.json"):
            if len(receipts) >= 10_000:
                raise _error("Retained evidence inventory exceeds the recovery bound.")
            _read_receipt(receipt)
            size = retention._regular_tree_size(receipt.parent)
            accounted += size
            receipts.append(receipt)
        if accounted != root_bytes:
            raise _error("Retained evidence without a complete receipt requires reconciliation.")
        total += root_bytes
    return total, receipts


def _configured_root(target: Path, *, has_evidence: bool, managed_export: bool) -> Path | None:
    configured = os.getenv("VECTOR_UPLOAD_RUN_FILESYSTEM_ROOT", "").strip()
    identity = os.getenv("VECTOR_UPLOAD_RUN_FILESYSTEM_ID", "").strip()
    if configured and not identity and managed_export:
        root = Path(configured).resolve(strict=True)
        if target.resolve().is_relative_to(root):
            raise _error("Vector evidence retention identity is not configured.")
    if not configured or not identity:
        if managed_export or not has_evidence:
            return None
        raise _error("Vector evidence retention identity is not configured.")
    root = Path(configured).resolve(strict=True)
    resolved = target.resolve()
    if resolved == root:
        raise _error("Retained evidence target must be below the configured filesystem root.")
    if not resolved.is_relative_to(root):
        # Existing server-resolved destinations on other storage are outside
        # this ledger. Both settings above establish that boundary explicitly.
        return None
    if target.is_symlink():
        raise _error("Retained evidence target must not be a symbolic link.")
    return root


def retained_tree_repair_pending(target: Path, operation: str, *, recovery_paths: Sequence[Path] = ()) -> bool:
    target = Path(target)
    root = _configured_root(
        target, has_evidence=_has_evidence(target) or any(_has_evidence(Path(path)) for path in recovery_paths),
        managed_export=False,
    )
    if root is None:
        return False
    return retention.retention_rebuild_obligation_pending(
        root, operation=operation, target=target.resolve().relative_to(root).as_posix(),
    )


@contextmanager
def borrow_retention_scope(key: str, lease: Any) -> Iterator[None]:
    """Expose an already-owned workflow scope without acquiring it again."""
    token = _BORROWED.set({**_BORROWED.get(), key: lease})
    try:
        yield
    finally:
        _BORROWED.reset(token)


@dataclass
class TreeOperation:
    repair_pending: bool = False
    maintenance: Any = None
    leases: tuple[Any, ...] = ()
    sync_paths: tuple[Path, ...] = ()

    def checkpoint(self) -> None:
        if self.maintenance is not None:
            self.maintenance.assert_owned()
        for lease in self.leases:
            lease.assert_owned()


def _copy_payload(receipt: Path, actor: retention.RetentionActor) -> tuple[bytes, dict[str, Any]]:
    raw, value = _read_receipt(receipt)
    updated = dict(value)
    updated["retention_actor"] = actor.receipt_value()
    updated["copied_from"] = {
        "receipt_sha256": hashlib.sha256(raw).hexdigest(),
        "project_identity": str(value.get("project_identity", ""))[:160],
        "attempt_id": str(value.get("attempt_id", ""))[:64],
    }
    return raw, updated


def _copy_allowance(receipts: list[Path], actor: retention.RetentionActor, size: int) -> int:
    # Count the complete physical copy, plus bounded metadata added by this copy.
    for receipt in receipts:
        raw, updated = _copy_payload(receipt, actor)
        encoded = json.dumps(updated, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        if len(encoded) > retention._RECEIPT_ALLOWANCE:
            raise _error("Copied evidence receipt exceeds its bound.")
        size += len(encoded) - len(raw) + len(raw)
    return size


def _admit_copy(maintenance: Any, root: Path, allowance: int, actor: retention.RetentionActor) -> None:
    prefix = f"vector-upload-retention:{os.environ['VECTOR_UPLOAD_RUN_FILESYSTEM_ID'].strip()}"
    totals = maintenance.connection.hgetall(f"{prefix}:totals")
    bucket = actor.ledger_bucket
    principal = maintenance.connection.hgetall(
        f"{prefix}:principal:{hashlib.sha256(bucket.encode()).hexdigest()}"
    )
    try:
        if totals.get("initialized") != "1":
            raise ValueError("ledger is not initialized")
        total_committed = int(totals.get("committed", 0))
        principal_committed = int(principal.get("committed", 0))
        total_reserved = int(totals.get("reserved", 0))
        principal_reserved = int(principal.get("reserved", 0))
        total_bytes = total_committed + total_reserved
        principal_bytes = principal_committed + principal_reserved
        if min(total_committed, principal_committed, total_reserved, principal_reserved) < 0:
            raise ValueError("negative accounting")
    except (ValueError, TypeError) as exc:
        raise _error("Retained evidence accounting requires reconciliation.") from exc
    limit = retention._UNATTRIBUTED_LIMIT if bucket == "unattributed" else retention._PRINCIPAL_LIMIT
    if total_bytes + allowance > retention._GLOBAL_LIMIT or principal_bytes + allowance > limit:
        raise _error("Copied evidence exceeds the retention quota.")
    if retention.shutil.disk_usage(root).free < allowance + total_reserved + retention._FREE_SPACE_RESERVE:
        raise _error("Copied evidence would exhaust the filesystem reserve.")


def _write_raw(path: Path, raw: bytes) -> None:
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        retention._fsync_directory(path.parent)
    finally:
        temporary.unlink(missing_ok=True)


def _publish_copy_provenance(source: Path, target: Path, receipts: list[Path], actor: retention.RetentionActor, state: TreeOperation) -> None:
    for receipt in receipts:
        state.checkpoint()
        destination = target / receipt.relative_to(source)
        if not destination.exists():
            # Established partial forks can deliberately omit entire model roots.
            if destination.parent.exists() and retention._regular_tree_size(destination.parent):
                raise _error("Copied evidence is missing its receipt; repair is required.")
            continue
        if destination.is_symlink():
            raise _error("Copied evidence receipt must not be a symbolic link.")
        # Verify copied evidence, rather than treating copy exit status as truth.
        for original in receipt.parent.rglob("*"):
            if original.is_file():
                copied = destination.parent / original.relative_to(receipt.parent)
                if retention._hash_regular(original) != retention._hash_regular(copied):
                    raise _error("Copied evidence bytes do not match the source.")
        raw, updated = _copy_payload(receipt, actor)
        _write_raw(destination.parent / _COPY_RECEIPT, raw)
        retention._atomic_json(destination, updated)


def _sync_evidence(target: Path) -> None:
    ancestors = set()
    for root in _roots(target):
        retention._regular_tree_size(root)
        directories = []
        for directory, _children, files in os.walk(root):
            directories.append(Path(directory))
            for name in files:
                descriptor = os.open(Path(directory) / name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
                try:
                    os.fsync(descriptor)
                finally:
                    os.close(descriptor)
        for directory in reversed(directories):
            retention._fsync_directory(directory)
        ancestor = root.parent
        while ancestor.is_relative_to(target):
            ancestors.add(ancestor)
            if ancestor == target:
                break
            ancestor = ancestor.parent
    if target.exists():
        ancestors.add(target)
    for ancestor in sorted(ancestors, key=lambda path: len(path.parts), reverse=True):
        retention._fsync_directory(ancestor)
    boundary = Path(os.environ["VECTOR_UPLOAD_RUN_FILESYSTEM_ROOT"]).resolve(strict=True)
    parent = target.resolve().parent
    while parent.is_relative_to(boundary):
        if parent.exists():
            retention._fsync_directory(parent)
        if parent == boundary:
            break
        parent = parent.parent


def discover_retention_scopes(
    maintenance: Any, root: Path, paths: Sequence[Path], project_keys: Sequence[str],
) -> set[str]:
    """Include already-reserved descendant uploads before a parent mutation."""
    scopes = set(project_keys)
    resolved_paths = tuple(Path(path).resolve() for path in paths)
    prefix = f"vector-upload-retention:{os.environ['VECTOR_UPLOAD_RUN_FILESYSTEM_ID'].strip()}"
    for index, key in enumerate(maintenance.connection.scan_iter(match=f"{prefix}:reservation:*", count=100)):
        if index >= 10_000:
            raise _error("Retained evidence reservation inventory exceeds the recovery bound.")
        maintenance.assert_owned()
        metadata = maintenance.connection.hgetall(key)
        if metadata.get("state") == "committed":
            continue
        scope = str(metadata.get("project") or "")
        relative = str(metadata.get("attempt_relpath") or "")
        descendant = any(scope.startswith(parent + ";;") for parent in project_keys)
        if relative:
            attempt = (root / relative).resolve()
            if not attempt.is_relative_to(root):
                raise _error("Retained evidence reservation path requires reconciliation.")
            descendant = descendant or any(attempt.is_relative_to(path) for path in resolved_paths)
        if descendant:
            if not scope:
                raise _error("Retained evidence reservation scope requires reconciliation.")
            scopes.add(scope)
    return scopes


@contextmanager
def retained_tree_operation(
    target: Path,
    *,
    source: Path | None = None,
    project_keys: Sequence[str] = (),
    actor: retention.RetentionActor | None = None,
    operation: str = "project_copy",
    managed_export: bool = False,
    recovery_paths: Sequence[Path] = (),
) -> Iterator[TreeOperation]:
    """Fence, admit and account for an existing filesystem copy/reset operation.

    Failure leaves its deterministic obligation for an identical operation retry.
    Offline exports must be explicitly identified by their established caller.
    """
    target = Path(target)
    source = Path(source) if source is not None else None
    if source is not None:
        _reject_linked_evidence(source)
    has_evidence = (_has_evidence(target) or (source is not None and _has_evidence(source))
                    or any(_has_evidence(Path(path)) for path in recovery_paths))
    root = _configured_root(target, has_evidence=bool(has_evidence), managed_export=managed_export)
    if root is None:
        yield TreeOperation()
        return
    if source is not None and (source.resolve().is_relative_to(target.resolve()) or target.resolve().is_relative_to(source.resolve())):
        raise _error("Retained evidence copy source and destination overlap.")
    if not project_keys:
        raise _error("Retained evidence mutation requires its project scope.")
    borrowed = _BORROWED.get()
    cleanup = ExitStack()
    maintenance = None
    state = TreeOperation(sync_paths=tuple(Path(path) for path in recovery_paths))
    actor = actor or retention.RetentionActor("unattributed", None)
    try:
        # Maintenance acquisition never waits. A borrowed caller scope cannot
        # deadlock a global holder waiting for that project: it fails before work.
        maintenance = retention.acquire_retention_maintenance_lease()
        cleanup.callback(maintenance.release)
        state.maintenance = maintenance
        affected_paths = (target, *(Path(path) for path in recovery_paths))
        if source is not None:
            affected_paths += (source,)
        scopes = discover_retention_scopes(maintenance, root, affected_paths, project_keys)
        for key in sorted(scopes):
            lease = borrowed.get(key)
            if lease is None:
                lease = retention.RedisScopeLeaseFactory()(key)
                cleanup.callback(lease.release)
            state.leases += (lease,)
        state.checkpoint()
        has_evidence = (_has_evidence(target) or (source is not None and _has_evidence(source))
                    or any(_has_evidence(Path(path)) for path in recovery_paths))
        relative = target.resolve().relative_to(root).as_posix()
        state.repair_pending = retention.retention_rebuild_obligation_pending(
            root, operation=operation, target=relative, connection=maintenance.connection,
        )
        if not has_evidence and not state.repair_pending:
            yield state
            return
        receipts = []
        if source is not None:
            _reject_linked_evidence(source)
            source_bytes, receipts = _inventory(source)
            allowance = _copy_allowance(receipts, actor, source_bytes)
            # Existing bytes remain charged: cleanup may defer removal of a
            # renamed workspace, so speculative replacement credit is unsafe.
            _admit_copy(maintenance, root, allowance, actor)
        state.checkpoint()
        marker = retention.begin_retention_rebuild_obligation(
            root, operation=operation, target=relative, connection=maintenance.connection,
        )
        yield state
        state.checkpoint()
        if source is not None:
            _publish_copy_provenance(source, target, receipts, actor, state)
            _inventory(target)
        _sync_evidence(target)
        for recovery_path in state.sync_paths:
            _sync_evidence(recovery_path)
        state.checkpoint()
        retention.reconcile_retention(
            root, apply=True, rebuild_ledger=True, committed_only=True,
            maintenance_lease=maintenance, required_scope_leases=state.leases,
        )
        state.checkpoint()
        retention.complete_retention_rebuild_obligation(marker, connection=maintenance.connection)
    finally:
        cleanup.close()


__all__ = ["has_retained_evidence", "discover_retention_scopes", "borrow_retention_scope", "retained_tree_operation", "retained_tree_repair_pending"]
