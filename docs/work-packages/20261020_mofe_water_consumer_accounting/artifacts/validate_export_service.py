from pathlib import Path
import shutil,json,zipfile,hashlib
import pandas as pd
import numpy as np
from wepppy.nodb.mods.features_export.service import execute_features_export
source=Path('/wc1/runs/up/up-pedantry')
root=Path('/wc1/runs/mo/mofe-water-replay-five-year-20261020')
for name in ['ron.nodb','watershed.nodb','wepp.nodb','unitizer.nodb','nodb.version','config','watershed/hillslopes.parquet','watershed/channels.parquet','dem/topaz/SUBCATCHMENTS.WGS.JSON','dem/topaz/CHANNELS.WGS.JSON','dem/topaz/BOUND.WGS.JSON','dem/wbt/subcatchments.WGS.geojson','dem/wbt/channels.WGS.geojson','dem/wbt/bound.WGS.geojson','wepp/output/interchange/interchange_version.json']:
 incoming=source/name
 if not incoming.is_file():continue
 target=root/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(incoming,target)
 if name.endswith('.nodb'): target.write_text(target.read_text().replace(str(source),str(root)))
wat=pd.read_parquet(root/'wepp/output/interchange/H.wat.parquet')
terminal_rows=wat[wat.ofe_id==wat.ofe_id.max()]
wet=terminal_rows.loc[terminal_rows.Q.idxmax()]
selected_date=f'{int(wet.year):04d}-{int(wet.month):02d}-{int(wet.day_of_month):02d}'
suffix=selected_date.replace('-', '_')
day=wat[(wat.year==wet.year)&(wat.julian==wet.julian)];terminal=day.loc[day.ofe_id.idxmax()]
expected={'P':(day.P*day.Area).sum()/day.Area.sum(),'Q':terminal.Q,'latqcc':terminal.latqcc*terminal.Area/day.Area.sum()}
receipts=[];layer='wepp.interchange.hill_wat'
for fmt in ['csv','parquet','geojson','geoparquet']:
 result=execute_features_export(root,runid=root.name,config='canada-wbt-mofe',payload={'format':fmt,'units':'si','layers':[layer],'temporal':{'mode':'event','event':{'selector':'date','dates':[selected_date]}},'column_selection':{layer:{'include':['P','Q','latqcc']}}},job_id='water-replay-'+fmt)
 artifact=root/result['artifact_relpath']
 with zipfile.ZipFile(artifact) as archive:
  name=next(n for n in archive.namelist() if n.endswith('.'+fmt))
  with archive.open(name) as member:
   if fmt=='csv':frame=pd.read_csv(member)
   elif fmt=='parquet':frame=pd.read_parquet(member)
   elif fmt=='geoparquet':
    import geopandas as gpd
    frame=gpd.read_parquet(member);assert frame.crs.to_epsg()==4326 and frame.geometry.notna().all()
    original=gpd.read_file(root/'dem/topaz/SUBCATCHMENTS.WGS.JSON').dissolve(by='WeppID').sort_index().reset_index()
    frame=frame.sort_values('wepp_id').reset_index(drop=True)
    np.testing.assert_array_equal(frame.wepp_id,original.WeppID);assert frame.geometry.geom_equals(original.geometry).all()
    frame=pd.DataFrame(frame.drop(columns=frame.geometry.name))
   else:
    doc=json.load(member);doc=doc.get('feature_collection',doc);frame=pd.DataFrame([f['properties'] for f in doc['features']])
 rows=len(frame);frame=frame.loc[frame.wepp_id==5]
 for metric,value in expected.items():np.testing.assert_allclose(frame[next(c for c in frame if c.startswith(metric+'_'+suffix))],value)
 receipts.append(dict(format=fmt,date=selected_date,result=result,packaged_rows=rows,oracle=expected,observed=json.loads(frame.to_json(orient='records')),sha256=hashlib.sha256(artifact.read_bytes()).hexdigest()))
(root/'service-receipt.json').write_text(json.dumps(receipts,indent=2))
Path('/workdir/wepppy/docs/work-packages/20261020_mofe_water_consumer_accounting/artifacts/20261020_export_service.json').write_text(json.dumps(receipts,indent=2)+'\n')
print(json.dumps(receipts,indent=2))
