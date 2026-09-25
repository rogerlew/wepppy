"""Independent source aggregation and official SBS comparison; no run writes."""
from pathlib import Path
import json, hashlib
import numpy as np
import pandas as pd
import rasterio
from rasterio.warp import reproject,Resampling,transform
O=Path(__file__).resolve().parent
R=Path('/wc1/runs/th/thespian-cleanness')
P=R/'postfire_debris_flow/attempts/0a34c96cd0dc4e6bb7bb7780d8f8915b/predictors'
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(p):
 with rasterio.open(p) as d:return d.read(1,masked=True),d.profile
def warp(path,grid,nodata=np.nan):
 with rasterio.open(path) as d:
  a=np.full((grid['height'],grid['width']),nodata,dtype='float64')
  reproject(rasterio.band(d,1),a,src_transform=d.transform,src_crs=d.crs,src_nodata=d.nodata,dst_transform=grid['transform'],dst_crs=grid['crs'],dst_nodata=nodata,resampling=Resampling.nearest)
  return a
b,g=read(P/'prepared/domain.tif'); b=b.filled(0)==1
sbs,_=read(P/'prepared/sbs.tif'); use,_=read(P/'valid_mask.tif'); use=use.filled(0)==1
thick,_=read(P/'soil/thickness_cm.tif'); src,_=read(P/'soil/source.tif'); src=src.filled(0)
original=O/'GrizzlyCreek_SBS_final.tif'; upload=R/'disturbed/GrizzlyCreek_SBS_final.tif'
raw,rg=read(original); aligned=warp(original,g)
# BAER 1..4 -> canonical 0..3, NoData retained.
aligned_canonical=aligned-1
known=b & np.isin(aligned,[1,2,3,4])
local_known=b & ~np.ma.getmaskarray(sbs)
comp=pd.read_csv(P/'soil/components.csv'); horizons=pd.read_csv(P/'soil/horizons_source.csv'); mus=pd.read_csv(P/'soil/mapunits.csv')
cs=pd.read_csv(P/'soil/components_source.csv')
mukeys=warp(P/'soil/sources/original_mukey.tif',g)
rows=[]; errs=[]; missing=[]
for key in np.unique(mukeys[b & np.isfinite(mukeys)]):
 selected=b & (mukeys==key); mu=mus[mus.mukey==key].iloc[0]
 components=comp[comp.mukey==key]; source=cs[cs.mukey==key]
 usable=components[(components.status=='valid') & (components.comppct_r>0)]
 cm=float(np.average(usable.thickness_cm,weights=usable.comppct_r)) if len(usable) else None
 if cm is not None:
  assert abs(cm-float(mu.mean_cm))<1e-10
  expected=np.float32(cm); errors=np.abs(thick[selected & (src==1)].astype('float64')-expected)
  if errors.size: errs.append(float(errors.max()))
 for c in usable.itertuples():
  hs=horizons[horizons.cokey==c.cokey].sort_values(['hzdept_r','hzdepb_r'])
  # Union of recorded non-R intervals is independently sufficient for these
  # accepted components; reported pair reductions and rejection reasons retained.
  intervals=[(float(h.hzdept_r),float(h.hzdepb_r)) for h in hs.itertuples() if h.desgnmaster!='R']
  total=0.; end=-float('inf')
  for lo,hi in intervals:
   total+=max(0,hi-max(lo,end)); end=max(end,hi)
  missing.append({'cokey':int(c.cokey),'cm':float(c.thickness_cm),'independent_union_cm':total,'difference':abs(total-c.thickness_cm),'reasons':str(c.reason_codes)})
 rows.append({'mukey':int(key),'cells':int(selected.sum()),'common_cells':int((selected & use).sum()),'mean_cm':cm,'valid_percentage':float(mu.valid_percentage),'reason_codes':str(mu.reason_codes),'components':source[['cokey','compname','comppct_r']].to_dict('records')})
fallback=warp(P/'soil/sources/fallback_native.tif',g)*2.54
fallback_error=float(np.max(np.abs(thick[src==2].astype('float64')-fallback[src==2].astype('float32'))))
outlet=json.loads((P/'terrain/prepared/outlet.geojson').read_text())['features'][0]['geometry']['coordinates']
lon,lat=transform(g['crs'],'EPSG:4326',[outlet[0]],[outlet[1]])
d={'official_source_url':'https://edcintl.cr.usgs.gov/downloads/sciweb1/shared/MTBS_Fire/data/baer/grizzlycreek_sbs.zip','official_zip_sha256':sha(O/'grizzlycreek_sbs.zip'),'official_tif_sha256':sha(original),'upload_tif_sha256':sha(upload),'upload_byte_identical':sha(original)==sha(upload),'native_grid':{'crs':str(rg['crs']),'resolution':[rg['transform'].a,rg['transform'].e],'nodata':rg['nodata'],'shape':list(raw.shape)},'official_values':{str(v):int((raw.filled(-999)==v).sum()) for v in np.unique(raw.compressed())},'sbs_direct_nearest':{'official_known_basin_cells':int(known.sum()),'local_known_basin_cells':int(local_known.sum()),'mask_disagreement':int((b & (known!=local_known)).sum()),'native_127_basin_cells':int((b & (aligned==127)).sum()),'outside_native_extent_cells':int((b & ~np.isfinite(aligned)).sum()),'class_disagreement_on_both_known':int((known & local_known & (sbs.filled(-999)!=aligned_canonical)).sum())},'outlet_lon_lat':[lon[0],lat[0]],'soil_mapunits':rows,'component_union_checks':missing,'max_primary_raster_error_cm':max(errs),'max_fallback_raster_error_cm':fallback_error,'largest_component_error_cm':max(r['difference'] for r in missing)}
(O/'source_audit.json').write_text(json.dumps(d,indent=2,allow_nan=False)+'\n')
print(json.dumps({k:v for k,v in d.items() if k not in ('soil_mapunits','component_union_checks')},indent=2))
# Small diagnostic map: no reprocessing of scientific outputs.
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap,BoundaryNorm
rr,cc=np.where(b); sl=(slice(rr.min(),rr.max()+1),slice(cc.min(),cc.max()+1))
img=np.full(b.shape,np.nan); img[b]=4; img[local_known]=sbs[local_known]
fig,ax=plt.subplots(figsize=(7,7)); cmap=ListedColormap(['#cccccc','#ffe266','#ee912d','#b32124','#679cbd'])
im=ax.imshow(img[sl],cmap=cmap,norm=BoundaryNorm(np.arange(-.5,5.5),5),interpolation='nearest')
ax.set_title('Dead Horse Creek M3: SBS support\n26.83 km² basin; blue cells excluded from F and S'); ax.set_axis_off()
cb=fig.colorbar(im,ax=ax,ticks=range(5),shrink=.7); cb.ax.set_yticklabels(['Unburned','Low','Moderate','High','SBS NoData'])
fig.tight_layout(); fig.savefig(O/'sbs_support.png',dpi=160); plt.close(fig)
