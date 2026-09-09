from pathlib import Path
import json
import numpy as np
import pandas as pd
from osgeo import gdal
from pyproj import Transformer

root=Path('/tmp/peridot-centroid-validation')
report={}
for mode in ['topaz','wbt','fields']:
    old=root/(mode+'-baseline');new=root/(mode+'-new')
    ds=gdal.Open(str(new/('dem/topaz/SUBWTA.ARC' if mode=='topaz' else 'dem/wbt/subwta.tif')))
    gt=ds.GetGeoTransform();tr=Transformer.from_crs(ds.GetProjection(),4326,always_xy=True)
    out='ag_fields/sub_fields' if mode=='fields' else 'watershed'
    tables=list((new/out).glob('*.csv' if mode=='fields' else '*.parquet'))
    assert tables,mode
    detail={}
    for p in tables:
        read=pd.read_csv if p.suffix=='.csv' else pd.read_parquet
        a=read(old/p.relative_to(new));b=read(p)
        assert list(a.columns)==list(b.columns)
        keys=[c for c in ['field_id','topaz_id','sub_field_id','fp_id'] if c in b.columns]
        a=a.sort_values(keys).reset_index(drop=True);b=b.sort_values(keys).reset_index(drop=True)
        other=[c for c in b.columns if c not in ['centroid_lon','centroid_lat']]
        differing=[c for c in other if not a[c].equals(b[c])]
        if mode != 'topaz':
            pd.testing.assert_frame_equal(a[other],b[other],check_exact=True)
        else:
            allowed={'slope_scalar','length','direction','aspect','area','width','length_estimate_mode','length_area_over_channel'}
            assert set(differing)<=allowed,differing
            repeat=read(root/'topaz-baseline-repeat'/out/p.name).sort_values(keys).reset_index(drop=True)
            repeat_differences=[c for c in other if not a[c].equals(repeat[c])]
            assert set(differing)<=set(repeat_differences),(differing,repeat_differences)
        x=gt[0]+b.centroid_px*gt[1]+b.centroid_py*gt[2];y=gt[3]+b.centroid_px*gt[4]+b.centroid_py*gt[5]
        lon,lat=tr.transform(x.to_numpy(),y.to_numpy());err=max(np.max(np.abs(lon-b.centroid_lon)),np.max(np.abs(lat-b.centroid_lat)))
        assert err<1e-8,(p,err)
        detail[p.name]={'rows':len(b),'max_coordinate_error_degrees':float(err),'other_columns_exact':not differing,'differing_columns':differing}
    changed=[];count=0
    for p in (new/out/'slope_files').rglob('*'):
        if p.is_file():
            count+=1
            if p.read_bytes()!=(old/p.relative_to(new)).read_bytes():changed.append(str(p.relative_to(new)))
    detail['slope_files']={'count':count,'changed':changed}
    if mode != "topaz":
        assert not changed,changed[:5]
    report[mode]=detail
print(json.dumps(report,indent=2))
