"""Original paired data figure; no model execution or statistical extrapolation."""
from pathlib import Path
import hashlib,json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
ROOT=Path(__file__).resolve().parent
p=ROOT/'paired-target-table.json';rows=json.loads(p.read_text())
fig,axes=plt.subplots(1,3,figsize=(13,7.8),sharey=True)
fig.subplots_adjust(left=.265,right=.985,bottom=.18,top=.795,wspace=.13)
fields=[('observed_first_two_layer_weighted_available_storage_mm','Consumed available storage','mm; first two layers'),('published_surface_out_m3','Buffer surface outflow','m³ on selected day'),('published_sediment_out_kg','Buffer sediment outflow','kg on selected day')]
labels=[]
for i in range(9):
 legacy,modern=rows[2*i:2*i+2];assert legacy['lane']=='legacy' and modern['lane']=='modern'
 labels.append(legacy['label'])
 for ax,(key,_,_) in zip(axes,fields):
  lv,mv=legacy[key],modern[key]
  ax.plot([lv,mv],[i,i],color='#b9c4c9',lw=1.6,zorder=1)
  ax.scatter(lv,i,color='#6b7280',s=34,zorder=3)
  ax.scatter(mv,i,color='#087e8b',s=38,zorder=4)
for ax,(key,title,unit) in zip(axes,fields):
 ax.set_title(title,fontsize=11,pad=13)
 ax.set_xlabel(unit,fontsize=10);ax.set_ylim(8.6,-.6)
 ax.set_xscale('symlog',linthresh=1,linscale=.7)
 ax.set_xlim(-.05,max(1,max(r[key] for r in rows))*1.35)
 ax.grid(axis='x',color='#e4e8ea',lw=.6);ax.set_axisbelow(True)
 ax.spines[['top','right','left']].set_visible(False);ax.tick_params(axis='y',length=0)
 ax.set_xticks([0,1,10,100]);ax.set_xticklabels(['0','1','10','100'])
axes[0].set_yticks(range(9));axes[0].set_yticklabels(labels,fontsize=9)
fig.suptitle('Same engine, different soil profiles: selected buffer responses',fontsize=15,y=.972)
fig.text(.5,.925,'All nine predeclared pairs · complete 16-year simulations · exact ordinary-output parity',ha='center',fontsize=10,color='#44535c')
fig.legend(handles=[Line2D([],[],marker='o',ls='',color='#6b7280',label='Whole legacy profile'),Line2D([],[],marker='o',ls='',color='#087e8b',label='Existing generated-soil candidate')],loc='upper center',bbox_to_anchor=(.5,.89),ncol=2,frameon=False)
fig.text(.265,.045,'Axes are linear near zero, logarithmic above 1. These selected contrasts do not isolate a coefficient.\nStorage is the consumed equivalent-plane calculation, not whole-profile pore volume.',fontsize=9,color='#44535c')
for ext in ('png','pdf','svg'):fig.savefig(ROOT/f'paired-buffer-process.{ext}',dpi=180)
receipt=dict(script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),data_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),rows=18,pairs=9,fields=[f[0] for f in fields],matplotlib_version=matplotlib.__version__,outputs={f'paired-buffer-process.{ext}':hashlib.sha256((ROOT/f'paired-buffer-process.{ext}').read_bytes()).hexdigest() for ext in ('png','pdf','svg')})
(ROOT/'figure-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
