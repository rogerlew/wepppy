"""A report-local relocation must not require unrelated parent-run datasets."""
import ast
import json
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory

from wepppy.wepp.reports.average_annuals_by_landuse import AverageAnnualsByLanduseReport

fixture_path = Path(__file__).with_name('reports_freshness_baseline_probe.py')
tree = ast.parse(fixture_path.read_text())
namespace = {}
exec(compile(ast.Module(body=[node for node in tree.body if isinstance(
    node, (ast.Import, ast.ImportFrom, ast.FunctionDef))], type_ignores=[]),
    str(fixture_path), 'exec'), namespace)

with TemporaryDirectory(prefix='report-unrelated-catalog-review-') as temporary:
    base = Path(temporary)
    parent = base / 'old-parent'
    child = parent / '_pups/omni/scenarios/child'
    namespace['write_landuse_sources'](child)
    expected = [dict(row.row) for row in AverageAnnualsByLanduseReport(child)]
    unrelated = parent / 'soils/soils.parquet'
    namespace['write_table'](unrelated, [{'topaz_id': 101, 'soil': 'unrelated'}])
    catalog_path = child / '_query_engine/catalog.json'
    catalog = json.loads(catalog_path.read_text())
    catalog['files'].append({'path': 'soils/soils.parquet', 'fs_path': str(unrelated),
                             'extension': '.parquet', 'size_bytes': unrelated.stat().st_size,
                             'modified': '2026-09-17', 'schema': None})
    catalog_path.write_text(json.dumps(catalog))
    standalone = base / 'standalone'
    shutil.copytree(child, standalone)
    try:
        report = AverageAnnualsByLanduseReport(standalone)
    except ValueError as error:
        observed = {'error': str(error), 'requested_sources_complete': True}
    else:
        observed = {'status': report.cache_status,
                    'rows_equal': [dict(row.row) for row in report] == expected,
                    'requested_sources_complete': True}
    print(json.dumps(observed, indent=2))
    assert 'error' in observed and 'allowed parent' in observed['error']
