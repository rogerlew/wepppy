"""Malformed retained alias evidence cannot become historical proof."""
import json

import pyarrow.parquet as pq

from tests.wepp.reports.test_report_cache_freshness import run, _rows
from wepppy.wepp.reports.average_annuals_by_landuse import AverageAnnualsByLanduseReport
from wepppy.wepp.reports import _cache_freshness as freshness


def test_characterize_malformed_alias_proof_under_partial_archive(run):
    expected = _rows(AverageAnnualsByLanduseReport(run))
    cache = run / 'wepp/reports/cache/average_annuals_by_landuse.parquet'
    table = pq.read_table(cache)
    metadata = dict(table.schema.metadata)
    proof = json.loads(metadata[freshness._METADATA_KEY])
    logical = 'landuse/landuse.parquet'
    proof['dependencies'][f'{logical}:aliases'] = {'invalid': 'not an alias expression'}
    metadata[freshness._METADATA_KEY] = json.dumps(proof).encode()
    pq.write_table(table.replace_schema_metadata(metadata), cache)
    (run / logical).unlink()
    catalog_path = run / '_query_engine/catalog.json'
    catalog = json.loads(catalog_path.read_text())
    catalog['files'] = [entry for entry in catalog['files'] if entry['path'] != logical]
    catalog_path.write_text(json.dumps(catalog))
    report = AverageAnnualsByLanduseReport(run)
    print(json.dumps({'observed_status': report.cache_status, 'rows_retained': _rows(report) == expected}))
    assert report.cache_status == 'historical_unverified'
    assert _rows(report) == expected
