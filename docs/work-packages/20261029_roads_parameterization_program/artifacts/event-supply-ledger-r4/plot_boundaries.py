"""Original figure: all43 declared small-reference misses, exact-R4 paired boundaries."""
from pathlib import Path
import hashlib
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

ROOT=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
rows=json.loads((ROOT/'case-summary.json').read_text())
rows=sorted([r for r in rows if r['group']=='small_exceedance'],key=lambda r:(r['climate'],r['soil'],r['surface'],r['traffic']))
assert len(rows)==43 and all(r['design']=='outunrut' for r in rows)
plt.rcParams.update({'font.size':8,'svg.fonttype':'none','axes.spines.top':False,'axes.spines.right':False})
fig,axes=plt.subplots(1,3,figsize=(13,13.5),sharey=True,gridspec_kw={'wspace':.10})
colors={'legacy':'#0072B2','modern':'#D55E00'}
labels=[f"{r['climate'][:3].title()}  {r['soil']}  {r['surface'][0].upper()}/{r['traffic'][0].upper()}" for r in rows]
points=[]
for i,r in enumerate(rows):
    row=dict(case_id=r['case_id'],climate=r['climate'],material=r['soil'],surface=r['surface'],traffic=r['traffic'],values={})
    for j,ax in enumerate(axes):
        a=r['lanes']['legacy']['ofes'][j]['sediment_out_kg'];b=r['lanes']['modern']['ofes'][j]['sediment_out_kg'];assert min(a,b)>=0
        ax.plot([a,b],[i,i],color='#999999',lw=.8,zorder=1)
        ax.scatter(a,i,s=25,marker='o',facecolors='white',edgecolors=colors['legacy'],linewidths=1.2,zorder=3)
        ax.scatter(b,i,s=20,marker='x',color=colors['modern'],linewidths=1.4,zorder=4)
        row['values'][('road','fill','buffer')[j]]=dict(legacy_kg_yr=a,modern_kg_yr=b)
    points.append(row)
for ax,title in zip(axes,('Road boundary','Fill boundary / buffer inflow','Buffer boundary / outlet')):
    ax.set_title(title,pad=12,fontweight='bold');ax.set_xlabel('Reported boundary sediment (kg/year)')
    ax.grid(axis='x',color='#e3e3e3',linewidth=.6);ax.set_axisbelow(True);ax.axvline(0,color='#999999',lw=.7)
    ax.set_ylim(42.8,-.8);ax.set_yticks(range(43));ax.tick_params(axis='y',length=0)
    previous=None
    for i,r in enumerate(rows):
        if previous and previous!=r['climate']:ax.axhline(i-.5,color='#aaaaaa',lw=.8)
        previous=r['climate']
axes[0].set_yticklabels(labels,fontsize=8)
legend=[Line2D([0],[0],marker='o',color='none',markeredgecolor=colors['legacy'],markerfacecolor='white',label='Legacy whole soil profile'),Line2D([0],[0],marker='x',color='none',markeredgecolor=colors['modern'],label='Generated soil profile')]
fig.legend(handles=legend,loc='lower center',bbox_to_anchor=(.58,.944),ncol=2,frameon=False,fontsize=10)
fig.suptitle('Small-reference misses: compare incoming sediment with downstream export',x=.57,y=.992,fontsize=13,fontweight='bold')
fig.text(.57,.965,'All 43 selected outsloped, unrutted cases · same revision-4 engine and non-soil inputs',ha='center',fontsize=9)
fig.text(.02,.025,'Rows: climate, material, surface (G gravel / P paved), traffic (H high / L low / N none).\nPoints are means of reported ELEMENT boundary totals over the complete simulation; all 43 cases are shown.\nBoundary export is not tagged sediment provenance. Complete profiles differ; this figure does not identify one causal parameter.\nMissing daily observations and undefined ratios remain explicit in the paired full-calendar ledger.',fontsize=8,va='bottom')
fig.subplots_adjust(left=.22,right=.985,top=.905,bottom=.13)
for suffix in ('png','svg','pdf'):fig.savefig(ROOT/f'small-reference-paired-boundaries.{suffix}',dpi=180)
plt.close(fig)
(ROOT/'figure-data.json').write_text(json.dumps(dict(script_sha256=sha(Path(__file__)),case_summary_sha256=sha(ROOT/'case-summary.json'),points=points,files={s:sha(ROOT/f'small-reference-paired-boundaries.{s}') for s in ('png','svg','pdf')}),indent=2)+'\n')
print('Figure contains all43 paired cases')
