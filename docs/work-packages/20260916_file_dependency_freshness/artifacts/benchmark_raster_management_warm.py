"""Real warmed-owner C03 hit/miss controls on existing disposable clones only."""
from contextlib import contextmanager
import json
from pathlib import Path
from statistics import mean
from time import perf_counter
from unittest.mock import patch

import pyarrow.parquet as pq
from wepppy.nodb.core import Landuse
from wepppy.nodb.core import landuse as module

ARTIFACTS = Path(__file__).parent
baseline = json.loads((ARTIFACTS / 'raster_consumer_performance_baseline.json').read_text())
original_pair = module.count_intersecting_raster_key_pairs
original_locked = Landuse.locked
native, locks = [], []
result = {'scope': 'Actual warmed-owner build_managements with native counting, NoDb lock/persist and Parquet publication; disposable existing clones only', 'cases': {}}


def pair(*args, **kwargs):
    started = perf_counter()
    value = original_pair(*args, **kwargs)
    native.append(perf_counter() - started)
    return value


@contextmanager
def locked(owner, *args, **kwargs):
    started = perf_counter()
    with original_locked(owner, *args, **kwargs):
        entered = perf_counter()
        try:
            yield
        finally:
            body_done = perf_counter()
    finished = perf_counter()
    locks.append({'seconds': finished - started, 'body_seconds': body_done - entered,
                  'acquire_seconds': entered - started, 'persist_unlock_seconds': finished - body_done})


def flush():
    (ARTIFACTS / 'raster_management_warm_baseline.json').write_text(json.dumps(result, indent=2) + '\n')


try:
    with patch.object(module, 'count_intersecting_raster_key_pairs', pair), patch.object(Landuse, 'locked', locked):
        for name in ('curable-program', 'beneficiary-forfeit'):
            root = Path(baseline['cases'][name]['root'])
            assert root.is_relative_to('/wc1/batch') and '-qa-' in root.name
            owner = Landuse.getInstance(str(root))
            assert owner.runid != name
            expected = pq.read_table(root / 'landuse/landuse.parquet')
            owner.build_managements()  # Explicit warm-up includes owner/import/catalog initialization.
            result['cases'][name] = {'root': str(root), 'measurements': []}
            for phase, count, force_miss in [('warm_hit', 5, False), ('warm_forced_miss', 3, True)]:
                before_native, before_locks = len(native), len(locks)
                times = []
                for _ in range(count):
                    if force_miss:
                        owner._invalidate_mofe_pair_count_cache(reason='QA warmed native miss control')
                    start = perf_counter()
                    owner.build_managements()
                    times.append(perf_counter() - start)
                assert len(native) - before_native == (count if force_miss else 0)
                result['cases'][name]['measurements'].append({'phase': phase, 'repeats': count,
                    'seconds': times, 'mean_seconds': mean(times),
                    'native_seconds': native[before_native:], 'locks': locks[before_locks:]})
                print(f'{name} {phase}: {mean(times)*1000:.3f} ms', flush=True)
                flush()
            result['cases'][name]['rows_types_values_preserved'] = expected.equals(pq.read_table(root / 'landuse/landuse.parquet'), check_metadata=False)
            assert result['cases'][name]['rows_types_values_preserved']
            flush()
finally:
    flush()
print(json.dumps(result, indent=2))
