"""Changed H.wat generations must discover their own native source IDs."""
import json

import pytest

from tests.wepp.reports.test_report_cache_freshness import run, _rewrite, _table
from wepppy.wepp.reports.hillslope_watbal import HillslopeWatbalReport


def test_characterize_changed_source_reuses_obsolete_ids(run):
    source = run / 'wepp/output/interchange/H.wat.parquet'
    _table(run / 'watershed/hillslopes.parquet', [
        {'topaz_id': 101, 'wepp_id': 1, 'area': 1000.},
        {'topaz_id': 201, 'wepp_id': 2, 'area': 1000.},
        {'topaz_id': 301, 'wepp_id': 3, 'area': 1000.}])
    _rewrite(source, 'wepp_id', 3)
    previous = HillslopeWatbalReport(run)
    _rewrite(source, 'wepp_id', 1)
    _table(run / 'watershed/hillslopes.parquet', [
        {'topaz_id': 101, 'wepp_id': 1, 'area': 1000.}])
    report = HillslopeWatbalReport(run)
    assert report.cache_status == 'built'
    rows = [dict(row.row) for row in report.avg_annual_iter()]
    assert [row['TopazID'] for row in rows] == [101]
    assert HillslopeWatbalReport(run).cache_status == 'current'
