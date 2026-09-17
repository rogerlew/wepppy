"""Actual PF-R02 producers and lineage acceptance on retained disposable copies.

No named-run writes; no producer, owner-loader, proof-reader or digest fallback.
Readiness measurements cover only selected CLI/Parquet source observation and
the native lineage predicate, not whole-project postfire.sources.
"""
from collections import defaultdict
import hashlib
import json
import os
from pathlib import Path
import shutil
from statistics import mean
import sys
from time import perf_counter, sleep
from unittest.mock import patch
from uuid import uuid4

import pyarrow.parquet as pq

from wepppy.all_your_base import file_digest
from wepppy.climates import cli_parquet
from wepppy.nodb.core import Climate
from wepppy.nodb.core import climate_artifact_export_service as service
from wepppy.nodb.mods.postfire_debris_flow import production, rainfall_io
from wepppy.wepp.interchange import _utils

ARTIFACTS = Path(__file__).parent
suffix = '_' + sys.argv[1] if len(sys.argv) > 1 else ''
OUTPUT = ARTIFACTS / ('cli_lineage_implementation_performance' + suffix + '.json')
baseline = json.loads((ARTIFACTS / 'cli_lineage_performance.json').read_text())
ROOT = Path('/wc1/batch') / ('qa-cli-lineage-implementation-' + uuid4().hex[:12])
ROOT.mkdir()
reads, checks = defaultdict(int), defaultdict(int)
owner_calls = []
tracked = set()
original_open = Path.open
original_local = rainfall_io.open_local
original_digest = production.cached_digest
original_export_digest = cli_parquet.sha256_file
original_active = service._active_cli_path


def named(value):
    return isinstance(value, (str, bytes, os.PathLike)) and str(Path(os.fsdecode(value)).absolute()).startswith('/wc1/runs/')


def audit(event, args):
    if event == 'open' and named(args[0]):
        mode, flags = args[1], args[2]
        if (mode and any(char in mode for char in 'wax+')) or flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC):
            raise PermissionError('No named-run writes in this benchmark')
    if event in {'os.mkdir', 'os.remove', 'os.rmdir', 'os.chmod', 'os.chown', 'os.utime', 'os.rename', 'os.link', 'os.symlink'}:
        if any(named(value) for value in args[:2]):
            raise PermissionError('No named-run mutations in this benchmark')


sys.addaudithook(audit)


