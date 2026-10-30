import sys,json,tempfile,shutil
from pathlib import Path
sys.path.insert(0,'/workdir/wepppy/docs/work-packages/20261029_roads_prepared_soil_hydraulics/artifacts')
import analyze
with tempfile.TemporaryDirectory() as tmp:
 root=Path(tmp);(root/'output').mkdir();(root/'runs').mkdir()
 out=root/'output/H1.loss.dat'
 shutil.copy2('/workdir/wepppy/tests/data/roads_soil_benchmark/legacy-detailed.txt',out)
 metrics=analyze.b.parse_loss(out,3.96);metrics.pop('annual_mean_export_delta_kg')
 record={'status':'completed','width_m':3.96,'inputs':{},'outputs':{'H1.loss.dat':analyze.b.digest(out)},'metrics':metrics}
 (root/'record.json').write_text(json.dumps(record))
 assert 'annual_mean_export_delta_kg' in analyze.verify(root)['metrics']
 record['metrics']['sediment_export_kg_yr']+=1
 (root/'record.json').write_text(json.dumps(record))
 try:analyze.verify(root)
 except ValueError as exc:assert 'Parsed loss differs' in str(exc)
 else:raise AssertionError('Changed scientific result was admitted')
print('PASS: additive diagnostic accepted; changed recorded export rejected')
