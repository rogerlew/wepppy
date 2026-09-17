"""Paired whole-consumer controls; this simple-file observer is only a cost probe.

Retained fixtures are local GTiff/AAIGrid without unproven companions. The probe
does not implement the contract's pre-open eligibility/security checks, so its
cost is a baseline, never implementation acceptance. All owner writes are to
uniquely named disposable clones from benchmark_raster_consumers.py.
"""
from contextlib import contextmanager
import json
from pathlib import Path
from statistics import mean
from time import perf_counter, sleep
from unittest.mock import patch

from osgeo import gdal
import pyarrow.parquet as pq
from wepppy.all_your_base import file_digest
from wepppy.nodb.core import Landuse
from wepppy.nodb.core import landuse as module

ARTIFACTS = Path(__file__).parent
OUTPUT = ARTIFACTS / 'raster_management_interleaved_baseline.json'
baseline = json.loads((ARTIFACTS / 'raster_consumer_performance_baseline.json').read_text())
root = Path(baseline['root'])
assert root.is_relative_to('/wc1/batch') and root.name.startswith('qa-raster-')
result = {'scope': __doc__, 'cache_note': 'Warm NFS/filesystem; helper cold does not mean cold storage', 'cases': {}}
real_locked = Landuse.locked
real_pair = module.count_intersecting_raster_key_pairs
observation_enabled = False
locks, native = [], []
gdal.UseExceptions()


def version(path):
    info = Path(path).stat()
    return tuple(getattr(info, key) for key in ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns'))


def inventory(path):
    dataset = gdal.OpenEx(str(path), gdal.OF_RASTER | gdal.OF_READONLY)
    driver = dataset.GetDriver().ShortName
    assert driver in {'GTiff', 'AAIGrid'}
    members = tuple(sorted(dataset.GetFileList() or []))
    assert members and all(Path(p).is_file() and Path(p).is_relative_to(root) for p in members)
    value = {'selected': str(path), 'resolved': str(Path(path).resolve()), 'driver': driver,
             'members': members, 'shape': [dataset.RasterYSize, dataset.RasterXSize]}
    dataset = None
    return value


def observe(owner):
    watershed = owner.watershed_instance
    paths = [watershed.subwta, watershed.mofe_map]
    nodes = [inventory(path) for path in paths]
    members = sorted({p for node in nodes for p in node['members']})
    versions = {p: version(p) for p in members}
    digests = {p: file_digest.sha256_file(p) for p in members}
    assert nodes == [inventory(path) for path in paths]
    assert versions == {p: version(p) for p in members}
    return {'nodes': nodes, 'digests': digests,
            'structure': owner._mofe_structure_signature(owner.domlc_mofe_d)}


@contextmanager
def locked(owner, *args, **kwargs):
    start = perf_counter()
    validation = 0.0
    with real_locked(owner, *args, **kwargs):
        entered = perf_counter()
        if observation_enabled:
            begin = perf_counter()
            before = observe(owner)
            validation += perf_counter() - begin
        yield
        if observation_enabled:
            begin = perf_counter()
            assert before == observe(owner)
            validation += perf_counter() - begin
        body_done = perf_counter()
    finished = perf_counter()
    locks.append({'seconds': finished - start, 'validation_seconds': validation,
                  'body_seconds': body_done - entered, 'acquire_seconds': entered - start,
                  'persist_unlock_seconds': finished - body_done})


def pair(*args, **kwargs):
    start = perf_counter()
    value = real_pair(*args, **kwargs)
    native.append(perf_counter() - start)
    return value


def flush():
    OUTPUT.write_text(json.dumps(result, indent=2) + '\n')


try:
    with patch.object(Landuse, 'locked', locked), patch.object(module, 'count_intersecting_raster_key_pairs', pair):
        for name in ('curable-program', 'beneficiary-forfeit'):
            owner_root = Path(baseline['cases'][name]['root'])
            assert owner_root.is_relative_to(root) and '-qa-' in owner_root.name
            owner = Landuse.getInstance(str(owner_root))
            assert owner.runid != name
            expected = pq.read_table(owner_root / 'landuse/landuse.parquet')
            owner.build_managements()
            observe(owner)
            sleep(1.05)
            observe(owner)
            case = result['cases'][name] = {'root': str(owner_root), 'measurements': []}
            for phase, force_miss, cold in [('settled_hit', False, False), ('settled_miss', True, False), ('cold_miss', True, True)]:
                for iteration in range(3):
                    # Alternate order to avoid always charging the same side for drift.
                    for composed in ([False, True] if iteration % 2 == 0 else [True, False]):
                        if force_miss:
                            owner._invalidate_mofe_pair_count_cache(reason='QA interleaved native miss control')
                        if cold and composed:
                            file_digest._digest.cache_clear()
                            file_digest._observed_at.cache_clear()
                        observation_enabled = composed
                        before_native, before_locks = len(native), len(locks)
                        start = perf_counter()
                        owner.build_managements()
                        elapsed = perf_counter() - start
                        assert len(native) - before_native == int(force_miss)
                        assert len(locks) - before_locks == 1
                        item = {'phase': phase, 'iteration': iteration, 'composed': composed,
                                'seconds': elapsed, 'native_seconds': native[before_native:], 'lock': locks[-1]}
                        case['measurements'].append(item)
                        print(f'{name} {phase} composed={composed}: {elapsed * 1000:.3f} ms', flush=True)
                        flush()
                groups = {flag: [m for m in case['measurements'] if m['phase'] == phase and m['composed'] == flag] for flag in (False, True)}
                case.setdefault('summary', {})[phase] = {
                    'baseline_mean_seconds': mean(m['seconds'] for m in groups[False]),
                    'composed_mean_seconds': mean(m['seconds'] for m in groups[True]),
                    'whole_added_seconds': mean(m['seconds'] for m in groups[True]) - mean(m['seconds'] for m in groups[False]),
                    'lock_added_seconds': mean(m['lock']['seconds'] for m in groups[True]) - mean(m['lock']['seconds'] for m in groups[False]),
                    'validation_mean_seconds': mean(m['lock']['validation_seconds'] for m in groups[True]),
                }
            case['rows_types_values_preserved'] = expected.equals(pq.read_table(owner_root / 'landuse/landuse.parquet'), check_metadata=False)
            assert case['rows_types_values_preserved']
            flush()
finally:
    flush()
print(json.dumps(result, indent=2))
