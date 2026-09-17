"""C03/C04 actual native/owner baselines and bounded observation cost discovery.

All native/controller operations consume disposable copies. The extra observation
wrapper is a cost composition for these simple local inputs, not the proposed
general recursive dependency implementation or a correctness certification.
"""
from collections import defaultdict
from contextlib import contextmanager
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

from osgeo import gdal
import pyarrow.parquet as pq
from wepppy.all_your_base import file_digest
from wepppy.nodb.core import Landuse
from wepppy.nodb.core import landuse as landuse_module
from wepppy.nodb.mods.baer import sbs_map

ARTIFACTS = Path(__file__).parent
ROOT = Path('/wc1/batch') / ('qa-raster-consumers-' + uuid4().hex[:12])
ROOT.mkdir()
OUTPUT = ARTIFACTS / 'raster_consumer_performance_baseline.json'
gdal.UseExceptions()
result = {'root': str(ROOT), 'uid': os.getuid(), 'gid': os.getgid(),
          'scope': 'Actual existing native SBS and MOFE/management consumers; probe-only coherent simple-file observations',
          'cache_note': 'Copied inputs prime NFS page cache; no OS cache drop; helper-cold is not cold storage',
          'gdal_version': gdal.VersionInfo(), 'cases': {}, 'named_inputs': {},
          'module_hashes': {str(Path(m.__file__)): hashlib.sha256(Path(m.__file__).read_bytes()).hexdigest() for m in (landuse_module, sbs_map)}}
reads = defaultdict(int)
tracked = set()
native_calls, lock_calls = [], []
real_open = Path.open
real_pair = landuse_module.count_intersecting_raster_key_pairs
real_summary = sbs_map._summarize_sbs_raster_rust
real_locked = Landuse.locked
observe_under_lock = False


def named(value):
    return isinstance(value, (str, bytes, os.PathLike)) and str(Path(os.fsdecode(value)).absolute()).startswith('/wc1/runs/')


def audit(event, args):
    if event == 'open' and named(args[0]):
        mode, flags = args[1], args[2]
        if (mode and any(char in mode for char in 'wax+')) or flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC):
            raise PermissionError('No named-run writes in this benchmark')
    if event in {'os.mkdir', 'os.remove', 'os.rmdir', 'os.chmod', 'os.chown', 'os.utime', 'os.rename', 'os.link', 'os.symlink'}:
        if any(named(value) for value in args[:2]):
            raise PermissionError('No named-run mutation in this benchmark')


sys.addaudithook(audit)


