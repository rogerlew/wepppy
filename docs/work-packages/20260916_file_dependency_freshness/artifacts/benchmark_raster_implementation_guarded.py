"""Final guarded C03/C04 acceptance, transparent instrumentation and old-method controls.

No composed observer is inserted. Actual new consumers call their production
helper. Original C03 methods from ceb715c08 are used only in labeled same-owner
controls. Every owner/native operation uses retained uniquely named QA copies.
"""
import ast
from collections import defaultdict
from contextlib import contextmanager, ExitStack
import hashlib
import json
import os
from pathlib import Path
from statistics import mean
import subprocess
import sys
from time import perf_counter, sleep
import traceback
from unittest.mock import patch
from uuid import uuid4

from osgeo import gdal
import pyarrow.parquet as pq
from wepppy.all_your_base import file_digest, raster_freshness
from wepppy.nodb.core import Landuse
from wepppy.nodb.core import landuse as landuse_module
from wepppy.nodb.mods.baer import sbs_map

ARTIFACTS = Path(__file__).parent
OUTPUT = ARTIFACTS / 'raster_implementation_performance_guarded.json'
baseline = json.loads((ARTIFACTS / 'raster_consumer_performance_baseline.json').read_text())
ROOT = Path('/wc1/batch') / ('qa-raster-implementation-' + uuid4().hex[:12])
ROOT.mkdir()
BASE_REF = 'ceb715c08'
result = {'scope': __doc__, 'root': str(ROOT), 'original_fixture_manifest': str(Path(baseline['root']) / 'benchmark-manifest.json'),
          'uid': os.getuid(), 'gid': os.getgid(), 'gdal_version': gdal.VersionInfo(),
          'cache_note': 'Retained filesystem-warm NFS copies; helper cold is not cold storage',
          'baseline_revision': BASE_REF, 'module_hashes': {}, 'inputs': {}, 'cases': {},
          'pressure': [], 'gates': []}
tracked, reads = set(), defaultdict(int)
native, observations, validations, locks = [], [], [], []
real_open = Path.open
real_pair = landuse_module.count_intersecting_raster_key_pairs
real_summary = sbs_map._summarize_sbs_raster_rust
real_joint = raster_freshness.observe_raster_dependencies
real_signature = Landuse._build_mofe_pair_count_signature
real_locked = Landuse.locked
mode = 'actual'


def named(value):
    return isinstance(value, (str, bytes, os.PathLike)) and str(Path(os.fsdecode(value)).absolute()).startswith('/wc1/runs/')


def audit(event, args):
    if event == 'open' and named(args[0]):
        access_mode, flags = args[1], args[2]
        if (access_mode and any(char in access_mode for char in 'wax+')) or flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC):
            raise PermissionError('No named-run writes in this benchmark')
    if event in {'os.mkdir', 'os.remove', 'os.rmdir', 'os.chmod', 'os.chown', 'os.utime', 'os.rename', 'os.link', 'os.symlink'}:
        if any(named(value) for value in args[:2]):
            raise PermissionError('No named-run mutation in this benchmark')


sys.addaudithook(audit)


