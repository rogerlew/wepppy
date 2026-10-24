"""Durable query-catalog intent, publication ownership and synchronous barriers.

Redis coordinates admission, never the durability of an accepted invalidation.
The filesystem guard also fences synchronous tools and destructive run lifecycle
operations. Scientific artifacts are read, never regenerated, by this module.
"""
from __future__ import annotations

import base64
import fcntl
import hashlib
import json
import logging
import os
import stat
import threading
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

LOGGER = logging.getLogger(__name__)
PROTOCOL = 1
REFRESH_PATH = Path('_query_engine/refresh')
__all__ = ['RootConfig', 'CatalogScope', 'CatalogRefreshConflict', 'configured_roots',
           'catalog_worker_configuration', 'resolve_scope', 'catalog_lifecycle_guard',
           'invalidate_catalog_incarnation', 'record_catalog_refresh', 'request_catalog_refresh',
           'pending_catalog_requests', 'refresh_catalog', 'ensure_catalog_fresh',
           'catalog_refresh_status', 'catalog_snapshot', 'publish_catalog', 'atomic_json',
           'is_refresh_path', 'set_catalog_refresh_state', 'catalog_guard_identity', 'catalog_refresh_enabled', 'is_catalog_readonly']


class CatalogRefreshConflict(RuntimeError):
    """The source scope or catalog changed while metadata was collected."""


@dataclass(frozen=True)
class RootConfig:
    path: Path
    namespace: str
    coordination: Path
    layout: str = 'sharded'


@dataclass(frozen=True)
class CatalogScope:
    base: Path
    owner: Path
    namespace: str
    relative_path: str
    scope_id: str
    managed: bool
    incarnation: str | None
    directory_identity: tuple[int, int] | None

    def as_dict(self) -> dict[str, Any]:
        return {'wd': str(self.base), 'namespace': self.namespace,
                'relative_path': self.relative_path, 'scope_id': self.scope_id,
                'managed': self.managed, 'incarnation': self.incarnation}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _default_roots() -> list[RootConfig]:
    roots = []
    for storage in ('/wc1', '/geodata/wc1'):
        for name, layout in [('runs', 'sharded'), ('batch', 'batch'), ('culverts', 'culverts')]:
            roots.append(RootConfig(Path(storage) / name, 'wc1:' + name,
                                    Path(storage) / 'query-engine-coordination/locks', layout))
    roots.append(RootConfig(Path('/geodata/weppcloud_runs'), 'legacy:runs',
                            Path('/geodata/wc1/query-engine-coordination/locks'), 'flat'))
    return roots


def configured_roots() -> list[RootConfig]:
    """Configured shared roots; canonical roots never silently become standalone."""
    raw = os.environ.get('QUERY_CATALOG_ROOTS_JSON')
    if not raw:
        if catalog_refresh_enabled():
            raise ValueError('QUERY_CATALOG_ROOTS_JSON is required when catalog refresh is enabled')
        return _default_roots()
    data = json.loads(raw)
    if not isinstance(data, list) or not data:
        raise ValueError('QUERY_CATALOG_ROOTS_JSON must be a nonempty list')
    roots = []
    for item in data:
        if not isinstance(item, dict):
            raise ValueError('Catalog root configuration must be an object')
        root = RootConfig(Path(item['path']).resolve(), str(item['namespace']),
                          Path(item['coordination']).resolve(), str(item.get('layout', 'sharded')))
        if not root.namespace or root.layout not in {'sharded', 'flat', 'batch', 'culverts'}:
            raise ValueError('Invalid catalog root namespace or layout')
        if root.coordination.is_relative_to(root.path):
            raise ValueError('Coordination must be outside replaceable run roots')
        roots.append(root)
    return roots


def catalog_worker_configuration() -> dict[str, Any]:
    return {'protocol': PROTOCOL, 'roots': [
        {'path': str(r.path), 'namespace': r.namespace, 'coordination': str(r.coordination),
         'layout': r.layout} for r in configured_roots()]}


def _root_for(base: Path) -> RootConfig | None:
    configured = configured_roots()
    for root in sorted(configured, key=lambda r: len(r.path.parts), reverse=True):
        if base.is_relative_to(root.path.resolve()):
            return root
    if any(base.is_relative_to(r.path.resolve()) for r in _default_roots()):
        raise ValueError('Managed catalog root lacks shared coordination configuration')
    return None


