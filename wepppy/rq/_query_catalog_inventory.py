"""Replayable directory streaming; Redis state is coordination, never provenance."""
from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import time
from typing import Any

from redis.exceptions import WatchError


class InventorySuperseded(RuntimeError):
    """A replaced inventory attempt cannot publish progress."""


class InventoryScopeMissing(FileNotFoundError):
    """A discovered child disappeared while its required root remains present."""


def validated_scope_path(roots: list[Any], value: str) -> Path:
    """Map a Redis locator lexically before any resolving/project-writing API."""
    if not isinstance(value, str):
        raise ValueError('Malformed inventory scope path')
    path = Path(value)
    if not path.is_absolute() or '..' in path.parts:
        raise ValueError('Inventory scope must be inside a configured root')
    matches = []
    for index, root in enumerate(roots):
        try:
            relative = path.relative_to(root.path)
        except ValueError:
            continue
        matches.append((len(Path(root.path).parts), index, relative))
    if not matches:
        raise ValueError('Inventory scope is outside configured roots')
    _, index, relative = max(matches)
    try:
        return _validated_scope_relative(roots, index, relative)
    except InventoryScopeMissing:
        raise
    except FileNotFoundError:
        # Only explicitly configured namespace/layout aliases may replace a
        # missing root spelling. Never redirect a symlink or missing child.
        missing_child = None
        for alias_index, alias in enumerate(roots):
            if (alias_index == index or alias.namespace != roots[index].namespace or
                    alias.layout != roots[index].layout):
                continue
            try:
                return _validated_scope_relative(roots, alias_index, relative)
            except InventoryScopeMissing as exc:
                missing_child = exc
            except FileNotFoundError:
                continue
        if missing_child is not None:
            raise missing_child
        raise


def _validated_scope_relative(roots: list[Any], index: int, relative: Path) -> Path:
    root = Path(roots[index].path)
    # A missing required root remains an error, never a deleted-child success.
    validated_path(roots, {'root': index, 'relative': '.'})
    _identity(root)
    try:
        result = validated_path(roots, {'root': index, 'relative': str(relative)})
        _identity(result)
    except (FileNotFoundError, NotADirectoryError) as exc:
        validated_path(roots, {'root': index, 'relative': '.'})
        _identity(root)
        if relative == Path('.'):
            raise
        raise InventoryScopeMissing('Discovered scope is no longer a directory') from exc
    return result


def state(connection: Any, key: str) -> dict[str, Any]:
    raw = connection.get(key + ':discovery')
    return json.loads(raw) if raw else {}


def initialize(pipeline: Any, key: str, cycle: str, roots: list[Any], *, seeds: list[dict[str, Any]] | None = None) -> None:
    pipeline.delete(*(key + suffix for suffix in (':frontier', ':seen', ':scopes', ':stream')))
    pipeline.set(key + ':discovery', json.dumps({
        'cycle': cycle, 'job_id': None, 'started_at': time.time(), 'visited': 0,
        'entries': 0, 'errors': [],
    }))
    frontier = seeds if seeds is not None else [{'root': i, 'relative': '.'} for i in range(len(roots))]
    if frontier:
        pipeline.rpush(key + ':frontier', *(json.dumps(item) for item in frontier))


def validated_path(roots: list[Any], item: dict[str, Any]) -> Path:
    index = item.get('root')
    relative = item.get('relative')
    if type(index) is not int or not 0 <= index < len(roots) or not isinstance(relative, str):
        raise ValueError('Malformed inventory frontier')
    rel = Path(relative)
    if rel.is_absolute() or '..' in rel.parts:
        raise ValueError('Inventory path escapes configured root')
    root = Path(roots[index].path)
    path = root
    # Check each component, including intermediate scenario containers.
    for component in (None, *rel.parts):
        if component is not None:
            path = path / component
        if stat.S_ISLNK(path.lstat().st_mode):
            raise ValueError('Inventory symlink is not traversable')
    path.resolve().relative_to(root.resolve())
    return path


def _identity(path: Path) -> list[int]:
    info = path.stat()
    if not stat.S_ISDIR(info.st_mode):
        raise NotADirectoryError(str(path))
    return [info.st_dev, info.st_ino]


def checkpoint(connection: Any, key: str, job_id: str, cycle: str, *,
               children: list[dict[str, Any]] = (), scope: str | None = None,
               identity: list[int] | None = None, exhausted: bool = False,
               entries: int = 0, error: str | None = None) -> None:
    """Fence dedup, frontier, discoveries and completion in one transaction."""
    with connection.pipeline() as pipe:
        pipe.watch(key + ':discovery', key + ':generation')
        current = state(pipe, key)
        if current.get('job_id') != job_id or current.get('cycle') != cycle:
            raise InventorySuperseded('Inventory attempt was replaced')
        reset = identity is not None and current.get('directory_identity') != identity
        fresh = []
        for child in children:
            encoded = json.dumps(child, sort_keys=True)
            if reset or not pipe.sismember(key + ':seen', encoded):
                fresh.append(encoded)
        publish_scope = scope is not None and not pipe.sismember(key + ':scopes', scope)
        current['entries'] = current.get('entries', 0) + entries
        current['updated_at'] = time.time()
        current['errors'] = [error] if error else []
        if identity is not None:
            current['directory_identity'] = identity
        if exhausted:
            current['visited'] = current.get('visited', 0) + 1
            current.pop('directory_identity', None)
        pipe.multi()
        if reset:
            pipe.delete(key + ':seen')
        if fresh:
            pipe.sadd(key + ':seen', *fresh)
            pipe.rpush(key + ':frontier', *fresh)
        if publish_scope:
            pipe.sadd(key + ':scopes', scope)
            pipe.xadd(key + ':stream', {'path': scope})
        if exhausted:
            pipe.lpop(key + ':frontier')
            pipe.delete(key + ':seen')
        pipe.set(key + ':discovery', json.dumps(current))
        try:
            pipe.execute()
        except WatchError as exc:
            raise InventorySuperseded('Inventory checkpoint ownership changed') from exc


