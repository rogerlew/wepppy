from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from scipy.signal import find_peaks

root = Path('/workdir/warming-rrinit-totalwatsed-20261006')
out = root / 'figures'
out.mkdir(exist_ok=True)
cases = ['rr10', 'rr17', 'rr60']
colors = ['#242b38', '#007fba', '#dc6630']
styles = ['-', '--', ':']
frames = {c: pd.read_parquet(root / c / 'totalwatsed3.parquet') for c in cases}
b = frames['rr10']
dates = pd.to_datetime(dict(year=b.year, month=b.month, day=b.day_of_month))
q = np.column_stack([frames[c].Streamflow * frames[c].Area / 86400000 for c in cases])
assert len(q) == 8766 and np.isfinite(q).all() and (q > 0).all()
for c in cases:
    assert frames[c][['year', 'julian']].equals(b[['year', 'julian']])
delta = 100 * (q[:, 1:] / q[:, :1] - 1)
plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False})

fig, axes = plt.subplots(2, 1, figsize=(15, 7), sharex=True, gridspec_kw={'height_ratios': [2, 1]})
for k, c in enumerate(cases):
    axes[0].plot(dates, q[:, k], color=colors[k], ls=styles[k], lw=1.1, label=c[2:] + ' cm')
for k in range(2):
    axes[1].plot(dates, delta[:, k], color=colors[k+1], lw=.8, label=cases[k+1][2:] + ' cm')
axes[0].set(ylabel='Daily-average streamflow (m³/s)', title='warming-championship | totalwatsed streamflow, 1980–2003')
axes[0].legend(ncol=3, loc='upper right')
axes[1].set(ylabel='Change from 10 cm (%)')
axes[1].axhline(0, color='#777777', lw=.6)
for ax in axes:
    ax.grid(alpha=.2)
axes[1].xaxis.set_major_locator(mdates.YearLocator(2))
axes[1].xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
fig.text(.08, .02, 'Streamflow = runoff + lateral flow + baseflow. Daily volumes converted to discharge; not channel-routed instantaneous flow.', fontsize=10)
fig.tight_layout(rect=[0, .05, 1, 1])
fig.savefig(out / 'totalwatsed-hydrograph.png', dpi=180)
plt.close(fig)

# Define event peaks from baseline alone, before examining treatment differences.
peaks, props = find_peaks(q[:, 0], distance=7, prominence=.1)
median = float(np.median(q[peaks, 0]))
small = peaks[q[peaks, 0] <= median]
# Inspect the largest treatment departures among the smaller baseline events.
score = {int(p): float(np.max(np.abs(delta[max(0,p-3):min(len(q),p+4)]))) for p in small}
chosen = []
for p in sorted(small, key=lambda p: score[int(p)], reverse=True):
    if p >= 5 and p + 5 < len(q) and all(abs(int(p)-s) > 10 for s in chosen):
        chosen.append(int(p))
    if len(chosen) == 3:
        break
fig, axes = plt.subplots(2, 3, figsize=(15, 7), gridspec_kw={'height_ratios': [2, 1]})
records = []
for col, p in enumerate(chosen):
    ix = np.arange(p-5, p+6)
    for k, c in enumerate(cases):
        axes[0, col].plot(dates.iloc[ix], q[ix,k], color=colors[k], ls=styles[k], lw=1.7, marker='o', ms=3, label=c[2:]+' cm')
    for k in range(2):
        axes[1,col].plot(dates.iloc[ix], delta[ix,k], color=colors[k+1], lw=1.5, marker='o', ms=3)
    axes[0,col].set_title(f'Baseline event peak: {dates.iloc[p]:%Y-%m-%d}\n{q[p,0]:.3f} m³/s')
    axes[0,col].axvline(dates.iloc[p], color='#777777', alpha=.3, lw=.7)
    axes[1,col].axhline(0, color='#777777', lw=.7)
    for row in range(2):
        axes[row,col].grid(alpha=.2)
        axes[row,col].xaxis.set_major_locator(mdates.DayLocator(interval=3))
        axes[row,col].xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
    records.append({'baseline_peak_date': str(dates.iloc[p].date()), 'baseline_peak_m3s': float(q[p,0]), 'selection_max_abs_departure_pct_within_3days': score[p], 'window_min_departure_pct': delta[ix].min(axis=0).tolist(), 'window_max_departure_pct': delta[ix].max(axis=0).tolist(), 'window_volume_change_pct': (100*(q[ix,1:].sum(axis=0)/q[ix,0].sum()-1)).tolist()})
axes[0,0].set_ylabel('Daily-average streamflow (m³/s)')
axes[1,0].set_ylabel('Change from 10 cm (%)')
axes[0,2].legend(ncol=3, fontsize=9)
fig.suptitle('Smaller events | three most responsive, non-overlapping examples', fontsize=16)
fig.text(.065, .045, f'Baseline peaks: ≥7 days apart, prominence ≥0.1 m³/s. Smaller = lower half of peaks (≤{median:.3f} m³/s).\nExamples ranked by largest absolute treatment departure within ±3 days; ±5-day windows shown. Deliberately sensitivity-focused, not typical events.', fontsize=10)
fig.tight_layout(rect=[0, .10, 1, .94])
fig.savefig(out / 'totalwatsed-smaller-events.png', dpi=180)
plt.close(fig)
result = {'baseline_event_count': len(peaks), 'smaller_event_count':len(small), 'smaller_event_threshold_m3s':median, 'selected_events':records}
(out / 'selection.json').write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps(result, indent=2))
