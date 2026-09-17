"""Actual report/native/query-engine baselines using disposable parquet inputs.

Run with wctl exec weppcloud python <this file>. Only NoDb controller acquisition
is injected: its real translator_factory reads the real disposable watershed
tables. Native summary production and DuckDB report queries are not mocked.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pandas as pd
from wepppy.nodb.core import Watershed
from wepppy.wepp.reports.average_annuals_by_landuse import AverageAnnualsByLanduseReport
from wepppy.wepp.reports.helpers import ReportCacheManager
from wepppy.wepp.reports.hillslope_watbal import HillslopeWatbalReport


def write_table(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(records).to_parquet(path, index=False, compression=None,
                                   use_dictionary=False, write_statistics=False)


def rewrite_table(path, mutate):
    before = path.stat()
    old_digest = hashlib.sha256(path.read_bytes()).hexdigest()
    frame = pd.read_parquet(path)
    mutate(frame)
    frame.to_parquet(path, index=False, compression=None,
                     use_dictionary=False, write_statistics=False)
    os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
    assert path.stat().st_size == before.st_size
    assert path.stat().st_mtime_ns == before.st_mtime_ns
    assert hashlib.sha256(path.read_bytes()).hexdigest() != old_digest


def watershed_for_run(wd):
    controller = object.__new__(Watershed)
    controller.wd = str(wd)
    controller._subs_summary = None
    controller._chns_summary = None
    return controller


def write_watershed(root):
    write_table(root / 'watershed/hillslopes.parquet', [
        {'topaz_id': 101, 'wepp_id': 1, 'area': 1000.0},
        {'topaz_id': 201, 'wepp_id': 2, 'area': 3000.0},
    ])
    write_table(root / 'watershed/channels.parquet', [{'topaz_id': 204}])


def write_wat(root, *, roads=False):
    source = root / ('wepp/roads/output/interchange/H.wat.parquet' if roads
                     else 'wepp/output/interchange/H.wat.parquet')
    write_table(source, [{
        'wepp_id': 900001 if roads else 1, 'ofe_id': 1,
        'sim_day_index': 1, 'water_year': 2001,
        'P': 3.0 if roads else 1.0, 'Dp': 0.5, 'QOFE': 0.2, 'latqcc': 0.1,
        'Ep': 0.05, 'Es': 0.03, 'Er': 0.02, 'Area': 1000.0,
    }])
    return source


def hill_rows(root, *, roads=False):
    report = HillslopeWatbalReport(root, output_scope='roads' if roads else 'baseline')
    return [dict(row.row) for row in report.avg_annual_iter()]


def landuse_rows(root):
    return [dict(row.row) for row in AverageAnnualsByLanduseReport(root)]


def write_landuse_sources(root):
    write_watershed(root)
    write_table(root / 'landuse/landuse.parquet', [
        {'topaz_id': 101, 'key': 100, 'desc': 'Forest'},
        {'topaz_id': 201, 'key': 200, 'desc': 'Meadow'},
    ])
    write_table(root / 'wepp/output/interchange/loss_pw0.hill.parquet', [
        {'wepp_id': 1, 'Runoff Volume': 100.0, 'Subrunoff Volume': 20.0,
         'Baseflow Volume': 10.0, 'Soil Loss': 5.0, 'Sediment Yield': 3.0,
         'Sediment Deposition': 2.0},
        {'wepp_id': 2, 'Runoff Volume': 30.0, 'Subrunoff Volume': 6.0,
         'Baseflow Volume': 3.0, 'Soil Loss': 2.0, 'Sediment Yield': 1.0,
         'Sediment Deposition': 1.0},
    ])


def run_probes(root):
    results = {}
    for name in ('source', 'translator', 'roads_manifest'):
        run = root / ('hillslope_' + name)
        write_watershed(run)
        source = write_wat(run, roads=name == 'roads_manifest')
        roads = name == 'roads_manifest'
        manifest = run / 'wepp/roads/segments/roads.segment.pass.manifest.json'
        if roads:
            manifest.parent.mkdir(parents=True)
            manifest.write_text(json.dumps([{'segment_run_id': 900001,
                                             'target_hillslope_wepp_id': 1}]))
            write_wat(run)
            baseline_rows = hill_rows(run)
        before = hill_rows(run, roads=roads)
        if name == 'source':
            rewrite_table(source, lambda frame: frame.__setitem__('P', 9.0))
        elif name == 'translator':
            mapping_file = run / 'watershed/hillslopes.parquet'
            rewrite_table(mapping_file, lambda frame: frame.__setitem__('topaz_id', [301, 401]))
        else:
            version = manifest.stat()
            manifest.write_text(manifest.read_text().replace('wepp_id": 1', 'wepp_id": 2'))
            os.utime(manifest, ns=(version.st_atime_ns, version.st_mtime_ns))
            assert manifest.stat().st_size == version.st_size
        cached = hill_rows(run, roads=roads)
        key = 'hillslope_watbal_summary_roads' if roads else 'hillslope_watbal_summary'
        ReportCacheManager(run).invalidate(key)
        rebuilt = hill_rows(run, roads=roads)
        assert cached == before and rebuilt != before
        results['C08_' + name] = {'before': before, 'cached_after_change': cached,
                                  'native_rebuilt_control': rebuilt,
                                  'stale_report_confirmed': True}
        if roads:
            assert hill_rows(run) == baseline_rows
            results['C08_' + name]['baseline_scope_preserved'] = True

    for legacy in (False, True):
        run = root / ('cache_only_legacy' if legacy else 'cache_only_current')
        write_watershed(run)
        source = write_wat(run)
        expected = hill_rows(run)
        if legacy:
            cache_path = run / 'wepp/reports/cache/hillslope_watbal_summary.parquet'
            shutil.copyfile(cache_path, source.parent / 'hillslope_watbal_summary.parquet')
            ReportCacheManager(run).invalidate('hillslope_watbal_summary')
        source.unlink()
        shutil.rmtree(run / 'watershed')
        with patch.object(HillslopeWatbalReport, '_build_summary', side_effect=AssertionError('unexpected rebuild')):
            assert hill_rows(run) == expected
        results['C08_cache_only_' + ('legacy' if legacy else 'current')] = {
            'source_and_mapping_absent': True, 'reads_prior_rows_without_rebuild': True}

    for name in ('loss', 'loss_newer', 'hillslope_area', 'landuse_mapping'):
        run = root / ('annual_' + name)
        write_landuse_sources(run)
        before = landuse_rows(run)
        if name in ('loss', 'loss_newer'):
            source = run / 'wepp/output/interchange/loss_pw0.hill.parquet'
            rewrite_table(source, lambda frame: frame.__setitem__('Runoff Volume', [900.0, 30.0]))
            if name == 'loss_newer':
                cache_file = run / 'wepp/reports/cache/average_annuals_by_landuse.parquet'
                newer = cache_file.stat().st_mtime_ns + 2_000_000_000
                os.utime(source, ns=(newer, newer))
                assert source.stat().st_mtime_ns > cache_file.stat().st_mtime_ns
        elif name == 'hillslope_area':
            source = run / 'watershed/hillslopes.parquet'
            rewrite_table(source, lambda frame: frame.__setitem__('area', [2000.0, 3000.0]))
        else:
            source = run / 'landuse/landuse.parquet'
            rewrite_table(source, lambda frame: frame.__setitem__('desc', ['Shrubs', 'Meadow']))
        cached = landuse_rows(run)
        ReportCacheManager(run).invalidate('average_annuals_by_landuse')
        rebuilt = landuse_rows(run)
        assert cached == before and rebuilt != before
        results['C09_' + name] = {'before': before, 'cached_after_change': cached,
                                  'duckdb_rebuilt_control': rebuilt,
                                  'stale_report_confirmed': True}

    run = root / 'annual_cache_only'
    write_landuse_sources(run)
    expected = landuse_rows(run)
    for relative in (AverageAnnualsByLanduseReport._LOSS_DATASET,
                     AverageAnnualsByLanduseReport._HILLSLOPE_DATASET,
                     AverageAnnualsByLanduseReport._LANDUSE_DATASET):
        (run / relative).unlink()
    with patch.object(AverageAnnualsByLanduseReport, '_build_dataframe', side_effect=AssertionError('unexpected query')):
        assert landuse_rows(run) == expected
    results['C09_cache_only_observed'] = {
        'all_three_sources_absent': True, 'reads_prior_rows_without_query': True,
        'explicit_normative_compatibility_not_yet_ratified': True}
    return results


with TemporaryDirectory(prefix='reports-freshness-review-') as temporary:
    with patch.object(Watershed, 'getInstance', side_effect=watershed_for_run):
        result = run_probes(Path(temporary))
    print(json.dumps(result, indent=2))
