import importlib.util,json,hashlib,time
from pathlib import Path
import numpy as np
import pyarrow.parquet as pq
from wepppy.wepp.interchange.hill_wat_interchange import load_hill_wat_dataframe
from wepppy.nodb.mods.features_export.temporal_wide_materializer import materialize_temporal_layer_wide
binary=Path('/workdir/wepppyo3/target/release/libwepp_interchange_rust.so')
spec=importlib.util.spec_from_file_location('wepp_interchange_rust',binary);native=importlib.util.module_from_spec(spec);spec.loader.exec_module(native)
receipts=[]
for variant in ['five-year','hourly']:
 root=Path(f'/wc1/runs/mo/mofe-water-replay-{variant}-20261020')
 out=root/'wepp/output'; inter=out/'interchange';inter.mkdir(exist_ok=True)
 native.hillslope_wat_files_to_parquet([str(out/'H5.wat.dat')],str(inter/'H.wat.parquet'),1,0)
 native.hillslope_pass_files_to_parquet([str(out/'H5.pass.dat')],str(inter/'H.pass.parquet'),1,0)
 wat=pq.read_table(inter/'H.wat.parquet').to_pandas()
 loaded=load_hill_wat_dataframe(str(out),5,collapse='daily')
 areas=wat.groupby('ofe_id').Area.first();terminal=wat[wat.ofe_id==wat.ofe_id.max()].sort_values(['year','julian'])
 assert len(loaded)==len(terminal)
 np.testing.assert_allclose(loaded.Q,terminal.Q)
 np.testing.assert_allclose(loaded.latqcc,terminal.latqcc*areas.iloc[-1]/areas.sum())
 expected=wat.assign(pvolume=wat.P*wat.Area).groupby(['year','julian']).pvolume.sum()/areas.sum()
 np.testing.assert_allclose(loaded.P,expected)
 native.hillslope_watbal_to_parquet(str(inter/'H.wat.parquet'),str(inter/'consumer-summary.parquet'),{5:105})
 report=pq.read_table(inter/'consumer-summary.parquet').to_pandas()
 for name,raw in [('Precipitation (mm)','P'),('Surface Runoff (mm)','Q'),('Lateral Flow (mm)','latqcc')]:
  expected=loaded.groupby('water_year')[raw].sum()
  np.testing.assert_allclose(report[name],expected)
 wat['key']=105
 export=materialize_temporal_layer_wide(frame=wat,layer_id='wepp.interchange.hill_wat',temporal_mode='yearly',selected_columns=('P','Q','latqcc'),unit_mapping={},join_key_column='key',event_selector=None).frame
 export.to_parquet(inter/'consumer-export.parquet',index=False)
 actual=pq.read_table(inter/'consumer-export.parquet').to_pandas().iloc[0]
 for year,group in loaded.groupby('year'):
  for name in ['P','Q','latqcc']: np.testing.assert_allclose(actual[f'{name}_yr{year}'],group[name].sum())
 receipts.append(dict(variant=variant,rows=len(wat),days=len(loaded),areas=areas.to_dict(),annual=report.to_dict('records'),export_columns=list(export),source_sha256=hashlib.sha256((out/'H5.wat.dat').read_bytes()).hexdigest(),native_sha256=hashlib.sha256(binary.read_bytes()).hexdigest()))
Path('/workdir/wepppy/docs/work-packages/20261020_mofe_water_consumer_accounting/artifacts/20261020_replay_consumers.json').write_text(json.dumps(receipts,indent=2)+'\n')
print(json.dumps(receipts,indent=2))