def _owner(root: RootConfig, base: Path) -> Path:
    relative = base.relative_to(root.path.resolve())
    depth = 2 if root.layout == 'sharded' else 1
    if root.layout in {'batch', 'culverts'}:
        depth = 1
    if len(relative.parts) < depth:
        raise ValueError('Catalog scope must name a project, not a run root')
    return root.path.resolve().joinpath(*relative.parts[:depth])


def _read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(data, dict):
        raise ValueError('Catalog metadata must be a JSON object')
    return data


def _identity(base: Path) -> tuple[int, int]:
    stat = base.stat()
    if not base.is_dir():
        raise NotADirectoryError(base)
    return stat.st_dev, stat.st_ino


def _validate_metadata_tree(base: Path) -> None:
    query = base / '_query_engine'
    refresh = base / REFRESH_PATH
    for path in (query, refresh, query / 'catalog.json', refresh / 'requests',
                 refresh / 'attempts', refresh / 'incarnation.json', refresh / 'status.json'):
        if path.is_symlink():
            raise ValueError('Catalog metadata directories cannot be symlinks')


def is_catalog_readonly(wd: str | Path) -> bool:
    base = Path(wd).expanduser().resolve()
    root = _root_for(base)
    owner = _owner(root, base) if root else base
    return (base / 'READONLY').exists() or (owner / 'READONLY').exists()


def resolve_scope(wd: str | Path, *, create: bool = False) -> CatalogScope:
    base = Path(wd).expanduser().resolve()
    _validate_metadata_tree(base)
    root = _root_for(base)
    owner = _owner(root, base) if root else base
    namespace = root.namespace if root else 'standalone'
    relative = base.relative_to(root.path.resolve()).as_posix() if root else str(base)
    scope_id = _hash(namespace + '\0' + relative)
    marker = base / REFRESH_PATH / 'incarnation.json'
    incarnation = None
    if marker.exists():
        data = _read_json(marker)
        if data.get('scope_id') != scope_id or bool(data.get('managed')) != bool(root):
            if root is not None or data.get('managed'):
                raise CatalogRefreshConflict('Catalog identity belongs to another project scope')
            # Detached standalone copies have no executable background authority.
            # Reads remain valid; first publication rotates copied coordination.
            if create:
                if is_catalog_readonly(base):
                    raise PermissionError('Readonly project cannot initialize refresh state')
                invalidate_catalog_incarnation(base)
                return resolve_scope(base)
        else:
            incarnation = str(data['incarnation'])
    identity = _identity(base) if base.exists() else None
    scope = CatalogScope(base, owner, namespace, relative, scope_id, root is not None,
                         incarnation, identity)
    if create and incarnation is None:
        with catalog_lifecycle_guard(base):
            if is_catalog_readonly(base):
                raise PermissionError('Readonly project cannot initialize refresh state')
            if marker.exists():
                return resolve_scope(base)
            incarnation = str(uuid4())
            atomic_json(marker, {'protocol': PROTOCOL, 'scope_id': scope_id,
                                 'managed': root is not None, 'incarnation': incarnation})
        return resolve_scope(base)
    return scope


def catalog_guard_identity(wd: str | Path) -> tuple[str, str]:
    """Canonical owner identity for ordering multiple lifecycle guards."""
    base = Path(wd).expanduser().resolve()
    root = _root_for(base)
    if root is None:
        return ('standalone', str(base))
    return (root.namespace, _owner(root, base).relative_to(root.path.resolve()).as_posix())


_held = threading.local()
_lock_registry: dict[str, threading.RLock] = {}
_registry_guard = threading.Lock()


def _after_fork() -> None:
    global _held, _lock_registry, _registry_guard
    _held = threading.local()
    _lock_registry = {}
    _registry_guard = threading.Lock()


os.register_at_fork(after_in_child=_after_fork)


