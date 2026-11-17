"""Select explicit valid real-geometry slices; do not claim full-site acceptance."""
from pathlib import Path
import json
import shutil
from pyproj import CRS, Geod, Transformer
import rasterio
from shapely.geometry import mapping
from wepppy.nodb.mods.roads import Roads
from wepppy.nodb.mods.roads import _unrutted

root = Path('/wc1/runs/ru/rupc-misty-validation')
r = Roads.getInstance(str(root))
features = r._load_prepared_segments_geojson()['features']
pending = [dict(segment_id=f['properties']['segment_id'], feature=f, properties=f['properties']) for f in features]
w = r.watershed_instance
selected, _, _ = r._select_outslope_unrutted_hillslope_segments(pending_segments=pending,
    input_crs=CRS.from_epsg(4326), geod=Geod(ellps='WGS84'), top2wepp=w.translator_factory().top2wepp)
accepted = []
with rasterio.open(w.discha) as dataset:
    transform = Transformer.from_crs(4326, dataset.crs, always_xy=True)
    for topaz in (141, 42):
        candidates = [c for rows in selected.values() for c in rows if c['topaz_id_hill'] == topaz]
        for c in sorted(candidates, key=lambda c: -c['overlap_length_m']):
            distance = r._sample_discha_median_from_wgs84_geometry(c['overlap_geometry_wgs84'],
                discha_dataset=dataset, wgs84_to_discha=transform)
            if distance >= w.hillslope_length(topaz) - 4:
                continue
            accepted.append(c)
            break
assert {c['topaz_id_hill'] for c in accepted} == {141,42}
payload = {'type':'FeatureCollection','features':[]}
for c in accepted:
    for part in _unrutted.line_parts(c['overlap_geometry_wgs84']):
        payload['features'].append({'type':'Feature','geometry':mapping(part),'properties':c['properties']})
path = root/'validation-slices.geojson'
path.write_text(json.dumps(payload))
(root/'validation-slice-selection.json').write_text(json.dumps([
    {k:c[k] for k in ('topaz_id_hill','overlap_length_m','inclusion_ratio','source_segment_ids')}
    for c in accepted], indent=2))
prior = json.loads((root/'roads.nodb').read_text())['py/state']['_last_run_summary']
(root/'validation-full-upload-failure.json').write_text(json.dumps(prior, indent=2))
r.set_uploaded_geojson(str(path))
print('PREPARED',r.prepare_segments(),flush=True)
result = r.run_roads_wepp()
(root/'validation-slices-result.json').write_text(json.dumps(result,indent=2))
print('STATUS',result['status'],flush=True)
