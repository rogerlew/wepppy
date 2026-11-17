"""RUPC-02 full-upload native acceptance; synthetic fill/buffer, isolated copy."""
from pathlib import Path
import json
import shutil
import argparse
import validate_forest as base
from wepppy.nodb.mods.roads import Roads

parser=argparse.ArgumentParser()
parser.add_argument('--short-fill', action='store_true', help='Separate synthetic 5m-fill acceptance experiment')
args=parser.parse_args()
base.ROOT = root = Path('/wc1/runs/ru/rupc2-misty-shortfill' if args.short_fill else '/wc1/runs/ru/rupc2-misty-validation')
if root.exists():
    raise RuntimeError('Refuse to overwrite existing RUPC-02 validation evidence.')
before = base.inventory(base.SOURCE)
shutil.copytree(base.SOURCE, root, ignore=shutil.ignore_patterns('_query_engine','_logs','export','*.log'))
for path in root.glob('*.nodb'):
    path.write_text(json.dumps(base.rebase(json.loads(path.read_text()))))
(root/'validation-source-before.json').write_text(json.dumps(before, indent=2))
data=json.loads((root/'roads/roads.uploaded.geojson').read_text())
values=dict(FILL_LENGTH_M=5. if args.short_fill else 30., FILL_SLOPE_PCT=10., BUFFER_LENGTH_M=30., BUFFER_SLOPE_PCT=10.)
for feature in data['features']:
    feature['properties'].update(values)
path=root/'validation-input.geojson';path.write_text(json.dumps(data))
(root/'validation-provenance.json').write_text(json.dumps({
    'source':str(base.SOURCE),'synthetic_parameters':values,'purpose':'geometry acceptance, not site prediction',
    'input_sha256':base.digest(path)}, indent=2))
r=Roads.getInstance(str(root))
r.set_uploaded_geojson(str(path)); prepared=r.prepare_segments()
print('PREPARED',prepared['output_feature_count'],flush=True)
try:
    result=r.run_roads_wepp()
finally:
    (root/'validation-result.json').write_text(json.dumps(r._last_run_summary,indent=2))
    assert before==base.inventory(base.SOURCE), 'Source changed'
print('COMPLETED',result['executed_segment_count'],flush=True)
