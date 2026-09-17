"""Final C05/C06 actual service/provenance/publication performance acceptance.

Native opens use a new copy of the retained audited representative fixture.
Actual current services are compared with exact ancestor 31f77bef1 modules.
The wd/ArtifactIO owner seam excludes HTTP/RQ/kernel and source owner discovery;
no named project, controller status identity, or production/test mutation.
"""
from collections import defaultdict
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
from statistics import mean
import subprocess
import sys
from time import perf_counter, sleep
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

import numpy as np
import rasterio
from wepppy.all_your_base import file_digest, raster_freshness
from wepppy.nodb.mods.geneva.collaborators.artifact_io import GenevaArtifactIO
from wepppy.nodb.mods.geneva.collaborators import _cache_freshness as freshness
from wepppy.nodb.mods.geneva.collaborators import hru_map_geometry_service as geometry_module
from wepppy.nodb.mods.geneva.collaborators import hsg_assignment_service as burn_module

ARTIFACTS = Path(__file__).parent
OUTPUT = ARTIFACTS / 'geneva_implementation_performance.json'
BASELINE = json.loads((ARTIFACTS / 'geneva_consumer_performance_baseline.json').read_text())
PRIOR = Path(BASELINE['root'])
ROOT = Path('/wc1/batch') / ('qa-geneva-implementation-' + uuid4().hex[:12])
ROOT.mkdir()
result = {'scope': __doc__, 'root': str(ROOT), 'uid': os.getuid(), 'gid': os.getgid(),
          'source_fixture_manifest': str(PRIOR / 'benchmark-manifest.json'),
          'cache_note': 'Copied warm filesystem pages, not cold storage; cold/evicted refers to digest helper.',
          'module_hashes': {}, 'ancestor': '31f77bef1', 'ancestor_module_hashes': {},
          'copied_inputs': {}, 'measurements': [], 'gates': [], 'errors': []}
for module in (file_digest, raster_freshness, freshness, geometry_module, burn_module):
    source = Path(module.__file__)
    raw = source.read_bytes()
    result['module_hashes'][str(source)] = hashlib.sha256(raw).hexdigest()
    (ROOT / ('actual_' + source.name)).write_bytes(raw)


def audit(event, args):
    def named(value):
        return isinstance(value, (str, bytes, os.PathLike)) and str(Path(os.fsdecode(value)).absolute()).startswith('/wc1/runs/')
    if event == 'open' and named(args[0]):
        raise PermissionError('No named project opens in final Geneva benchmark')
    if event in {'os.mkdir', 'os.remove', 'os.rmdir', 'os.chmod', 'os.chown', 'os.utime', 'os.rename', 'os.link', 'os.symlink'}:
        if any(named(value) for value in args[:2]):
            raise PermissionError('No named project mutation in final Geneva benchmark')


sys.addaudithook(audit)


def version(path):
    info = Path(path).stat()
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def ancestor(module, name):
    relative = 'wepppy/nodb/mods/geneva/collaborators/' + Path(module.__file__).name
    raw = subprocess.check_output(['git', 'show', '31f77bef1:' + relative])
    path = ROOT / ('ancestor_' + Path(relative).name)
    path.write_bytes(raw)
    result['ancestor_module_hashes'][relative] = hashlib.sha256(raw).hexdigest()
    spec = importlib.util.spec_from_file_location('wepppy.nodb.mods.geneva.collaborators.' + name, path)
    loaded = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = loaded
    spec.loader.exec_module(loaded)
    return loaded


old_geometry_module = ancestor(geometry_module, '_qa_ancestor_geometry')
old_burn_module = ancestor(burn_module, '_qa_ancestor_burn')
reads = defaultdict(int)
observations, native_calls = [], []
real_open = Path.open
real_observe = freshness.observe_raster_dependencies
real_materialize = geometry_module.GenevaHruMapGeometryService._materialize_feature_collection_from_raster
real_old_materialize = old_geometry_module.GenevaHruMapGeometryService._materialize_feature_collection_from_raster
real_stack = burn_module.raster_stacker


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
        reads[str(self.path)] += len(value)
        return value


def counted_open(path, *args, **kwargs):
    stream = real_open(path, *args, **kwargs)
    access = args[0] if args else kwargs.get('mode', 'r')
    if access == 'rb' and path.is_relative_to(ROOT) and path.suffix in {'.tif', '.json'}:
        return CountedStream(stream, path)
    return stream


def observe(paths):
    start = perf_counter()
    value = real_observe(paths)
    observations.append({'paths': [str(path) for path in paths], 'seconds': perf_counter() - start})
    return value


