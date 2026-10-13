"""Read generated climates to quantify auxiliary-field risks and PRISM signal retention."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from wepppy.climates.edde.cligen import read_cli
from wepppy.climates.edde.client import sha256,write_json
from workflows import HERE,ROOT
from assess import metrics


def main():
    quality=[]
    for parent in [ROOT/'workflows-full',ROOT/'canadian-full']:
        for manifest in parent.glob('**/climate/manifest.json'):
            state=json.loads(manifest.read_text())
            if state['status']!='complete':continue
            path=manifest.parent/'wepp.cli';frame=read_cli(path)
            quality.append(dict(path=str(path.relative_to(ROOT)),sha256=sha256(path),days=len(frame),
                                negative_precipitation=int((frame.prcp<0).sum()),
                                inverted_temperature=int((frame.tmin>frame.tmax).sum()),
                                dewpoint_above_tmin_days=int((frame.tdew>frame.tmin).sum()),
                                dewpoint_above_tmax_days=int((frame.tdew>frame.tmax).sum()),
                                max_dewpoint_above_tmax_c=float((frame.tdew-frame.tmax).max()),
                                min_duration_wet_h=float(frame.loc[frame.prcp>0,'dur'].min()),
                                maximum_source_error=state['maximum_source_error'],
                                source_wet_days=state['source_wet_days'],cli_wet_days=state['cli_wet_days']))
    write_json(HERE/'generated-climate-quality.json',quality)
    results=[];seasonal=[]
    for model,scenario in [('WRF-MPI','SSP2-4.5'),('WRF-Nor','SSP2-4.5'),('WRF-MPI','SSP3-7.0')]:
        root=ROOT/'workflows-full'/model
        for group in ['apostolic-saw','cryptic-beechnut']:
            historical=root/'Historical'/group/'climate'
            future=root/scenario/group/'climate'
            if not (historical/'wepp.cli').exists():continue
            bh,bf=read_cli(historical/'wepp.cli'),read_cli(future/'wepp.cli')
            for target in sorted(future.glob('*-prism.cli')):
                htarget=historical/target.name
                if not htarget.exists():continue
                rh,rf=read_cli(htarget),read_cli(target)
                for season, months in [('DJF',[12,1,2]),('MAM',[3,4,5]),('JJA',[6,7,8]),('SON',[9,10,11])]:
                    summaries = {}
                    for label, frame in [('base_historical',bh),('base_future',bf),('prism_historical',rh),('prism_future',rf)]:
                        subset=frame[frame.index.month.isin(months)].rename(columns={'prcp':'prday'})
                        summaries[label]=metrics(subset)
                    row=dict(model=model,scenario=scenario,group=group,target=target.stem,season=season)
                    for metric in ['wet_fraction_1mm','max_dry_spell_days','max_wet_spell_days','wet_p95_mm','daily_p99_mm','mean_annual_max_p_mm','maximum_p_mm']:
                        for label, values in summaries.items():row[f'{label}_{metric}']=values[metric]
                        row[f'base_change_{metric}']=summaries['base_future'][metric]-summaries['base_historical'][metric]
                        row[f'prism_change_{metric}']=summaries['prism_future'][metric]-summaries['prism_historical'][metric]
                    seasonal.append(row)
                for month in range(1,13):
                    a,b=bh[bh.index.month==month],bf[bf.index.month==month]
                    x,y=rh[rh.index.month==month],rf[rf.index.month==month]
                    if a.prcp.sum()<=0 or x.prcp.sum()<=0:raise ValueError('Undefined monthly signal')
                    base_ratio=float(b.prcp.sum()/a.prcp.sum())
                    revised_ratio=float(y.prcp.sum()/x.prcp.sum())
                    tx_error=float((y.tmax.mean()-x.tmax.mean())-(b.tmax.mean()-a.tmax.mean()))
                    tn_error=float((y.tmin.mean()-x.tmin.mean())-(b.tmin.mean()-a.tmin.mean()))
                    results.append(dict(model=model,scenario=scenario,group=group,target=target.stem,month=month,
                                        base_p_ratio=base_ratio,revised_p_ratio=revised_ratio,
                                        p_ratio_error=revised_ratio-base_ratio,
                                        tmax_signal_error_c=tx_error,tmin_signal_error_c=tn_error))
    pd.DataFrame(results).to_csv(HERE/'prism-future-signal.csv',index=False)
    pd.DataFrame(seasonal).to_csv(HERE/'prism-seasonal-extremes.csv',index=False)
    print('Climate files',len(quality),'paired monthly PRISM checks',len(results))


if __name__=='__main__':main()
