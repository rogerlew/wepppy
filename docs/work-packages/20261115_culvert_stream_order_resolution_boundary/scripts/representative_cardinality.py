"""Delineate selected networks at the fixed retained 1040 outlet; never snap."""
import json
from pathlib import Path
import numpy as np
import rasterio
from whitebox_tools import WhiteboxTools, WhiteboxAppError

ROOT=Path('/wc1/culvert-resolution-replay')
RUN=Path('/wc1/culverts/402e8594-d597-4c25-a724-008bb72a83e7/runs/1040/dem/wbt')
DEM=RUN.parents[3]/'topo/breached_filled_DEM_UTM.tif'
DEST=Path('/workdir/wepppy/docs/work-packages/20261115_culvert_stream_order_resolution_boundary/artifacts/representative-cardinality.json')

def main():
    xy=json.loads((RUN/'outlet.geojson').read_text())['features'][0]['geometry']['coordinates']
    cases=[('native1','area8697',0),('native1','area8697',1),('coarse2','cells100',2),('coarse4','cells100',1),('coarse8','cells100',1),('coarse10','cells100',1)]
    results=json.loads(DEST.read_text()) if DEST.exists() else []
    for label,mode,passes in cases:
        if any((r['grid'],r['mode'],r['passes'])==(label,mode,passes) for r in results): continue
        directory=ROOT/'calibration/1m' if label=='native1' else ROOT/f'calibration-grid-corrected/{label[6:]}m'
        dem=DEM if label=='native1' else directory/'conditioned.tif'
        work=directory/f'cardinality1040-{mode}-p{passes}';work.mkdir(exist_ok=True)
        with rasterio.open(directory/f'{mode}-order.tif') as ds:
            a=ds.read(1); valid=ds.read_masks(1)>0; row,col=ds.index(*xy)
            record={'grid':label,'mode':mode,'passes':passes,'point_id':1040,'outlet_on_stream':bool(valid[row,col] and a[row,col]>passes)}
            profile=ds.profile.copy(); profile.update(dtype='float32',nodata=0)
        if not record['outlet_on_stream']:
            record['status']='not_delineated_fixed_outlet_off_stream'
        else:
            w=WhiteboxTools(verbose=False,raise_on_error=True);w.set_working_dir(str(work))
            w.watershed(str(directory/'pointer.tif'),str(RUN/'outlet.geojson'),str(work/'bound.tif'))
            with rasterio.open(work/'bound.tif') as ds: b=ds.read(1); inside=(ds.read_masks(1)>0)&(b>0)
            mask=(valid&(a>passes)&inside).astype('float32')
            with rasterio.open(work/'netw0.tif','w',**profile) as ds: ds.write(mask,1)
            w.stream_junction_identifier(str(directory/'pointer.tif'),str(work/'netw0.tif'),str(work/'junction.tif'))
            w.strahler_stream_order(str(directory/'pointer.tif'),str(work/'netw0.tif'),str(work/'order.tif'))
            try:
                w.hillslopes_topaz(dem=str(dem),d8_pntr=str(directory/'pointer.tif'),streams=str(work/'netw0.tif'),pour_pts=str(RUN/'outlet.geojson'),watershed=str(work/'bound.tif'),chnjnt=str(work/'junction.tif'),subwta=str(work/'subwta.tif'),order=str(work/'order.tif'),netw=str(work/'netw.tsv'))
            except WhiteboxAppError as exc:
                record.update(status="tool_failed",error=str(exc))
                results.append(record); DEST.write_text(json.dumps(results,indent=2)+"\n")
                print(json.dumps(record),flush=True)
                continue
            with rasterio.open(work/'subwta.tif') as ds:
                ids=np.unique(ds.read(1));ids=ids[(ids>0)&(ids!=ds.nodata)]
                record.update(status='delineated',channels=int(np.sum(ids%10==4)),hillslopes=int(np.sum(ids%10!=4)),area_m2=float(inside.sum()*abs(ds.transform.a*ds.transform.e)))
        results.append(record);DEST.write_text(json.dumps(results,indent=2)+'\n');print(json.dumps(record),flush=True)

if __name__=='__main__':main()
