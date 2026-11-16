"""Sample fixed-reference contributing area and native D8 distance to streams."""
import json
from pathlib import Path
import numpy as np
import rasterio
from pyproj import Transformer
from whitebox_tools import WhiteboxTools
from osgeo import gdal

ROOT=Path('/wc1/culvert-resolution-replay')
PACKAGE=Path('/workdir/wepppy/docs/work-packages/20261115_culvert_stream_order_resolution_boundary/artifacts')
DEM=Path('/wc1/culverts/402e8594-d597-4c25-a724-008bb72a83e7/topo/breached_filled_DEM_UTM.tif')

def sample(path, points):
    with rasterio.open(path) as ds:
        result=[]
        for xy in points:
            row,col=ds.index(*xy)
            if not (0<=row<ds.height and 0<=col<ds.width):
                result.append(None); continue
            value=next(ds.sample([xy],masked=True))[0]
            result.append(None if np.ma.is_masked(value) or not np.isfinite(value) else float(value))
        return result

def main():
    source=ROOT/'calibration/source'
    features=json.loads((source/'culvert_points.geojson').read_text())['features']
    transformer=Transformer.from_crs(4326,32617,always_xy=True)
    refs=[{'point_id':str(f['properties']['Point_ID']),'kind':'payload_snapped','xy':f['geometry']['coordinates'][:2]} for f in features]
    for item in json.loads((source/'resolved-outlets.json').read_text()):
        if item['outlet']:
            refs.append({'point_id':item['point_id'],'kind':'retained_wepp_outlet','xy':transformer.transform(*item['outlet']['actual_loc']['py/tuple'])})
    xy=[r['xy'] for r in refs]
    areas=[]; distances=[]
    grids=[('native1',ROOT/'calibration/1m',DEM),
           ('baseline',ROOT/'calibration/baseline-native/1m',ROOT/'calibration/baseline/dem.tif')]
    grids += [(f'coarse{s}',ROOT/f'calibration-grid-corrected/{s}m',ROOT/f'calibration-grid-corrected/{s}m/conditioned.tif') for s in [2,4,8,10]]
    for label,directory,dem in grids:
        with rasterio.open(dem) as ds: cellarea=abs(ds.transform.a*ds.transform.e)
        accum=sample(directory/'accumulation.tif',xy)
        for ref,value in zip(refs,accum):
            areas.append(dict(ref,grid=label,area_m2=None if value is None or value<=0 else value*cellarea))
        work=directory/'fidelity'; work.mkdir(exist_ok=True)
        with rasterio.open(dem) as d:
            zero_nodata = d.nodata == 0
        if zero_nodata:
            safe_dem = work/'dem-negative-nodata.tif'
            gdal.UseExceptions()
            gdal.Warp(str(safe_dem),str(dem),srcNodata=0,dstNodata=-9999,creationOptions=['COMPRESS=LZW']).FlushCache()
            with rasterio.open(dem) as original, rasterio.open(safe_dem) as safe:
                assert original.transform == safe.transform
                assert np.array_equal(original.read_masks(1),safe.read_masks(1))
                valid_dem=original.read_masks(1)>0
                assert np.array_equal(original.read(1)[valid_dem],safe.read(1)[valid_dem])
            dem=safe_dem
        w=WhiteboxTools(verbose=False,raise_on_error=True);w.set_working_dir(str(work))
        for mode in ['cells100','area8697']:
            with rasterio.open(directory/f'{mode}-order.tif') as ds:
                order=ds.read(1); valid=ds.read_masks(1)>0; profile=ds.profile.copy();profile.update(dtype='float32',nodata=-9999)
            passes_to_measure=[4,5] if label=='native1' else range(6)
            for passes in passes_to_measure:
                mask=np.where(valid,((order>passes)&(order>0)).astype('float32'),-9999)
                streams=work/f'{mode}-p{passes}.tif';output=work/f'{mode}-p{passes}-distance.tif'
                with rasterio.open(streams,'w',**profile) as dst: dst.write(mask,1)
                w.downslope_distance_to_stream(str(dem),str(streams),str(output),dinf=False)
                for ref,value in zip(refs,sample(output,xy)):
                    distances.append(dict(ref,grid=label,mode=mode,passes=passes,d8_downstream_distance_m=value))
                (PACKAGE/'outlet-downstream-distances.json').write_text(json.dumps(distances,indent=2)+'\n')
                print(label,mode,passes,flush=True)
        (PACKAGE/'outlet-contributing-areas.json').write_text(json.dumps(areas,indent=2)+'\n')

if __name__=='__main__': main()