@contextmanager
def catalog_lifecycle_guard(wd: str | Path, *, allow_missing: bool = False, blocking: bool = True) -> Iterator[None]:
    """Stable managed-owner record lock, with process-local thread exclusion.

    Standalone missing directories have no asynchronous/lifecycle participants.
    Their creation path is permitted, but concurrent tree replacement must use a
    configured managed root, not the standalone local lock.
    """
    base = Path(wd).expanduser().resolve()
    _validate_metadata_tree(base)
    root = _root_for(base)
    marker = base / REFRESH_PATH / 'incarnation.json'
    if root is None and marker.exists() and _read_json(marker).get('managed'):
        raise ValueError('Managed project cannot use standalone coordination')
    if not base.exists() and not allow_missing:
        raise FileNotFoundError(base)
    if root:
        owner = _owner(root, base)
        key = _hash(root.namespace + '\0' + owner.relative_to(root.path.resolve()).as_posix())
        lock_path = root.coordination / (key + '.lock')
    else:
        if not base.exists():
            yield
            return
        lock_path = base / REFRESH_PATH / 'publication.lock'
    key = str(lock_path.resolve())
    with _registry_guard:
        thread_lock = _lock_registry.setdefault(key, threading.RLock())
    held = getattr(_held, 'locks', {})
    if getattr(_held, 'pid', None) != os.getpid():
        held = {}
        _held.pid = os.getpid()
    if key in held:
        yield
        return
    # POSIX record locks interoperate between the NFS client and the server's
    # local filesystem. flock does not on the shared NFS/local ZFS pairing.
    # Record locks are per-process, so threads must also share this mutex.
    if not thread_lock.acquire(blocking=blocking):
        raise BlockingIOError('Catalog owner guard is busy')
    try:
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o660)
        try:
            fcntl.lockf(fd, fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB))
            held[key] = fd
            _held.locks = held
            yield
        finally:
            held.pop(key, None)
            fcntl.lockf(fd, fcntl.LOCK_UN)
            os.close(fd)
    finally:
        thread_lock.release()


def atomic_json(path: Path, data: dict[str, Any], *, metadata_source: Path | None = None) -> None:
    """Publish complete durable JSON using a same-directory temporary inode."""
    path.parent.mkdir(parents=True, exist_ok=True)
    source = metadata_source if metadata_source is not None else path
    try:
        original = source.stat(follow_symlinks=False)
    except FileNotFoundError:
        if metadata_source is not None:
            raise
        original = None
    if original is not None and not stat.S_ISREG(original.st_mode):
        raise ValueError('Atomic catalog metadata destination must be a regular file')
    attributes = ({name: os.getxattr(source, name, follow_symlinks=False)
                   for name in os.listxattr(source, follow_symlinks=False)}
                  if original is not None else {})
    temporary = path.with_name('.' + path.name + '.' + str(uuid4()) + '.tmp')
    payload = json.dumps(data, indent=2, sort_keys=True).encode()
    fd = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600 if original is not None else 0o666)
    try:
        with os.fdopen(fd, 'wb') as stream:
            if original is not None:
                current = os.fstat(stream.fileno())
                if (current.st_uid, current.st_gid) != (original.st_uid, original.st_gid):
                    os.fchown(stream.fileno(), original.st_uid, original.st_gid)
            stream.write(payload)
            stream.flush()
            if original is not None:
                mode = stat.S_IMODE(original.st_mode)
                inherited = set(os.listxattr(stream.fileno()))
                for name in inherited - attributes.keys():
                    os.removexattr(stream.fileno(), name)
                for name, value in attributes.items():
                    if name not in inherited or os.getxattr(stream.fileno(), name) != value:
                        os.setxattr(stream.fileno(), name, value)
                preserved = {name: os.getxattr(stream.fileno(), name)
                             for name in os.listxattr(stream.fileno())}
                if preserved != attributes:
                    raise PermissionError('Cannot preserve catalog metadata extended attributes')
                os.fchmod(stream.fileno(), mode)
                if any(os.getxattr(stream.fileno(), name) != value for name, value in attributes.items()):
                    raise PermissionError('Catalog mode update changed extended attributes')
                current = os.fstat(stream.fileno())
                if (current.st_uid, current.st_gid, stat.S_IMODE(current.st_mode)) != (
                        original.st_uid, original.st_gid, mode):
                    raise PermissionError('Cannot preserve catalog metadata ownership and mode')
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        parent_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(parent_fd)
        finally:
            os.close(parent_fd)
    finally:
        temporary.unlink(missing_ok=True)


def is_refresh_path(path: str | Path) -> bool:
    parts = Path(path).parts
    return any(parts[i:i + 2] == ('_query_engine', 'refresh') for i in range(len(parts) - 1))


