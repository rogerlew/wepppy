"""Redis-backed metadata helper mirroring the legacy Prep controller."""

from __future__ import annotations

import os
import stat
import time
import weakref
from contextlib import contextmanager

from redis.exceptions import RedisError, WatchError
from wepppy.query_engine.catalog_refresh import redisprep_snapshot_guard, resolve_scope
from ._redis_prep_snapshot import RedisPrepSnapshotError, publish_snapshot, read_snapshot, validate_snapshot
from enum import Enum
from os.path import exists as _exists
from os.path import join as _join
from os.path import split as _split
from typing import Dict, Optional

from wepppy.config.redis_settings import RedisDB, redis_client


class TaskEnum(Enum):
    """Enumerate workflow tasks mirrored into Redis progress keys."""

    if_exists_rmtree = 'rmtree'
    project_init = 'project_init'
    set_outlet = 'set_outlet'
    abstract_watershed = 'abstract_watershed'
    build_channels = 'build_channels'
    find_outlet = 'find_outlet'
    build_subcatchments = 'build_subcatchments'
    build_landuse = 'build_landuse'
    build_treatments = 'build_treatments'
    build_rangeland_cover = 'build_rangeland_cover'
    build_soils = 'build_soils'
    build_climate = 'build_climate'
    fetch_rap_ts = 'build_rap_ts'
    fetch_openet_ts = 'build_openet_ts'
    fetch_polaris = 'build_polaris'
    run_wepp_hillslopes = 'run_wepp_hillslopes'
    run_wepp_watershed = 'run_wepp_watershed'
    run_ag_fields = 'run_ag_fields'
    run_observed = 'run_observed'
    run_debris = 'run_debris'
    run_postfire_debris_flow = 'run_postfire_debris_flow'
    run_roads = 'run_roads'
    run_watar = 'run_watar'
    run_geneva = 'run_geneva'
    run_rhem = 'run_rhem'
    fetch_dem = 'fetch_dem'
    landuse_map = 'landuse_map'
    init_sbs_map = 'init_sbs_map'
    run_omni_scenarios = 'run_omni_scenarios'
    run_omni_contrasts = 'run_omni_contrasts'
    dss_export = 'dss_export'
    run_features_export = 'run_features_export'
    build_rusle = 'build_rusle'
    set_readonly = 'set_readonly'
    run_path_cost_effective = 'run_path_ce'

    def __str__(self) -> str:
        return self.value.replace('TaskEnum.', '')
    
    def label(self) -> str:
        """Return a human-friendly label for the task."""

        return {
            TaskEnum.if_exists_rmtree: 'Remove existing files',
            TaskEnum.project_init: 'Initialize Project',
            TaskEnum.set_outlet: 'Set Outlet',
            TaskEnum.abstract_watershed: 'Abstract Watershed',
            TaskEnum.build_channels: 'Build Channels',
            TaskEnum.find_outlet: 'Find Outlet',
            TaskEnum.build_subcatchments: 'Build Subcatchments',
            TaskEnum.build_landuse: 'Build Landuse',
            TaskEnum.build_treatments: 'Build Treatments',
            TaskEnum.build_rangeland_cover: 'Build Rangeland Cover',
            TaskEnum.build_soils: 'Build Soils',
            TaskEnum.build_climate: 'Build Climate',
            TaskEnum.fetch_rap_ts: 'Build RAP TS',
            TaskEnum.fetch_openet_ts: 'Build OpenET TS',
            TaskEnum.fetch_polaris: 'Build POLARIS Layers',
            TaskEnum.run_wepp_hillslopes: 'Run WEPP Hillslopes',
            TaskEnum.run_wepp_watershed: 'Run WEPP Watershed',
            TaskEnum.run_ag_fields: 'Run Agricultural Fields',
            TaskEnum.run_observed: 'Run Observed',
            TaskEnum.run_debris: 'Run Debris',
            TaskEnum.run_postfire_debris_flow: 'Run Post-fire Debris Flow',
            TaskEnum.run_roads: 'Run Roads',
            TaskEnum.run_watar: 'Run WATAR',
            TaskEnum.run_geneva: 'Run Geneva',
            TaskEnum.run_rhem: 'Run RHEM',
            TaskEnum.fetch_dem: 'Fetch DEM',
            TaskEnum.landuse_map: 'Landuse Map',
            TaskEnum.init_sbs_map: 'Initialize SBS Map',
            TaskEnum.run_omni_scenarios: 'Run OMNI Scenarios',
            TaskEnum.run_omni_contrasts: 'Run OMNI Contrasts',
            TaskEnum.dss_export: 'Export DSS',
            TaskEnum.run_features_export: 'Export Features',
            TaskEnum.build_rusle: 'Build RUSLE',
            TaskEnum.set_readonly: 'Set Readonly',
            TaskEnum.run_path_cost_effective: 'Run PATH Cost-Effective',
        }.get(self, self.value)
    
    def emoji(self) -> str:
        """Return an emoji glyph representing the task."""

        return {
            TaskEnum.if_exists_rmtree: '🗑️',
            TaskEnum.project_init: '🚀',
            TaskEnum.set_outlet: '📍',
            TaskEnum.abstract_watershed: '💎',
            TaskEnum.build_channels: '🌊',
            TaskEnum.find_outlet: '📍',
            TaskEnum.build_subcatchments: '🧩',
            TaskEnum.build_landuse: '🌲',
            TaskEnum.build_treatments: '💊',
            TaskEnum.build_rangeland_cover: '🦎',
            TaskEnum.build_soils: '🪱',
            TaskEnum.build_climate: '☁️',
            TaskEnum.fetch_rap_ts: '🐮',
            TaskEnum.fetch_openet_ts: '🛰️',
            TaskEnum.fetch_polaris: '🧱',
            TaskEnum.run_wepp_hillslopes: '💧',
            TaskEnum.run_wepp_watershed: '⛰️',
            TaskEnum.run_ag_fields: '🌽',
            TaskEnum.run_observed: '📊',
            TaskEnum.run_debris: '🪨',
            TaskEnum.run_postfire_debris_flow: '🌋',
            TaskEnum.run_roads: '🚗',
            TaskEnum.run_watar: '🌋',
            TaskEnum.run_geneva: '🐈',
            TaskEnum.run_rhem: '🌵',
            TaskEnum.fetch_dem: '🌍',
            TaskEnum.landuse_map: '🗺️',
            TaskEnum.init_sbs_map: '🔥',
            TaskEnum.run_omni_scenarios: '🪓',
            TaskEnum.run_omni_contrasts: '⚖️',
            TaskEnum.dss_export: '📤',
            TaskEnum.run_features_export: '📦',
            TaskEnum.build_rusle: '🔱',
            TaskEnum.set_readonly: '🔒',
            TaskEnum.run_path_cost_effective: '🧮',
        }.get(self, self.value)

    def __getstate__(self) -> str:
        return self.value


