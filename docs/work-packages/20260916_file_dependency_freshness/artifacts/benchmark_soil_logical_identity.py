"""PF-R01 read-only source survey and actual safe snapshot cost discovery.

Run with wctl exec weppcloud python <this path> [output-stem]. Named SQLite
sources are never connected to, checkpointed, or written. Retained copies live
under the new /wc1/batch/qa-soil-logical-perf-* directory recorded in JSON.
"""
from collections import defaultdict
import hashlib
import json
import os
from pathlib import Path
from statistics import mean
import sqlite3
import sys
from time import perf_counter, sleep
from unittest.mock import patch
from urllib.parse import unquote, urlsplit
from uuid import uuid4

from wepppy.all_your_base import file_digest
from wepppy.nodb.mods.postfire_debris_flow import production_soils, soil_snapshot

ARTIFACTS = Path(__file__).parent
OUTPUT = ARTIFACTS / ((sys.argv[1] if len(sys.argv) > 1 else 'soil_logical_performance') + '.json')
DISPOSABLE = Path('/wc1/batch') / ('qa-soil-logical-perf-' + uuid4().hex[:12])
DISPOSABLE.mkdir()
connected_paths = []
blocked_events = []
content_reads = defaultdict(int)
copy_reads = defaultdict(int)
physical_checks = defaultdict(int)
profile = defaultdict(float)
profile_calls = defaultdict(int)
original_open = Path.open
original_local = soil_snapshot.open_local
original_copy = soil_snapshot._copy_source
original_tables = soil_snapshot._read_tables
original_logical = soil_snapshot._logical


def named_path(value):
    return isinstance(value, (str, bytes, os.PathLike)) and str(Path(os.fsdecode(value)).absolute()).startswith('/wc1/runs/')


def audit(event, args):
    if event == 'sqlite3.connect':
        value = str(args[0])
        candidate = Path(unquote(urlsplit(value).path) if value.startswith('file:') else value).absolute()
        if not candidate.is_relative_to(DISPOSABLE):
            blocked_events.append({'event': event, 'path': value})
            raise PermissionError('Benchmark permits SQLite connections only to retained disposable copies')
        connected_paths.append(str(candidate))
    if event == 'open' and named_path(args[0]):
        mode, flags = args[1], args[2]
        if (mode and any(char in mode for char in 'wax+')) or flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC):
            blocked_events.append({'event': event, 'path': str(args[0])})
            raise PermissionError('Benchmark forbids named-run writes')
    if event in {'os.mkdir', 'os.remove', 'os.rmdir', 'os.chmod', 'os.chown', 'os.utime', 'os.rename', 'os.link', 'os.symlink'}:
        if any(named_path(arg) for arg in args[:2]):
            blocked_events.append({'event': event, 'arguments': repr(args[:2])})
            raise PermissionError('Benchmark forbids named-run mutations')


sys.addaudithook(audit)


def state_optional(path):
    try:
        info = path.lstat()
    except FileNotFoundError:
        return None
    return {field: getattr(info, field) for field in ('st_dev', 'st_ino', 'st_mode', 'st_size', 'st_mtime_ns', 'st_ctime_ns')}


survey = []
for path in Path('/wc1/runs').glob('*/*/soils/ssurgo_tabular_cache.sqlite'):
    members = {suffix or 'main': state_optional(Path(str(path) + suffix)) for suffix in ('', '-wal', '-shm', '-journal')}
    survey.append({'path': str(path), 'members': members,
                   'total_bytes': sum(value['st_size'] for value in members.values() if value),
                   'prepared_metadata_present': (path.parent.parent / 'postfire_debris_flow/inputs/soil_sources.json').exists()})
wal = max((item for item in survey if item['members']['-wal'] is not None), key=lambda item: item['total_bytes'])
standalone = max((item for item in survey if item['members']['-wal'] is None), key=lambda item: item['total_bytes'])
prepared = max((item for item in survey if item['prepared_metadata_present']), key=lambda item: item['total_bytes'])
selections = {'largest_wal': wal, 'largest_main_without_wal': standalone, 'largest_prepared': prepared}
source_paths = {Path(str(Path(item['path'])) + suffix) for item in selections.values() for suffix in ('', '-wal', '-shm') if Path(str(Path(item['path'])) + suffix).exists()}


