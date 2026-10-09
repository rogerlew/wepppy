#!/usr/bin/env python3
"""Summarize RRINIT response and rank changes without imposing acceptance gates."""
from itertools import product
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from run_sensitivity import ROOT, matrix, save


def read_case(row):
    folder=ROOT/'cases'/row['case']
    p=pd.read_parquet(folder/'peaks.parquet')
    e=pd.read_parquet(folder/'events.parquet')
    p['sediment_kg']=p[[f'sedcon_{i}' for i in range(1,6)]].sum(axis=1)*p.runvol
    return p,e


def percent(value, baseline):
    return 100*(value/baseline-1) if baseline != 0 else np.nan


def main():
    execution=json.loads((ROOT/'execution.json').read_text())
    assert execution['complete']==execution['expected']==896 and not execution['failures']
    out=ROOT/'analysis';out.mkdir(exist_ok=False)
    f=pd.read_csv(ROOT/'case-results.csv')
    assert len(f)==896 and not f.duplicated('case').any()
    refs={(r['profile'],r['id']):r for r in f.to_dict('records') if r['reference']}
    assert len(refs)==192
    reference_data={key:read_case(row) for key,row in refs.items()}
    rows=[];annual=[]
    for row in f.to_dict('records'):
        p,e=read_case(row)
        baseline=refs[row['profile'],row['id']]
        bp,be=reference_data[row['profile'],row['id']]
        paired=p.merge(bp,on=['year','julian'],how='outer',suffixes=('_trial','_reference'),indicator=True,validate='one_to_one')
        matched=paired.loc[paired._merge.eq('both')]
        paired_e=e.merge(be,on=['year','julian'],how='outer',suffixes=('_trial','_reference'),indicator=True,validate='one_to_one')
        sediment=float(p.sediment_kg.sum());base_sediment=float(bp.sediment_kg.sum())
        first=float(p.loc[p.year.eq(2000),'sediment_kg'].sum())
        first_ref=float(bp.loc[bp.year.eq(2000),'sediment_kg'].sum())
        rr=pd.read_parquet(ROOT/'cases'/row['case']/'soil.parquet',columns=['year','julian','Rough'])
        slope=.2 if row['profile']=='gentle' else .385601965
        rough=rr.Rough.to_numpy()/1000
        potential=np.maximum(0,.112*rough+3.1*rough**2-1.2*rough*slope)*1000
        geometry=(ROOT/'cases'/row['case']/'runs'/f'p{row["id"]}.slp').read_text().splitlines()
        area=float(geometry[2].split()[1])*float(geometry[3].split()[1])
        gap=row['pass_surface_m3']-row['runoff_mm']*area/1000
        base_gap=baseline['pass_surface_m3']-baseline['runoff_mm']*area/1000
        row.update(runoff_change_pct=percent(row['pass_surface_m3'],baseline['pass_surface_m3']),
            runoff_delta_mm=row['runoff_mm']-baseline['runoff_mm'],
            sediment_delta_kg_m=row['sediment_kg_m']-baseline['sediment_kg_m'],
            pass_sediment_kg=sediment,pass_sediment_delta_kg=sediment-base_sediment,
            pass_sediment_change_pct=percent(sediment,base_sediment),
            first_year_pass_sediment_delta_kg=first-first_ref,
            later_pass_sediment_delta_kg=sediment-base_sediment-(first-first_ref),
            peak_max_change_pct=percent(row['peak_max_m3_s'],baseline['peak_max_m3_s']),
            paired_peak_events=len(matched),trial_only_peak_events=int(paired._merge.eq('left_only').sum()),
            reference_only_peak_events=int(paired._merge.eq('right_only').sum()),
            max_paired_peak_delta_m3_s=float((matched.peakro_trial-matched.peakro_reference).abs().max()) if len(matched) else 0.,
            paired_ebe_events=int(paired_e._merge.eq('both').sum()),
            trial_only_ebe_events=int(paired_e._merge.eq('left_only').sum()),
            reference_only_ebe_events=int(paired_e._merge.eq('right_only').sum()),
            input_area_m2=area,pass_minus_ebe_volume_m3=gap,
            pass_minus_ebe_gap_change_m3=gap-base_gap,
            potential_storage_max_mm=float(potential.max()),
            potential_storage_positive_days=int((potential>0).sum()),
            reported_rrc_scope='daily printed SOIL Rough; derived storage diagnostic, not an observed ponding trace')
        rows.append(row)
        for year in range(2000,2100):
            py=p.loc[p.year.eq(year)];ey=e.loc[e.year.eq(year)]
            annual.append(dict(case=row['case'],year=year,runoff_mm=float(ey.Runoff.sum()),
                sediment_kg_m=float(ey['Sed.Del'].sum()),pass_sediment_kg=float(py.sediment_kg.sum()),
                surface_m3=float(py.runvol.sum()),peak_max_m3_s=float(py.peakro.max()) if len(py) else 0.))
    f=pd.DataFrame(rows)
    f.to_csv(out/'responses.csv',index=False)
    pd.DataFrame(annual).to_parquet(out/'annual.parquet',index=False,compression='zstd')
    event_extremes=[]
    for row in f.nlargest(12,'max_paired_peak_delta_m3_s').to_dict('records'):
        p,_=read_case(row);bp,_=reference_data[row['profile'],row['id']]
        pairs=p.merge(bp,on=['year','julian'],suffixes=('_trial','_reference'),validate='one_to_one')
        pairs['delta_m3_s']=pairs.peakro_trial-pairs.peakro_reference
        for event in pairs.loc[pairs.delta_m3_s.abs().nlargest(3).index].to_dict('records'):
            event_extremes.append(dict(case=row['case'],year=event['year'],julian=event['julian'],
                reference_peak=event['peakro_reference'],trial_peak=event['peakro_trial'],
                delta_m3_s=event['delta_m3_s']))
    pd.DataFrame(event_extremes).to_csv(out/'largest-event-changes.csv',index=False)

    rankings=[]
    for profile,texture,veg,level in product(['steep','gentle'],matrix.TEXTURES,matrix.VEG_TYPES,['current',.006,.01,.02,.04]):
        group=f.loc[f.profile.eq(profile)&f.texture.eq(texture)&f.vegetation.eq(veg)]
        group=group.loc[group.reference] if level=='current' else group.loc[group.rrinit_m.eq(level)]
        group=group.sort_values('severity')
        assert len(group)==4 and list(group.severity)==[0,1,2,3]
        for metric in ['runoff_mm','pass_sediment_kg','peak_max_m3_s']:
            values=group[metric].to_numpy()
            rankings.append(dict(profile=profile,texture=texture,vegetation=veg,level=str(level),
                metric=metric,unburned=values[0],low=values[1],moderate=values[2],high=values[3],
                nondecreasing=bool((np.diff(values)>=0).all()),
                low_ge_unburned=bool(values[1]>=values[0]),moderate_ge_low=bool(values[2]>=values[1]),
                high_ge_moderate=bool(values[3]>=values[2])))
    ranks=pd.DataFrame(rankings);ranks.to_csv(out/'rankings.csv',index=False)

    # Complete matrix coverage in one figure; no normalization by zero sediment.
    fig,axes=plt.subplots(3,2,figsize=(20,11),layout='constrained')
    columns=list(product(matrix.VEG_TYPES,range(4)))
    short={'forest':'F','deciduous forest':'D','mixed forest':'M','shrub':'S','tall grass':'G','young forest':'Y'}
    metrics=[('runoff_change_pct','Maximum absolute PASS surface-volume change (%)',1),
             ('sediment_delta_kg_m','Maximum absolute sediment change (kg/m/year)',.01),
             ('peak_max_change_pct','Maximum absolute change in maximum peak (%)',1)]
    for j,profile in enumerate(['steep','gentle']):
        for i,(metric,title,scale) in enumerate(metrics):
            grid=np.array([[f.loc[f.profile.eq(profile)&f.texture.eq(t)&f.vegetation.eq(v)&f.severity.eq(s),metric].abs().max()*scale
                            for v,s in columns] for t in matrix.TEXTURES])
            ax=axes[i,j];im=ax.imshow(np.log1p(grid),aspect='auto',cmap='viridis')
            ax.set_title(f'{profile.title()} profile: {title}',fontsize=11)
            ax.set_yticks(range(4),matrix.TEXTURES,fontsize=9)
            ax.set_xticks(range(24),[f'{short[v]}{s}' for v,s in columns],fontsize=8)
            for y in range(4):
                for x in range(24):
                    ax.text(x,y,f'{grid[y,x]:.2g}',ha='center',va='center',fontsize=6,color='white' if np.log1p(grid[y,x])<im.norm.vmax*.6 else 'black')
            bar=fig.colorbar(im,ax=ax,shrink=.8)
            bar.set_label('Color = ln(1 + displayed magnitude)',fontsize=8)
    fig.suptitle('RRINIT sensitivity: WEPP 261009, 896 cases, synthetic 2000-2099 climate\nF forest; D deciduous; M mixed; S shrub; G tall grass; Y young forest. Severity 0/1/2/3.',fontsize=14)
    fig.savefig(out/'response-matrix.png',dpi=180);plt.close(fig)

    fig,axes=plt.subplots(2,2,figsize=(13,9),layout='constrained')
    for ax,texture in zip(axes.flat,matrix.TEXTURES):
        for veg in ['forest','young forest','shrub','tall grass']:
            row=f.loc[f.profile.eq('gentle')&f.texture.eq(texture)&f.vegetation.eq(veg)&f.severity.eq(0)&f.reference].iloc[0]
            s=pd.read_parquet(ROOT/'cases'/row['case']/'soil.parquet')
            ax.plot(np.arange(1,len(s)+1),s.Rough/10,label=f'{veg}: input {row.rrinit_m*100:g} cm',lw=1)
        ax.axhline(1.14/23*100,color='black',ls=':',lw=.8,label='Interrill cutoff')
        ax.set_xscale('log');ax.set_title(texture);ax.set_xlabel('Simulation day (log scale)');ax.set_ylabel('Effective random roughness (cm)')
        ax.legend(fontsize=8);ax.grid(alpha=.2)
    fig.suptitle('Reported model-state trajectory: current unburned controls, 20% profile')
    fig.savefig(out/'effective-roughness.png',dpi=180);plt.close(fig)
    altered=f.loc[~f.reference]
    extremes={metric:altered.loc[altered[metric].abs().nlargest(12).index,
        ['case','texture','vegetation','severity','profile','rrinit_m',metric]].to_dict('records')
        for metric in ['runoff_change_pct','sediment_delta_kg_m','pass_sediment_delta_kg','peak_max_change_pct']}
    summary=dict(cases=len(f),references=int(f.reference.sum()),mutated_cases=len(altered),years=[2000,2099],
        max_absolute_runoff_change_pct=float(altered.runoff_change_pct.abs().max()),
        max_absolute_sediment_delta_kg_m=float(altered.sediment_delta_kg_m.abs().max()),
        max_absolute_peak_change_pct=float(altered.peak_max_change_pct.abs().max()),
        zero_reported_runoff_change=int(altered.runoff_delta_mm.eq(0).sum()),
        zero_reported_sediment_change=int(altered.sediment_delta_kg_m.eq(0).sum()),
        rankings=[dict(level=str(level),metric=metric,nondecreasing=int(g.nondecreasing.sum()),total=len(g))
                  for (level,metric),g in ranks.groupby(['level','metric'])],extremes=extremes,
        note='Descriptive sensitivity and weak rank order, not automatic acceptance; production defaults unchanged.')
    save(out/'summary.json',summary)
    print(json.dumps(summary,indent=2),flush=True)


if __name__=='__main__':
    main()
