#!/usr/bin/env python3
"""Trusted operator controller for the finite, disabled-mode catalog pilot.

No queue/root/environment overrides or source overlays are accepted. Evidence is
private operator data; this program never enables ordinary asynchronous refresh.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import threading
import time
from typing import Any

ROOT = Path('/wc1/runs/qc')
SOURCE = Path('/wc1/query-catalog-validation/20261026/rollout-cycle-2355/runs/representative')
MARKER = '.query-catalog-pilot-owner.json'
OBSERVE_SECONDS = 10
TICK_SECONDS = 30
SOURCE_FILES = 79
SOURCE_BYTES = 73328103


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def write_json(path: Path, value: Any, *, exclusive: bool = False) -> None:
    # Evidence is operator-private, including exact job trees and controller state.
    flags = os.O_WRONLY | os.O_CREAT | (os.O_EXCL if exclusive else os.O_TRUNC) | os.O_NOFOLLOW
    fd = os.open(path, flags, 0o600)
    with os.fdopen(fd, 'w') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


def canonical(path: Path) -> Path:
    if not path.is_absolute() or path.resolve() != path:
        raise ValueError('Pilot paths must be absolute and contain no symlink redirection')
    return path


def fixture_paths(pilot_id: str) -> list[Path]:
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{7,63}', pilot_id):
        raise ValueError('Invalid pilot identifier')
    canonical(ROOT)
    return [ROOT / f'qcat-pilot-{pilot_id}-{suffix}' for suffix in [*(f'{i:02d}' for i in range(8)), 'sentinel']]


def tree_digest(path: Path) -> dict[str, str]:
    canonical(path)
    result = {}
    for directory, dirs, files in os.walk(path, followlinks=False):
        for name in dirs + files:
            if (Path(directory) / name).is_symlink():
                raise ValueError('Symlink in owned fixture')
        for name in files:
            target = Path(directory) / name
            result[target.relative_to(path).as_posix()] = digest(target)
    return result


def source_manifest() -> list[dict[str, Any]]:
    canonical(SOURCE)
    all_files = tree_digest(SOURCE)
    files = [dict(path=name, sha256=value, bytes=(SOURCE / name).stat().st_size,
                  modified_ns=(SOURCE / name).stat().st_mtime_ns)
             for name, value in sorted(all_files.items()) if name.endswith('.parquet')]
    if len(files) != SOURCE_FILES or sum(row['bytes'] for row in files) != SOURCE_BYTES:
        raise ValueError('Owned source fixture size/count differs from retained evidence')
    return files


def assert_owned(path: Path, pilot_id: str) -> None:
    canonical(path)
    if path not in fixture_paths(pilot_id):
        raise ValueError('Path is not an exact pilot fixture')
    marker = path / MARKER
    if marker.is_symlink() or json.loads(marker.read_text()) != {'pilot_id': pilot_id}:
        raise ValueError('Missing or mismatched fixture ownership')


def prepare(pilot_id: str, evidence: Path, cr: Any) -> dict[str, Any]:
    paths = fixture_paths(pilot_id)
    files = source_manifest()
    ROOT.mkdir(exist_ok=True)  # Canonical qc shard may not exist before the first pilot.
    if not canonical(ROOT).is_dir():
        raise NotADirectoryError(ROOT)
    if any(path.exists() or path.is_symlink() for path in paths):
        raise FileExistsError('Pilot fixtures must be exclusively new; no overwrite or automatic repair')
    for path in paths:
        path.mkdir()  # Existing canonical parent must already be available.
        write_json(path / MARKER, {'pilot_id': pilot_id}, exclusive=True)
        write_json(path / 'wepp.nodb', {}, exclusive=True)
        for row in files:
            target = path / row['path']
            target.parent.mkdir(parents=True, exist_ok=True)
            with (SOURCE / row['path']).open('rb') as source, target.open('xb') as dest:
                shutil.copyfileobj(source, dest)
            if digest(target) != row['sha256']:
                raise ValueError('Fixture copy checksum mismatch')
        scope = cr.resolve_scope(path, create=True)
        if not scope.managed or not scope.incarnation:
            raise ValueError('Fixture did not resolve to an initialized canonical scope')
    receipt = cr.record_catalog_refresh(paths[-1])
    setup = dict(pilot_id=pilot_id, paths=[str(path) for path in paths[:-1]],
                 sentinel=str(paths[-1]), files=files, sentinel_receipt=receipt,
                 sentinel_before=tree_digest(paths[-1]), created_at=time.time())
    write_json(evidence / 'setup.json', setup, exclusive=True)
    return setup


def load_setup(evidence: Path, pilot_id: str) -> dict[str, Any]:
    setup = json.loads((evidence / 'setup.json').read_text())
    expected = fixture_paths(pilot_id)
    if (setup['pilot_id'] != pilot_id or setup['paths'] != [str(p) for p in expected[:-1]]
            or setup['sentinel'] != str(expected[-1])):
        raise ValueError('Evidence fixture locators do not match the exact pilot')
    for path in expected:
        assert_owned(path, pilot_id)
    if setup['files'] != source_manifest():
        raise ValueError('Source manifest changed')
    return setup


def raw_ready(setup: dict[str, Any], cr: Any) -> bool:
    return all((Path(path) / '_query_engine/catalog.json').is_file()
               and not cr.pending_catalog_requests(path) for path in setup['paths'])


def verify_bindings(setup: dict[str, Any], cr: Any, bindings: list[dict[str, Any]]) -> None:
    """Compare artifact identity with admission authority, never just itself."""
    if len(bindings) != len(setup['paths']) or {item['path'] for item in bindings} != set(setup['paths']):
        raise ValueError('Artifact scope set differs from admitted manifest')
    for binding in bindings:
        path = Path(binding['path'])
        assert_owned(path, setup['pilot_id'])
        scope = cr.resolve_scope(path, create=False)
        if (scope.scope_id != binding['scope_id'] or scope.incarnation != binding['incarnation']
                or scope.namespace != binding['namespace']
                or {'inode': path.stat().st_ino} != binding['directory_identity']):
            raise ValueError('Artifact identity differs from admitted manifest')


def verify_artifacts(setup: dict[str, Any], cr: Any, *, consumers: bool = True,
                     bindings: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Raw publication gates precede every potentially repairing consumer call."""
    import duckdb
    import pyarrow.parquet as pq

    if bindings is not None:
        verify_bindings(setup, cr, bindings)
    if not raw_ready(setup, cr):
        raise ValueError('Raw publication incomplete; consumer repair is not acceptance')
    expected = {row['path']: row for row in setup['files']}
    results = []
    for name in setup['paths']:
        path = Path(name)
        assert_owned(path, setup['pilot_id'])
        catalog = json.loads((path / '_query_engine/catalog.json').read_text())
        indexed = {row['path']: row for row in catalog['files']}
        if len(indexed) != len(catalog['files']) or not expected.keys() <= indexed.keys():
            raise ValueError('Missing or duplicated catalog dataset')
        if not indexed.keys() <= expected.keys() | {'wepp.nodb', MARKER, '_query_engine/catalog.json'}:
            raise ValueError('Unexpected catalog dataset')
        publication = json.loads((path / cr.REFRESH_PATH / 'status.json').read_text())
        scope = cr.resolve_scope(path, create=False)
        if (publication.get('state') != 'current' or publication.get('incarnation') != scope.incarnation
                or publication.get('catalog_digest') != digest(path / '_query_engine/catalog.json')):
            raise ValueError('Raw publication identity/digest is not current')
        cr._verify_required(path, catalog, list(expected))
        for row in catalog['files']:
            physical = Path(row.get('fs_path') or row['path'])
            physical = physical if physical.is_absolute() else path / physical
            if not physical.resolve().is_relative_to(path):
                raise ValueError('Unexpected external catalog reference')
        for relative, row in expected.items():
            target = path / relative
            if target.is_symlink() or digest(target) != row['sha256']:
                raise ValueError('Copied scientific source changed')
            if not pq.read_schema(target).equals(pq.read_schema(SOURCE / relative), check_metadata=True):
                raise ValueError('Copied schema differs from source')
        results.append(dict(path=name, catalog_entries=len(indexed), catalog_sha256=digest(path / '_query_engine/catalog.json')))
    if tree_digest(Path(setup['sentinel'])) != setup['sentinel_before']:
        raise ValueError('Excluded sentinel changed')
    if source_manifest() != setup['files']:
        raise ValueError('Owned source changed')
    if bindings is not None:
        verify_bindings(setup, cr, bindings)
    probes = ['watershed/channels.parquet', 'wepp/output/interchange/H.pass.parquet',
              next(name for name in expected if name.startswith('climate/'))]
    queries = []
    with duckdb.connect() as conn:
        for relative in probes:
            reference = conn.execute('SELECT count(*) FROM read_parquet(?)', [str(SOURCE / relative)]).fetchone()[0]
            for name in setup['paths']:
                actual = conn.execute('SELECT count(*) FROM read_parquet(?)', [str(Path(name) / relative)]).fetchone()[0]
                if actual != reference:
                    raise ValueError('DuckDB row-count mismatch')
                if consumers:
                    from wepppy.query_engine.catalog import DatasetCatalog
                    from wepppy.query_engine.context import RunContext
                    from wepppy.query_engine.core import run_query
                    from wepppy.query_engine.payload import QueryRequest
                    context = RunContext(name, Path(name), None, DatasetCatalog.load(Path(name) / '_query_engine/catalog.json'))
                    result = run_query(context, QueryRequest(datasets=[relative], columns=[],
                                       aggregations=[{'fn': 'count', 'column': '*', 'alias': 'n'}], include_schema=True))
                    if result.records != [{'n': reference}] or not result.schema:
                        raise ValueError('Query-engine consumer result mismatch')
                queries.append(dict(path=name, dataset=relative, rows=actual, source_rows=reference))
    if bindings is not None:
        verify_bindings(setup, cr, bindings)
    for row in results:
        if digest(Path(row['path']) / '_query_engine/catalog.json') != row['catalog_sha256']:
            raise ValueError('Consumer changed publication; repair cannot be credited')
    return dict(status='passed', scopes=results, queries=queries, sentinel_unchanged=True, source_unchanged=True)