class CountedStream:
    def __init__(self, stream, key, counter):
        self.stream, self.key, self.counter = stream, key, counter

    def __enter__(self):
        self.stream.__enter__()
        return self

    def __exit__(self, *args):
        return self.stream.__exit__(*args)

    def __getattr__(self, key):
        return getattr(self.stream, key)

    def read(self, *args, **kwargs):
        block = self.stream.read(*args, **kwargs)
        self.counter[self.key] += len(block)
        return block


def counted_open(path, *args, **kwargs):
    stream = original_open(path, *args, **kwargs)
    mode = args[0] if args else kwargs.get('mode', 'r')
    if mode == 'rb' and path.absolute() in source_paths:
        return CountedStream(stream, str(path.absolute()), content_reads)
    return stream


def counted_local(path, *args, **kwargs):
    stream = original_local(path, *args, **kwargs)
    return CountedStream(stream, str(Path(path).absolute()), copy_reads)


def profiled(kind, callback, *args, **kwargs):
    started = perf_counter()
    try:
        return callback(*args, **kwargs)
    finally:
        profile[kind] += perf_counter() - started
        profile_calls[kind] += 1


def profiled_logical(value):
    return profiled('logical_table' if isinstance(value, list) else 'logical_row_sort_key', original_logical, value)


def digest(path, **kwargs):
    physical_checks[str(path)] += 1
    return file_digest.sha256_file(path, **kwargs)


def io():
    return {line.split(':')[0]: int(line.split(':')[1]) for line in Path('/proc/self/io').read_text().splitlines()}


def delta(current, before):
    return {key: value - before.get(key, 0) for key, value in current.items() if value != before.get(key, 0)}


result = {'disposable_root': str(DISPOSABLE), 'uid': os.getuid(), 'gid': os.getgid(), 'survey': survey,
          'selection_rule': 'largest observed main+WAL+SHM, largest without WAL, largest with prepared metadata; no SQLite connection in selection',
          'selections': selections, 'cases': {}, 'source_module_sha256': {str(Path(module.__file__)): hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest() for module in (soil_snapshot, production_soils)},
          'physical_storage_note': 'No OS cache drop. Before/after raw byte verification primes page cache; helper-cold is not cold-storage evidence.'}


def flush():
    OUTPUT.write_text(json.dumps(result, indent=2) + '\n')
    (DISPOSABLE / 'benchmark-manifest.json').write_text(json.dumps(result, indent=2) + '\n')


def measured(case, name, callback, repeats=1):
    before_reads, before_copies = dict(content_reads), dict(copy_reads)
    before_checks, before_io = dict(physical_checks), io()
    times, value, error = [], None, None
    for _ in range(repeats):
        started = perf_counter()
        try:
            value = callback()
        except (ValueError, OSError, sqlite3.Error) as exc:
            error = {'type': type(exc).__name__, 'message': str(exc)}
        times.append(perf_counter() - started)
        if error:
            break
    after_io = io()
    record = {'name': name, 'requested_repeats': repeats, 'completed_attempts': len(times), 'seconds': times,
              'mean_seconds': mean(times), 'error': error, 'physical_digest_bytes': delta(content_reads, before_reads),
              'source_copy_bytes': delta(copy_reads, before_copies), 'physical_digest_checks': delta(physical_checks, before_checks),
              'process_rchar_delta': after_io['rchar'] - before_io['rchar'],
              'process_physical_read_bytes_delta': after_io['read_bytes'] - before_io['read_bytes']}
    case['measurements'].append(record)
    flush()
    print(f'{case["label"]} {name}: {mean(times)*1000:.3f} ms {error or ""}', flush=True)
    return value