def invalidate_catalog_incarnation(wd: str | Path, *, recursive: bool = True) -> str:
    """Rotate lifecycle identity; retained old receipts are historical evidence."""
    base = Path(wd).resolve()
    with catalog_lifecycle_guard(base):
        # A copied marker may belong to the source project: establish fresh identity.
        root = _root_for(base)
        relative = base.relative_to(root.path.resolve()).as_posix() if root else str(base)
        namespace = root.namespace if root else 'standalone'
        incarnation = str(uuid4())
        receipts = base / REFRESH_PATH / 'requests'
        if receipts.exists():
            history = base / REFRESH_PATH / 'attempts' / ('retired-' + incarnation)
            history.parent.mkdir(parents=True, exist_ok=True)
            os.replace(receipts, history)
            receipts.mkdir()
        atomic_json(base / REFRESH_PATH / 'incarnation.json', {
            'protocol': PROTOCOL, 'scope_id': _hash(namespace + '\0' + relative),
            'managed': root is not None, 'incarnation': incarnation})
        atomic_json(base / REFRESH_PATH / 'status.json', {
            'protocol': PROTOCOL, 'incarnation': incarnation, 'state': 'pending',
            'reason': 'lifecycle_replaced', 'updated_at': _now()})
        if recursive:
            for marker in sorted(base.rglob('_query_engine/refresh/incarnation.json')):
                child = marker.parents[2]
                if child != base and not marker.is_symlink():
                    invalidate_catalog_incarnation(child, recursive=False)
        return incarnation


def _catalog_digest(base: Path) -> str | None:
    try:
        return hashlib.sha256((base / '_query_engine/catalog.json').read_bytes()).hexdigest()
    except FileNotFoundError:
        return None


def catalog_snapshot(wd: str | Path) -> tuple[CatalogScope, str | None]:
    if is_catalog_readonly(wd):
        raise PermissionError('Readonly project cannot publish catalog metadata')
    with catalog_lifecycle_guard(wd):
        return resolve_scope(wd, create=True), _catalog_digest(Path(wd).resolve())


def _validate_scope(scope: CatalogScope) -> None:
    current = resolve_scope(scope.base)
    if (current.incarnation != scope.incarnation or
            current.directory_identity != scope.directory_identity):
        raise CatalogRefreshConflict('Project was replaced during catalog collection')
    if is_catalog_readonly(scope.base):
        raise PermissionError('Project became readonly during catalog collection')


def publish_catalog(wd: str | Path, catalog: dict[str, Any], *,
                    snapshot: tuple[CatalogScope, str | None] | None = None,
                    acknowledged: Iterable[str] = ()) -> dict[str, Any]:
    base = Path(wd).resolve()
    with catalog_lifecycle_guard(base):
        scope = resolve_scope(base, create=True)
        if snapshot:
            _validate_scope(snapshot[0])
            if _catalog_digest(base) != snapshot[1]:
                raise CatalogRefreshConflict('Catalog changed during metadata collection')
        _validate_scope(scope)
        catalog = dict(catalog)
        catalog['files'] = [e for e in catalog.get('files', []) if not is_refresh_path(e['path'])]
        atomic_json(base / '_query_engine/catalog.json', catalog)
        acknowledged = sorted(acknowledged)
        status = {'protocol': PROTOCOL, 'incarnation': scope.incarnation,
                  'catalog_digest': _catalog_digest(base), 'publication_id': str(uuid4()),
                  'state': 'current', 'updated_at': _now(), 'acknowledged': acknowledged}
        if pending_catalog_requests(base):
            status['state'] = 'pending'
        atomic_json(base / REFRESH_PATH / 'status.json', status)
        return status


def _asset_path(base: Path, asset_path: str | None) -> str | None:
    if asset_path is None:
        return None
    from .activate import _is_allowed_target, _normalize_relative_parts
    raw = Path(asset_path)
    if raw.is_absolute():
        raw = raw.relative_to(base)
    normalized = Path(*_normalize_relative_parts(raw)).as_posix()
    if normalized in {'landuse.parquet', 'soils.parquet', 'watershed.parquet'}:
        raise ValueError('Retired root dataset aliases are not catalog keys')
    if is_refresh_path(normalized):
        raise ValueError('Refresh metadata is not a query dataset')
    if is_refresh_path((base / normalized).resolve()):
        raise ValueError('Refresh metadata is not a query dataset')
    if not _is_allowed_target(base, (base / normalized).resolve()):
        raise ValueError('Catalog asset escapes its authorized project scope')
    return normalized


def record_catalog_refresh(wd: str | Path, asset_path: str | None = None) -> dict[str, Any]:
    base = Path(wd).resolve()
    asset = _asset_path(base, asset_path)
    if is_catalog_readonly(base):
        raise PermissionError('Readonly project cannot record catalog intent')
    with catalog_lifecycle_guard(base):
        scope = resolve_scope(base, create=True)
        _validate_scope(scope)
        identifier = str(uuid4())
        request = {'protocol': PROTOCOL, 'scope_id': scope.scope_id,
                   'incarnation': scope.incarnation, 'request_id': identifier,
                   'asset_path': asset, 'created_at': _now()}
        atomic_json(base / REFRESH_PATH / 'requests' / (identifier + '.json'), request)
        return {**request, 'state': 'pending'}


