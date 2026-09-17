"""Run with wctl run-pytest <this file> -v -s; isolated actual finalizers.

Numerical collection is injected; input file writes and finalization are real.
Assertions characterize the defect and are expected to fail after its repair.
"""
import os
from pathlib import Path
from types import SimpleNamespace

import pytest
from tests.nodb.test_batch_climate_rap_contention import controllers, helpers, rap_module

pytestmark = pytest.mark.unit


def rewrite_preserving_metadata(path):
    path = Path(path)
    before = path.stat()
    original = path.read_bytes()
    path.write_bytes(b'X' * len(original))
    os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
    assert path.read_bytes() != original
    assert (path.stat().st_size, path.stat().st_mtime_ns) == (before.st_size, before.st_mtime_ns)


def test_prism_publishes_after_restored_time_source_change(controllers, monkeypatch):
    climate, _ = controllers
    monkeypatch.setattr(helpers, '_retrieve_prism_revision_tiles', lambda *args: None)
    monkeypatch.setattr(helpers, '_collect_prism_revision_monthlies', lambda *args: ([], [], []))
    monkeypatch.setattr(helpers, 'ClimateFile', lambda path: SimpleNamespace(cli_fn=path, breakpoint=False))
    def revise(*args):
        rewrite_preserving_metadata(climate.cli_path)
        Path(args[-1]).write_text('output collected from old generation')
    monkeypatch.setattr(helpers, 'cli_revision', revise)
    climate._prism_revision()
    assert Path(climate.cli_dir, '_1.cli').exists()
    print('CONFIRMED: PRISM published despite changed source bytes with restored size/mtime')


def test_rap_publishes_after_restored_time_source_change(controllers, monkeypatch):
    _, rap = controllers
    import threading
    gate = threading.Lock()
    changed = False
    def analyze(**kwargs):
        nonlocal changed
        with gate:
            if not changed:
                rewrite_preserving_metadata(kwargs['parameter_fn'])
                changed = True
        return {'1': 25.0}
    monkeypatch.setattr(rap_module, 'identify_median_single_raster_key', analyze)
    rap.analyze()
    assert Path(rap.rap_dir, 'rap_ts.parquet').exists()
    print('CONFIRMED: RAP published despite changed source bytes with restored size/mtime')
