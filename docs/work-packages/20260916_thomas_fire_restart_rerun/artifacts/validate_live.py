"""Independent coefficient, raster mean, table and browser CSV checks of live outputs."""
import csv,hashlib,json,math,sys
from pathlib import Path
import numpy as np
import pandas as pd
import rasterio
from wepppy.nodb.mods.postfire_debris_flow.results import open_results
from wepppy.nodb.mods.postfire_debris_flow.kf_source import POLICY
out=Path(__file__).parent
runid=sys.argv[1];root=Path('/wc1/runs')/runid[:2]/runid
state=json.loads((root/'postfire_debris_flow.nodb').read_text())['py/state']['_state']
accepted=state['last_successful_run'];assert accepted['soil_policy']==POLICY
attempt=root/'postfire_debris_flow/attempts'/accepted['id']
manifest=json.loads((attempt/'results/manifest.json').read_text())
catalog=open_results(attempt/'results',expected_manifest_sha256=hashlib.sha256((attempt/'results/manifest.json').read_bytes()).hexdigest())
assert manifest['predictor_snapshot']['schema_version']==3
assert manifest['predictor_snapshot']['soil_policy']==POLICY
coeff={15:(-3.63,.41,.67,.70),30:(-3.61,.26,.39,.50),60:(-3.21,.17,.20,.220)}
v={k:p['value'] for k,p in manifest['predictor_snapshot']['predictors'].items()}
def raster(name):
    with rasterio.open(attempt/name) as ds:return ds.read(1,masked=True)
mask=raster('predictors/valid_mask.tif').filled(0)==1
kf=raster('predictors/kf/kf.tif');dnbr=raster('predictors/prepared/dnbr.tif');intersection=raster('predictors/wbt/intersection.tif')
assert np.all(~np.ma.getmaskarray(kf)[mask])
independent=dict(S=float(np.mean(kf.data[mask],dtype='float64')),F=float(np.mean(dnbr.data[mask],dtype='float64')),T=float(np.mean(intersection.data[mask]==1)))
for k in v:assert math.isclose(v[k],independent[k],rel_tol=1e-12,abs_tol=1e-12),(k,v[k],independent[k])
assert int(mask.sum())==manifest['coverage']['valid_cells']
def prob(duration,intensity):
    b,ct,cf,cs=coeff[duration];z=b+intensity*duration/60*(ct*v['T']+cf*v['F']+cs*v['S'])
    return 1/(1+math.exp(-z))
checks={}
for name in ('events','design','inverse'):
    table=pd.read_parquet(attempt/f'results/{name}.parquet')
    count=0
    for row in table.to_dict('records'):
        intensity=row['intensity_mm_per_hour']
        if intensity is None or not math.isfinite(intensity):continue
        expected=row['target_probability'] if name=='inverse' else row['probability']
        assert math.isclose(prob(row['duration_minutes'],intensity),expected,rel_tol=1e-12,abs_tol=1e-14)
        count+=1
    checks[name]=count
browser=out/'browser'/runid
for file in sorted(browser.glob('curve-*.csv')):
    with file.open(newline='') as f:rows=list(csv.DictReader(f))
    assert rows
    for row in rows:
        intensity=float(row['peak_intensity'])/(.0393701 if row['intensity_unit']=='in/hour' else 1)
        assert row['intensity_unit'] in ('mm/hour','in/hour')
        assert math.isclose(prob(int(row['duration_minutes']),intensity),float(row['probability_fraction']),rel_tol=1e-12)
        assert row['soil_source']=='NRCS-derived STATSGO fine-earth Kf'
    checks[file.name]=len(rows)
source=json.loads((attempt/'kf/manifest.json').read_text())
for name,h in source['artifacts_sha256'].items():assert hashlib.sha256((attempt/'kf'/name).read_bytes()).hexdigest()==h
for name,h in source['requests_sha256'].items():assert hashlib.sha256((attempt/'kf/requests'/name).read_bytes()).hexdigest()==h
p50={str(d):-coeff[d][0]/sum(c*v[k] for c,k in zip(coeff[d][1:],('T','F','S')))*60/d for d in coeff}
result=dict(runid=runid,attempt_id=accepted['id'],job_id=state['run_attempt']['job_id'],model='M1',soil_policy=POLICY,
    predictors=v,independent_raster_predictors=independent,coverage=manifest['coverage'],probability_i15_24=prob(15,24),p50_mm_per_hour=p50,
    checks=checks,english_display_factor=.0393701,source_url=source['source_url'],source_identity=source['object_identity'],source_valid_cells=source['valid_cells'],
    source_missing_cells=source['missing_cells'],source_request_files=len(source['requests_sha256']),rainfall_provenance=manifest['rainfall_provenance'])
(out/(runid+'_numeric_validation.json')).write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