def ordinary_waits(jobs: dict[str, Any], waiting: list[str], now: float) -> dict[str, Any]:
    waits = {}
    unavailable = []
    for job_id, fields in jobs.items():
        try:
            def timestamp(value):
                parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
                return (parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)).timestamp()
            enqueued = timestamp(fields['enqueued_at'])
            if fields.get('started_at'):
                waits[job_id] = max(0.0, timestamp(fields['started_at']) - enqueued)
            elif job_id in waiting:
                waits[job_id] = max(0.0, now - enqueued)
        except (AttributeError, TypeError, ValueError, KeyError):
            unavailable.append(job_id)
    return dict(wait_seconds=waits, max_observed_wait_seconds=max(waits.values(), default=0),
                unavailable_timestamps=unavailable)


class Runtime:
    def __init__(self) -> None:
        import redis
        from rq import Queue
        from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
        from wepppy.query_engine import catalog_refresh
        from wepppy.rq import query_catalog_rq, _query_catalog_pilot
        self.connection = redis.Redis(**redis_connection_kwargs(RedisDB.RQ))
        self.queue = Queue('batch', connection=self.connection)
        self.cr = catalog_refresh
        self.cq = query_catalog_rq
        self.pilot = _query_catalog_pilot
        self.ordinary_seen: set[str] = set()
        if self.cr.catalog_refresh_enabled():
            raise ValueError('This pilot requires general asynchronous refresh disabled')

    def preflight(self, *, require_all: bool = True) -> dict[str, Any]:
        import socket
        status = self.cq.consumer_status(self.queue)
        if require_all and (status['compatible'] != 8 or status['incompatible'] or status['suspended']):
            raise RuntimeError('Pilot requires the eight existing compatible unsuspended consumers')
        return dict(host=socket.gethostname(), uid=os.getuid(), gid=os.getgid(), groups=os.getgroups(),
                    consumers=status, configuration=self.cq.catalog_worker_configuration(),
                    source_sha256={name: digest(Path(module.__file__)) for name, module in
                                   [('catalog_refresh', self.cr), ('query_catalog_rq', self.cq), ('pilot', self.pilot)]},
                    operator_tool_sha256=digest(Path(__file__)))

    def raw_ordinary(self, status: dict[str, Any]) -> dict[str, Any]:
        from rq.registry import StartedJobRegistry
        decode = lambda value: value.decode() if isinstance(value, bytes) else str(value)
        waiting = [decode(value) for value in self.connection.lrange(self.queue.key, 0, -1)]
        started = [decode(value) for value in self.connection.zrange(StartedJobRegistry('batch', connection=self.connection).key, 0, -1)]
        admitted = status['global_job_ids']
        self.ordinary_seen.update(jid for jid in waiting + started if jid not in admitted)
        jobs = self.raw_jobs({'jobs': {jid: {} for jid in sorted(self.ordinary_seen)}})
        waits = ordinary_waits(jobs, waiting, time.time())
        return dict(waiting_ids=waiting, started_ids=started, jobs=jobs, **waits)

    def status(self, pilot_id: str) -> dict[str, Any]:
        return self.pilot.pilot_status(self.connection, pilot_id)

    def observe(self, pilot_id: str, token: str) -> dict[str, Any]:
        return self.pilot.observe_pilot(self.connection, pilot_id, token)

    def pause(self, pilot_id: str, reason: str) -> None:
        self.pilot.pause_pilot(self.connection, pilot_id, reason)

    def phase(self, pilot_id: str, token: str, phase: str, value: Any) -> None:
        self.pilot.record_phase(self.connection, pilot_id, token, phase, value)

    def public_jobs(self, status: dict[str, Any]) -> dict[str, Any]:
        from wepppy.rq.job_info import get_wepppy_rq_job_info
        return {job_id: get_wepppy_rq_job_info(job_id) for job_id in status['jobs']}

    def raw_jobs(self, status: dict[str, Any]) -> dict[str, Any]:
        # HGET fields only: no deserialization of task payloads or registry cleanup.
        fields = ['status', 'origin', 'created_at', 'enqueued_at', 'started_at', 'ended_at', 'worker_name', 'dependency_ids']
        return {job_id: dict(zip(fields, [value.decode() if isinstance(value, bytes) else value
                    for value in self.connection.hmget('rq:job:' + job_id, fields)])) for job_id in status['jobs']}