def materialize(self, *args, **kwargs):
    native_calls.append('current_geometry')
    return real_materialize(self, *args, **kwargs)


def old_materialize(self, *args, **kwargs):
    native_calls.append('ancestor_geometry')
    return real_old_materialize(self, *args, **kwargs)


def stacker(*args, **kwargs):
    native_calls.append('raster_stacker')
    return real_stack(*args, **kwargs)


def flush():
    value = json.dumps(result, indent=2) + '\n'
    OUTPUT.write_text(value)
    (ROOT / 'benchmark-manifest.json').write_text(value)


def measure(name, callback, repeats=1, prepare=None, expected_native=None):
    rows = []
    for _ in range(repeats):
        if prepare:
            prepare()
        previous = dict(reads)
        before_observe, before_native = len(observations), len(native_calls)
        start = perf_counter()
        value = callback()
        seconds = perf_counter() - start
        calls = native_calls[before_native:]
        if expected_native is not None:
            assert len(calls) == expected_native, (name, calls)
        rows.append({'seconds': seconds, 'digest_read_bytes': {path: count - previous.get(path, 0)
                    for path, count in reads.items() if count != previous.get(path, 0)},
                     'observations': observations[before_observe:], 'native_calls': calls})
    result['measurements'].append({'name': name, 'repeats': repeats, 'mean_ms': mean(row['seconds'] for row in rows) * 1000,
                                    'samples': rows})
    print(name, round(result['measurements'][-1]['mean_ms'], 3), 'ms', flush=True)
    flush()
    return value


def clear_digest():
    file_digest._observed_at.cache_clear()
    file_digest._digest.cache_clear()


def evict():
    for path in pressure_files:
        file_digest.sha256_file(path)
    sleep(1.05)
    for path in pressure_files:
        file_digest.sha256_file(path)
    assert file_digest._observed_at.cache_info().currsize == 512
    assert file_digest._digest.cache_info().currsize == 512
    result['actual512_evictions'] = result.get('actual512_evictions', 0) + 1


def retain_output(path, label):
    if path.exists():
        target = ROOT / 'retained' / (label + '-' + uuid4().hex[:8] + '-' + path.name)
        target.parent.mkdir(exist_ok=True)
        path.rename(target)


def gate(name, actual, limit):
    result['gates'].append({'name': name, 'actual': actual, 'limit': limit, 'passed': actual <= limit})


