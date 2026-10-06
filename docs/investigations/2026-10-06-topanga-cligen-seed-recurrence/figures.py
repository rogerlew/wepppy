"""Scientific figures from retained seed-level result tables."""
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from study import ROOT

root=ROOT/'analysis'
focal=pd.read_csv(root/'focal-probabilities.csv')
values=pd.read_csv(root/'focal-values.csv')
events=pd.read_parquet(root/'event-pairs.parquet')
spec=[('ksat','1980-02-14','Ksat 20 → 35 mm/h'),('cover','1986-02-15','Ground cover 0.90 → 0.80'),('dense','1986-02-15','Dense management (secondary)')]
fig,axes=plt.subplots(1,3,figsize=(13,4.3),layout='constrained')
for ax,(pair,day,title) in zip(axes,spec):
    v=values[(values.pair==pair)&(values.date==day)].copy()
    p=v.baseline_production_peak_mm_h;q=v.mutant_production_peak_mm_h
    flags=events[(events.pair==pair)&(events.date==day)].groupby('seed').peak_gt25pct_runoff_lt5pct.any()
    flagged=v.seed.map(flags).fillna(False).astype(bool)
    ax.scatter(p[~flagged],q[~flagged],s=20,color='#778899',alpha=.75,label='Below strict screen')
    ax.scatter(p[flagged],q[flagged],s=24,color='#ba4435',alpha=.85,label='Strict screen')
    lim=max(p.max(),q.max())*1.05
    ax.plot([0,lim],[0,lim],color='#555555',linewidth=.8,linestyle='--')
    ax.set(xlim=(0,lim),ylim=(0,lim),xlabel='Baseline peak (mm/h)',ylabel='Mutant peak (mm/h)',title=f'{title}\n{day}')
    record=focal[(focal.pair==pair)&(focal.date==day)&(focal.flag=='peak_gt25pct_runoff_lt5pct')].iloc[0]
    ax.text(.04,.96,f"{int(record.k)}/100 flagged\n95% CI {record.ci95_low:.0%}–{record.ci95_high:.0%}",transform=ax.transAxes,va='top',fontsize=9,bbox={'facecolor':'white','alpha':.9,'edgecolor':'none'})
axes[0].legend(loc='lower right',fontsize=8)
fig.suptitle('Topanga Hill 106: the same observed dates under 100 CLIGEN seeds',fontsize=13)
fig.savefig(root/'focal-seed-scatter.png',dpi=180)
fig.savefig(root/'focal-seed-scatter.svg')
plt.close(fig)

dates=pd.read_csv(root/'date-probabilities.csv')
dates=dates[dates.flag=='peak_gt25pct_runoff_lt5pct']
focus=['1980-02-14','1986-02-15','1995-01-10','2005-01-09','2021-12-30']
ranked=dates.groupby('date').probability.max().sort_values(ascending=False)
selected=sorted(set(focus+[d for d in ranked.index if d not in focus][:7]))
matrix=dates.pivot(index='pair',columns='date',values='probability').reindex(index=['ksat','cover','dense'],columns=selected).fillna(0)
fig,ax=plt.subplots(figsize=(12,3.8),layout='constrained')
im=ax.imshow(matrix.values,vmin=0,vmax=1,cmap='YlOrRd',aspect='auto')
ax.set_xticks(range(len(selected)),selected,rotation=45,ha='right')
ax.set_yticks(range(3),['Ksat pair','Ground-cover pair','Dense management'])
for i in range(3):
    for j in range(len(selected)):
        v=matrix.iloc[i,j];ax.text(j,i,f'{v:.0%}',ha='center',va='center',color='white' if v>.65 else 'black',fontsize=9)
fig.colorbar(im,ax=ax,label='Fraction of 100 seeds flagged',shrink=.8)
ax.set_title('Strict anomaly-screen recurrence by calendar date\nFive focal dates + seven other highest-recurrence dates (exploratory selection)')
fig.savefig(root/'date-recurrence.png',dpi=180)
fig.savefig(root/'date-recurrence.svg')
