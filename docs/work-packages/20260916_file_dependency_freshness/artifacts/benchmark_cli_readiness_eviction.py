"""Probe-only lineage readiness after actual bounded shared-cache eviction.

Uses only retained disposable files from benchmark_cli_lineage.py. No producer,
named-project mutation, or production readiness implementation is invoked.
"""
from collections import defaultdict
import json
import os
from pathlib import Path
from statistics import mean
from time import perf_counter, sleep
from unittest.mock import patch
from uuid import uuid4

import pyarrow.parquet as pq

from wepppy.all_your_base import file_digest

ARTIFACTS = Path(__file__).parent
baseline = json.loads((ARTIFACTS / 'cli_lineage_performance.json').read_text())
root = Path(baseline['root'])
assert root.is_relative_to('/wc1/batch')
pressure_root = root / ('readiness-pressure-' + uuid4().hex[:8])
pressure_root.mkdir(mode=0o700)
pressure = []
for index in range(512):
    path = pressure_root / str(index)
    path.write_bytes(f'lineage QA pressure {index}\n'.encode())
    pressure.append(path)

reads = defaultdict(int)
tracked = set()
original_open = Path.open


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


def version(info):
    return tuple(getattr(info, name) for name in ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns'))


def cache_info():
    return {'digest': file_digest._digest.cache_info()._asdict(),
            'observation': file_digest._observed_at.cache_info()._asdict()}


result = {'scope': 'Probe-only coherent footer + proof + selected CLI digest composition; excludes full postfire.sources',
          'cache_note': 'OS cache warm; no cold-storage claim',
          'pressure_root': str(pressure_root), 'pressure_paths': len(pressure), 'cases': {}}
with patch.object(Path, 'open', counted_open):
    for name, case in baseline['cases'].items():
        source = Path(case['copy_source'])
        parquet = sorted(source.parent.glob('composed-*/climate/wepp_cli.parquet'))[0]
        assert source.is_relative_to(root) and parquet.is_relative_to(root)
        tracked.update((source, parquet))

        def readiness():
            with parquet.open('rb') as stream:
                before = version(os.fstat(stream.fileno()))
                metadata = pq.read_schema(stream).metadata
                assert before == version(os.fstat(stream.fileno())) == version(parquet.stat())
            proof = json.loads(metadata[b'wepppy_cli_source'])
            assert proof['selected_cli'] == source.name
            assert proof['sha256'] == file_digest.sha256_file(source)

        file_digest._digest.cache_clear()
        file_digest._observed_at.cache_clear()
        readiness()
        sleep(1.05)
        readiness()
        settled = cache_info()
        assert settled['digest']['currsize'] == 1
        times = []
        measurements = []
        for _ in range(3):
            # All 512 distinct observations and then all 512 admitted digests
            # displace the original source from both existing bounded caches.
            for path in pressure:
                file_digest.sha256_file(path)
            sleep(1.05)
            for path in pressure:
                file_digest.sha256_file(path)
            pressured = cache_info()
            assert pressured['digest']['currsize'] == pressured['observation']['currsize'] == 512
            before_reads = dict(reads)
            started = perf_counter()
            readiness()
            elapsed = perf_counter() - started
            current_reads = {path: count - before_reads.get(path, 0) for path, count in reads.items()
                             if count != before_reads.get(path, 0)}
            assert current_reads[str(source)] == case['source_bytes']
            assert current_reads[str(parquet)] == 65536
            measurements.append({'seconds': elapsed, 'tracked_read_bytes': current_reads,
                                 'source_digest_checks': 1, 'cache_before': pressured,
                                 'cache_after': cache_info()})
            times.append(elapsed)
        result['cases'][name] = {'source': str(source), 'parquet': str(parquet),
                                'source_bytes': case['source_bytes'], 'mean_seconds': mean(times),
                                'measurements': measurements}
        print(f'{name}: evicted readiness mean {mean(times) * 1000:.3f} ms', flush=True)
        (ARTIFACTS / 'cli_lineage_readiness_eviction.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