try:
    relative_paths = ['geneva/hru_map.tif', 'geneva/hru_map_legend.json', 'geneva/hru_map_features.wgs.geojson',
                      'disturbed/sbs_4class.tif', 'dem/wbt/bound.tif', 'geneva/inputs/burn_severity_4class.tif']
    for relative in relative_paths:
        source, target = PRIOR / relative, ROOT / relative
        result['copied_inputs'][str(source)] = {'version': version(source), 'sha256': digest(source), 'bytes': source.stat().st_size}
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        assert digest(target) == result['copied_inputs'][str(source)]['sha256']
    hru, legend, features, source, bound, target = [ROOT / path for path in relative_paths]
    original_geojson = json.loads(features.read_text())
    original_modes = {str(path.relative_to(ROOT)): oct(path.stat().st_mode & 0o777) for path in (features, target)}
    with rasterio.open(target) as dataset:
        original_burn, original_profile = dataset.read(), dataset.profile
    owner = SimpleNamespace(wd=str(ROOT), artifact_io=GenevaArtifactIO())
    geometry, old_geometry = geometry_module.GenevaHruMapGeometryService(), old_geometry_module.GenevaHruMapGeometryService()
    burn, old_burn = burn_module.GenevaHsgAssignmentService(), old_burn_module.GenevaHsgAssignmentService()
    geometry_query = lambda: geometry.query_feature_collection(owner)
    old_geometry_query = lambda: old_geometry.query_feature_collection(owner)
    burn_query = lambda: burn._materialize_auto_burn_severity(owner, source_path=str(source), bound_tif=str(bound))
    old_burn_query = lambda: old_burn._materialize_auto_burn_severity(owner, source_path=str(source), bound_tif=str(bound))
    pressure_root = ROOT / 'pressure'
    pressure_root.mkdir()
    pressure_files = [pressure_root / str(index) for index in range(512)]
    for index, path in enumerate(pressure_files):
        path.write_bytes(f'pressure-{index}'.encode())
    with patch.object(Path, 'open', counted_open), patch.object(freshness, 'observe_raster_dependencies', observe), \
            patch.object(geometry_module.GenevaHruMapGeometryService, '_materialize_feature_collection_from_raster', materialize), \
            patch.object(old_geometry_module.GenevaHruMapGeometryService, '_materialize_feature_collection_from_raster', old_materialize), \
            patch.object(burn_module, 'raster_stacker', stacker), patch.object(old_burn_module, 'raster_stacker', stacker):
        # Actual prior generation conversion, retaining baseline outputs before replacement.
        for path in (features, target):
            destination = ROOT / 'retained' / ('initial-' + path.name)
            destination.parent.mkdir(exist_ok=True)
            shutil.copy2(path, destination)
        generated = measure('geometry_legacy_admission', geometry_query, expected_native=1)
        measure('burn_legacy_admission', burn_query, expected_native=1)
        result['legacy_admission_modes_preserved'] = original_modes == {
            str(path.relative_to(ROOT)): oct(path.stat().st_mode & 0o777) for path in (features, target)}
        for label, query in [('geometry', geometry_query), ('burn', burn_query)]:
            sleep(1.05)
            query()
            measure(label + '_settled_hit', query, repeats=30, expected_native=0)
            measure(label + '_cold_hit', query, repeats=3, prepare=clear_digest, expected_native=0)
            sleep(1.05)
            query()
            measure(label + '_post_admission_hit', query, repeats=10, expected_native=0)
            measure(label + '_evicted_hit', query, repeats=3, prepare=evict, expected_native=0)
        # Paired complete misses on the same inputs/output path, alternating exact ancestor and actual implementation.
        for cache_state in ('settled', 'cold'):
            for label, old_query, query, output in [('geometry', old_geometry_query, geometry_query, features),
                                                   ('burn', old_burn_query, burn_query, target)]:
                if cache_state == 'settled':
                    query()
                    sleep(1.05)
                    query()
                for index in range(3):
                    for revision, callback in [('ancestor', old_query), ('current', query)]:
                        def prepare():
                            retain_output(output, label + '-' + revision + '-' + cache_state)
                            if cache_state == 'cold':
                                clear_digest()
                        measure(f'{label}_{cache_state}_miss_{revision}_{index}', callback,
                                prepare=prepare, expected_native=1)
        generated = geometry_query()
        current_collection = dict(generated['feature_collection'])
        current_collection.pop(freshness.GEOJSON_PROOF)
        result['geometry_matches_original'] = current_collection == original_geojson
        result['feature_count'] = generated['feature_count']
        with rasterio.open(target) as dataset:
            result['burn_pixels_profile_match_original'] = np.array_equal(dataset.read(), original_burn) and dataset.profile == original_profile
        result['target_proofs_present'] = freshness.GEOJSON_PROOF in generated['feature_collection'] and freshness.clean_tiff_proof(target)[1] is not None
    rows = {row['name']: row for row in result['measurements']}
    for label, settled_limit, cold_limit, miss_limit in [('geometry', 40, 75, 100), ('burn', 25, 40, 35)]:
        gate(label + '_settled_hit_ms', rows[label + '_settled_hit']['mean_ms'], settled_limit)
        gate(label + '_post_admission_hit_ms', rows[label + '_post_admission_hit']['mean_ms'], settled_limit)
        for state in ('cold', 'evicted'):
            gate(label + '_' + state + '_hit_ms', rows[label + '_' + state + '_hit']['mean_ms'], cold_limit)
        for state in ('settled', 'cold'):
            old = mean(rows[f'{label}_{state}_miss_ancestor_{index}']['mean_ms'] for index in range(3))
            current = mean(rows[f'{label}_{state}_miss_current_{index}']['mean_ms'] for index in range(3))
            gate(label + '_' + state + '_miss_added_ms', current - old, miss_limit)
            result.setdefault('paired_misses', []).append({'name': label + '_' + state,
                'ancestor_mean_ms': old, 'current_mean_ms': current, 'added_mean_ms': current - old})
        for state in ('settled', 'post_admission'):
            payload = sum(sum(sample['digest_read_bytes'].values()) for sample in rows[label + '_' + state + '_hit']['samples'])
            gate(label + '_' + state + '_hit_payload_reads', payload, 0)
    assert result['geometry_matches_original'] and result['burn_pixels_profile_match_original']
    assert result['legacy_admission_modes_preserved'] and result['target_proofs_present']
    result['completed'] = True
    result['acceptance_passed'] = all(item['passed'] for item in result['gates'])
except BaseException as error:
    result['errors'].append({'type': type(error).__name__, 'message': str(error)})
    raise
finally:
    result['source_fixture_unchanged'] = all(version(path) == tuple(info['version']) and digest(path) == info['sha256']
                                            for path, info in result['copied_inputs'].items())
    result['module_files_unchanged_during_measurement'] = all(digest(path) == sha for path, sha in result['module_hashes'].items())
    flush()
    print(json.dumps(result, indent=2), flush=True)
