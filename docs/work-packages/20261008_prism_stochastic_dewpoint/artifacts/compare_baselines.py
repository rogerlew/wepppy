#!/usr/bin/env python3
"""Compare precipitation targets and paired ET with frozen earlier experiments."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

import study

HERE = Path(__file__).resolve().parent
PREVIOUS = HERE.parents[1] / '20261008_stochastic_dewpoint/artifacts'


def main():
    m = study.manifest()
    normal = pd.read_csv(HERE/'normals.csv', skiprows=10)
    parameters = pd.read_csv(HERE/'localization-readback.csv')
    previous = pd.read_csv(PREVIOUS/'station-site-mismatch.csv').set_index('site')
    current = pd.read_csv(HERE/'station-site-mismatch.csv').set_index('site')
    detailed = []
    for s in m['sites']:
        for seed in study.SEEDS:
            _, _, values, dates = study.climate(study.ROOT/'climates'/s['site']/str(seed)/'output.cli')
            frame = pd.DataFrame(dict(p=values[:,3],tmax=values[:,7],tmin=values[:,8],td=values[:,12]),index=dates)
            for period, data in [('full',frame),('assessment',frame.loc['2016':'2022'])]:
                annual = data.p.resample('YS').sum()
                climate = data.groupby(data.index.month).mean()
                precip = data.p.resample('MS').sum().groupby(lambda x:x.month).mean()
                target = parameters[parameters.site == s['site']].set_index('month')
                for month in range(1,13):
                    detailed.append(dict(site=s['site'],seed=seed,period=period,month=month,precip_mm=precip.loc[month],tmax_c=climate.loc[month,'tmax'],tmin_c=climate.loc[month,'tmin'],td_c=climate.loc[month,'td'],prism_p_mm=target.loc[month,'prism_p_mm'],prism_tmin_c=target.loc[month,'prism_tmin_c'],prism_tmax_c=target.loc[month,'prism_tmax_c'],prism_tdmean_c=target.loc[month,'prism_tdmean_c']))
    detailed=pd.DataFrame(detailed)
    detailed.to_csv(HERE/'generated-monthly-climatology.csv',index=False)
    comparisons=[]
    for s in m['sites']:
        site=s['site']; gen=detailed[detailed.site == site]
        target=parameters[parameters.site == site]
        normal_annual=float(normal[(normal.Name == site)&(normal.Date == 'Annual')]['ppt (mm)'].iloc[0])
        expected=target.prism_p_mm.sum()
        full=gen[gen.period == 'full'].groupby('seed').precip_mm.sum()
        assessment=gen[gen.period == 'assessment'].groupby('seed').precip_mm.sum()
        g=current.loc[site,'gridmet_hill_p_mm_y']
        comparisons.append(dict(site=site,watershed=s['watershed'],prism_annual_normal_mm=normal_annual,prism_monthly_sum_mm=expected,par_implied_p_mm=target.par_implied_p_mm.sum(),full_generated_p_mm=full.mean(),full_seed_min_mm=full.min(),full_seed_max_mm=full.max(),assessment_generated_p_mm=assessment.mean(),assessment_seed_min_mm=assessment.min(),assessment_seed_max_mm=assessment.max(),station_baseline_p_mm=previous.loc[site,'station_p_mm_y'],gridmet_hill_p_mm=g,full_to_prism_ratio=full.mean()/expected,assessment_to_prism_ratio=assessment.mean()/expected,assessment_to_gridmet_ratio=assessment.mean()/g,baseline_to_gridmet_ratio=previous.loc[site,'station_p_mm_y']/g,gridmet_absolute_error_improvement_mm=abs(previous.loc[site,'station_p_mm_y']-g)-abs(assessment.mean()-g)))
    comparisons=pd.DataFrame(comparisons)
    comparisons.to_csv(HERE/'precipitation-comparison.csv',index=False)
    metrics=pd.read_csv(HERE/'comparison-metrics.csv')
    prior=pd.read_csv(PREVIOUS/'comparison-metrics.csv')
    merged=metrics.merge(prior,on=['site','arm','model','seed'],suffixes=('_prism','_station'),validate='one_to_one')
    merged.to_csv(HERE/'baseline-et-comparison.csv',index=False)
    stats={}
    for scope in ['pooled','seedwise']:
        sub=merged[merged.seed == 'pooled'] if scope=='pooled' else merged[merged.seed != 'pooled']
        stats[scope]={arm:{metric:int((g[metric+'_prism']<g[metric+'_station']).sum()) for metric in ['cycle_mae_mm','cycle_rmse_mm','monthly_distribution_distance_mm']} for arm,g in sub.groupby('arm')}
    stats['precipitation_closer_to_gridmet_sites']=int((comparisons.gridmet_absolute_error_improvement_mm>0).sum())
    stats['generation_diagnostics']={'affected':sum(g['unmet_random_deviate_quality_targets']>0 for g in m['generations']),'total':len(m['generations']),'unmet_targets':sum(g['unmet_random_deviate_quality_targets'] for g in m['generations'])}
    study.save(HERE/'baseline-conclusions.json',stats)
    print(comparisons[['site','prism_monthly_sum_mm','full_generated_p_mm','assessment_generated_p_mm','gridmet_hill_p_mm','assessment_to_gridmet_ratio']].to_string(index=False))
    print(json.dumps(stats,indent=2))
    plot_precip(comparisons)


def plot_precip(df):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,3,figsize=(14,5),constrained_layout=True,sharey=True)
    for ax,(_,g) in zip(axes,df.groupby('watershed',sort=False)):
        x=np.arange(len(g))
        for offset,key,label,color in [(-.27,'station_baseline_p_mm','Station stochastic','#94a3b8'),(-.09,'assessment_generated_p_mm','PRISM stochastic','#2563eb'),(.09,'prism_monthly_sum_mm','PRISM 1991–2020 normal','#16a34a'),(.27,'gridmet_hill_p_mm','GridMET 2016–2022','#ea580c')]:
            ax.bar(x+offset,g[key],width=.18,label=label,color=color)
        mean=g.assessment_generated_p_mm.to_numpy()
        ax.errorbar(x-.09,mean,yerr=np.vstack([mean-g.assessment_seed_min_mm.to_numpy(),g.assessment_seed_max_mm.to_numpy()-mean]),fmt='none',ecolor='black',capsize=2,linewidth=.8)
        ax.set_xticks(x,[f"H{s.rsplit('-h',1)[1]}" for s in g.site])
        ax.set_title(g.watershed.iloc[0]);ax.set_ylabel('Precipitation (mm/year)');ax.grid(axis='y',alpha=.2)
    axes[0].legend(fontsize=8)
    fig.suptitle('PRISM localization corrects much of the station precipitation deficit\nStochastic bars: ten-seed assessment mean; whiskers: seed range. Reference periods differ.')
    fig.savefig(HERE/'precipitation-comparison.png',dpi=160)
    fig.savefig(HERE/'precipitation-comparison.svg')
    plt.close(fig)


if __name__=='__main__':
    main()