def version(path):
    info = path.stat()
    return tuple(getattr(info, key) for key in ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns'))


def copy_named(source, destination):
    if not source.is_file():
        raise FileNotFoundError(source)
    result['named_inputs'][str(source)] = {'version': version(source), 'sha256': file_digest.sha256_file(source, use_cache=False)}
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    tracked.add(destination)


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
    mode = args[0] if args else kwargs.get('mode', 'r')
    if mode == 'rb' and path.absolute() in tracked:
        return CountedStream(stream, str(path.absolute()))
    return stream


def flush():
    OUTPUT.write_text(json.dumps(result, indent=2) + '\n')
    (ROOT / 'benchmark-manifest.json').write_text(json.dumps(result, indent=2) + '\n')


def measured(case, name, callback, repeats=1):
    before_reads, before_native, before_locks = dict(reads), len(native_calls), len(lock_calls)
    times = []
    for _ in range(repeats):
        started = perf_counter()
        value = callback()
        times.append(perf_counter() - started)
    case['measurements'].append({'name': name, 'repeats': repeats, 'seconds': times,
        'mean_seconds': mean(times),
        'digest_read_bytes': {p: n - before_reads.get(p, 0) for p, n in reads.items() if n != before_reads.get(p, 0)},
        'native_calls': native_calls[before_native:], 'locks': lock_calls[before_locks:]})
    flush()
    print(f'{case["name"]} {name}: {mean(times)*1000:.3f} ms', flush=True)
    return value


def inventory(path):
    dataset = gdal.OpenEx(str(path), gdal.OF_RASTER | gdal.OF_READONLY)
    if dataset is None:
        raise RuntimeError(f'No native dataset: {path}')
    driver = dataset.GetDriver().ShortName
    assert driver in {'GTiff', 'AAIGrid'}, driver
    members = tuple(sorted(dataset.GetFileList() or []))
    shape = [dataset.RasterYSize, dataset.RasterXSize]
    dataset = None
    assert members and all(Path(p).is_file() and Path(p).is_relative_to(ROOT) for p in members)
    return {'selected': str(path), 'resolved': str(Path(path).resolve()), 'driver': driver,
            'members': members, 'shape': shape}


def observe(paths, structure=None):
    # Complete for the retained simple GTiff/AAIGrid fixtures only. Inventory is
    # reopened after hashes, and every member generation is rechecked.
    before = [inventory(path) for path in paths]
    members = sorted({p for node in before for p in node['members']})
    versions = {p: version(Path(p)) for p in members}
    digests = {p: file_digest.sha256_file(p) for p in members}
    assert before == [inventory(path) for path in paths]
    assert versions == {p: version(Path(p)) for p in members}
    return {'nodes': before, 'digests': digests, 'structure': structure}


def pair_observation(owner):
    watershed = owner.watershed_instance
    structure = owner._mofe_structure_signature(owner.domlc_mofe_d)
    return observe([Path(watershed.subwta), Path(watershed.mofe_map)], structure)


def counted_pair(*args, **kwargs):
    started = perf_counter()
    value = real_pair(*args, **kwargs)
    native_calls.append({'operation': 'pair_count', 'seconds': perf_counter() - started})
    return value


def counted_summary(*args, **kwargs):
    started = perf_counter()
    value = real_summary(*args, **kwargs)
    native_calls.append({'operation': 'sbs_summary', 'seconds': perf_counter() - started})
    return value


@contextmanager
def timed_locked(owner, *args, **kwargs):
    start = perf_counter()
    with real_locked(owner, *args, **kwargs):
        entered = perf_counter()
        before = pair_observation(owner) if observe_under_lock else None
        try:
            yield
        finally:
            if observe_under_lock:
                assert before == pair_observation(owner)
            body_done = perf_counter()
    ended = perf_counter()
    lock_calls.append({'total_seconds': ended - start, 'acquire_seconds': entered - start,
                       'body_seconds': body_done - entered, 'persist_unlock_seconds': ended - body_done,
                       'probe_observation_enabled': observe_under_lock})


def clear_digest():
    file_digest._digest.cache_clear()
    file_digest._observed_at.cache_clear()


try:
    with patch.object(Path, 'open', counted_open), \
            patch.object(landuse_module, 'count_intersecting_raster_key_pairs', counted_pair), \
            patch.object(sbs_map, '_summarize_sbs_raster_rust', counted_summary), \
            patch.object(Landuse, 'locked', timed_locked):
        for source in (Path('/wc1/runs/th/thespian-cleanness/disturbed/GrizzlyCreek_SBS_final.tif'),
                       Path('/wc1/runs/th/thespian-cleanness/disturbed/baer.cropped.tif')):
            target = ROOT / ('sbs-' + source.stem) / source.name
            copy_named(source, target)
            for extra in source.parent.glob(source.name + '.*'):
                if extra.is_file():
                    copy_named(extra, target.parent / extra.name)
            case = {'name': source.name, 'source': str(target), 'bytes': target.stat().st_size,
                    'inventory': inventory(target), 'measurements': []}
            result['cases'][case['name']] = case
            sbs_map._summarize_sbs_raster_cached.cache_clear()
            original = measured(case, 'actual_summary_cold', lambda: sbs_map._summarize_sbs_raster(str(target)))
            measured(case, 'actual_summary_hit', lambda: sbs_map._summarize_sbs_raster(str(target)), 100)
            measured(case, 'actual_native_summary_uncached', lambda: counted_summary(str(target)), 3)

            def observed_summary():
                before = observe([target])
                value = sbs_map._summarize_sbs_raster(str(target))
                assert before == observe([target])
                assert value == original
                return value

            clear_digest()
            measured(case, 'composed_summary_hit_cold_observation', observed_summary)
            sleep(1.05)
            observed_summary()
            measured(case, 'composed_summary_hit_settled', observed_summary, 30)
            sbs_map._summarize_sbs_raster_cached.cache_clear()
            measured(case, 'composed_summary_miss_settled_observation', observed_summary)
            clear_digest()
            sbs_map._summarize_sbs_raster_cached.cache_clear()
            measured(case, 'composed_summary_miss_cold_observation', observed_summary)

        for name in ('curable-program', 'beneficiary-forfeit'):
            named_root = Path('/wc1/runs') / name[:2] / name
            root = ROOT / (name + '-qa-' + uuid4().hex[:8])
            for relative in ('ron.nodb', 'watershed.nodb', 'landuse.nodb', 'wepp.nodb', 'disturbed.nodb',
                             'nodb.version', 'watershed/hillslopes.parquet', 'watershed/channels.parquet', 'watershed/mofe.tif'):
                copy_named(named_root / relative, root / relative)
            (root / 'landuse').mkdir()
            relative = 'dem/topaz/SUBWTA.ARC' if name == 'beneficiary-forfeit' else 'dem/wbt/subwta.tif'
            copy_named(named_root / relative, root / relative)
            for base in (named_root / relative, named_root / 'watershed/mofe.tif'):
                extras = list(base.parent.glob(base.name + '.*'))
                if base.suffix == '.ARC':
                    extras += list(base.parent.glob(base.stem + '.PRJ'))
                for extra in extras:
                    if extra.is_file():
                        copy_named(extra, root / extra.relative_to(named_root))
            owner = Landuse.getInstance(str(root))
            assert owner.runid != name and owner.multi_ofe
            watershed = owner.watershed_instance
            paths = [Path(watershed.subwta), Path(watershed.mofe_map)]
            assert all(p.is_relative_to(root) for p in paths)
            case = {'name': name, 'root': str(root), 'hillslopes': len(owner.domlc_mofe_d),
                    'inventories': [inventory(p) for p in paths], 'measurements': []}
            result['cases'][name] = case
            counted = measured(case, 'actual_native_pair_count', lambda: counted_pair(
                key_fn=str(paths[0]), key2_fn=str(paths[1]), ignore_channels=False,
                ignore_keys=None, ignore_keys2=None), 3)
            owner._invalidate_mofe_pair_count_cache(reason='QA native miss baseline')
            measured(case, 'actual_management_miss', owner.build_managements)
            expected = {key: value.as_dict() for key, value in owner.managements.items()}
            measured(case, 'actual_management_hit', owner.build_managements, 10)
            assert owner._mofe_pair_count_cache == counted
            output = root / 'landuse/landuse.parquet'
            expected_table = pq.read_table(output)
            case['management_rows'] = expected_table.num_rows
            clear_digest()
            measured(case, 'pair_observation_cold', lambda: pair_observation(owner))
            sleep(1.05)
            pair_observation(owner)
            measured(case, 'pair_observation_settled', lambda: pair_observation(owner), 30)
            observe_under_lock = True
            measured(case, 'composed_management_hit_settled_observation', owner.build_managements, 10)
            owner._invalidate_mofe_pair_count_cache(reason='QA composed miss baseline')
            measured(case, 'composed_management_miss_settled_observation', owner.build_managements)
            clear_digest()
            owner._invalidate_mofe_pair_count_cache(reason='QA cold composed miss baseline')
            measured(case, 'composed_management_miss_cold_observation', owner.build_managements)
            observe_under_lock = False
            case['management_values_unchanged'] = expected == {key: value.as_dict() for key, value in owner.managements.items()}
            case['management_parquet_unchanged'] = expected_table.equals(pq.read_table(output), check_metadata=False)
            assert case['management_values_unchanged'] and case['management_parquet_unchanged']
            case['persisted_owner_bytes'] = (root / 'landuse.nodb').stat().st_size
            case['output_bytes'] = output.stat().st_size
            flush()
    result['named_inputs_unchanged'] = all(tuple(entry['version']) == version(Path(path)) and entry['sha256'] == file_digest.sha256_file(path, use_cache=False) for path, entry in result['named_inputs'].items())
    assert result['named_inputs_unchanged']
finally:
    flush()
print(json.dumps(result, indent=2))