def version(path):
    info = path.stat()
    return tuple(getattr(info, key) for key in ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns'))


class CountedStream:
    def __init__(self, stream, path):
        self.stream, self.path = stream, path

    def __enter__(self):
        self.stream.__enter__()
        return self

    def __exit__(self, *args):
        return self.stream.__exit__(*args)

    def __getattr__(self, key):
        return getattr(self.stream, key)

    def read(self, *args, **kwargs):
        value = self.stream.read(*args, **kwargs)
        reads[self.path] += len(value)
        return value


def counted_open(path, *args, **kwargs):
    stream = original_open(path, *args, **kwargs)
    mode = args[0] if args else kwargs.get('mode', 'r')
    if mode == 'rb' and path.absolute() in tracked:
        return CountedStream(stream, str(path.absolute()))
    return stream


def counted_local(path, *args, **kwargs):
    stream = original_local(path, *args, **kwargs)
    return CountedStream(stream, str(Path(path).absolute())) if Path(path).absolute() in tracked else stream


def counted_digest(path, **kwargs):
    checks['readiness:' + str(path)] += 1
    return original_digest(path, **kwargs)


def counted_export_digest(path, **kwargs):
    checks['export:' + str(path)] += 1
    return original_export_digest(path, **kwargs)


def counted_active(owner):
    started = perf_counter()
    value = original_active(owner)
    owner_calls.append({'seconds': perf_counter() - started, 'selected': str(value)})
    return value


def delta(current, before):
    return {key: value - before.get(key, 0) for key, value in current.items() if value != before.get(key, 0)}


modules = (cli_parquet, service, _utils, production, rainfall_io)
result = {'root': str(ROOT), 'uid': os.getuid(), 'gid': os.getgid(), 'cases': {},
          'scope': 'Actual producer with real copied Climate owner and actual selected-CLI/Parquet lineage validation',
          'limits': 'Warm OS cache; no cache drop; source slice excludes other owners/global/raster checks and accepted-result validation',
          'module_hashes_start': {str(Path(m.__file__)): hashlib.sha256(Path(m.__file__).read_bytes()).hexdigest() for m in modules}}


def flush():
    OUTPUT.write_text(json.dumps(result, indent=2) + '\n')
    (ROOT / 'benchmark-manifest.json').write_text(json.dumps(result, indent=2) + '\n')


def measured(case, label, callback, repeats=1):
    before_reads, before_checks = dict(reads), dict(checks)
    before_owner = len(owner_calls)
    times = []
    for _ in range(repeats):
        started = perf_counter()
        value = callback()
        times.append(perf_counter() - started)
    record = {'name': label, 'repeats': repeats, 'seconds': times, 'mean_seconds': mean(times),
              'tracked_read_bytes': delta(reads, before_reads), 'digest_checks': delta(checks, before_checks),
              'owner_reloads': owner_calls[before_owner:]}
    case['measurements'].append(record)
    flush()
    print(f'{case["name"]} {label}: {mean(times)*1000:.3f} ms', flush=True)
    return value


def caches():
    return {'digest': production._digest_version.cache_info()._asdict(),
            'observation': production._digest_observed_at.cache_info()._asdict()}


def clear_caches():
    production._digest_version.cache_clear()
    production._digest_observed_at.cache_clear()


try:
    with patch.object(Path, 'open', counted_open), patch.object(rainfall_io, 'open_local', counted_local), \
            patch.object(production, 'cached_digest', counted_digest), \
            patch.object(cli_parquet, 'sha256_file', counted_export_digest), \
            patch.object(service, '_active_cli_path', counted_active):
        for name, previous in baseline['cases'].items():
            # NoDb uses the directory basename for its logging/status identity;
            # keep it distinct from the named source project as well as its path.
            root = ROOT / (name + '-qa-' + uuid4().hex[:8])
            (root / 'climate').mkdir(parents=True)
            named_root = Path(previous['named_source']).parents[1]
            inputs = [named_root / 'climate.nodb', named_root / 'nodb.version']
            named_before = {str(path): {'version': version(path), 'sha256': file_digest.sha256_file(path, use_cache=False)} for path in inputs}
            for path in inputs:
                shutil.copy2(path, root / path.name)
            source = root / 'climate/wepp.cli'
            shutil.copy2(previous['copy_source'], source)
            source.chmod(0o600)
            tracked.add(source)
            owner = Climate.getInstance(str(root))
            assert Path(owner.cli_dir) / owner.cli_fn == source
            assert owner.runid != name
            output = root / 'climate/wepp_cli.parquet'
            tracked.add(output)
            case = {'name': name, 'source_bytes': source.stat().st_size,
                    'source': str(source), 'output': str(output), 'owner': str(root / 'climate.nodb'),
                    'owner_runid': owner.runid,
                    'measurements': []}
            result['cases'][name] = case

            def export():
                value = owner._export_cli_parquet()
                if value != output:
                    raise RuntimeError('Actual exporter failed; retained output and log identify the cause')
                return value

            # Force the first publication's real getInstance to hydrate an owner;
            # subsequent calls exercise normal singleton checks and logging.
            with Climate._instances_lock:
                Climate._instances.pop(str(root), None)
            measured(case, 'actual_export_with_owner_rehydration', export)
            output.chmod(0o640)
            measured(case, 'actual_export_settled_owner', export, 3)
            assert output.stat().st_mode & 0o777 == 0o640
            baseline_output = sorted(Path(previous['copy_source']).parent.glob('service-*/climate/wepp_cli.parquet'))[0]
            actual_table = pq.read_table(output)
            case['rows_and_types_equal_original'] = actual_table.equals(pq.read_table(baseline_output), check_metadata=False)
            assert case['rows_and_types_equal_original']
            case['rows'] = actual_table.num_rows
            case['output_bytes'] = output.stat().st_size
            case['output_mode'] = oct(output.stat().st_mode & 0o777)
            with output.open('rb') as stream:
                case['proof'] = cli_parquet._read_proof(stream, rainfall_io.MAX_TEXT)[0]

            def interchange():
                directory = root / ('interchange-' + uuid4().hex[:8]) / 'climate'
                directory.mkdir(parents=True)
                shutil.copy2(source, directory / source.name)
                value = _utils._ensure_cli_parquet(directory, cli_file_hint=source.name)
                if value is None:
                    raise RuntimeError('Actual interchange generation failed')
                return value

            interchange_output = measured(case, 'actual_interchange_including_disposable_input_copy', interchange, 3)
            case['interchange_equal_rows_types'] = actual_table.equals(pq.read_table(interchange_output), check_metadata=False)
            assert case['interchange_equal_rows_types']

            files = {'cli': output, 'active_cli': source}
            observed_records = {key: production.signature(root, path) for key, path in files.items()}

            def readiness(content):
                if content is None:
                    # The new predicate receives already-observed records in
                    # production. Include all its actual strict path/open guards
                    # and active CLI digest, excluding the old inventory loop.
                    assert production._cli_lineage_current(root, files, observed_records, {})
                    return True
                records, hashes = {}, {}
                for key, path in files.items():
                    records[key] = production.signature(root, path)
                    if content:
                        hashes[key] = production.cached_digest(path, local=True)
                    assert production.signature(root, path) == records[key]
                assert production._cli_lineage_current(root, files, records, hashes)
                return True

            for content in (None, False, True):
                label = 'lineage_only' if content is None else 'content_true' if content else 'content_false'
                clear_caches()
                measured(case, label + '_helper_cold', lambda: readiness(content))
                measured(case, label + '_during_admission', lambda: readiness(content), 2)
                sleep(1.05)
                measured(case, label + '_admitting', lambda: readiness(content))
                before_reads = dict(reads)
                measured(case, label + '_settled', lambda: readiness(content), 100)
                assert reads[str(source)] == before_reads.get(str(source), 0)
                assert reads[str(output)] - before_reads.get(str(output), 0) == 100 * (65536 + 12)
                pressure_root = root / ('pressure-' + label)
                pressure_root.mkdir()
                pressure = []
                for index in range(512):
                    path = pressure_root / str(index)
                    path.write_bytes(f'actual lineage eviction {index}\n'.encode())
                    pressure.append(path)
                case[label + '_eviction_cache_states'] = []
                for index in range(3):
                    for path in pressure:
                        production.cached_digest(path, local=True)
                    sleep(1.05)
                    for path in pressure:
                        production.cached_digest(path, local=True)
                    before = caches()
                    assert before['digest']['currsize'] == before['observation']['currsize'] == 512
                    measured(case, label + f'_evicted_{index}', lambda: readiness(content))
                    case[label + '_eviction_cache_states'].append({'before': before, 'after': caches()})

            case['named_owner_inputs_unchanged'] = all(info['version'] == version(Path(path)) and info['sha256'] == file_digest.sha256_file(path, use_cache=False) for path, info in named_before.items())
            assert case['named_owner_inputs_unchanged']
            attempts = list((root / 'climate_artifacts/cli_parquet/attempts').iterdir())
            case['attempts'] = [{'path': str(path), 'mode': oct(path.stat().st_mode & 0o777),
                                 'status': json.loads((path / 'status.json').read_text()),
                                 'snapshot_bytes': (path / 'source.cli').stat().st_size,
                                 'snapshot_mode': oct((path / 'source.cli').stat().st_mode & 0o777),
                                 'status_mode': oct((path / 'status.json').stat().st_mode & 0o777)} for path in attempts]
            assert all(item['mode'] == '0o700' and item['status']['status'] == 'complete' for item in case['attempts'])
            assert all(item['snapshot_mode'] == item['status_mode'] == '0o600' for item in case['attempts'])
            flush()
finally:
    result['module_hashes_end'] = {str(Path(m.__file__)): hashlib.sha256(Path(m.__file__).read_bytes()).hexdigest() for m in modules}
    flush()
print(json.dumps(result, indent=2))