try:
    with patch.object(Path, 'open', counted_open), patch.object(soil_snapshot, 'open_local', counted_local):
        for label, selected in selections.items():
            source = Path(selected['path'])
            paths = [Path(str(source) + suffix) for suffix in ('', '-wal', '-shm') if Path(str(source) + suffix).exists()]
            case_root = DISPOSABLE / label
            case_root.mkdir()
            case = {'label': label, 'source': str(source), 'output_root': str(case_root), 'measurements': []}
            result['cases'][label] = case
            before = {suffix or 'main': state_optional(Path(str(source) + suffix)) for suffix in ('', '-wal', '-shm', '-journal')}
            before_hashes = {str(path): digest(path, use_cache=False) for path in paths}
            case['before_state'], case['before_physical_sha256'] = before, before_hashes
            measured(case, 'source_state', lambda: soil_snapshot.source_state(source), 100)
            inventory = measured(case, 'actual_production_soils_inventory', lambda: production_soils.inventory(source.parent.parent), 30)
            case['actual_inventory'] = inventory
            file_digest._digest.cache_clear()
            file_digest._observed_at.cache_clear()
            measured(case, 'physical_set_first_observation', lambda: [digest(path) for path in paths])
            measured(case, 'physical_set_during_admission', lambda: [digest(path) for path in paths], 2)
            sleep(1.05)
            measured(case, 'physical_set_admitting', lambda: [digest(path) for path in paths])
            measured(case, 'physical_set_settled', lambda: [digest(path) for path in paths], 100)
            first = measured(case, 'actual_snapshot_first', lambda: soil_snapshot.snapshot_cache(source, case_root / 'first'))
            if first is not None:
                case['logical_identity'] = {key: first[key] for key in ('source_schema', 'logical_sha256')}
                case['row_counts'] = {key: len(first[key]) for key in ('components', 'horizons')}
                case['consumed_typed_json_bytes'] = {key: len(json.dumps(soil_snapshot._hashable(first[key]), sort_keys=True, separators=(',', ':'), allow_nan=False).encode()) for key in ('components', 'horizons')}
                identities = []

                def repeat_snapshot():
                    value = soil_snapshot.snapshot_cache(source, case_root / ('warm-' + uuid4().hex[:8]))
                    identities.append({key: value[key] for key in ('source_schema', 'logical_sha256')})
                    return value

                measured(case, 'actual_snapshot_warm', repeat_snapshot, 5)
                case['repeated_logical_identity_equal'] = all(value == case['logical_identity'] for value in identities)
                profile.clear()
                profile_calls.clear()
                with patch.object(soil_snapshot, '_copy_source', lambda *a, **k: profiled('source_copy', original_copy, *a, **k)), \
                        patch.object(soil_snapshot, '_read_tables', lambda *a, **k: profiled('table_parse', original_tables, *a, **k)), \
                        patch.object(soil_snapshot, '_logical', profiled_logical):
                    measured(case, 'actual_snapshot_profiled', lambda: soil_snapshot.snapshot_cache(source, case_root / 'profiled'))
                case['profile_seconds'], case['profile_call_counts'] = dict(profile), dict(profile_calls)
            after = {suffix or 'main': state_optional(Path(str(source) + suffix)) for suffix in ('', '-wal', '-shm', '-journal')}
            after_hashes = {str(path): digest(path, use_cache=False) for path in paths}
            case['after_state'], case['after_physical_sha256'] = after, after_hashes
            case['source_state_unchanged'] = before == after
            case['source_main_wal_shm_bytes_unchanged'] = before_hashes == after_hashes
            case['retained_files'] = {str(path.relative_to(case_root)): path.stat().st_size for path in case_root.rglob('*') if path.is_file()}
            flush()
finally:
    result['sqlite_connections'] = connected_paths
    result['blocked_events'] = blocked_events
    result['all_sqlite_connections_to_disposable_copies'] = all(Path(path).is_relative_to(DISPOSABLE) for path in connected_paths)
    flush()
print(json.dumps(result, indent=2))