def version(path):
    info = Path(path).stat()
    return tuple(getattr(info, key) for key in ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns'))


def retain_input(path):
    path = Path(path).absolute()
    assert path.is_relative_to('/wc1/batch')
    tracked.add(path)
    result['inputs'][str(path)] = {'version': version(path), 'mode': oct(path.stat().st_mode & 0o777),
        'sha256': file_digest.sha256_file(path, use_cache=False)}


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
    stream = real_open(path, *args, **kwargs)
    access_mode = args[0] if args else kwargs.get('mode', 'r')
    if access_mode == 'rb' and path.absolute() in tracked:
        return CountedStream(stream, str(path.absolute()))
    return stream


def counted_pair(*args, **kwargs):
    started = perf_counter()
    value = real_pair(*args, **kwargs)
    native.append({'operation': 'pair_count', 'seconds': perf_counter() - started})
    return value


def counted_summary(*args, **kwargs):
    started = perf_counter()
    value = real_summary(*args, **kwargs)
    native.append({'operation': 'sbs_summary', 'seconds': perf_counter() - started})
    return value


def observed(paths):
    started = perf_counter()
    value = real_joint(paths)
    observations.append({'seconds': perf_counter() - started, 'verified': value is not None})
    return value


def signature(owner, **kwargs):
    started = perf_counter()
    value = real_signature(owner, **kwargs)
    validations.append({'seconds': perf_counter() - started, 'verified': value is not None})
    return value


@contextmanager
def locked(owner, *args, **kwargs):
    started = perf_counter()
    with real_locked(owner, *args, **kwargs):
        entered = perf_counter()
        try:
            yield
        finally:
            body_done = perf_counter()
    finished = perf_counter()
    locks.append({'seconds': finished - started, 'body_seconds': body_done - entered,
                  'acquire_seconds': entered - started, 'persist_unlock_seconds': finished - body_done})


def flush():
    text = json.dumps(result, indent=2) + '\n'
    OUTPUT.write_text(text)
    (ROOT / 'benchmark-manifest.json').write_text(text)


def gate(name, actual, limit, unit='seconds'):
    passed = actual <= limit
    result['gates'].append({'name': name, 'actual': actual, 'limit': limit, 'unit': unit, 'passed': passed})
    return passed


def measured(case, phase, callback, repeats=1, expected_native=None):
    before_reads = dict(reads)
    offsets = [len(items) for items in (native, observations, validations, locks)]
    times = []
    for _ in range(repeats):
        started = perf_counter()
        value = callback()
        times.append(perf_counter() - started)
    item = {'phase': phase, 'mode': mode, 'repeats': repeats, 'seconds': times, 'mean_seconds': mean(times),
            'digest_read_bytes': {p: n - before_reads.get(p, 0) for p, n in reads.items() if n != before_reads.get(p, 0)}}
    for name, items, offset in zip(('native', 'observations', 'validations', 'locks'),
                                  (native, observations, validations, locks), offsets):
        item[name] = items[offset:]
    case['measurements'].append(item)
    if expected_native is not None:
        assert len(item['native']) == expected_native, (case['name'], phase, len(item['native']), expected_native)
    assert all(entry['verified'] for entry in item['observations']), (case['name'], phase, 'unverified representative')
    print(f'{case["name"]} {phase} [{mode}]: {item["mean_seconds"] * 1000:.3f} ms; hash bytes={sum(item["digest_read_bytes"].values())}', flush=True)
    flush()
    # A parent can pause future runs after a completed consumer, outside its lock.
    while (ROOT / 'pause_requested').exists():
        sleep(.2)
    return value, item


def clear_digest():
    file_digest._digest.cache_clear()
    file_digest._observed_at.cache_clear()


def settle(callback):
    callback()
    sleep(1.05)
    callback()


pressure_dir = ROOT / 'pressure'
pressure_dir.mkdir()
pressure_files = []
for number in range(512):
    path = pressure_dir / f'{number:04d}.bin'
    path.write_bytes(f'QA pressure {number}\n'.encode())
    pressure_files.append(path)


def evict():
    before = {'digest': file_digest._digest.cache_info()._asdict(), 'observed': file_digest._observed_at.cache_info()._asdict()}
    for path in pressure_files:
        file_digest.sha256_file(path)
    sleep(1.05)
    for path in pressure_files:
        file_digest.sha256_file(path)
    after = {'digest': file_digest._digest.cache_info()._asdict(), 'observed': file_digest._observed_at.cache_info()._asdict()}
    assert after['digest']['currsize'] == after['observed']['currsize'] == 512
    result['pressure'].append({'files': 512, 'before': before, 'after': after})
    flush()


# Retain exact old source; compile only the original methods into their original
# names with the present module's unchanged imports. No second NoDb class exists.
old_raw = subprocess.check_output(['git', 'show', BASE_REF + ':wepppy/nodb/core/landuse.py'])
(ROOT / 'landuse_ancestor.py').write_bytes(old_raw)
result['baseline_source_sha256'] = hashlib.sha256(old_raw).hexdigest()
tree = ast.parse(old_raw)
landuse_class = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'Landuse')
method_names = {'build_managements', '_build_mofe_pair_count_signature', '_mofe_pair_count_file_signature'}
methods = [node for node in landuse_class.body if isinstance(node, ast.FunctionDef) and node.name in method_names]
assert len(methods) == len(method_names)
old_namespace = dict(landuse_module.__dict__)
old_namespace['count_intersecting_raster_key_pairs'] = counted_pair
exec(compile(ast.Module(body=methods, type_ignores=[]), str(ROOT / 'landuse_ancestor.py'), 'exec'), old_namespace)


