"""Retained actual C06 component profile after failed revision2 acceptance run.

No production changes. Uses an isolated output owner and read-only copied
representative source/bound files. Inclusive component times must not be added
together. cProfile output is diagnostic and is not an acceptance timing.
"""
from collections import defaultdict
import cProfile
import hashlib
import json
import os
from pathlib import Path
import pstats
import shutil
from statistics import mean
from time import perf_counter, sleep
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from wepppy.all_your_base import file_digest
from wepppy.nodb.mods.geneva.collaborators.artifact_io import GenevaArtifactIO
from wepppy.nodb.mods.geneva.collaborators import _cache_freshness as fresh
from wepppy.nodb.mods.geneva.collaborators import hsg_assignment_service as service

ARTIFACTS = Path(__file__).parent
previous = json.loads((ARTIFACTS / 'geneva_implementation_performance_revision2.json').read_text())
source_root = Path(previous['root'])
ROOT = Path('/wc1/batch') / ('qa-geneva-profile-' + uuid4().hex[:12])
ROOT.mkdir()
source = source_root / 'disturbed/sbs_4class.tif'
bound = source_root / 'dem/wbt/bound.tif'
target = ROOT / 'geneva/inputs/burn_severity_4class.tif'
target.parent.mkdir(parents=True)
shutil.copy2(source_root / 'geneva/inputs/burn_severity_4class.tif', target)
owner = SimpleNamespace(wd=str(ROOT), artifact_io=GenevaArtifactIO())
consumer = service.GenevaHsgAssignmentService()
query = lambda: consumer._materialize_auto_burn_severity(owner, source_path=str(source), bound_tif=str(bound))
result = {'scope': __doc__, 'root': str(ROOT), 'measurements': [],
          'input_sha256': {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in (source, bound)},
          'module_hashes': {str(Path(m.__file__)): hashlib.sha256(Path(m.__file__).read_bytes()).hexdigest()
                            for m in (file_digest, fresh, service)}}
counts = defaultdict(list)
read_bytes = 0
real_open = Path.open


class CountedStream:
    def __init__(self, wrapped): self.wrapped = wrapped
    def __enter__(self): self.wrapped.__enter__(); return self
    def __exit__(self, *args): return self.wrapped.__exit__(*args)
    def __getattr__(self, key): return getattr(self.wrapped, key)
    def read(self, *args, **kwargs):
        global read_bytes
        block = self.wrapped.read(*args, **kwargs)
        read_bytes += len(block)
        return block


def opened(path, *args, **kwargs):
    wrapped = real_open(path, *args, **kwargs)
    mode = args[0] if args else kwargs.get('mode', 'r')
    return CountedStream(wrapped) if mode == 'rb' and path.suffix == '.tif' else wrapped


def timed(name, original):
    def wrapper(*args, **kwargs):
        started = perf_counter()
        try: return original(*args, **kwargs)
        finally: counts[name].append(perf_counter() - started)
    return wrapper


def phase(name, repeats, prepare=None):
    times, samples = [], []
    for _ in range(repeats):
        if prepare: prepare()
        before = {key: len(values) for key, values in counts.items()}
        before_reads = read_bytes
        started = perf_counter()
        query()
        times.append(perf_counter() - started)
        samples.append({'reads': read_bytes - before_reads, 'inclusive_components': {
            key: {'calls': len(values) - before.get(key, 0), 'ms': sum(values[before.get(key, 0):]) * 1000}
            for key, values in counts.items()}})
    row = {'name': name, 'mean_ms': mean(times) * 1000, 'seconds': times, 'samples': samples}
    result['measurements'].append(row)
    print(name, row['mean_ms'], flush=True)
    return row


def retain():
    if target.exists():
        folder = ROOT / 'retained'
        folder.mkdir(exist_ok=True)
        target.rename(folder / (uuid4().hex + '.tif'))


try:
    with patch.object(Path, 'open', opened), \
            patch.object(fresh, 'observe_raster_dependencies', timed('raster_observation', fresh.observe_raster_dependencies)), \
            patch.object(service, 'alignment_inputs', timed('alignment_inputs', service.alignment_inputs)), \
            patch.object(service, 'clean_tiff_proof', timed('clean_tiff_proof_initial', service.clean_tiff_proof)), \
            patch.object(fresh, 'clean_tiff_proof', timed('clean_tiff_proof_publication', fresh.clean_tiff_proof)), \
            patch.object(service, 'raster_stacker', timed('native_stacker', service.raster_stacker)), \
            patch.object(fresh._Inputs, 'check_unchanged', timed('same_call_final_validation', fresh._Inputs.check_unchanged)), \
            patch.object(fresh._Attempt, 'candidate', timed('attempt_member_resolution', fresh._Attempt.candidate)), \
            patch.object(fresh._Attempt, '_status', timed('attempt_status', fresh._Attempt._status)), \
            patch.object(GenevaArtifactIO, 'resolve_path', timed('artifact_resolve', GenevaArtifactIO.resolve_path)):
        file_digest._digest.cache_clear()
        file_digest._observed_at.cache_clear()
        query()  # Observe first, wait second, admit third: no initial-admission mislabel.
        sleep(1.05)
        query()
        row = phase('actual_settled_hit', 30)
        assert all(sample['reads'] == 0 for sample in row['samples'])
        phase('actual_settled_miss_absent_target', 5, prepare=retain)
        query()
        sleep(1.05)
        query()
        profile = cProfile.Profile()
        profile.enable()
        for _ in range(20): query()
        profile.disable()
        path = ARTIFACTS / 'geneva_alignment_hit_profile_revision2.txt'
        with path.open('w') as outgoing:
            pstats.Stats(profile, stream=outgoing).strip_dirs().sort_stats('cumulative').print_stats(55)
        profile = cProfile.Profile()
        for _ in range(3):
            retain()
            profile.enable()
            query()
            profile.disable()
        with (ARTIFACTS / 'geneva_alignment_miss_profile_revision2.txt').open('w') as outgoing:
            pstats.Stats(profile, stream=outgoing).strip_dirs().sort_stats('cumulative').print_stats(65)
    result['completed'] = True
finally:
    result['inputs_unchanged'] = all(hashlib.sha256(Path(path).read_bytes()).hexdigest() == sha for path, sha in result['input_sha256'].items())
    result['modules_unchanged'] = all(hashlib.sha256(Path(path).read_bytes()).hexdigest() == sha for path, sha in result['module_hashes'].items())
    payload = json.dumps(result, indent=2) + '\n'
    (ARTIFACTS / 'geneva_alignment_component_profile_revision2.json').write_text(payload)
    (ROOT / 'benchmark-manifest.json').write_text(payload)
    print(payload, flush=True)
