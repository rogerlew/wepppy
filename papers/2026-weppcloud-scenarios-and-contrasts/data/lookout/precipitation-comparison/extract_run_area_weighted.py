from pathlib import Path
import numpy as np,pandas as pd,json,sys
p=Path('/geodata/wc1/runs/tr/traveled-calligrapher')
h=pd.read_parquet(p/'watershed/hillslopes.parquet')
weighted=np.zeros(14610);minimum=np.full(14610,np.inf);maximum=np.zeros(14610)
for row in h.itertuples():
 f=p/'climate'/f'_{row.topaz_id}.cli'
 a=np.loadtxt(f,skiprows=15,usecols=(0,1,2,3))
 assert len(a)==14610
 weighted+=a[:,3]*row.area
 minimum=np.minimum(minimum,a[:,3]);maximum=np.maximum(maximum,a[:,3])
d=pd.to_datetime(dict(year=a[:,2],month=a[:,1],day=a[:,0]))
assert list(d)==list(pd.date_range('1986-01-01','2025-12-31'))
pd.DataFrame({'date':d,'wepp_hillslope_area_weighted_mm':weighted/h.area.sum(),'hillslope_min_mm':minimum,'hillslope_max_mm':maximum}).to_csv(sys.stdout,index=False)
