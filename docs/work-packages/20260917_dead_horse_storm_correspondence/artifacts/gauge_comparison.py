import io,json,math,hashlib
from pathlib import Path
import requests,numpy as np,pandas as pd,rasterio
from pyproj import Transformer
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
O=Path(__file__).resolve().parent
m=pd.read_csv(O/'1a_Storm_matrix_2021_gr1mmhr.csv');m['date']=pd.to_datetime(m.Date,format='%m/%d/%y');col='GCEC2_EastForkDeadHorse 15-minute Intensity (mm/h)'
g=m[['date',col,'Debris Flow (1 = debris flow, 0 = no debris flow)']].rename(columns={col:'gauge_I15_mm_h','Debris Flow (1 = debris flow, 0 = no debris flow)':'regional_debris_flow_flag'})
g=g[g.date.between('2021-07-25','2021-08-16')].copy()
lon,lat=-107.197311,39.628533
url=f'https://daymet.ornl.gov/single-pixel/api/data?lat={lat}&lon={lon}&year=2021';path=O/'daymet_2021_eastfork_gauge.csv'
if not path.exists():
 r=requests.get(url,timeout=90);r.raise_for_status();path.write_bytes(r.content)
lines=path.read_text().splitlines();start=next(i for i,l in enumerate(lines) if l.startswith('year,'));d=pd.read_csv(io.StringIO('\n'.join(lines[start:])));d.columns=[s.replace(' ','') for s in d.columns];d['date']=pd.to_datetime(d.year.astype(int).astype(str)+'-'+d.yday.astype(int).astype(str),format='%Y-%j')
g=g.merge(d[['date','prcp(mm/day)']].rename(columns={'prcp(mm/day)':'Daymet_at_gauge_daily_mm'}),on='date',how='left')
e=pd.read_csv(O/'events_context.csv',parse_dates=['date']);e=e[e.duration_minutes==15]
for label in ['Daymet','GridMET']:
 sub=e[e.source==label][['date','intensity_mm_per_hour','probability']].rename(columns={'intensity_mm_per_hour':f'{label}_CLI_I15_mm_h','probability':f'{label}_CLI_M3'})
 g=g.merge(sub,on='date',how='left')
# Missing event row means no wet event, not an absent gauge observation.
for c in ['Daymet_CLI_I15_mm_h','GridMET_CLI_I15_mm_h']:g[c]=g[c].fillna(0)
manifest=json.loads(Path('/wc1/runs/th/thespian-cleanness/postfire_debris_flow/attempts/8190121c8a4b45e1952861e74d909693/results/manifest.json').read_text());T,F,S=[manifest['predictor_snapshot']['predictors'][k]['value'] for k in ['T','F','S']]
g['M3_using_gauge_I15']=1/(1+np.exp(-(-3.71+g.gauge_I15_mm_h/4*(.32*T+.33*F+.47*S))))
g.to_csv(O/'gauge_cli_comparison.csv',index=False)
with rasterio.open('/wc1/runs/th/thespian-cleanness/postfire_debris_flow/attempts/8190121c8a4b45e1952861e74d909693/predictors/prepared/domain.tif') as ds:
 x,y=Transformer.from_crs('EPSG:4326',ds.crs,always_xy=True).transform(lon,lat);inside=int(next(ds.sample([(x,y)]))[0])==1
summary={'gauge':'GCEC2_EastForkDeadHorse','coordinates':[lon,lat],'inside_modeled_basin':inside,'daymet_query':url,'daymet_raw_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'rows':json.loads(g.to_json(orient='records',date_format='iso')),'interpretation':'Gauge-forced M3 probabilities use the unchanged whole-basin predictors; illustrative forcing comparison, not a rerun or independent validation of basin-scale M3. Regional flag is not a Dead Horse Creek event label. Missing gauge entries remain NaN.'}
(O/'gauge_comparison.json').write_text(json.dumps(summary,indent=2)+'\n')
fig,ax=plt.subplots(figsize=(10,4));ax.plot(g.date,g.gauge_I15_mm_h,'o-',label='East Fork Deadhorse gauge (measured)',color='black');ax.plot(g.date,g.Daymet_CLI_I15_mm_h,'s--',label='Daymet CLI (generated)');ax.plot(g.date,g.GridMET_CLI_I15_mm_h,'^--',label='GridMET CLI (generated)');ax.axhline(30.116761,color='grey',linestyle=':',label='Whole-basin M3 P50');ax.axvspan(pd.Timestamp('2021-07-30'),pd.Timestamp('2021-08-02 23:59'),alpha=.12,color='green');ax.set(ylabel='Peak 15-minute intensity (mm/hour)',title='Dead Horse Creek: measured vs. generated rainfall peaks');ax.legend(fontsize=8);fig.autofmt_xdate();fig.tight_layout();fig.savefig(O/'gauge_cli_comparison.png',dpi=160)
print('Gauge inside basin:',inside);print(g.to_string(index=False))