class RedisPrep:
    """Cache limited Prep metadata in Redis for lightweight lookups."""

    def __init__(self, wd: str, cfg_fn: Optional[str] = None):
        self.wd = wd
        self.cfg_fn = cfg_fn
        self.redis = redis_client(RedisDB.LOCK, decode_responses=True)
        self._directory_fd = None
        self._scope = None
        self._publication_count = 0
        _, self.run_id = _split(wd.rstrip('/'))
        if os.path.isdir(self.wd):
            self._directory_fd = os.open(self.wd, os.O_RDONLY | os.O_DIRECTORY)
            weakref.finalize(self, os.close, self._directory_fd)
            self._scope = resolve_scope(self.wd)
            opened = os.fstat(self._directory_fd)
            if self._scope.directory_identity != (opened.st_dev, opened.st_ino):
                raise RedisPrepSnapshotError('RedisPrep directory changed while binding; reload')
            self.run_id = self._read_namespace()
        if not os.path.lexists(self.dump_filepath):
            self.lazy_load()

    def _read_namespace(self) -> str:
        _, run_id = _split(self.wd.rstrip('/'))
        try:
            fd = os.open('.redisprep-run-id', os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                         dir_fd=self._directory_fd)
        except FileNotFoundError:
            return run_id
        with os.fdopen(fd, encoding='utf-8') as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise ValueError('Invalid RedisPrep profile namespace file')
            namespace = stream.read().strip()
        parts = namespace.split(';;')
        if len(parts) != 3 or parts[:2] != ['profile', 'fork'] or not parts[2]:
            raise ValueError(f'Invalid RedisPrep profile namespace: {namespace!r}')
        return namespace

    def __getstate__(self) -> Dict[str, Optional[str]]:
        return {
            'wd': self.wd,
            'cfg_fn': self.cfg_fn,
            'run_id': self.run_id,
        }

    @staticmethod
    def getInstance(wd: str = '.', allow_nonexistent: bool = False, ignore_lock: bool = False) -> 'RedisPrep':
        instance = RedisPrep(wd)
        instance.lazy_load()
        return instance

    @staticmethod
    def tryGetInstance(wd: str = '.', allow_nonexistent: bool = True, ignore_lock: bool = False) -> Optional['RedisPrep']:
        try:
            return RedisPrep.getInstance(wd, allow_nonexistent=allow_nonexistent, ignore_lock=ignore_lock)
        except FileNotFoundError:
            return None
        
    @staticmethod
    def getInstanceFromRunID(runid: str, allow_nonexistent: bool = False, ignore_lock: bool = False) -> 'RedisPrep':
        from wepppy.weppcloud.utils.helpers import get_wd
        return RedisPrep.getInstance(
            get_wd(runid), allow_nonexistent=allow_nonexistent, ignore_lock=ignore_lock)

    @property
    def dump_filepath(self) -> str:
        return _join(self.wd, 'redisprep.dump')

    @contextmanager
    def _guard(self):
        # Callers can already hold NoDb/config/Roads locks. Never wait in the
        # reverse lifecycle order: contention is explicit and retryable.
        publications_before = self._publication_count
        body_completed = False
        try:
            with redisprep_snapshot_guard(self.wd):
                if not os.path.exists(self.wd):
                    yield False
                else:
                    if self._read_namespace() != self.run_id:
                        raise RedisPrepSnapshotError('RedisPrep namespace changed during lifecycle replacement; reload')
                    current = resolve_scope(self.wd)
                    if (self._scope is not None
                            and current.directory_identity == self._scope.directory_identity
                            and self._scope.incarnation is None and current.initialization_only):
                        # Initial catalog creation did not replace project contents.
                        # Adopt once; every subsequent incarnation change is fenced.
                        self._scope = current
                    if (self._scope is None or current.directory_identity != self._scope.directory_identity
                            or current.incarnation != self._scope.incarnation):
                        raise RedisPrepSnapshotError('RedisPrep wrapper belongs to a replaced project; reload it')
                    yield True
                body_completed = True
        except OSError as exc:
            if body_completed:
                raise RedisPrepSnapshotError(
                    'RedisPrep operation completed; coordination release failed; inspect committed state',
                    published=self._publication_count > publications_before,
                ) from exc
            raise

    def dump(self) -> None:
        with self._guard() as present:
            if present:
                self._load_locked()
                self._dump_locked()

    def _dump_locked(self) -> None:
        # HGETALL is the capture point. The lifecycle guard stays held through
        # replace, so an earlier capture cannot publish after a later one.
        captured = self.redis.hgetall(self.run_id)
        if str(captured.get('attrs:loaded', '')).lower() != 'true':
            raise RedisPrepSnapshotError('RedisPrep live readiness lost before capture; reload before publication')
        publish_snapshot(self._directory_fd, captured)
        self._publication_count += 1

    def lazy_load(self) -> None:
        # Healthy live reads never require permission to create coordination files.
        if self._get_bool_config('loaded') and os.path.lexists(self.dump_filepath):
            return
        with self._guard() as present:
            if not present:
                # Preserve missing-run initialization without creating a directory.
                if self._scope is None:
                    self.redis.hset(self.run_id, 'attrs:loaded', 'true')
                return
            self._load_locked()

    def _load_locked(self) -> None:
        if self._get_bool_config('loaded') and os.path.lexists(self.dump_filepath):
            return
        try:
            with self.redis.pipeline() as pipe:
                pipe.watch(self.run_id)
                live = pipe.hgetall(self.run_id)
                if str(live.get('attrs:loaded', '')).lower() == 'true':
                    if not os.path.lexists(self.dump_filepath):
                        self._dump_locked()
                    return
                try:
                    payload = read_snapshot(self._directory_fd)
                except FileNotFoundError:
                    payload = None
                if payload is not None:
                    owned = {k for k in live if k != 'attrs:loaded'
                             and k != 'last_modified' and not k.startswith('locked:')}
                    if owned:
                        raise RedisPrepSnapshotError(
                            'RedisPrep recovery has ambiguous partial/live metadata; reconcile before loading')
                    payload.pop('attrs:loaded', None)
                    # Independently recreated NoDb mirrors are live authority.
                    payload.update(live)
                else:
                    payload = live
                payload['attrs:loaded'] = 'true'
                pipe.multi()
                pipe.hset(self.run_id, mapping=payload)
                self._execute_transaction(pipe)
            # A loaded snapshot is already durable. Only first creation needs
            # publication; empty JSON is valid and need not be rewritten.
            if not os.path.exists(self.dump_filepath):
                self._persist_committed_live()
        except WatchError as exc:
            raise RedisPrepSnapshotError('RedisPrep recovery conflicted with a live writer; reload') from exc

    @staticmethod
    def _execute_transaction(pipe) -> None:
        try:
            pipe.execute()
        except WatchError:
            raise
        except RedisError as exc:
            raise RedisPrepSnapshotError(
                'RedisPrep Redis transaction outcome uncertain; inspect live state before retry',
                live_committed=None,
            ) from exc

    def _persist_committed_live(self) -> None:
        try:
            self._dump_locked()
        except (OSError, ValueError, RedisError, RedisPrepSnapshotError) as exc:
            raise RedisPrepSnapshotError(
                'RedisPrep live mutation committed; snapshot publication failed or uncertain',
                published=getattr(exc, 'published', False), live_committed=True,
            ) from exc

    def update_metadata(self, values=None, *, remove=(), persist=True) -> None:
        """Atomically apply a bounded field update, then publish its snapshot.

        A snapshot error does not roll back a committed Redis mutation.
        """
        values = validate_snapshot(dict(values or {}))
        if any(str(key).startswith('locked:') for key in remove):
            raise ValueError('RedisPrep cannot remove live NoDb lock ownership')
        with self._guard() as present:
            if not present:
                if self._scope is not None:
                    raise RedisPrepSnapshotError('RedisPrep project was deleted; refusing stale live mutation')
                return
            self._load_locked()
            with self.redis.pipeline() as pipe:
                if remove:
                    pipe.hdel(self.run_id, *remove)
                if values:
                    pipe.hset(self.run_id, mapping=values)
                self._execute_transaction(pipe)
            if persist:
                self._persist_committed_live()

    def restore_snapshot(self, payload=None) -> None:
        """Install incoming fork/archive metadata under the lifecycle guard.

        This is an explicit replacement, not ordinary lazy recovery. Preserve
        independently owned live NoDb fields, and remove obsolete receipts.
        """
        with self._guard() as present:
            if not present:
                return
            incoming = read_snapshot(self._directory_fd) if payload is None else validate_snapshot(payload)
            incoming.pop('attrs:loaded', None)
            incoming['attrs:loaded'] = 'true'
            try:
                with self.redis.pipeline() as pipe:
                    pipe.watch(self.run_id)
                    live = pipe.hgetall(self.run_id)
                    unrelated = {k: v for k, v in live.items()
                                 if not k.startswith(('attrs:', 'timestamps:', 'rq:', 'postfire_debris_flow:'))
                                 and k != 'archive:job_id'}
                    incoming.update(unrelated)
                    obsolete = [k for k in live if k not in incoming]
                    pipe.multi()
                    if obsolete:
                        pipe.hdel(self.run_id, *obsolete)
                    pipe.hset(self.run_id, mapping=incoming)
                    self._execute_transaction(pipe)
            except WatchError as exc:
                raise RedisPrepSnapshotError('RedisPrep replacement conflicted with a live writer') from exc
            self._persist_committed_live()

    @property
    def sbs_required(self) -> bool:
        return self._get_bool_config('sbs_required')

    @sbs_required.setter
    def sbs_required(self, value: bool) -> None:
        self._set_bool_config('sbs_required', value)

    @property
    def has_sbs(self) -> bool:
        return self._get_bool_config('has_sbs')

    @has_sbs.setter
    def has_sbs(self, value: bool) -> None:
        self._set_bool_config('has_sbs', value)

    def _get_bool_config(self, key: str) -> bool:
        value = self.redis.hget(self.run_id, f'attrs:{key}')
        return value.lower() == 'true' if value is not None else False

    def _set_bool_config(self, key: str, value: bool) -> None:
        self.update_metadata({f'attrs:{key}': str(bool(value)).lower()})

    def timestamp(self, key: TaskEnum) -> None:
        now = int(time.time())
        self.__setitem__(str(key), now)

    def timestamps_report(self) -> str:
        s = [f'RedisPrep Timestamps ({self.run_id}):']
        for key in TaskEnum:
            timestamp = self.redis.hget(self.run_id, f'timestamps:{key}')
            s.append(f'  {key}: {timestamp}')
        return '\n'.join(s)

    def remove_timestamp(self, key: TaskEnum) -> None:
        self.update_metadata(remove=(f'timestamps:{key}',))

    def remove_all_timestamp(self) -> None:
        self.update_metadata(remove=tuple(f'timestamps:{task}' for task in TaskEnum))

    def __setitem__(self, key: str, value: int) -> None:
        self.update_metadata({f'timestamps:{key}': value})

    def __getitem__(self, key: str) -> Optional[int]:
        v = self.redis.hget(self.run_id, f'timestamps:{key}')
        if v is None:
            return None
        return int(v)
    
    def set_rq_job_id(self, key: str, job_id: str) -> None:
        self.update_metadata({f'rq:{key}': job_id})

    def get_rq_job_id(self, key: str) -> Optional[str]:
        v = self.redis.hget(self.run_id, f'rq:{key}')
        if v is None:
            return None
        return v

    def get_rq_job_ids(self) -> Dict[str, str]:
        return {key[3:]: value for key, value in self.redis.hgetall(self.run_id).items()
                if key.startswith('rq:')}

    def set_archive_job_id(self, job_id: str) -> None:
        self.update_metadata({'archive:job_id': job_id})

    def get_archive_job_id(self) -> Optional[str]:
        return self.redis.hget(self.run_id, 'archive:job_id')

    def clear_archive_job_id(self) -> None:
        self.update_metadata(remove=('archive:job_id',))
