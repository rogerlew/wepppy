import csv,json,math
from pathlib import Path
import rasterio
root=Path('/workdir/weppcloud-wbt/test_fixtures/staley_m3_resolution')
rows=[]
for site in ['moscow_mountain','topanga','az_ponderosa']:
    pair=[]
    for res in ['10m','30m']:
        base=root/site/res
        props=json.loads((base/'dem/wbt/outlet.geojson').read_text())['features'][0]['properties']
        with rasterio.open(base/'dem/dem.tif') as dem, rasterio.open(base/'dem/wbt/flovec.tif') as flow:
            pair.append(dict(site=site,resolution=res,rows=dem.height,columns=dem.width,epsg=dem.crs.to_epsg(),requested_lon=props['requested_lon'],requested_lat=props['requested_lat'],requested_x=props['requested_easting'],requested_y=props['requested_northing'],snapped_x=props['easting'],snapped_y=props['northing'],outlet_row=props['row'],outlet_column=props['column'],dem_pointer_grid_match=dem.shape==flow.shape and dem.transform==flow.transform and dem.crs==flow.crs,upstream_completeness='not assessed'))
    for row in pair:
        row['pair_requested_offset_m']=math.hypot(pair[0]['requested_x']-pair[1]['requested_x'],pair[0]['requested_y']-pair[1]['requested_y'])
        row['pair_snapped_offset_m']=math.hypot(pair[0]['snapped_x']-pair[1]['snapped_x'],pair[0]['snapped_y']-pair[1]['snapped_y'])
    rows.extend(pair)
with open('/tmp/staley-m3-terrain-study/catchments.csv','w') as out:
    w=csv.DictWriter(out,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
print(json.dumps(rows,indent=2))
