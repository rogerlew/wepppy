"""Actual replay model inputs with an explicitly constructed one-hill PASS baseline."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from wepppy.climates.cligen import ClimateFile
from wepppy.nodb.mods.ash_transport.ash_multi_year_model import WhiteAshModel, YearlessDate
from wepppy.nodb.mods.ash_transport.water_provenance import post_inputs,publish_post_proof,historical_warning
from wepppy.wepp.interchange.hill_wat_interchange import load_hill_wat_dataframe
from wepppyo3.wepp_interchange import wepp_interchange_rust as native
root=Path('/wc1/runs/mo/mofe-water-replay-five-year-20261020')
wat=load_hill_wat_dataframe(root/'wepp/output',5,collapse='daily')
cli=ClimateFile(str(root/'wepp/runs/p5.cli')).as_dataframe().iloc[:len(wat)]
out=root/'ash';out.mkdir(exist_ok=True)
model=WhiteAshModel();model.run_model(YearlessDate(7,1),cli,wat,str(out),'H5',ini_ash_load=10.,run_wind_transport=False)
inter=root/'wepp/output/interchange';raw=pd.read_parquet(inter/'H.wat.parquet');area=raw.groupby('ofe_id').Area.first().sum()
passes=pd.read_parquet(inter/'H.pass.parquet')
baseline=passes[['year','julian']].copy();baseline['Area']=area
baseline['Runoff']=passes.runvol/area*1000;baseline['Lateral Flow']=passes.sbrunv/area*1000;baseline['Baseflow']=0.;baseline['Streamflow']=baseline.Runoff+baseline['Lateral Flow'];baseline['seddep_1']=0.
baseline.to_parquet(inter/'totalwatsed3.parquet',index=False)
manifest=[('ash/H5_ash.parquet',41,area/10000,3)];mapping={'manifest':[list(manifest[0])],'ash_wepp_ids':[5]}
proof=post_inputs(root,manifest,mapping)
result=native.ashpost_to_parquet(str(root),str(out/'post'),manifest,[2,5],hydrology_path='wepp/output/interchange/totalwatsed3.parquet',pass_path='wepp/output/interchange/H.pass.parquet',ash_wepp_ids=[5])
publish_post_proof(root,proof)
assert historical_warning(root,mapping) is None
actual=pd.read_parquet(out/'post/watershed_daily.parquet')
joined=actual.merge(baseline,on=['year','julian'],validate='many_to_one')
expected=joined['ash_runoff (m^3)']/area*1000+joined['Lateral Flow']
np.testing.assert_allclose(joined['Streamflow_ash_corr (mm)'],expected,rtol=1e-10,atol=1e-8)
receipt={'baseline':'constructed single-hill equivalent from fresh replay PASS; not a routed watershed replay','days':len(wat),'model_rows':pq.read_metadata(out/'H5_ash.parquet').num_rows,'post_rows':len(actual),'area_m2':area,'proof':json.loads((out/'post/water_accounting.json').read_text()),'native_result':result}
Path('/workdir/wepppy/docs/work-packages/20261020_mofe_water_consumer_accounting/artifacts/20261020_ash_replay.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
