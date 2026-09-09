from pathlib import Path
import json
import shutil
import pandas as pd
from wepppy.all_your_base.geo import RasterDatasetInterpolator
from wepppy.nodb.core.wepp import prep_multi_ofe_hillslope
from wepppy.wepp.soils.utils import WeppSoilUtil

root=Path('/workdir/peridot/target/centroid-validation')
source=Path('/wc1/runs/se/seductive-sabra')
run=root/'prepared-run'
for rel in ['soils','landuse','watershed/slope_files/hillslopes','wepp/runs']:
    (run/rel).mkdir(parents=True,exist_ok=True)
rows=pd.read_parquet(root/'hillslopes.parquet')
original=pd.read_parquet(source/'watershed/hillslopes.parquet').set_index('topaz_id')
raster=RasterDatasetInterpolator(str(root/'kslast.tif'))
examples=[]
for row in rows.itertuples():
    top=int(row.topaz_id)
    if top not in [202,212,232,252,263,282,292,293]:continue
    wepp=int(original.loc[top,'wepp_id'])
    for rel in [f'soils/hill_{top}.mofe.sol',f'landuse/hill_{top}.mofe.man',f'watershed/slope_files/hillslopes/hill_{top}.mofe.slp']:
        shutil.copy2(source/rel,run/rel)
    value=raster.get_location_info(row.centroid_lon,row.centroid_lat,method='nearest')
    assert value==0.0001,(top,value)
    prep_multi_ofe_hillslope((str(top),wepp,str(run),str(run/'wepp/runs'),1,value,0.75,False,300.0,False,2000.0,False,0.0))
    soil=WeppSoilUtil(str(run/f'wepp/runs/p{wepp}.sol'))
    values=[o['res_lyr']['kslast'] for o in soil.obj['ofes']]
    assert all(v==value for v in values),(top,values)
    examples.append({'topaz_id':top,'wepp_id':wepp,'kslast':value,'ofes':len(values)})
assert len(examples)==8
print(json.dumps({'verified_soil_inputs':examples},indent=2))