def pending_catalog_requests(wd: str | Path) -> list[dict[str, Any]]:
    scope = resolve_scope(wd)
    directory = scope.base / REFRESH_PATH / 'requests'
    requests: list[dict[str, Any]] = []
    if not directory.exists() or scope.incarnation is None:
        return requests
    for path in sorted(directory.glob('*.json')):
        if path.is_symlink():
            raise ValueError('Catalog receipt cannot be a symlink')
        try:
            request = _read_json(path)
        except FileNotFoundError:
            # A publisher may acknowledge this immutable receipt after glob.
            # It replaces the catalog before unlinking; readers load it afterward.
            continue
        if (request.get('scope_id') != scope.scope_id or
                request.get('incarnation') != scope.incarnation):
            raise CatalogRefreshConflict('Pending request belongs to another incarnation')
        if not isinstance(request.get('request_id'), str) or request['request_id'] + '.json' != path.name:
            raise ValueError('Pending request identity does not match filename')
        _asset_path(scope.base, request.get('asset_path'))
        requests.append(request)
    return requests


def catalog_refresh_enabled() -> bool:
    value = os.environ.get('QUERY_CATALOG_REFRESH_ENABLED', 'false').lower()
    if value not in {'true', 'false', '1', '0'}:
        raise ValueError('QUERY_CATALOG_REFRESH_ENABLED must be true, false, 1, or 0')
    return value in {'true', '1'}


def request_catalog_refresh(wd: str | Path, asset_path: str | None = None) -> dict[str, Any]:
    scope = resolve_scope(wd)
    enabled = catalog_refresh_enabled()
    if not scope.managed or not enabled:
        from .activate import activate_query_engine, update_catalog_entry
        if asset_path is None:
            activate_query_engine(wd, run_interchange=False, force_refresh=True)
        else:
            update_catalog_entry(wd, asset_path)
        return {'state': 'current', 'scope_id': scope.scope_id, 'request_id': None}
    receipt = record_catalog_refresh(wd, asset_path)
    from wepppy.rq.query_catalog_rq import enqueue_catalog_refresh
    admission_scope = dict(scope.as_dict(), scope_id=receipt['scope_id'],
                           incarnation=receipt['incarnation'])
    admission = enqueue_catalog_refresh(wd, scope=admission_scope)
    if admission:
        receipt.update(admission)
    return receipt


def _load_catalog(base: Path, *, rebuild_malformed: bool = False) -> dict[str, Any] | None:
    try:
        catalog = _read_json(base / '_query_engine/catalog.json')
        if (not isinstance(catalog.get('root'), str) or
                not isinstance(catalog.get('version'), int) or
                not isinstance(catalog.get('files'), list)):
            raise ValueError('Invalid query catalog structure')
        for entry in catalog['files']:
            if (not isinstance(entry, dict) or
                    not all(isinstance(entry.get(key), str) for key in ('path', 'extension', 'modified')) or
                    not isinstance(entry.get('size_bytes'), int) or
                    (entry.get('fs_path') is not None and not isinstance(entry['fs_path'], str)) or
                    (entry.get('schema') is not None and not isinstance(entry['schema'], dict))):
                raise ValueError('Invalid query catalog entry structure')
        return catalog
    except FileNotFoundError:
        return None
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
        if not rebuild_malformed:
            raise
        # A catalog is derived metadata. Retain the corrupt bytes until a valid
        # replacement is published; log its digest so repair remains observable.
        LOGGER.warning('Rebuilding malformed query catalog scope=%s digest=%s',
                       base, _catalog_digest(base), exc_info=True)
        return None


