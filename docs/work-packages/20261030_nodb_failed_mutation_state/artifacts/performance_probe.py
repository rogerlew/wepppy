"""Opt-in diagnostic, not a timing threshold test. Run with wctl run-pytest -s."""
import json
import os
import statistics
import time
import pytest
import wepppy.nodb.base as base
from tests.nodb.test_base_boundary_characterization import _RedisStub


def test_real_controller_cost(tmp_path, monkeypatch):
    from wepppy.nodb.core import Ron, Soils, Watershed, Wepp
    monkeypatch.setattr(base, 'redis_lock_client', _RedisStub())
    monkeypatch.setattr(base, 'redis_nodb_cache_client', None)
    monkeypatch.setattr(Wepp, 'clean', lambda self: None)
    wd = str(tmp_path)
    config = 'canada-wbt-mofe.cfg'
    ron = Ron(wd, config, initialize_components=False)
    watershed = Watershed(wd, config)
    soils = Soils(wd, config)
    wepp = Wepp(wd, config)
    results = {}
    try:
        for controller, field in [(soils, '_initial_sat'), (wepp, '_kslast')]:
            times = []
            for i in range(45):
                start = time.perf_counter()
                with controller.locked():
                    setattr(controller, field, 0.2 + (i % 2) * 0.01)
                if i >= 5:
                    times.append((time.perf_counter() - start) * 1000)
            start = time.perf_counter()
            for _ in range(100000):
                getattr(controller, field)
            results[type(controller).__name__] = {
                'median_locked_ms': statistics.median(times),
                'p90_locked_ms': sorted(times)[35],
                '100k_attribute_reads_ms': (time.perf_counter()-start)*1000,
                'serialized_bytes': os.stat(controller._nodb).st_size,
            }
        print('NFMS_PERFORMANCE ' + json.dumps(results, sort_keys=True))
    finally:
        for controller in (wepp, soils, watershed, ron):
            controller._safe_stop_queue_listener()
