"""Run in rq-worker after each pipeline completes; verify consumed inputs and model output."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import sys
import numpy as np
import pandas as pd
from wepppy.nodb.core import Climate,Watershed,Wepp
from wepppy.nodb.core.climate_build_helpers import get_monthlies
from wepppy.climates.prism.wepp_adapter import validate_cli
from wepppy.rq.job_info import get_wepppy_rq_job_info

mode=int(sys.argv[1]); wd=Path('/wc1/runs/ch/chemotherapeutic-scope')
out=Path('/workdir/wepppy/docs/work-packages/20261008_prism_wepp_integration/artifacts')
c=Climate.getInstance(str(wd)); w=Watershed.getInstance(str(wd)); wepp=Wepp.getInstance(str(wd))
assert int(c.climate_mode)==16 and int(c.climate_spatialmode)==mode and c.has_climate
assert c.cligen_seed==84568
assert c.precip_scaling_mode is None
cli_dir=Path(c.cli_dir); dates=pd.date_range('2019-01-01','2021-12-31')
ws=validate_cli(c.cli_path,dates); raw_ws=pd.read_parquet(cli_dir/'prism800m-source-ws.parquet')
wind=pd.read_parquet(cli_dir/'gridmet-wind.parquet')
proof=json.loads((cli_dir/'provenance.json').read_text())
for source in proof['sources']:
 assert (wd/source['source_directory']).is_dir()
 assert (wd/source['freshness_check_directory']).is_dir()
wat=pd.read_parquet(wd/'wepp/output/interchange/H.wat.parquet')
assert set(wat.year)=={2019,2020,2021}
assert len(wat)==104*len(dates)
assert np.isfinite(wat[['P','Q','Ep','Es','Er','Dp']].to_numpy()).all()
assert (wat[['P','Q','Ep','Es','Er']]>=0).all().all()
translator=w.translator_factory(); rows=[]; aliases={}; calendars=set(); monthly=dates.month-1
if mode==1:
 ws_norm={v:np.asarray(get_monthlies(str(cli_dir/(v+'.tif')),*w.centroid)) for v in ['ppt','tmin','tmax']}
for top,_ in w.centroid_hillslope_iter():
 top=str(top); file=cli_dir/c.sub_cli_fns[top]; hill=validate_cli(file,dates)
 wepp_id=translator.wepp(top=int(top)); prepared=wd/f'wepp/runs/p{wepp_id}.cli'
 assert prepared.read_bytes()==file.read_bytes(),top
 if mode==1:
  normals={v:np.asarray(get_monthlies(str(cli_dir/(v+'.tif')),*w.hillslope_centroid_lnglat(top))) for v in ws_norm}
  expected_p=ws.prcp.to_numpy()*normals['ppt'][monthly]/ws_norm['ppt'][monthly]
  for v in ['tmin','tmax']:
   expected=ws[v].to_numpy()-ws_norm[v][monthly]+normals[v][monthly]
   assert np.allclose(hill[v],expected,atol=.051,rtol=0),(top,v)
  source=raw_ws
  assert np.allclose(hill.prcp,expected_p,atol=.051,rtol=0),top
 else:
  cell=proof['locations'][top]['cell'];source=pd.read_parquet(cli_dir/(cell+'-source.parquet'))
  expected_p=np.round(source.ppt/.254)*.254
  assert np.allclose(hill.prcp,expected_p,atol=.101,rtol=0),top
  weather=hill[['prcp','dur','tp','ip','tmin','tmax','rad','w-vl','w-dir','tdew']]
  if cell in aliases:pd.testing.assert_frame_equal(weather,aliases[cell])
  else:aliases[cell]=weather
 assert np.allclose(hill.tdew,np.maximum(source.tdmean,hill.tmin),atol=.051,rtol=0),top
 assert np.allclose(hill.rad,source.soltotal*1e6/41840,atol=.501,rtol=0),top
 assert np.allclose(hill['w-vl'],wind['vs(m/s)'],atol=.051,rtol=0),top
 model=wat[wat.wepp_id==wepp_id].sort_values('sim_day_index')
 assert np.allclose(model.P,hill.prcp,atol=.051,rtol=0),top
 calendars.add(hashlib.sha256((hill.prcp>0).to_numpy().tobytes()).hexdigest())
 rows.append({'topaz_id':top,'wepp_id':wepp_id,'cli':file.name,'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),
              'precip_mm':float(hill.prcp.sum()),'wet_days':int((hill.prcp>0).sum()),
              'runoff_mm':float(model.Q.sum()),'et_mm':float(model[['Ep','Es','Er']].sum().sum())})
job_id=json.loads((out/f'forest-wepp-{mode}.json').read_text())['payload']['job_id']
jobtree=get_wepppy_rq_job_info(job_id)
def statuses(node):
 values=[node['status']]
 for group in node.get('children',{}).values():
  for child in group:values+=statuses(child)
 return values
assert set(statuses(jobtree))=={'finished'},statuses(jobtree)
(out/f'forest-wepp-{mode}-jobtree.json').write_text(json.dumps(jobtree,indent=2,default=str)+'\n')
loss=pd.read_parquet(wd/'wepp/output/interchange/loss_pw0.out.parquet')
assert len(loss)>0 and np.isfinite(loss.value).all()
record={'mode':mode,'years':[2019,2020,2021],'days':len(dates),'hillslopes':len(rows),
        'unique_cells':len(aliases) if mode==2 else 1,'distinct_wet_day_calendars':len(calendars),
        'model_water_balance_rows':len(wat),'finished_rq_jobs':len(statuses(jobtree)),
        'uid':os.getuid(),'gid':os.getgid(),'cache':os.environ['PRISM_CACHE_DIR'],
        'station':c.climatestation,'seed':c.cligen_seed,'wepp_binary':wepp.wepp_bin,
        'watershed_loss':loss.to_dict('records'),'hillslope_checks':rows}
(out/f'forest-readback-{mode}.json').write_text(json.dumps(record,indent=2)+'\n')
backup=wd/f'archives/prism-integration-mode{mode}-2019-2021'
backup.mkdir(exist_ok=False)
for name in ['climate','wepp','climate.nodb','wepp.nodb','redisprep.dump']:
 src=wd/name
 if src.is_dir():shutil.copytree(src,backup/name)
 elif src.exists():shutil.copy2(src,backup/name)
record['snapshot']=str(backup)
(out/f'forest-readback-{mode}.json').write_text(json.dumps(record,indent=2)+'\n')
print({k:v for k,v in record.items() if k not in ['hillslope_checks','watershed_loss']})
