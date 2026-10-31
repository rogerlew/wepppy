"""Plot the paired diagnostic response; the diagonal is not an acceptance bound."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE=Path(__file__).resolve().parent

def main():
    data=json.loads((HERE/'soil-hourly-interaction-v1-analysis.json').read_text())
    fig,axes=plt.subplots(1,2,figsize=(10,4.6),sharex=True,sharey=True)
    colors={'meaningful_low':'#ca7000','meaningful_high':'#b2182b','small_exceedance':'#7b3294','meaningful_pass':'#2166ac','small_pass':'#2166ac'}
    maximum=max(c['export_kg_yr'] for r in data['rows'] for c in r['cells'].values() if c['physical_pass'])*1.2
    for ax,soil in zip(axes,('generated','legacy')):
        for group in colors:
            rows=[r for r in data['rows'] if r['group']==group and r['cells'][f'{soil}-on']['physical_pass'] and r['cells'][f'{soil}-off']['physical_pass']]
            ax.scatter([r['cells'][f'{soil}-on']['export_kg_yr'] for r in rows], [r['cells'][f'{soil}-off']['export_kg_yr'] for r in rows],s=23,alpha=.7,color=colors[group],label=group.replace('_',' '))
        ax.plot([0,maximum],[0,maximum],color='#555',lw=.8,linestyle='--')
        ax.set(xscale='symlog',yscale='symlog',xlim=(-.1,maximum),ylim=(-.1,maximum),title=f'{soil.capitalize()} soil',xlabel='Hourly on: outlet sediment (kg/year)')
        ax.grid(alpha=.2)
    axes[0].set_ylabel('Hourly off: outlet sediment (kg/year)')
    axes[1].legend(fontsize=8,loc='upper left')
    fig.suptitle('111 selected cases; PMET and snow fixed; dashed line = unchanged output',fontsize=11)
    fig.tight_layout()
    fig.savefig(HERE/'soil-hourly-interaction-v1.png',dpi=160)
    plt.close(fig)

if __name__=='__main__':main()
