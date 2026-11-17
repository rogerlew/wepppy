# Usage: python replay_selection.py PAYLOAD_ZIP DISPOSABLE_ROOT OUTPUT_JSON
from pathlib import Path
import zipfile,json,sys,numpy as np,rasterio
from whitebox_tools import WhiteboxTools
from wepppy.nodb.culverts_runner import CulvertsRunner
from wepppy.nodb import culvert_stream_selection as s
root=Path(sys.argv[2]).resolve();root.mkdir(exist_ok=True)
with zipfile.ZipFile(sys.argv[1]) as z:z.extractall(root)
w=WhiteboxTools(verbose=False,raise_on_error=True);w.set_working_dir(str(root))
dem=root/'topo/breached_filled_DEM_UTM.tif';pointer=root/'topo/flovec.tif';streams=root/'topo/streams.tif';short=root/'topo/short.tif'
w.d8_pointer(str(dem),str(pointer))
s.write_json(root/s.POLICY,{'version':1,'selection_basis':s.ORIGINAL_OUTLET_BASIS})
runner=object.__new__(CulvertsRunner)
s.prepare_original_outlets(root,pointer,streams,dem,root/'culverts/culvert_points.geojson',root/'culverts/watersheds.geojson',runner)
with rasterio.open(streams) as ds:cell=abs(ds.transform.a)
w.remove_short_streams(str(pointer),str(streams),str(short),min_length=2*cell)
s.prepare(root,pointer,short,streams,1,dem=dem)
features=runner.load_watershed_features(str(root/'culverts/watersheds.geojson'));points,crs=runner.load_culvert_points(str(root/'culverts/culvert_points.geojson'))
results=[]
for pid,feat in features.items():
 mask=root/f'mask-{pid}.tif';feat.build_raster_mask(template_filepath=str(dem),dst_filepath=str(mask))
 try:
  chosen=s.select(root,root/'runs'/pid,pid,points[pid],crs,mask)
  receipt=s.read_json(root/'runs'/pid/s.RECEIPT);o=s.original_outlet(root,pid)
  s.install_original_outlet(root,pid,Path(chosen[0]),root/'runs'/pid/'outlet.geojson')
  with rasterio.open(mask) as ds: inside=bool(ds.read(1)[tuple(o['cell'])]>0)
  results.append({'point_id':pid,'state':'selected','passes':receipt['selected_passes'],'supplied_point':points[pid],'outlet':o['coordinates'],'outlet_in_mask':inside,'offset_m':float(np.linalg.norm(np.array(points[pid])-o['coordinates']))})
 except ValueError as e:results.append({'point_id':pid,'state':'failed','error':str(e)})
out=Path(sys.argv[3])
out.write_text(json.dumps(results,indent=2));print(json.dumps(results,indent=2))