@contextmanager
def original_methods():
    global mode
    prior = mode
    mode = 'ancestor_control'
    try:
        with ExitStack() as stack:
            for name in method_names:
                stack.enter_context(patch.object(Landuse, name, old_namespace[name], create=True))
            yield
    finally:
        mode = prior


def summarized(case):
    groups = defaultdict(list)
    for item in case['measurements']:
        groups[(item['phase'], item['mode'])].append(item)
    summary = {}
    for (phase, variant), items in groups.items():
        count = sum(item['repeats'] for item in items)
        summary[f'{phase}/{variant}'] = {
            'count': count, 'mean_seconds': sum(sum(item['seconds']) for item in items) / count,
            'mean_validation_seconds': sum(sum(entry['seconds'] for entry in item['validations']) for item in items) / count,
            'mean_lock_seconds': sum(sum(entry['seconds'] for entry in item['locks']) for item in items) / count,
            'digest_read_bytes': sum(sum(item['digest_read_bytes'].values()) for item in items),
            'native_calls': sum(len(item['native']) for item in items),
            'mean_native_seconds': sum(sum(entry['seconds'] for entry in item['native']) for item in items) / count,
            'observation_count': sum(len(item['observations']) for item in items),
        }
    case['summary'] = summary
    return summary


try:
    for module in (file_digest, raster_freshness, landuse_module, sbs_map):
        source = Path(module.__file__)
        raw = source.read_bytes()
        result['module_hashes'][str(source)] = hashlib.sha256(raw).hexdigest()
        (ROOT / ('actual_' + source.name)).write_bytes(raw)
    for old_case in baseline['cases'].values():
        inventories = old_case.get('inventories') or [old_case['inventory']]
        for inventory in inventories:
            for path in inventory['members']:
                retain_input(path)
    with patch.object(Path, 'open', counted_open), \
            patch.object(landuse_module, 'count_intersecting_raster_key_pairs', counted_pair), \
            patch.object(sbs_map, '_summarize_sbs_raster_rust', counted_summary), \
            patch.object(raster_freshness, 'observe_raster_dependencies', observed), \
            patch.object(landuse_module, 'observe_raster_dependencies', observed), \
            patch.object(sbs_map, 'observe_raster_dependencies', observed), \
            patch.object(Landuse, '_build_mofe_pair_count_signature', signature), \
            patch.object(Landuse, 'locked', locked):
        for name in ('GrizzlyCreek_SBS_final.tif', 'baer.cropped.tif'):
            source = baseline['cases'][name]['source']
            case = result['cases'][name] = {'name': name, 'source': source, 'measurements': []}
            direct = counted_summary(source)
            callback = lambda: sbs_map._summarize_sbs_raster(source)
            clear_digest()
            sbs_map._summarize_sbs_raster_cached.cache_clear()
            value, _ = measured(case, 'initial_admission', callback, expected_native=1)
            assert value == direct
            settle(callback)
            _, warm = measured(case, 'settled_hit', callback, 30, expected_native=0)
            gate(name + ': settled complete hit', warm['mean_seconds'], .025)
            gate(name + ': settled hash bytes', sum(warm['digest_read_bytes'].values()), 0, 'bytes')
            for iteration in range(3):
                measured(case, 'native_direct', lambda: counted_summary(source), expected_native=1)
                sbs_map._summarize_sbs_raster_cached.cache_clear()
                value, _ = measured(case, 'settled_miss', callback, expected_native=1)
                assert value == direct
                clear_digest()
                measured(case, 'cold_hit', callback, expected_native=0)
                clear_digest()
                sbs_map._summarize_sbs_raster_cached.cache_clear()
                measured(case, 'cold_miss', callback, expected_native=1)
                evict()
                _, pressure = measured(case, 'evicted_hit', callback, expected_native=0)
                assert sum(pressure['digest_read_bytes'].values()) > 0
                settle(callback)
            summary = summarized(case)
            native_mean = summary['native_direct/actual']['mean_seconds']
            for phase in ('settled_miss', 'cold_miss'):
                gate(name + ': ' + phase + ' added', summary[phase + '/actual']['mean_seconds'] - native_mean, .05)
                gate(name + ': ' + phase + ' measured nonnative overhead',
                     summary[phase + '/actual']['mean_seconds'] - summary[phase + '/actual']['mean_native_seconds'], .05)
            case['summary_matches_native'] = callback() == direct
            case['numerical_cache_parameters'] = sbs_map._summarize_sbs_raster_cached.cache_parameters()
            assert case['summary_matches_native'] and case['numerical_cache_parameters']['maxsize'] == 8
            flush()

        for name in ('curable-program', 'beneficiary-forfeit'):
            root = Path(baseline['cases'][name]['root'])
            assert root.is_relative_to('/wc1/batch') and '-qa-' in root.name
            owner = Landuse.getInstance(str(root))
            assert owner.runid != name and owner.multi_ofe
            output = root / 'landuse/landuse.parquet'
            expected_table = pq.read_table(output)
            expected_managements = {key: value.as_dict() for key, value in owner.managements.items()}
            case = result['cases'][name] = {'name': name, 'root': str(root), 'measurements': [],
                'before_modes': {str(path): oct(path.stat().st_mode & 0o777) for path in (root / 'landuse.nodb', output)}}
            # Establish a real legacy signature using the retained old consumer.
            with original_methods():
                owner.build_managements()
            clear_digest()
            measured(case, 'legacy_admission', owner.build_managements, expected_native=1)
            expected_counts = owner._mofe_pair_count_cache
            settle(owner.build_managements)
            for phase, force_miss, cold, pressure in (
                ('settled_hit', False, False, False), ('settled_miss', True, False, False),
                ('cold_hit', False, True, False), ('cold_miss', True, True, False),
                ('evicted_hit', False, False, True),
            ):
                for iteration in range(3):
                    for use_old in ([True, False] if iteration % 2 == 0 else [False, True]):
                        with ExitStack() as stack:
                            if use_old:
                                stack.enter_context(original_methods())
                            if not force_miss:
                                owner.build_managements()  # Prime this method version, outside measurement.
                            else:
                                owner._invalidate_mofe_pair_count_cache(reason='QA forced native miss')
                            if not use_old and cold:
                                clear_digest()
                            if not use_old and pressure:
                                evict()
                            _, item = measured(case, phase, owner.build_managements, expected_native=int(force_miss))
                            if not use_old:
                                assert len(item['validations']) == 2
                                assert owner._mofe_pair_count_cache == expected_counts
                                if cold or pressure:
                                    assert sum(item['digest_read_bytes'].values()) > 0
                            if not use_old and (cold or pressure):
                                settle(owner.build_managements)
                summary = summarized(case)
                actual, old = summary[phase + '/actual'], summary[phase + '/ancestor_control']
                validation_limit, added_limit = (.4, .45) if cold or pressure else (.075, .1)
                gate(name + ': ' + phase + ' validation', actual['mean_validation_seconds'], validation_limit)
                gate(name + ': ' + phase + ' whole added', actual['mean_seconds'] - old['mean_seconds'], added_limit)
                gate(name + ': ' + phase + ' lock added', actual['mean_lock_seconds'] - old['mean_lock_seconds'], added_limit)
                if not cold and not pressure:
                    gate(name + ': ' + phase + ' hash bytes', actual['digest_read_bytes'], 0, 'bytes')
                flush()
            owner.build_managements()  # Leave the disposable owner with actual current signature.
            case['management_values_preserved'] = expected_managements == {key: value.as_dict() for key, value in owner.managements.items()}
            case['parquet_rows_types_values_preserved'] = expected_table.equals(pq.read_table(output), check_metadata=False)
            case['after_modes'] = {str(path): oct(path.stat().st_mode & 0o777) for path in (root / 'landuse.nodb', output)}
            assert case['management_values_preserved'] and case['parquet_rows_types_values_preserved']
            assert case['before_modes'] == case['after_modes']
            flush()
except BaseException as exc:
    # Probe boundary: retain failure and all prior successful measurements.
    result['failure'] = {'type': type(exc).__name__, 'message': str(exc), 'traceback': traceback.format_exc()}
    raise
finally:
    result['inputs_unchanged'] = all(tuple(entry['version']) == version(Path(path)) and entry['sha256'] == file_digest.sha256_file(path, use_cache=False) for path, entry in result['inputs'].items())
    result['module_files_unchanged'] = all(hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest for path, digest in result['module_hashes'].items())
    result['acceptance_passed'] = bool(result['gates']) and all(gate['passed'] for gate in result['gates']) and result['inputs_unchanged'] and result['module_files_unchanged'] and 'failure' not in result
    flush()
print(json.dumps(result, indent=2))