class Observer:
    """One process-local observer, renewing only after the helper's raw observation."""
    def __init__(self, runtime: Runtime, pilot_id: str, token: str, evidence: Path):
        self.runtime, self.pilot_id, self.token, self.evidence = runtime, pilot_id, token, evidence
        self.stop = threading.Event()
        self.error: BaseException | None = None
        self.thread = threading.Thread(target=self._loop, name='catalog-pilot-observer', daemon=True)

    def once(self) -> dict[str, Any]:
        try:
            return self._sample()
        except Exception as exc:
            # Observation boundary: pause immediately in this thread, even while
            # the main controller is blocked in scientific artifact readback.
            try:
                self.runtime.pause(self.pilot_id, 'controller_observation_failure')
            except Exception as pause_error:
                raise ExceptionGroup('Observation and admission pause both failed', [exc, pause_error]) from None
            raise

    def _sample(self) -> dict[str, Any]:
        status = self.runtime.observe(self.pilot_id, self.token)
        if status['global_uncertain'] or status['global_outstanding'] is None or status['global_outstanding'] > 7:
            self.runtime.pause(self.pilot_id, 'accounting_failure')
        if status['counters']['refresh'] > 25 or status['counters']['inventory'] > 2:
            self.runtime.pause(self.pilot_id, 'accounting_failure')
        participants = self.runtime.preflight(require_all=False)
        live = participants['consumers']
        if live['compatible'] != 8 or live['incompatible'] or live['suspended']:
            self.runtime.pause(self.pilot_id, 'configuration_mismatch')
        ordinary = self.runtime.raw_ordinary(status)
        if ordinary.get('unavailable_timestamps'):
            self.runtime.pause(self.pilot_id, 'controller_observation_failure')
        if ordinary.get('max_observed_wait_seconds', 0) >= 300:
            self.runtime.pause(self.pilot_id, 'ordinary_wait_limit')
        row = dict(at=time.time(), status=status, jobs=self.runtime.raw_jobs(status),
                   ordinary=ordinary, participants=participants)
        with (self.evidence / 'observations.jsonl').open('a') as stream:
            stream.write(json.dumps(row, sort_keys=True) + '\n')
            stream.flush()
        return status

    def _loop(self) -> None:
        try:
            next_sample = time.monotonic() + OBSERVE_SECONDS
            while not self.stop.wait(max(0, next_sample - time.monotonic())):
                self.once()
                next_sample = max(next_sample + OBSERVE_SECONDS, time.monotonic())
        except Exception as exc:
            # Deliberate thread boundary: propagate observer failure to controller;
            # no separate heartbeat can keep admissions alive after this failure.
            self.error = exc
            self.stop.set()

    def check(self) -> None:
        if self.error is not None:
            raise RuntimeError('Pilot observation failed; acceptance cannot pass') from self.error

    def close(self) -> None:
        self.stop.set()
        if self.thread.ident is None:
            return
        self.thread.join(timeout=OBSERVE_SECONDS + 1)
        if self.thread.is_alive():
            raise RuntimeError('Observer did not drain; retained evidence is incomplete')


