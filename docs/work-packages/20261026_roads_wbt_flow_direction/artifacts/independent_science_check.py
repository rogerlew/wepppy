import json,math,hashlib
from pathlib import Path
import rasterio
import pyarrow.parquet as pq
base=Path('/wc1/ablation/20261026_roads_wbt_flow_direction'); root=base/'candidate'
raster=root/'dem/wbt'
with rasterio.open(raster/'flovec.tif') as ds: flow=ds.read(1); transform=ds.transform
with rasterio.open(raster/'relief.tif') as ds: elev=ds.read(1)
with rasterio.open(raster/'subwta.tif') as ds: sub=ds.read(1)
with rasterio.open(raster/'netful.tif') as ds: net=ds.read(1)
offsets={1:(-1,1),2:(0,1),4:(1,1),8:(1,0),16:(1,-1),32:(0,-1),64:(-1,-1),128:(-1,0)}
summary=json.loads((base/'run-summary.json').read_text()); records={r['segment_id']:r for r in summary['segment_execution_records']}
reports=pq.read_table(root/'wepp/roads/output/interchange/roads_segment_loss_summary.parquet').to_pylist(); reportids={r['segment_run_id'] for r in reports}
out=[]
for item in json.loads((base/'trace-evidence.json').read_text()):
 a=item['after']; coords=list(zip(a['rows'],a['cols'])); assert len(set(coords))==len(coords)
 for i,((r,c),(nr,nc)) in enumerate(zip(coords,coords[1:])):
  assert (nr-r,nc-c)==offsets[int(flow[r,c])]
  dx=transform.a*(nc-c)+transform.b*(nr-r); dy=transform.d*(nc-c)+transform.e*(nr-r); distance=math.hypot(dx,dy)
  assert math.isclose(a['distance_m'][i+1]-a['distance_m'][i],distance,abs_tol=1e-10)
  assert math.isclose(a['segment_slope'][i],(float(elev[r,c])-float(elev[nr,nc]))/distance,abs_tol=1e-10)
 r,c=coords[-1]; assert sub[r,c]==a['channel_topaz_id'] and net[r,c]>0
 rec=records[item['segment_id']]; rid=rec['segment_run_id']; assert rec['status']=='completed' and rid in reportids
 assert rec['trace_path_length_m']==a['path_length_m']==rec['buffer_length_m']
 assert (root/f'wepp/roads/output/H{rid}.pass.dat').stat().st_size>0
 assert int((root/f'wepp/roads/runs/p{rid}.slp').read_text().splitlines()[1])==2
 out.append(dict(segment=item['segment_id'],steps=len(coords)-1,length_m=a['path_length_m'],channel=int(sub[r,c]),segment_run_id=rid))
validation=json.loads((base/'validation.json').read_text())
for name,receipt in validation['parquet'].items():
 p=root/'wepp/roads/output/interchange'/name
 assert hashlib.sha256(p.read_bytes()).hexdigest()==receipt['sha256']
 assert pq.read_metadata(p).num_rows==receipt['rows']
print(json.dumps(dict(status='passed',recovered_geometry=out,parquet_hash_and_rowcounts=len(validation['parquet']),report_rows=len(reports)),indent=2))
