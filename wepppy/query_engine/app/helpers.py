"""Identifier-only, side-effect-free query target resolution."""
from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import re

from wepppy.weppcloud.utils import helpers as run_helpers


@dataclass(frozen=True)
class QueryTarget:
    runid: str
    config: str
    path: Path
    parent_id: str
    parent_path: Path
    group_base: Path | None = None

    @property
    def credential_ids(self) -> tuple[str, ...]:
        ids = [self.runid]
        if self.parent_id not in ids:
            ids.append(self.parent_id)
        parts = self.parent_id.split(';;')
        if len(parts) == 3 and parts[0] == 'batch':
            base = f'batch;;{parts[1]};;_base'
            if base not in ids:
                ids.append(base)
        return tuple(ids)


def validate_runid(runid: str) -> None:
    parts = runid.split(';;')
    if any(not part or part in {'.', '..'} or any(c in part for c in '/\\%')
           or any(ord(c) < 32 or ord(c) == 127 for c in part) for part in parts):
        raise ValueError('Invalid run identifier')
    if len(parts) == 1:
        return
    if len(parts) == 3:
        group, kind, _ = parts
        if group in {'batch', 'culvert'} or (group == 'profile' and kind in {'tmp', 'fork', 'archive'}):
            return
        if kind in {'omni', 'omni-contrast'} and group not in {'profile', 'batch', 'culvert'}:
            return
    if len(parts) == 5 and parts[0] == 'batch' and parts[3] in {'omni', 'omni-contrast'}:
        return
    raise ValueError('Invalid run identifier')


def _locations(runid: str) -> list[tuple[Path, Path]]:
    """Trusted root plus lexical relative location, never a resolved tenant root."""
    parts = runid.split(';;')
    if len(parts) > 1:
        group, name, leaf = parts
        if group == 'batch':
            tail = Path(name) / ('_base' if leaf == '_base' else f'runs/{leaf}')
            return [(Path(run_helpers.get_batch_root_dir()), tail)]
        if group == 'culvert':
            return [(Path(os.getenv('CULVERTS_ROOT', '/wc1/culverts')), Path(name) / 'runs' / leaf)]
        key, subdir = {'tmp': ('PROFILE_PLAYBACK_RUN_ROOT', 'runs'),
                       'fork': ('PROFILE_PLAYBACK_FORK_ROOT', 'fork'),
                       'archive': ('PROFILE_PLAYBACK_ARCHIVE_ROOT', 'archive')}[name]
        return [(Path(run_helpers._playback_path(key, subdir)), Path(leaf))]
    result = [(Path(run_helpers.PRIMARY_RUNS_ROOT), Path(runid[:2]) / runid),
              (Path(run_helpers.LEGACY_RUNS_ROOT), Path(runid))]
    if run_helpers._PLAYBACK_USE_CLONE:
        result.insert(0, (Path(run_helpers._playback_path('PROFILE_PLAYBACK_RUN_ROOT', 'runs')), Path(runid)))
    return result


def checked_path(path: Path, root: Path) -> Path:
    """Reject tenant-changing symlinks, including siblings inside a trusted mount."""
    expected = root.resolve() / path.relative_to(root)
    if path.resolve() != expected:
        raise FileNotFoundError('Run not found')
    return expected


def _check_cache(runid: str, expected: Path) -> None:
    cache = run_helpers.redis_wd_cache_client
    if cache is not None:
        cached = cache.get(runid)
        if cached is not None:
            if isinstance(cached, bytes):
                cached = cached.decode('utf-8')
            # Compare lexically before probing any client-influenced cache path.
            if os.path.normpath(cached) != os.path.normpath(str(expected)):
                raise FileNotFoundError('Run not found')


def resolve_target(runid: str, config: str = '') -> QueryTarget:
    validate_runid(runid)
    parts = runid.split(';;')
    omni = (len(parts) == 5 or (len(parts) == 3 and parts[0] not in {'batch', 'culvert', 'profile'}
                              and parts[1] in {'omni', 'omni-contrast'}))
    parent_id = ';;'.join(parts[:-2]) if omni else runid
    path = Path(run_helpers.get_wd(runid, prefer_active=False, read_only=True))
    parent_path = path.parents[3] if parent_id != runid else path
    for root, relative in _locations(parent_id):
        if parent_path == root / relative:
            checked_path(parent_path, root)
            checked_path(path, root)
            break
    else:
        raise FileNotFoundError('Run not found')
    _check_cache(runid, path)
    if parent_id != runid:
        _check_cache(parent_id, parent_path)
    if not path.is_dir():
        raise FileNotFoundError('Run not found')
    group_base = None
    if parent_id.startswith('batch;;'):
        group_base = Path(run_helpers.get_batch_base_wd(parent_id.split(';;')[1]))
        checked_path(group_base, Path(run_helpers.get_batch_root_dir()))
    return QueryTarget(runid, config, path.resolve(), parent_id, parent_path.resolve(),
                       group_base.resolve() if group_base else None)


def resolve_http_target(raw: str) -> QueryTarget:
    parts = raw.removesuffix('/').split('/')
    if len(parts) != 2 or not re.fullmatch(r'[A-Za-z0-9_.-]+', parts[1]) or parts[1] in {'.', '..'}:
        raise ValueError('Invalid run/config target')
    return resolve_target(parts[0], parts[1])


def resolve_run_path(runid_param: str) -> Path:
    """MCP accepts a bare identifier; neither transport accepts filesystem paths."""
    return resolve_target(runid_param).path
