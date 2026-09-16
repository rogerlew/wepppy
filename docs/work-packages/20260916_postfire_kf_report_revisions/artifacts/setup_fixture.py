"""Disposable Nevada terrain/climate fixture; Kf is prepared only by the real worker."""
from pathlib import Path
import json,uuid,time
import numpy as np
from wepppy.climates.cligen import ClimateFile
import rasterio
from rasterio.transform import from_origin
from wepppy.nodb.core import Ron,Watershed,Climate
from wepppy.nodb.core.climate import ClimateMode
from wepppy.nodb.core.watershed import Outlet
from wepppy.nodb.mods.disturbed import Disturbed
from wepppy.nodb.redis_prep import RedisPrep,TaskEnum
from wepppy.weppcloud.utils.helpers import get_wd
runid='pfdf-kf-'+uuid.uuid4().hex[:8]
wd=Path(get_wd(runid));wd.mkdir(parents=True,exist_ok=False)
ron=Ron(str(wd),'disturbed9002_wbt.cfg')
with ron.locked():ron._mods += ['postfire_debris_flow']
ron.set_map([-117.001,36.139,-116.996,36.144],[-117,36.14],14)
shape=(40,40);transform=from_origin(500000,4000000,10,10)
def raster(path,values,dtype='float32',nodata=-9999):
    path.parent.mkdir(parents=True,exist_ok=True)
    with rasterio.open(path,'w',driver='GTiff',width=40,height=40,count=1,dtype=dtype,nodata=nodata,crs='EPSG:32611',transform=transform) as dst:
        dst.write(np.asarray(values,dtype=dtype),1)
raster(Path(ron.dem_fn),np.tile(np.arange(40)*10,(40,1))+1000)
watershed=Watershed.getInstance(str(wd));mask=np.zeros(shape);mask[3:-3,3:-3]=1
raster(Path(watershed.wbt_wd)/'bound.tif',mask)
(Path(watershed.wbt_wd)/'outlet.geojson').write_text(json.dumps({'type':'Point','coordinates':[500035,3999965]}))
with watershed.locked():
    watershed._outlet=Outlet((-117,36.14),(-117,36.14),0,(3,3));watershed._centroid=(-117,36.14)
disturbed=Disturbed.getInstance(str(wd));raster(Path(disturbed.sbs_4class_path),np.full(shape,3),'uint8',255)
climate=Climate.getInstance(str(wd))
with climate.locked():climate.cli_fn='fixture.cli';climate._climate_mode=ClimateMode.Vanilla
Path(climate.cli_dir).mkdir(exist_ok=True)
header=Path('/workdir/wepppy/tests/climate/test.cli').read_text().splitlines()[:15]
header[2]='  Station: Controlled Kf acceptance fixture (synthetic climate)'
header[4]='    36.14 -117.00 1000 30 1 30'
cli=Path(climate.cli_dir)/'fixture.cli'
cli.write_text('\n'.join(header+[f'1 7 {year} 20.0 1.0 0.4 2.4 25 10 400 2 180 8' for year in range(1,31)])+'\n')
(wd/'climate').mkdir(exist_ok=True)
ClimateFile(str(cli)).as_dataframe(calc_peak_intensities=True).to_parquet(wd/'climate/wepp_cli.parquet')
upload=wd/'smoke-dnbr.tif';raster(upload,np.linspace(-200,900,1600).reshape(shape))
prep=RedisPrep.getInstance(str(wd));epoch=int(time.time())-10
for i,task in enumerate((TaskEnum.build_subcatchments,TaskEnum.abstract_watershed,TaskEnum.init_sbs_map,TaskEnum.build_climate)):
    prep[str(task)]=epoch+i
prep.dump()
meta=dict(runid=runid,wd=str(wd),config='disturbed9002_wbt',upload=str(upload),source_kind='controlled synthetic Nevada terrain/climate; actual network KFFACT')
assert not (wd/'rusle').exists() and not (wd/'polaris').exists()
Path(__file__).with_name('fixture.json').write_text(json.dumps(meta,indent=2)+'\n')
print(json.dumps(meta))
