"""Read-only geometric feasibility audit using existing native GEOS/PROJ bindings."""
import json
from pathlib import Path
from shapely.geometry import shape
from shapely.ops import transform, unary_union
from pyproj import Transformer
import pyarrow.parquet as pq

root=Path('/wc1/runs/cl/clogging-starch')
project=Transformer.from_crs('EPSG:4326','EPSG:32610',always_xy=True).transform
features=json.loads((root/'dem/wbt/subcatchments.WGS.geojson').read_text())['features']
hills={}
for f in features:
 h=int(f['properties']['WeppID'])
 hills.setdefault(h,[]).append(transform(project,shape(f['geometry'])))
hills={h:unary_union(v) for h,v in hills.items()}
watershed=unary_union(list(hills.values()))
boundary=unary_union([transform(project,shape(f['geometry'])) for f in json.loads((root/'dem/wbt/bound.WGS.geojson').read_text())['features']])
segments={f['properties']['segment_id']:f for f in json.loads((root/'wepp/roads/segments/roads.inslope.monotonic.geojson').read_text())['features']}
records=json.loads((root/'roads.nodb').read_text())['py/state']['_last_run_summary']['segment_execution_records']
wat=pq.read_table(root/'wepp/output/interchange/H.wat.parquet',columns=['wepp_id','ofe_id','Area']).to_pandas().drop_duplicates().groupby('wepp_id').Area.sum()
rows=[]; footprints=[]
for r in records:
 if r.get('status')!='completed':continue
 line=transform(project,shape(segments[r['segment_id']]['geometry']))
 footprint=line.buffer(r['road_width_m']/2,cap_style=2,join_style=2)
 clipped=footprint.intersection(watershed)
 ownership={str(h):clipped.intersection(g).area for h,g in hills.items() if clipped.intersects(g)}
 ownership={h:a for h,a in ownership.items() if a>1e-8}
 rows.append({'segment_id':r['segment_id'],'native_id':r['segment_run_id'],'routing_target':r['target_hillslope_wepp_id'],'modeled_area_m2':r['road_width_m']*r['segment_length_m'],'polygon_area_m2':footprint.area,'inside_area_m2':clipped.area,'outside_hillslope_area_m2':footprint.area-clipped.area,'external_watershed_area_m2':footprint.difference(boundary).area,'inside_boundary_unassigned_area_m2':footprint.intersection(boundary).difference(watershed).area,'ownership_m2':ownership})
 footprints.append(clipped)
result={'crs':'EPSG:32610','method':'flat-cap mitre-join road-width buffers; channel-associated single-OFE only','geometry_area_m2':watershed.area,'baseline_wat_area_m2':float(wat.sum()),'sum_clipped_area_m2':sum(g.area for g in footprints),'union_clipped_area_m2':unary_union(footprints).area,'boundary_area_m2':boundary.area,'sum_external_watershed_area_m2':sum(r['external_watershed_area_m2'] for r in rows),'sum_inside_boundary_unassigned_area_m2':sum(r['inside_boundary_unassigned_area_m2'] for r in rows),'segments':rows,'hill_area_comparison':[{'wepp_id':h,'geometry_m2':g.area,'wat_m2':float(wat.get(h,0))} for h,g in hills.items()]}
print(json.dumps(result,indent=2))