def _complete(connection: Any, key: str, job_id: str, cycle: str) -> None:
    with connection.pipeline() as pipe:
        pipe.watch(key + ':discovery', key + ':frontier', key + ':generation')
        current = state(pipe, key)
        if current.get('job_id') != job_id or current.get('cycle') != cycle:
            raise InventorySuperseded('Inventory completion ownership changed')
        if pipe.llen(key + ':frontier') or current.get('errors'):
            raise RuntimeError('Incomplete inventory cannot complete')
        current['completed_at'] = time.time()
        pipe.multi()
        pipe.set(key + ':discovery', json.dumps(current))
        try:
            pipe.execute()
        except WatchError as exc:
            raise InventorySuperseded('Inventory completion ownership changed') from exc


def run(connection: Any, key: str, job_id: str, cycle: str, roots: list[Any], limit: int, *, approved_paths: set[str] | None = None, validate_scope: Any = None) -> None:
    """Stream to exhaustion; restart replays only the current directory prefix.

    Each publication contains at most ``limit`` entry records. RQ supplies the
    overall execution deadline; slow directory I/O never holds a scheduler lock.
    """
    while True:
        current = state(connection, key)
        if current.get('job_id') != job_id or current.get('cycle') != cycle:
            raise InventorySuperseded('Inventory attempt was replaced')
        raw = connection.lindex(key + ':frontier', 0)
        if raw is None:
            _complete(connection, key, job_id, cycle)
            return
        item = json.loads(raw)
        try:
            path = validated_path(roots, item)
            if approved_paths is not None:
                if str(path) not in approved_paths:
                    raise ValueError('Inventory scope is outside pilot manifest')
                validate_scope(path)
            identity = _identity(path)
            checkpoint(connection, key, job_id, cycle, identity=identity)
            project = any((path / marker).is_file() for marker in ('ron.nodb', 'wepp.nodb', '_query_engine/catalog.json'))
            children = []
            if approved_paths is not None:
                if not project:
                    raise ValueError('Approved pilot project marker missing')
                validate_scope(path)
                checkpoint(connection, key, job_id, cycle, scope=str(path), exhausted=True)
                continue
            if project:
                for name in ('_pups', 'rhessys/scenarios', 'runs', '_base'):
                    child = path / name
                    try:
                        info = child.lstat()
                    except FileNotFoundError:
                        continue
                    if stat.S_ISDIR(info.st_mode):
                        children.append({'root': item['root'], 'relative': str(child.relative_to(roots[item['root']].path))})
                validated_path(roots, item)
                if _identity(path) != identity:
                    raise RuntimeError('Inventory directory replaced during discovery')
                for offset in range(0, len(children), limit):
                    checkpoint(connection, key, job_id, cycle, children=children[offset:offset + limit])
                checkpoint(connection, key, job_id, cycle, scope=str(path), exhausted=True)
                continue
            count = 0
            with os.scandir(path) as stream:
                for entry in stream:
                    count += 1
                    if entry.is_dir(follow_symlinks=False):
                        children.append({'root': item['root'], 'relative': str(Path(entry.path).relative_to(roots[item['root']].path))})
                    if count >= limit:
                        validated_path(roots, item)
                        if _identity(path) != identity:
                            raise RuntimeError('Inventory directory replaced during streaming')
                        checkpoint(connection, key, job_id, cycle, children=children, entries=count)
                        children, count = [], 0
            validated_path(roots, item)
            if _identity(path) != identity:
                raise RuntimeError('Inventory directory replaced during streaming')
            checkpoint(connection, key, job_id, cycle, children=children, entries=count, exhausted=True)
        except FileNotFoundError:
            # Removed children are no longer scopes. A required missing root is
            # degraded unless another configured alias covers its namespace.
            if item.get('relative') != '.':
                checkpoint(connection, key, job_id, cycle, exhausted=True)
                continue
            namespace = roots[item['root']].namespace
            aliases = [root for i, root in enumerate(roots) if i != item['root'] and root.namespace == namespace]
            if any(Path(root.path).is_dir() and os.access(root.path, os.R_OK | os.X_OK) for root in aliases):
                checkpoint(connection, key, job_id, cycle, exhausted=True)
                continue
            checkpoint(connection, key, job_id, cycle, error='FileNotFoundError')
            raise
        except InventorySuperseded:
            raise
        except (OSError, ValueError, RuntimeError) as exc:
            # Worker boundary retains incomplete frontier for retry; no project writes.
            checkpoint(connection, key, job_id, cycle, error=type(exc).__name__)
            raise
