"""Actual prior/current report writers on readonly cache, writable parent."""
import importlib.util
import json
import os
from pathlib import Path
import stat

import pytest

from tests.wepp.reports.test_report_cache_freshness import run, _rewrite
from wepppy.wepp.reports.hillslope_watbal import HillslopeWatbalReport
from wepppy.wepp.reports.average_annuals_by_landuse import AverageAnnualsByLanduseReport

pytestmark = pytest.mark.integration


def prior(kind):
    filename = ('reports_prior_hillslope_permission_snapshot.py' if kind == 'C08'
                else 'reports_prior_landuse_permission_snapshot.py')
    name = 'wepppy.wepp.reports._security_prior_' + kind
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.HillslopeWatbalReport if kind == 'C08' else module.AverageAnnualsByLanduseReport


@pytest.mark.parametrize('kind', ['C08', 'C09'])
@pytest.mark.parametrize('revision', ['prior_7d78e9810', 'current'])
def test_readonly_target_writable_parent(run, kind, revision):
    assert os.getuid() != 0
    report = (prior(kind) if revision.startswith('prior') else
              HillslopeWatbalReport if kind == 'C08' else AverageAnnualsByLanduseReport)
    report(run)
    cache = run / 'wepp/reports/cache' / (report._CACHE_KEY + '.parquet')
    cache.with_suffix('.meta.json').write_text('{"version":"force-rebuild"}')
    source = run / ('wepp/output/interchange/H.wat.parquet' if kind == 'C08'
                    else 'wepp/output/interchange/loss_pw0.hill.parquet')
    _rewrite(source, 'P' if kind == 'C08' else 'Runoff Volume', 9. if kind == 'C08' else 900.)
    sidecar = cache.with_suffix('.meta.json')
    previous_sidecar = sidecar.read_bytes()
    sidecar.chmod(0o444)
    previous = cache.read_bytes()
    assert os.access(cache.parent, os.W_OK)
    with pytest.raises(PermissionError):
        descriptor = os.open(sidecar, os.O_WRONLY)
        os.close(descriptor)
    observed = {'kind': kind, 'revision': revision, 'uid': os.getuid(),
                'parent_writable': True, 'prior_target_write_open_denied': True}
    try:
        rebuilt = report(run)
    except (OSError, RuntimeError, ValueError) as error:
        observed.update(error_type=type(error).__name__, error=str(error), returned=False)
    else:
        observed.update(returned=True, cache_status=getattr(rebuilt, 'cache_status', None))
    observed['exists'] = cache.exists()
    observed['prior_bytes_unchanged'] = cache.exists() and cache.read_bytes() == previous
    observed['final_mode'] = oct(stat.S_IMODE(cache.stat().st_mode)) if cache.exists() else None
    observed['prior_sidecar_unchanged'] = sidecar.read_bytes() == previous_sidecar
    observed['sidecar_final_mode'] = oct(stat.S_IMODE(sidecar.stat().st_mode))
    output = Path(__file__).with_name(f'reports_sidecar_authorization_{kind}_{revision}_after_fix.json')
    output.write_text(json.dumps(observed, indent=2) + '\n')
    print('WRITE_AUTHORIZATION ' + json.dumps(observed, sort_keys=True))
    assert observed['exists']
    if revision == 'current':
        assert not observed['returned']
        assert observed['error_type'] == 'PermissionError'
        assert observed['prior_bytes_unchanged'] and observed['prior_sidecar_unchanged']
        assert observed['sidecar_final_mode'] == '0o444'


@pytest.mark.parametrize('kind', ['C08', 'C09'])
@pytest.mark.parametrize('mode', [0o600, 0o640])
def test_current_writable_sidecar_keeps_own_mode(run, kind, mode):
    report = HillslopeWatbalReport if kind == 'C08' else AverageAnnualsByLanduseReport
    report(run)
    cache = run / 'wepp/reports/cache' / (report._CACHE_KEY + '.parquet')
    sidecar = cache.with_suffix('.meta.json')
    sidecar.write_text('{"version":"force-rebuild"}')
    sidecar.chmod(mode)
    assert stat.S_IMODE(cache.stat().st_mode) != mode
    assert report(run).cache_status == 'built'
    assert json.loads(sidecar.read_text()) == {'version': '1'}
    assert stat.S_IMODE(sidecar.stat().st_mode) == mode
    print('SIDECAR_OWN_MODE ' + json.dumps({'kind': kind, 'mode': oct(mode)}))
