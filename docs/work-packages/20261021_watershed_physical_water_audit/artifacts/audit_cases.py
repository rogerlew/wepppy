"""Independent printed-output accounting; residual screens do not assume missing stores zero."""
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd

COLS='ofe day year P RM Q Ep Es Er Dp UpStrmQ SubRIn latqcc Soil frozwt Snow QOFE Tile Irr Area SoilWaterTotal ProfileDepth Por FC WP'.split()

def wat(path):
    lines=path.read_text().splitlines()
    start=next(i for i,s in enumerate(lines) if len(s.split())==len(COLS) and s.split()[0].isdigit())
    return pd.read_csv(path,sep=r'\s+',skiprows=start,names=COLS)

def passes(path):
    records=[]; current=None
    for s in path.read_text().splitlines()[6:]:
        if s.startswith(('EVENT','SUBEVENT','NO EVENT')):
            if current is not None: records.append(current)
            kind=s[:8].strip();vals=s[8:].split()
            current=[kind,int(vals[0]),int(vals[1]),[float(v) for v in vals[2:]]]
        elif s.startswith('SRC3'):
            if current is not None: records.append(current);current=None
        elif current is not None and s.startswith(' '):
            current[3].extend(float(x) for x in s.split())
    if current is not None: records.append(current)
    result=[]
    for kind,y,d,v in records:
        if kind=='EVENT':
            assert len(v)==24,(y,d,len(v))
            q,l,t,b,deep=v[4],v[6],v[8],v[-2],v[-1]
        elif kind=='SUBEVENT':
            assert len(v)==6,(y,d,len(v))
            q,l,t,b,deep=0.,v[1],v[3],v[4],v[5]
        else:
            assert len(v)==2,(y,d,len(v))
            q,l,t,b,deep=0.,0.,0.,v[0],v[1]
        result.append((y,d,kind,q,l,t,b,deep))
    return pd.DataFrame(result,columns=['year','day','kind','surface','lateral','tile','baseflow','deepseep']).set_index(['year','day'])

def metrics(values):
    a=np.asarray(values,dtype=float)
    return dict(sum=float(a.sum()),absolute_sum=float(np.abs(a).sum()),max_abs=float(np.abs(a).max()),mean=float(a.mean()))