def _updated_catalog(base: Path, catalog: dict[str, Any] | None,
                     paths: Iterable[str | None], *, prefer_canonical: bool = False) -> dict[str, Any]:
    from .activate import _build_catalog, _build_catalog_subset, _build_entry
    paths = list(paths)
    if catalog is None or None in paths:
        entries = _build_catalog(base)
        # Native and PyArrow type spellings differ for dates/nested types. Use
        # one authoritative schema representation for collection and validation.
        from .activate import _read_parquet_schema
        for entry in entries:
            if entry.get('extension') == '.parquet':
                selected = Path(entry.get('fs_path') or entry['path'])
                selected = selected if selected.is_absolute() else base / selected
                entry['schema'] = _read_parquet_schema(selected)
    else:
        by_path = {entry['path']: entry for entry in catalog.get('files', [])
                   if not is_refresh_path(entry['path'])}
        for asset in sorted({p for p in paths if p is not None}):
            normalized = _asset_path(base, asset)
            assert normalized is not None
            target = base / normalized
            prefix = normalized.rstrip('/') + '/'
            old_entry = by_path.get(normalized)
            if old_entry and old_entry.get('fs_path'):
                candidate = Path(old_entry['fs_path'])
                if candidate.is_absolute() and catalog.get('root') != str(base):
                    from .core import _resolve_dataset_path, _find_parent_run_root
                    try:
                        _resolve_dataset_path(base, str(candidate), normalized)
                    except ValueError:
                        old_root = Path(str(catalog['root'])).resolve()
                        original = _resolve_dataset_path(old_root, str(candidate), normalized)
                        if original.is_relative_to(old_root):
                            candidate = base / original.relative_to(old_root)
                        else:
                            old_parent = _find_parent_run_root(old_root)
                            new_parent = _find_parent_run_root(base)
                            if old_parent is None or new_parent is None:
                                raise ValueError('Relocated input requires an allowed parent run')
                            candidate = new_parent / original.relative_to(old_parent)
                selected = candidate if candidate.is_absolute() else base / candidate
                # A newly generated child artifact supersedes inherited parent input.
                if not (prefer_canonical and target.exists() and not selected.resolve().is_relative_to(base)):
                    target = selected
                from .activate import _is_allowed_target
                if not _is_allowed_target(base, target.resolve()):
                    raise ValueError('Catalog selected source escapes project scope')
            # Subtree invalidation must remove deleted children as well as add new ones.
            for key in list(by_path):
                if key == normalized or key.startswith(prefix):
                    del by_path[key]
            if target.is_dir():
                for child_entry in _build_catalog_subset(base, target):
                    by_path[child_entry['path']] = child_entry
            elif target.exists():
                if is_refresh_path(target.resolve()):
                    raise ValueError('Refresh metadata is not a query dataset')
                if old_entry and target.suffix.lower() != '.parquet' and _matches_stat(old_entry, target.stat()):
                    entry = dict(old_entry)
                else:
                    built_entry = _build_entry(base, target, catalog_path=normalized)
                    if built_entry is None:
                        raise ValueError('Unsupported catalog asset type')
                    entry = built_entry
                if old_entry and entry and _matches_stat(old_entry, target.stat()):
                    entry['modified'] = old_entry['modified']
                if entry is None:
                    raise ValueError('Unsupported catalog asset type')
                if old_entry and old_entry.get('schema') and entry.get('schema') is None and entry['extension'] != '.parquet':
                    entry['schema'] = old_entry['schema']
                if old_entry and old_entry.get('fs_path'):
                    entry['fs_path'] = str(target.relative_to(base)) if target.is_relative_to(base) else str(target)
                by_path[normalized] = entry
        entries = sorted(by_path.values(), key=lambda e: e['path'])
    return {'version': 1, 'root': str(base), 'generated_at': _now(), 'files': entries}


def _required_inventory(base: Path, paths: Iterable[str | None]) -> set[str]:
    """Inventory required files without the legacy scanner's skip-on-error policy."""
    from .activate import SUPPORTED_EXTENSIONS, _is_allowed_target
    required: set[str] = set()
    seen: set[Path] = set()
    stack = [base if p is None else base / p for p in paths]
    while stack:
        path = stack.pop()
        if is_refresh_path(path.relative_to(base) if path.is_relative_to(base) else path):
            continue
        try:
            resolved = path.resolve(strict=True)
        except FileNotFoundError:
            # Deleted assets are legitimate invalidations, not failed metadata.
            continue
        if not _is_allowed_target(base, resolved) or is_refresh_path(resolved):
            continue
        if path.is_dir():
            if resolved in seen:
                continue
            seen.add(resolved)
            with os.scandir(path) as entries:
                stack.extend(Path(entry.path) for entry in entries)
        elif path.suffix.lower() in SUPPORTED_EXTENSIONS:
            path.stat()  # propagate unreadable/stat failure rather than certify current
            required.add(path.relative_to(base).as_posix())
    return required