def assert_job_lineage(status: dict[str, Any], setup: dict[str, Any], *, waves: int) -> None:
    scopes = {item['scope_id'] for item in status['manifest']['scopes']}
    counts = {scope: 0 for scope in scopes}
    kinds = {'refresh': 0, 'inventory': 0}
    for job_id, binding in status['jobs'].items():
        if not job_id.startswith('query_catalog_refresh_') or binding['status'] != 'finished':
            raise ValueError('Pilot job did not finish with canonical identity')
        kind = binding['kind']
        if kind not in kinds:
            raise ValueError('Unexpected pilot job kind')
        kinds[kind] += 1
        if kind == 'refresh':
            scope_id = binding['scope']['scope_id']
            if scope_id not in counts or binding['scope']['wd'] not in setup['paths']:
                raise ValueError('Pilot job escaped frozen scope set')
            counts[scope_id] += 1
    if (kinds != status['counters'] or kinds['refresh'] > 25 or not 1 <= kinds['inventory'] <= 2
            or any(count < waves for count in counts.values()) or len(scopes) != 8):
        raise ValueError('Pilot job/budget lineage does not prove the required waves')


def negative_controls(runtime: Runtime, setup: dict[str, Any], pilot_id: str, token: str) -> None:
    before = runtime.status(pilot_id)
    result = runtime.cq.enqueue_catalog_refresh(setup['sentinel'], queue=runtime.queue)
    if result.get('error_code') != 'query_catalog_refresh_disabled' or result.get('job_id'):
        raise ValueError('General disabled admission changed')
    for identifier, expected in [(pilot_id, 'Scope is not approved'),
                                 ('unknown-' + hashlib.sha256(pilot_id.encode()).hexdigest()[:16], 'authority is absent')]:
        try:
            runtime.cq.enqueue_catalog_refresh(setup['sentinel'], queue=runtime.queue,
                                              pilot_id=identifier, controller_token=token)
        except ValueError as exc:
            if expected not in str(exc):
                raise
        else:
            raise ValueError('Unapproved scope/pilot was not rejected')
    after = runtime.status(pilot_id)
    if before['jobs'] != after['jobs'] or before['counters'] != after['counters']:
        raise ValueError('Negative control changed admission ledger')
    if tree_digest(Path(setup['sentinel'])) != setup['sentinel_before']:
        raise ValueError('Denied admission changed sentinel')


