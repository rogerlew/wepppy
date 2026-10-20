"""Exercise the production export service on one real MOFE hill in an isolated copy."""
from pathlib import Path
import hashlib
import json
import shutil
import zipfile
import pandas as pd
import numpy as np
from wepppy.nodb.mods.features_export.service import execute_features_export

source = Path('/wc1/runs/mo/mofe-et-dp-validation-20261020')
root = Path('/wc1/runs/mo/mofe-et-dp-export-20261020')
root.mkdir(exist_ok=True)
for name in ['ron.nodb','watershed.nodb','wepp.nodb','unitizer.nodb','nodb.version','config',
             'watershed/hillslopes.parquet','watershed/channels.parquet',
             'dem/wbt/subcatchments.WGS.geojson','dem/wbt/channels.WGS.geojson',
             'dem/wbt/bound.WGS.geojson','wepp/output/interchange/interchange_version.json']:
    incoming = source/name
    if not incoming.is_file():
        continue
    target = root/name
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(incoming,target)
    if name.endswith('.nodb'):
        target.write_text(target.read_text().replace(str(source),str(root)))
wat = root/'wepp/output/interchange/H.wat.parquet'
wat.parent.mkdir(parents=True,exist_ok=True)
shutil.copyfile(source/'mofe-validation/actual-hill-water.parquet',wat)
observations = pd.read_parquet(wat)
day = observations[(observations.year == 2002) & (observations.julian == 182)]
expected = {
    'ET': ((day.Ep + day.Es + day.Er) * day.Area).sum() / day.Area.sum(),
    'Dp': (day.Dp * day.Area).sum() / day.Area.sum(),
}
receipts=[]
layer='wepp.interchange.hill_wat'
for fmt in ['csv','parquet','geojson','geoparquet']:
    payload={'format':fmt,'units':'si','layers':[layer],
             'temporal':{'mode':'event','event':{'selector':'date','dates':['2002-07-01']}},
             'column_selection':{layer:{'include':['ET','Dp']}}}
    result=execute_features_export(root,runid=root.name,config='canada-wbt-mofe',
                                  payload=payload,job_id='mofe-real-'+fmt)
    artifact=root/result['artifact_relpath']
    with zipfile.ZipFile(artifact) as archive:
        name=next(n for n in archive.namelist() if n.endswith('.'+fmt))
        with archive.open(name) as member:
            if fmt=='csv': frame=pd.read_csv(member)
            elif fmt=='parquet': frame=pd.read_parquet(member)
            elif fmt=='geoparquet':
                import geopandas as gpd
                frame=gpd.read_parquet(member)
                assert len(frame) == 455 and frame.geometry.notna().all()
                assert frame.crs.to_epsg() == 4326
                original=gpd.read_file(root/'dem/wbt/subcatchments.WGS.geojson')
                original=original.dissolve(by='WeppID').sort_index().reset_index()
                frame=frame.sort_values('wepp_id').reset_index(drop=True)
                np.testing.assert_array_equal(frame.wepp_id,original.WeppID)
                np.testing.assert_array_equal(frame.topaz_id,original.TopazID)
                assert frame.geometry.geom_equals(original.geometry).all()
                frame=pd.DataFrame(frame.drop(columns=frame.geometry.name))
            else:
                document=json.load(member)
                collection=document.get('feature_collection',document)
                frame=pd.DataFrame([f['properties'] for f in collection['features']])
    row_count = len(frame)
    et_column = next(c for c in frame if c.startswith('ET_2002_07_01'))
    frame = frame.loc[frame[et_column].notna()]
    assert len(frame) == 1
    assert frame.wepp_id.iloc[0] == 3 and frame.topaz_id.iloc[0] == 31
    for metric, value in expected.items():
        column = next(c for c in frame if c.startswith(metric+'_2002_07_01'))
        np.testing.assert_allclose(frame[column],value,rtol=1e-12)
    receipts.append({'format':fmt,'result':result,'columns':list(frame.columns),
                     'packaged_rows':row_count,'observed_rows':json.loads(frame.to_json(orient='records')),
                     'oracle':expected,'sha256':hashlib.sha256(artifact.read_bytes()).hexdigest()})
(root/'service-receipt.json').write_text(json.dumps(receipts,indent=2))
print(json.dumps(receipts,indent=2))