def _matches_stat(entry: dict[str, Any], stat: os.stat_result) -> bool:
    rounded = datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat()
    truncated = datetime.fromtimestamp(stat.st_mtime_ns // 1_000_000_000, timezone.utc).replace(
        microsecond=(stat.st_mtime_ns % 1_000_000_000) // 1000).isoformat()
    return stat.st_size == entry.get('size_bytes') and entry.get('modified') in {rounded, truncated}


def _verify_required(base: Path, catalog: dict[str, Any], paths: Iterable[str | None]) -> None:
    paths = list(paths)
    from .activate import _is_allowed_target
    returned = {entry['path'] for entry in catalog.get('files', [])}
    missing = _required_inventory(base, paths) - returned
    if missing:
        raise ValueError('Required catalog assets were skipped: ' + ', '.join(sorted(missing)))
    for entry in catalog.get('files', []):
        name = entry['path']
        required = None in paths or any(name == p or name.startswith(p.rstrip('/') + '/')
                                        for p in paths if p is not None)
        if not required:
            continue
        raw = Path(entry.get('fs_path') or name)
        selected = raw if raw.is_absolute() else base / raw
        if not _is_allowed_target(base, selected.resolve()):
            raise ValueError('Catalog dependency escapes project scope')
        stat = selected.stat()
        if is_refresh_path(selected.resolve()):
            raise ValueError('Refresh metadata is not a query dataset')
        if not _matches_stat(entry, stat):
            raise CatalogRefreshConflict('Catalog source changed during collection')
        if entry.get('extension') == '.parquet':
            import pyarrow.parquet as pq  # type: ignore[import-untyped]
            actual = pq.read_schema(selected)  # preserve read-denial/corruption types
            fields = []
            for field in actual:
                description = {'name': field.name, 'type': str(field.type)}
                for key in ('units', 'description'):
                    if field.metadata and key.encode() in field.metadata:
                        description[key] = field.metadata[key.encode()].decode(errors='ignore')
                fields.append(description)
            if entry.get('schema') != {'fields': fields}:
                raise CatalogRefreshConflict('Required Parquet schema changed during collection')


def _acknowledge(base: Path, scope: CatalogScope, snapshot: list[dict[str, Any]],
                 publication: dict[str, Any]) -> None:
    identifiers = [r['request_id'] for r in snapshot]
    attempt = dict(publication, request_ids=identifiers, state='published')
    atomic_json(base / REFRESH_PATH / 'attempts' / (publication['publication_id'] + '.json'), attempt)
    for identifier in identifiers:
        (base / REFRESH_PATH / 'requests' / (identifier + '.json')).unlink(missing_ok=True)
    status = dict(publication)
    status['state'] = 'pending' if pending_catalog_requests(base) else 'current'
    atomic_json(base / REFRESH_PATH / 'status.json', status)


def refresh_catalog(wd: str | Path, *, expected_incarnation: str | None = None,
                    strict: bool = True) -> dict[str, Any]:
    """Refresh one finite pending snapshot; later arrivals are never acknowledged."""
    base = Path(wd).resolve()
    if is_catalog_readonly(base):
        raise PermissionError('Readonly project cannot refresh its catalog')
    with catalog_lifecycle_guard(base):
        scope, digest = catalog_snapshot(base)
        if expected_incarnation is not None and expected_incarnation != scope.incarnation:
            raise CatalogRefreshConflict('Queued refresh belongs to an old project incarnation')
        requests = pending_catalog_requests(base)
        catalog = _load_catalog(base, rebuild_malformed=True)
        if catalog is None and (base / '_query_engine/catalog.json').exists():
            raw_catalog = (base / '_query_engine/catalog.json').read_bytes()
            atomic_json(base / REFRESH_PATH / 'attempts' / ('malformed-' + str(uuid4()) + '.json'), {
                'protocol': PROTOCOL, 'incarnation': scope.incarnation,
                'state': 'malformed_catalog', 'catalog_digest': hashlib.sha256(raw_catalog).hexdigest(),
                'catalog_bytes_base64': base64.b64encode(raw_catalog).decode('ascii'),
                'updated_at': _now()}, metadata_source=base / '_query_engine/catalog.json')
        paths = ([r['asset_path'] for r in requests] or [None]) if catalog is not None else [None]
        set_catalog_refresh_state(base, 'running', expected_incarnation=scope.incarnation)
    try:
        candidate = _updated_catalog(base, catalog, paths, prefer_canonical=True)
        if strict:
            _verify_required(base, candidate, paths)
        with catalog_lifecycle_guard(base):
            if strict:
                _verify_required(base, candidate, paths)
            publication = publish_catalog(base, candidate, snapshot=(scope, digest),
                                          acknowledged=[r['request_id'] for r in requests])
            _acknowledge(base, scope, requests, publication)
        return catalog_refresh_status(base)
    except (OSError, ValueError, RuntimeError) as exc:
        # Deliberate maintenance boundary: persist safe diagnostic state, then fail.
        LOGGER.exception('Catalog refresh failed scope=%s', scope.scope_id)
        with catalog_lifecycle_guard(base):
            current = resolve_scope(base)
            if (current.incarnation == scope.incarnation and
                    current.directory_identity == scope.directory_identity and
                    not is_catalog_readonly(base)):
                failure = {'protocol': PROTOCOL, 'incarnation': scope.incarnation,
                           'state': 'failed', 'error_code': 'catalog_refresh_failed',
                           'error_type': type(exc).__name__, 'updated_at': _now(),
                           'request_ids': [r['request_id'] for r in requests]}
                atomic_json(base / REFRESH_PATH / 'attempts' / (str(uuid4()) + '.json'), failure)
                atomic_json(base / REFRESH_PATH / 'status.json', failure)
        raise


def catalog_refresh_status(wd: str | Path) -> dict[str, Any]:
    scope = resolve_scope(wd)
    path = scope.base / REFRESH_PATH / 'status.json'
    status = _read_json(path) if path.exists() else {'state': 'pending'}
    pending = pending_catalog_requests(scope.base)
    if (status.get('incarnation') != scope.incarnation or
            status.get('catalog_digest') != _catalog_digest(scope.base)):
        if status.get('state') != 'failed':
            status['state'] = 'pending'
    elif pending and status.get('state') == 'current':
        status['state'] = 'pending'
    return dict(status, scope_id=scope.scope_id, pending_count=len(pending),
                oldest_pending_at=min((r['created_at'] for r in pending), default=None))


def ensure_catalog_fresh(wd: str | Path, required_paths: Iterable[str] | None = None) -> dict[str, Any]:
    """Drain existing intent and verify selected sources without Redis/queue waits."""
    base = Path(wd).resolve()
    required_paths = list(required_paths or [])
    for path in required_paths:
        if str(path) in {'landuse.parquet', 'soils.parquet', 'watershed.parquet'}:
            raise FileNotFoundError(f'Retired root dataset alias is not a catalog key: {path}')
    required = [_asset_path(base, p) for p in required_paths]
    pending = pending_catalog_requests(base)
    catalog = _load_catalog(base, rebuild_malformed=True)
    if catalog is None:
        refresh_catalog(base)
        catalog = _load_catalog(base)
    elif pending:
        refresh_catalog(base)
        catalog = _load_catalog(base, rebuild_malformed=True)
    if catalog is None:
        raise RuntimeError('Catalog publication did not produce a readable catalog')
    if required:
        candidate = _updated_catalog(base, catalog, required)
        old = {e['path']: e for e in catalog.get('files', [])}
        new = {e['path']: e for e in candidate['files']}
        _verify_required(base, candidate, required)
        if catalog.get('root') != str(base):
            return candidate
        if old != new:
            if is_catalog_readonly(base):
                raise PermissionError('Readonly catalog has stale required metadata')
            scope, digest = catalog_snapshot(base)
            # Re-read current catalog after snapshot; another publisher may have
            # changed unrelated entries before ownership was obtained.
            candidate = _updated_catalog(base, _load_catalog(base), required)
            _verify_required(base, candidate, required)
            publish_catalog(base, candidate, snapshot=(scope, digest))
            catalog = candidate
    return catalog


def set_catalog_refresh_state(wd: str | Path, state: str, *,
                              expected_incarnation: str | None = None,
                              job_id: str | None = None,
                              error_code: str | None = None) -> None:
    """Record admission/execution progress without claiming source freshness."""
    if state not in {'pending', 'queued', 'running', 'failed'}:
        raise ValueError('Invalid catalog maintenance state')
    base = Path(wd).resolve()
    if is_catalog_readonly(base):
        raise PermissionError('Readonly project cannot write catalog state')
    with catalog_lifecycle_guard(base):
        scope = resolve_scope(base)
        if expected_incarnation is not None and scope.incarnation != expected_incarnation:
            raise CatalogRefreshConflict('Catalog state belongs to another incarnation')
        _validate_scope(scope)
        path = base / REFRESH_PATH / 'status.json'
        current = _read_json(path) if path.exists() else {}
        current.update(protocol=PROTOCOL, incarnation=scope.incarnation,
                       catalog_digest=_catalog_digest(base), state=state, updated_at=_now())
        if job_id is not None:
            current['job_id'] = job_id
        if error_code is not None:
            current['error_code'] = error_code
        atomic_json(path, current)
