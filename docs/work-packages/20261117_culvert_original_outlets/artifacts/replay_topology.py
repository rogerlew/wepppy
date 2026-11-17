# Usage: python replay_topology.py DISPOSABLE_ROOT OUTPUT_JSON
from pathlib import Path
import json,sys,numpy as np,rasterio
from rasterio.windows import Window
from whitebox_tools import WhiteboxTools
from wepppy.nodb import culvert_stream_selection as s
from wepppy.topo.wbt.wbt_topaz_emulator import WhiteboxToolsTopazEmulator
from wepppy.rq.culvert_rq import _extend_watershed_mask_to_candidate,_generate_masked_stream_junctions,_ensure_outlet_junction
root=Path(sys.argv[1]).resolve();results=[]
for pid in ['252','587','755','791','1751','2905','2915']:
 run=root/'runs'/pid; receipt=s.read_json(run/s.RECEIPT);o=s.original_outlet(root,pid)
 with rasterio.open(root/f'mask-{pid}.tif') as ds:
  rr,cc=np.where(ds.read(1)>0);a=max(0,int(rr.min())-5);b=max(0,int(cc.min())-5);window=Window(b,a,min(ds.width-b,int(cc.max())-b+6),min(ds.height-a,int(rr.max())-a+6))
 for source,target in [(root/'topo/flovec.tif','pointer.tif'),(root/'topo/breached_filled_DEM_UTM.tif','dem.tif'),(s.resolve(root,receipt['candidate']['streams']),'streams.tif'),(root/f'mask-{pid}.tif','mask.tif')]:
  with rasterio.open(source) as ds:
   profile=ds.profile.copy();profile.update(driver='GTiff',width=int(window.width),height=int(window.height),transform=ds.window_transform(window))
   with rasterio.open(run/target,'w',**profile) as dst:dst.write(ds.read(1,window=window),1)
 s.install_original_outlet(root,pid,run/'streams.tif',run/'cropped-outlet.geojson')
 gj=json.loads((run/'cropped-outlet.geojson').read_text());p=gj['features'][0]['properties'];row,col=p['row'],p['column']
 emulator=WhiteboxToolsTopazEmulator(str(run),dem_fn=str(run/'dem.tif'))
 outlet_object=emulator.set_outlet_from_geojson(str(run/'cropped-outlet.geojson'))
 assert outlet_object.pixel_coords == (col,row)
 assert _extend_watershed_mask_to_candidate(run/'mask.tif',(row,col))
 _generate_masked_stream_junctions(run/'pointer.tif',run/'streams.tif',run/'mask.tif',run/'junctions.tif')
 _ensure_outlet_junction(run/'junctions.tif',(col,row),run/'mask.tif')
 w=WhiteboxTools(verbose=False,raise_on_error=True);w.set_working_dir(str(run))
 try:
  w.watershed(d8_pntr=str(run/'pointer.tif'),pour_pts=str(run/'cropped-outlet.geojson'),output=str(run/'bound.tif'))
  w.clip_raster_to_raster(str(run/'streams.tif'),str(run/'bound.tif'),str(run/'netw0.tif'))
  w.strahler_stream_order(str(run/'pointer.tif'),str(run/'netw0.tif'),str(run/'order.tif'))
  w.hillslopes_topaz(dem=str(run/'dem.tif'),d8_pntr=str(run/'pointer.tif'),streams=str(run/'netw0.tif'),pour_pts=str(run/'cropped-outlet.geojson'),watershed=str(run/'bound.tif'),chnjnt=str(run/'junctions.tif'),subwta=str(run/'subwta.tif'),order=str(run/'order.tif'),netw=str(run/'netw.tsv'))
  with rasterio.open(run/'subwta.tif') as ds:ids=np.unique(ds.read(1,masked=True).compressed());ids=ids[ids>0]
  with rasterio.open(run/'netw0.tif') as ds:assert ds.read(1)[row,col]>0
  results.append({'point_id':pid,'state':'topology_generated','outlet':o['coordinates'],'cropped_cell':[row,col],'outlet_object_pixel_coords':list(outlet_object.pixel_coords),'subcatchments':len(ids),'channels':int(sum(int(x)%10==4 for x in ids))})
 except Exception as e: results.append({'point_id':pid,'state':'failed','error':str(e)[-600:]})
 print(results[-1],flush=True)
Path(sys.argv[2]).write_text(json.dumps(results,indent=2))