def receipt_wave(runtime: Runtime, setup: dict[str, Any], pilot_id: str, token: str) -> None:
    phases = runtime.status(pilot_id)['phases']
    if 'receipt_wave_complete' in phases:
        return
    if 'receipt_wave_started' in phases:
        raise RuntimeError('Incomplete receipt wave requires explicit operator reconciliation')
    runtime.phase(pilot_id, token, 'receipt_wave_started', True)
    receipts = []
    for name in setup['paths']:
        if runtime.status(pilot_id)['state'] != 'active':
            return  # Safe stop retains partial-wave evidence and created receipts.
        runtime.pilot.authorize_receipt(runtime.connection, pilot_id, name, token)
        with runtime.cr.catalog_lifecycle_guard(name):
            runtime.pilot.authorize_receipt(runtime.connection, pilot_id, name, token)
            receipts.append(runtime.cr.record_catalog_refresh(name, 'watershed/channels.parquet'))
        # Canonical enqueue only; disabled general behavior is never bypassed.
        runtime.cq.enqueue_catalog_refresh(name, queue=runtime.queue, pilot_id=pilot_id, controller_token=token)
    runtime.phase(pilot_id, token, 'receipt_wave_complete', receipts)


def retry_receipt_wave(runtime: Runtime, setup: dict[str, Any], pilot_id: str, token: str) -> None:
    """A completed inventory frontier is not discovery of later explicit receipts."""
    if 'receipt_wave_complete' not in runtime.status(pilot_id)['phases']:
        return
    for name in setup['paths']:
        if runtime.status(pilot_id)['state'] != 'active':
            return
        runtime.pilot.authorize_receipt(runtime.connection, pilot_id, name, token)
        if runtime.cr.pending_catalog_requests(name):
            runtime.cq.enqueue_catalog_refresh(name, queue=runtime.queue,
                                              pilot_id=pilot_id, controller_token=token)


