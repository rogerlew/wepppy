"""C05/C06 actual consumer baseline and composed identity-cost discovery.

Named files are ordinary-read copied before any native raster open. Actual
services and ArtifactIO consume only disposable copies. The wd/ArtifactIO owner
seam excludes HTTP/RQ/NoDb orchestration; no named status identity is constructed.
Composition is a pre-implementation cost probe, not a publication/coherence fix.
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
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

import numpy as np
import rasterio
from wepppy.all_your_base import file_digest, raster_freshness
from wepppy.nodb.mods.geneva.collaborators.artifact_io import GenevaArtifactIO
from wepppy.nodb.mods.geneva.collaborators import hru_map_geometry_service as geometry_module
from wepppy.nodb.mods.geneva.collaborators import hsg_assignment_service as burn_module

ARTIFACTS = Path(__file__).parent
OUTPUT = ARTIFACTS / 'geneva_consumer_performance_baseline.json'
NAMED = Path('/wc1/runs/in/incomparable-gracefulness')
ROOT = Path('/wc1/batch') / ('qa-geneva-consumers-' + uuid4().hex[:12])
ROOT.mkdir()
result = {'scope': __doc__, 'root': str(ROOT), 'uid': os.getuid(), 'gid': os.getgid(),
          'cache_note': 'Copied files prime NFS pages; helper-cold is not cold storage',
          'named_inputs': {}, 'measurements': [], 'module_hashes': {},
          'rasterio_version': rasterio.__version__}
for module in (file_digest, raster_freshness, geometry_module, burn_module):
    source = Path(module.__file__)
    raw = source.read_bytes()
    result['module_hashes'][str(source)] = hashlib.sha256(raw).hexdigest()
    (ROOT / source.name).write_bytes(raw)

tracked = set()
reads = defaultdict(int)
native = []
real_open = Path.open
real_materialize = geometry_module.GenevaHruMapGeometryService._materialize_feature_collection_from_raster
real_stacker = burn_module.raster_stacker


def is_named(value):
    return isinstance(value, (str, bytes, os.PathLike)) and str(Path(os.fsdecode(value)).absolute()).startswith('/wc1/runs/')


def audit(event, args):
    if event == 'open' and is_named(args[0]):
        mode, flags = args[1], args[2]
        if (mode and any(char in mode for char in 'wax+')) or flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC):
            raise PermissionError('No named-run writes in this benchmark')
    if event in {'os.mkdir', 'os.remove', 'os.rmdir', 'os.chmod', 'os.chown', 'os.utime', 'os.rename', 'os.link', 'os.symlink'}:
        if any(is_named(value) for value in args[:2]):
            raise PermissionError('No named-run mutation in this benchmark')


sys.addaudithook(audit)


def version(path):
    info = Path(path).stat()
    return tuple(getattr(info, key) for key in ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns'))


def copy_named(source):
    target = ROOT / source.relative_to(NAMED)
    if str(source) in result['named_inputs']:
        return target
    result['named_inputs'][str(source)] = {'version': version(source),
        'sha256': file_digest.sha256_file(source, use_cache=False)}
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    tracked.add(target)
    return target


def copy_raster(source):
    target = copy_named(source)
    # Copy native companion candidates without native-opening the named source.
    bases = {source.name.lower(), source.stem.lower()}
    suffixes = ('.prj', '.wld', '.tfw', '.tifw', '.tab', '.hdr', '.aux', '.aux.xml', '.xml', '.msk', '.ovr')
    candidates = {base + suffix for base in bases for suffix in suffixes}
    for entry in source.parent.iterdir():
        if entry.name.lower() in candidates and entry.is_file():
            copy_named(entry)
    return target


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


def materialize(service, *args, **kwargs):
    started = perf_counter()
    value = real_materialize(service, *args, **kwargs)
    native.append({'operation': 'geometry_materialization', 'seconds': perf_counter() - started})
    return value


def stacker(*args, **kwargs):
    started = perf_counter()
    value = real_stacker(*args, **kwargs)
    native.append({'operation': 'raster_stacker', 'seconds': perf_counter() - started})
    return value


def flush():
    text = json.dumps(result, indent=2) + '\n'
    OUTPUT.write_text(text)
    (ROOT / 'benchmark-manifest.json').write_text(text)


def measure(name, callback, repeats=1):
    before_reads, before_native = dict(reads), len(native)
    times = []
    for _ in range(repeats):
        started = perf_counter()
        value = callback()
        times.append(perf_counter() - started)
    result['measurements'].append({'name': name, 'repeats': repeats, 'seconds': times,
        'mean_seconds': mean(times), 'native': native[before_native:],
        'digest_read_bytes': {p: n - before_reads.get(p, 0) for p, n in reads.items() if n != before_reads.get(p, 0)}})
    print(f'{name}: {mean(times) * 1000:.3f} ms', flush=True)
    flush()
    return value


def clear_digest():
    file_digest._digest.cache_clear()
    file_digest._observed_at.cache_clear()


def retain_output(path, label):
    if path.exists():
        previous = ROOT / 'retained' / (label + '-' + uuid4().hex[:6] + '-' + path.name)
        previous.parent.mkdir(exist_ok=True)
        path.rename(previous)


try:
    hru = copy_raster(NAMED / 'geneva/hru_map.tif')
    legend = copy_named(NAMED / 'geneva/hru_map_legend.json')
    features = copy_named(NAMED / 'geneva/hru_map_features.wgs.geojson')
    source = copy_raster(NAMED / 'disturbed/sbs_4class.tif')
    bound = copy_raster(NAMED / 'dem/wbt/bound.tif')
    target = copy_named(NAMED / 'geneva/inputs/burn_severity_4class.tif')
    result['selected_source'] = 'Existing preferred Disturbed.sbs_4class_path; source-selection owner lookup excluded from component timing'
    result['inputs'] = {}
    for path in (hru, source, bound):
        with rasterio.open(path) as dataset:
            result['inputs'][str(path.relative_to(ROOT))] = {'bytes': path.stat().st_size,
                'shape': list(dataset.shape), 'driver': dataset.driver, 'profile': {k: repr(v) for k,v in dataset.profile.items()},
                'files': dataset.files}
            assert all(Path(item).is_relative_to(ROOT) for item in dataset.files)
    result['legend_bytes'] = legend.stat().st_size
    result['existing_geometry_bytes'] = features.stat().st_size
    original_geojson = json.loads(features.read_text())
    with rasterio.open(target) as dataset:
        original_burn, original_profile = dataset.read(), dataset.profile
    owner = SimpleNamespace(wd=str(ROOT), artifact_io=GenevaArtifactIO())
    geometry = geometry_module.GenevaHruMapGeometryService()
    burn = burn_module.GenevaHsgAssignmentService()

    def geometry_identity():
        paths = (hru, legend)
        before = {str(p): version(p) for p in paths}
        raster = raster_freshness.raster_dependency_signature(hru)
        assert raster is not None, 'Representative HRU raster unverified'
        identity = (raster, str(legend), str(legend.resolve()), file_digest.sha256_file(legend))
        assert before == {str(p): version(p) for p in paths}
        return identity

    def bound_profile():
        before = version(bound)
        with rasterio.open(bound) as dataset:
            profile = tuple(sorted((k, repr(v)) for k, v in dataset.profile.items()))
        assert before == version(bound)
        return str(bound), str(bound.resolve()), profile

    def burn_identity():
        before = {str(p): version(p) for p in (source, bound)}
        raster = raster_freshness.raster_dependency_signature(source)
        assert raster is not None, 'Representative burn raster unverified'
        identity = raster, bound_profile()
        assert before == {str(p): version(p) for p in (source, bound)}
        return identity

    def geometry_query():
        return geometry.query_feature_collection(owner)

    def burn_query():
        return burn._materialize_auto_burn_severity(owner, source_path=str(source), bound_tif=str(bound))

    def composed(query, identity):
        before = identity()
        value = query()
        assert before == identity()
        return value

    with patch.object(Path, 'open', counted_open), \
            patch.object(geometry_module.GenevaHruMapGeometryService, '_materialize_feature_collection_from_raster', materialize), \
            patch.object(burn_module, 'raster_stacker', stacker):
        measure('geometry_existing_query_hit', geometry_query, 20)
        counter = [0]
        def geometry_miss():
            counter[0] += 1
            retain_output(features, 'geometry-before-native')
            return geometry_query()
        generated = measure('geometry_actual_native_query_miss', geometry_miss, 3)
        result['feature_count'] = generated['feature_count']
        result['geometry_matches_original'] = generated['feature_collection'] == original_geojson
        assert result['geometry_matches_original']
        clear_digest()
        measure('geometry_identity_cold', geometry_identity)
        sleep(1.05)
        geometry_identity()
        measure('geometry_identity_settled', geometry_identity, 30)
        measure('geometry_composed_query_hit_settled', lambda: composed(geometry_query, geometry_identity), 20)
        measure('geometry_composed_query_miss_settled', lambda: composed(geometry_miss, geometry_identity), 3)
        clear_digest()
        measure('geometry_composed_query_hit_cold', lambda: composed(geometry_query, geometry_identity))

        measure('burn_existing_materializer_hit', burn_query, 30)
        def burn_miss():
            retain_output(target, 'burn-before-native')
            return burn_query()
        measure('burn_actual_native_materializer_miss', burn_miss, 3)
        clear_digest()
        measure('burn_identity_cold', burn_identity)
        measure('bound_rasterio_profile_only', bound_profile, 30)
        sleep(1.05)
        burn_identity()
        measure('burn_identity_settled', burn_identity, 30)
        measure('burn_composed_materializer_hit_settled', lambda: composed(burn_query, burn_identity), 30)
        measure('burn_composed_materializer_miss_settled', lambda: composed(burn_miss, burn_identity), 3)
        clear_digest()
        measure('burn_composed_materializer_hit_cold', lambda: composed(burn_query, burn_identity))
        with rasterio.open(target) as dataset:
            result['burn_pixels_profile_match_original'] = np.array_equal(dataset.read(), original_burn) and dataset.profile == original_profile
        assert result['burn_pixels_profile_match_original']
    result['named_inputs_unchanged'] = all(tuple(entry['version']) == version(Path(path)) and entry['sha256'] == file_digest.sha256_file(path, use_cache=False) for path, entry in result['named_inputs'].items())
    result['module_files_unchanged_during_measurement'] = all(hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest for path, digest in result['module_hashes'].items())
    assert result['named_inputs_unchanged']
finally:
    flush()
print(json.dumps(result, indent=2))
