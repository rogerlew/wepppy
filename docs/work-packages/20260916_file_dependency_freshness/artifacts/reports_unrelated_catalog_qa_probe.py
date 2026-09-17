"""Actual relocated C09 report with an unrelated unusable catalog entry."""
import json
from pathlib import Path
import shutil
from uuid import uuid4

from wepppy.wepp.reports.average_annuals_by_landuse import AverageAnnualsByLanduseReport

artifacts = Path(__file__).parent
measurement = json.loads((artifacts / 'reports_implementation_performance_final.json').read_text())
source = Path(measurement['disposable_source_clone'])
run = artifacts / 'reports_unrelated_catalog_inputs' / uuid4().hex[:12]
for relative in ['_query_engine/catalog.json', 'wepp/output/interchange/loss_pw0.hill.parquet',
                 'watershed/hillslopes.parquet', 'landuse/landuse.parquet',
                 'wepp/reports/cache/average_annuals_by_landuse.parquet',
                 'wepp/reports/cache/average_annuals_by_landuse.meta.json']:
    destination = run / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source / relative, destination)
before = AverageAnnualsByLanduseReport(run)
catalog_path = run / '_query_engine/catalog.json'
catalog = json.loads(catalog_path.read_text())
unrelated = dict(catalog['files'][0])
unrelated.update(path='unused/unrelated.parquet', fs_path='/tmp/qa-unconsumed-outside.parquet')
catalog['files'].append(unrelated)
catalog_path.write_text(json.dumps(catalog))
result = {'run': str(run), 'baseline_status': before.cache_status,
          'unused_entry': unrelated, 'source': 'Copied disposable benchmark output, no named-run mutation'}
try:
    after = AverageAnnualsByLanduseReport(run)
    result['with_unused_entry'] = {'status': after.cache_status, 'rows_equal': after._dataframe.equals(before._dataframe)}
except (ValueError, OSError) as exc:
    result['with_unused_entry'] = {'error_type': type(exc).__name__, 'error': str(exc)}
catalog['files'].pop()
catalog_path.write_text(json.dumps(catalog))
control = AverageAnnualsByLanduseReport(run)
result['control_status'] = control.cache_status
result['control_rows_equal'] = control._dataframe.equals(before._dataframe)
(artifacts / 'reports_unrelated_catalog_qa_probe.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