def run_controller(runtime: Runtime, pilot_id: str, evidence: Path, *, resume: bool = False,
                   monitor_seconds: float = 5400, drain_only: bool = False) -> dict[str, Any]:
    setup = {} if drain_only else load_setup(evidence, pilot_id)
    write_json(evidence / 'preflight.json', runtime.preflight(require_all=not drain_only))
    before = runtime.status(pilot_id)
    if not drain_only and 'acceptance_failure' in before['phases']:
        raise RuntimeError('Retained acceptance failure cannot become a passed pilot')
    if not drain_only and before['phases'].get('receipt_wave_started') and 'receipt_wave_complete' not in before['phases']:
        raise RuntimeError('Interrupted receipt wave requires operator reconciliation before resume')
    if not drain_only and not resume and before['phases']:
        raise ValueError('Existing pilot progress requires explicit resume')
    token = runtime.pilot.acquire_controller(runtime.connection, pilot_id)
    observer = Observer(runtime, pilot_id, token, evidence)
    began = time.monotonic()
    next_tick = 0.0
    outcome = 'incomplete'
    try:
        observer.once()
        if drain_only:
            runtime.pause(pilot_id, 'operator_drain')
        else:
            runtime.pilot.resume_pilot(runtime.connection, pilot_id, token)
        observer.thread.start()
        if not drain_only and 'negative_controls' not in before['phases']:
            negative_controls(runtime, setup, pilot_id, token)
            runtime.phase(pilot_id, token, 'negative_controls', True)
        while time.monotonic() - began < monitor_seconds:
            observer.check()
            status = runtime.status(pilot_id)
            active = not drain_only and status['state'] == 'active' and not status['failures']
            if active and time.monotonic() >= next_tick:
                tick_start = time.monotonic()
                runtime.cq.reconcile_query_catalogs(queue=runtime.queue, pilot_id=pilot_id, controller_token=token)
                retry_receipt_wave(runtime, setup, pilot_id, token)
                next_tick = tick_start + TICK_SECONDS
            status = runtime.status(pilot_id)
            if not status['outstanding']:
                if status['failures'] or status['state'] != 'active':
                    outcome = 'safely_stopped' if not status['failures'] else 'failed'
                    break
                if raw_ready(setup, runtime.cr):
                    phases = status['phases']
                    assert_job_lineage(status, setup, waves=2 if 'receipt_wave_complete' in phases else 1)
                    verification = verify_artifacts(setup, runtime.cr, bindings=status['manifest']['scopes'])
                    observer.check()
                    phases = runtime.status(pilot_id)['phases']
                    if 'inventory_verified' not in phases:
                        write_json(evidence / 'inventory-readback.json', verification)
                        runtime.phase(pilot_id, token, 'inventory_verified', True)
                        receipt_wave(runtime, setup, pilot_id, token)
                    elif 'receipt_wave_complete' in phases:
                        write_json(evidence / 'receipt-readback.json', verification)
                        for receipt in phases['receipt_wave_complete']:
                            scope = next(item for item in status['manifest']['scopes'] if item['scope_id'] == receipt['scope_id'])
                            published = json.loads((Path(scope['path']) / runtime.cr.REFRESH_PATH / 'status.json').read_text())
                            if receipt['request_id'] not in published.get('acknowledged', []):
                                raise ValueError('Owned receipt lacks publication acknowledgment')
                        runtime.phase(pilot_id, token, 'artifact_verified', True)
                        runtime.pause(pilot_id, 'acceptance_readback_complete')
                        observer.once()
                        outcome = 'completed'
                        break
            time.sleep(1)
        if outcome == 'incomplete':
            runtime.pause(pilot_id, 'controller_monitor_bound')
        final = runtime.status(pilot_id)
        result = dict(outcome=outcome, status=final, jobs=runtime.raw_jobs(final), elapsed_seconds=time.monotonic()-began)
        failed = bool(final['failures'] or 'acceptance_failure' in final['phases'])
        if final['outstanding'] or failed or final['global_uncertain']:
            result['outcome'] = 'failed' if failed else 'incomplete_drain'
        result['public_job_trees'] = runtime.public_jobs(final)
        write_json(evidence / 'result.json', result)
        return result
    except BaseException as exc:
        # Operator/exception boundary: stop new work, preserve receipts and exact
        # prior evidence. Failure to pause is visible; the observer lease expires.
        reason = ('operator_interruption' if isinstance(exc, (KeyboardInterrupt, SystemExit))
                  else 'controller_observation_failure' if observer.error else 'artifact_failure')
        runtime.pause(pilot_id, reason)
        if not isinstance(exc, (KeyboardInterrupt, SystemExit)):
            runtime.phase(pilot_id, token, 'acceptance_failure', {'error_type': type(exc).__name__})
        raise
    finally:
        observer.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['prepare', 'register', 'status', 'run', 'resume', 'pause', 'drain', 'verify'])
    parser.add_argument('--pilot-id', required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    args = parser.parse_args(argv)
    fixture_paths(args.pilot_id)
    evidence = canonical(args.evidence)
    evidence.mkdir(mode=0o700, parents=True, exist_ok=True)
    if (evidence.stat().st_mode & 0o077) or evidence.stat().st_uid != os.getuid():
        raise PermissionError('Evidence directory must be private and owned by this operator')
    if (os.getuid(), os.getgid()) != (1002, 130):
        raise PermissionError('Pilot operator requires production UID1002/GID130')
    runtime = Runtime()
    if args.command == 'prepare':
        result = prepare(args.pilot_id, evidence, runtime.cr)
    elif args.command == 'register':
        setup = load_setup(evidence, args.pilot_id)
        write_json(evidence / 'preflight-register.json', runtime.preflight())
        result = runtime.pilot.register_pilot(runtime.connection, args.pilot_id, setup['paths'])
        write_json(evidence / 'registration.json', result, exclusive=True)
    elif args.command == 'status':
        result = runtime.status(args.pilot_id)
    elif args.command == 'pause':
        runtime.pause(args.pilot_id, 'operator_pause')
        result = runtime.status(args.pilot_id)
    elif args.command == 'verify':
        result = verify_artifacts(load_setup(evidence, args.pilot_id), runtime.cr,
                                  bindings=runtime.status(args.pilot_id)['manifest']['scopes'])
        write_json(evidence / 'manual-readback.json', result)
    else:
        result = run_controller(runtime, args.pilot_id, evidence, resume=args.command == 'resume',
                                drain_only=args.command == 'drain')
    print(json.dumps(result, sort_keys=True))
    return 0 if result.get('outcome', 'completed') == 'completed' else 2


if __name__ == '__main__':
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    raise SystemExit(main())
