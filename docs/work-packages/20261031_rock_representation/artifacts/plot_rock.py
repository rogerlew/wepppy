"""Illustrate dimensional distinctions; not field calibration."""
import argparse
import csv
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ap=argparse.ArgumentParser();ap.add_argument('--data',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
if a.out.exists():raise FileExistsError(a.out)
rows=list(csv.DictReader((a.data/'mass-volume-grid.csv').open()))
fig,axes=plt.subplots(1,2,figsize=(10,4.5),layout='constrained')
for rho in [.8,1.3,2.0]:
    r=[r for r in rows if float(r['fine_density_g_cm3'])==rho]
    axes[0].plot([100*float(x['source_volume_fraction']) for x in r],[100*float(x['mass_fraction']) for x in r],label=f'Fine-earth density {rho:g} g/cm³')
axes[0].plot([0,100],[0,100],color='gray',linestyle=':',label='Equal numeric percentages')
axes[0].axhline(85,color='black',linestyle='--',label='Existing native mass cap')
axes[0].set(xlabel='Profile rock volume (%)',ylabel='Profile rock dry mass (%)',title='Volume and mass are different inputs')
axes[0].legend(fontsize=8)
b=np.linspace(0,1,201);s=.25;lo=np.maximum(0,b+s-1);hi=np.minimum(b,s)
axes[1].fill_between(b*100,lo*100,hi*100,color='#9ecae1',alpha=.65,label='Feasible exposed-rock range')
axes[1].plot(b*100,b*s*100,color='#08519c',label='Independence assumption')
axes[1].plot(b*100,hi*100,color='#b45f06',linestyle='--',label='All rock exposed, clipped')
axes[1].set(xlabel='Bare fraction of ground (%)',ylabel='Exposed rock / total ground (%)',title='Total surface rock fixed at 25%')
axes[1].legend(fontsize=8)
for ax in axes:ax.grid(alpha=.2);ax.set_xlim(0,100)
fig.suptitle('Rock representation: dimensional and overlap diagnostics',fontsize=13)
fig.savefig(a.out,dpi=160)