def audit(case):
    w=wat(case/'output/H1.wat.dat')
    assert not w.duplicated(['year','day','ofe']).any()
    assert np.isfinite(w.to_numpy()).all()
    n=int(w.ofe.max()); area=w.groupby('ofe').Area.first(); total=area.sum()
    assert w.groupby(['year','day']).size().eq(n).all()
    w=w.sort_values(['year','day','ofe'])
    terminal=w[w.ofe==n].set_index(['year','day'])
    p=passes(case/'output/H1.pass.dat')
    assert p.index.equals(terminal.index) and not p.index.duplicated().any()
    expected=pd.MultiIndex.from_tuples([(d.year,d.dayofyear) for d in pd.date_range('1980-01-01','2023-12-31')],names=['year','day'])
    assert p.index.equals(expected)
    ofe=[]
    for i in range(1,n+1):
        a=w[w.ofe==i].set_index(['year','day']);cum=area.loc[:i].sum()
        # Outgoing boundary QOFE volume vs cumulative-area Q volume.
        relation=(a.QOFE*a.Area-a.Q*cum)/1000
        soil_screen=(a.P+a.Irr+a.UpStrmQ+a.SubRIn-a.Ep-a.Es-a.Er-a.Dp-a.QOFE-a.latqcc-a.Tile)*a.Area/1000
        storage=(a.SoilWaterTotal+a.Snow)*a.Area/1000
        residual=soil_screen.iloc[1:]-storage.diff().iloc[1:]
        row=dict(ofe=i,area_m2=float(area[i]),Q_QOFE_volume_difference_m3=metrics(relation),soil_snow_screen_excluding_unknown_interception_m3=metrics(residual))
        if i>1:
            up=w[w.ofe==i-1].set_index(['year','day'])
            row['surface_transfer_difference_m3']=metrics((a.UpStrmQ*a.Area-up.QOFE*up.Area)/1000)
            row['lateral_transfer_difference_m3']=metrics((a.SubRIn*a.Area-up.latqcc*up.Area)/1000)
        ofe.append(row)
    v=w.copy()
    for k in ['P','Ep','Es','Er','Dp','SoilWaterTotal','Snow','Irr']:
        v[k]=v[k]*v.Area/1000
    hill=v.groupby(['year','day'])[['P','Ep','Es','Er','Dp','SoilWaterTotal','Snow','Irr']].sum()
    hill['Q']=terminal.Q*total/1000
    hill['lateral']=terminal.latqcc*terminal.Area/1000
    hill['tile']=terminal.Tile*terminal.Area/1000
    hill['residual_screen']=hill.P+hill.Irr-hill.Ep-hill.Es-hill.Er-hill.Dp-hill.Q-hill.lateral-hill.tile-(hill.SoilWaterTotal+hill.Snow).diff()
    event=p.kind.eq('EVENT');sub=p.kind.ne('NO EVENT')
    # GW uses prior-day withdrawals; reconstruct recurrence independently from WAT Dp.
    gw=0.;prior_b=0.;prior_d=0.;errors=[]
    for idx,r in p.iterrows():
        gw=gw+hill.loc[idx,'Dp']-prior_b-prior_d
        errors.append(r.baseflow-.04*gw)
        prior_b=r.baseflow;prior_d=r.deepseep
    out=dict(case=case.name,days=len(p),ofes=ofe,annual_mm={k:float(hill[k].sum()/total*1000/44) for k in ['P','Ep','Es','Er','Dp','Q','lateral','tile']},
        hill_soil_snow_screen_m3=metrics(hill.residual_screen.iloc[1:]),
        event_surface_difference_m3=metrics((hill.Q-p.surface)[event]),
        delivered_lateral_difference_m3=metrics((hill.lateral-p.lateral)[sub]),
        omitted_surface_m3=float(hill.Q[~event].sum()),omitted_lateral_m3=float(hill.lateral[~sub].sum()),
        pass_totals_m3=p[['surface','lateral','tile','baseflow','deepseep']].sum().to_dict(),
        gw_recurrence_difference_m3=metrics(errors),reconstructed_gw_end_before_current_withdrawals_m3=gw)
    chpath=case/'runs/chanwb.out'
    lines=chpath.read_text().splitlines();start=next(i for i,s in enumerate(lines) if len(s.split())==10 and s.split()[0].isdigit())
    ch=pd.read_csv(chpath,sep=r'\s+',skiprows=start,names=['year','day','element','channel','inflow','outflow','storage','baseflow','loss','balance']).set_index(['year','day'])
    assert ch.index.equals(p.index)
    out['channel_totals_m3']=ch[['inflow','outflow','loss','balance']].sum().to_dict()
    out['channel_end_storage_m3']=float(ch.storage.iloc[-1])
    out['channel_recomputed_publication_residual_m3']=metrics(ch.inflow-ch.outflow-ch.loss-ch.storage.diff().fillna(ch.storage.iloc[0]))
    out['channel_input_minus_pass_m3']=metrics(ch.inflow-p.surface-p.lateral-p.baseflow)
    chout=case/'runs/chan.out';lines=chout.read_text().splitlines();start=next(i for i,s in enumerate(lines) if len(s.split())==6 and s.split()[0].isdigit())
    hydro=pd.read_csv(chout,sep=r'\s+',skiprows=start,names=['year','day','element','channel','time','q'])
    # Right-rectangle integral covers every printed interval; compare trapezoids too.
    hydro['dt']=hydro.groupby(['year','day']).time.diff().fillna(hydro.time)
    assert hydro.dt.gt(0).all() and hydro.groupby(['year','day']).time.last().eq(86400).all()
    hydro['vol']=hydro.q*hydro.dt
    integrated=hydro.groupby(['year','day']).vol.sum()
    out['hydrograph_rectangle_minus_published_m3']=metrics(integrated-ch.outflow)
    out['integrated_hydrograph_m3']=float(integrated.sum())
    joined=hill.join(p.drop(columns='kind'),rsuffix='_pass').join(ch[['inflow','outflow','storage','loss']])
    joined.to_csv(case/'water-ledger.csv')
    (case/'audit.json').write_text(json.dumps(out,indent=2)+'\n')
    return out

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args()
    results=[]
    for case in sorted(a.root.iterdir()):
        if case.is_dir() and (case/'execution.json').exists():
            e=json.loads((case/'execution.json').read_text())
            if len(e['results'])==2 and all(r['success'] for r in e['results']):
                result=audit(case);results.append(result);print(case.name,result['annual_mm'],flush=True)
    (a.root/'audit.json').write_text(json.dumps(results,indent=2)+'\n')
