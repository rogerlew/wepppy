"""Plot the complete diagnostic factorial without implying broad acceptance."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
summary = json.loads((HERE / 'combined-hydraulics-r4-summary.json').read_text())
lanes = ['road_off_baseline', 'road_off_fill_fixed', 'road_off_buffer_cap', 'road_off_both',
         'road_on_baseline', 'road_on_fill_fixed', 'road_on_buffer_cap', 'road_on_both']
labels = ['Original', 'Fill', 'Buffer', 'Fill + buffer', 'Road package',
          'Road + fill', 'Road + buffer', 'Road + fill + buffer']
fig, axes = plt.subplots(1, 2, figsize=(10, 4.5), sharey=True, constrained_layout=True)
y = list(range(8))
recovered = [summary['groups'][n]['recovered_original_misses'] for n in lanes]
retained = [20 - summary['groups'][n]['control_regressions'] for n in lanes]
axes[0].barh(y, recovered, color='#427a9d')
axes[1].barh(y, retained, color='#666666')
for ax, values in zip(axes, (recovered, retained)):
    for pos, value in zip(y, values):
        ax.text(value + .4, pos, str(value), va='center', fontsize=9)
    ax.grid(axis='x', alpha=.2)
axes[0].set(yticks=y, yticklabels=labels, xlim=(0, 100), xlabel='Original misses recovered / 96')
axes[1].set(xlim=(0, 22), xlabel='Passing controls retained / 20')
axes[0].invert_yaxis()
fig.suptitle('Revision 4: hydraulic combinations do not resolve the tradeoff')
fig.text(.01, -.035, 'Selected 116-case diagnostic panel. No parameter candidate accepted; three strict fraction flags remain visible.', fontsize=9)
fig.savefig(HERE / 'combined-hydraulics-r4-outcomes.png', dpi=180, bbox_inches='tight')
