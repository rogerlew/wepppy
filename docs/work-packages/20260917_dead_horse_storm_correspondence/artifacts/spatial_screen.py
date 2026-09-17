"""Five-location Daymet rainfall screen; not an exhaustive watershed raster extraction."""
import io,json,hashlib
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import numpy as np,pandas as pd,rasterio,requests
from pyproj import Transformer
O=Path(__file__).resolve().parent
P=Path('/wc1/runs/th/thespian-cleanness/postfire_debris_flow/attempts/8190121c8a4b45e1952861e74d909693/predictors/prepared/domain.tif')
with rasterio.open(P) as ds:
 rows,cols=np.where(ds.read(1)==1);xs,ys=rasterio.transform.xy(ds.transform,rows,cols);xs=np.array(xs);ys=np.array(ys);tr=Transformer.from_crs(ds.crs,'EPSG:4326',always_xy=True)
 targets={'SW':(.2,.2),'NW':(.2,.8),'SE':(.8,.2),'NE':(.8,.8),'center':(.5,.5)};points=[]
 for label,(fx,fy) in targets.items():
  x=xs.min()+fx*np.ptp(xs);y=ys.min()+fy*np.ptp(ys);i=np.argmin((xs-x)**2+(ys-y)**2);lon,lat=tr.transform(xs[i],ys[i]);points.append({'label':label,'longitude':lon,'latitude':lat})
def fetch(point):
 label=point['label'];url=f"https://daymet.ornl.gov/single-pixel/api/data?lat={point['latitude']}&lon={point['longitude']}&year=2021";path=O/f'daymet_2021_{label}.csv'
 if not path.exists():
  response=requests.get(url,timeout=90);response.raise_for_status();path.write_text(response.text)
 text=path.read_text();lines=text.splitlines();start=next(i for i,l in enumerate(lines) if l.startswith('year,'));df=pd.read_csv(io.StringIO('\n'.join(lines[start:])));df.columns=[s.replace(' ','') for s in df.columns];df['date']=pd.to_datetime(df.year.astype(int).astype(str)+'-'+df.yday.astype(int).astype(str),format='%Y-%j');df=df[df.date.between('2021-07-25','2021-08-16')][['date','prcp(mm/day)']];df['location']=label
 return df,{**point,'url':url,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
with ThreadPoolExecutor(max_workers=5) as pool: results=list(pool.map(fetch,points))
df=pd.concat([v[0] for v in results]);df.to_csv(O/'spatial_daily_screen.csv',index=False);pivot=df.pivot(index='date',columns='location',values='prcp(mm/day)');pivot.to_csv(O/'spatial_daily_pivot.csv')
(O/'spatial_receipt.json').write_text(json.dumps({'method':'Five domain cells nearest 20/80 percent bounding-box targets and center; points snapped inside basin. Screening only, not all Daymet pixels.','points':[v[1] for v in results],'candidate_totals_mm':pivot.loc['2021-07-30':'2021-08-02'].sum().to_dict(),'later_window_totals_mm':pivot.loc['2021-08-05':'2021-08-12'].sum().to_dict()},indent=2)+'\n');print(pivot.to_string())
