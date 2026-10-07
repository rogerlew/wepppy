#!/usr/bin/env python3
"""Figures 1–3, retaining original Topanga filters and visual encodings."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import to_rgba
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd

COLORS = {'undisturbed': '#238b57', 'burned': '#e67e22'}
LABELS = {'undisturbed': 'Unburned (undisturbed)', 'burned': 'Burned'}
MARKERS = {('ksat', 'minus'): 'v', ('ksat', 'plus'): '^',
           ('cover', 'minus'): '<', ('cover', 'plus'): '>'}
MUTATIONS = {('ksat', 'minus'): 'Ksat −1%', ('ksat', 'plus'): 'Ksat +1%',
             ('cover', 'minus'): 'Cover −0.01', ('cover', 'plus'): 'Cover +0.01'}


def statistics(f):
    ratio = f.y / f.x
    ties = f.x.eq(f.y)
    congruent = (f.direction.eq('plus') & f.y.lt(f.x)) | (f.direction.eq('minus') & f.y.gt(f.x))
    return {'n': len(f), 'outside_2x': int(((ratio < .5) | (ratio > 2)).sum()),
            'outside_5x': int(((ratio < .2) | (ratio > 5)).sum()),
            'congruent': int(congruent.sum()), 'ties': int(ties.sum()),
            'incongruent_including_ties': int((~congruent).sum())}


def plot(frame, number, title, xlabel, limits, output, peak=False):
    fig, axes = plt.subplots(1, 2, figsize=(15.6, 7.4), dpi=180, sharex=True, sharey=True)
    bg = '#fbfaf7'
    fig.patch.set_facecolor(bg)
    for ax, scenario in zip(axes, ('undisturbed', 'burned')):
        ax.set_facecolor(bg)
        for factor, style, label in [(2, '--', '2× / 0.5×'), (.5, '--', None), (5, ':', '5× / 0.2×'), (.2, ':', None)]:
            ax.plot(limits, limits * factor, color='#888888', lw=.85, ls=style, label=label, zorder=1)
        s = frame.loc[frame.scenario.eq(scenario)]
        for (family, direction), marker in MARKERS.items():
            m = s.loc[s.family.eq(family) & s.direction.eq(direction)]
            groups = [(False, '#777777'), (True, COLORS[scenario])] if peak else [(None, COLORS[scenario])]
            for has_return, color in groups:
                subset = m if has_return is None else m.loc[m.has_surdra.eq(has_return)]
                congruent = ((subset.direction.eq('plus') & subset.y.lt(subset.x)) |
                             (subset.direction.eq('minus') & subset.y.gt(subset.x)))
                rgba = np.tile(to_rgba(color), (len(subset), 1))
                rgba[:, 3] = np.where(congruent, .2, .6)
                ax.scatter(subset.x, subset.y, marker=marker, s=10, linewidths=.45,
                           facecolors='none', edgecolors=rgba, rasterized=True, zorder=2)
        ax.plot(limits, limits, color='#4a4a4a', lw=.7, zorder=4, label='1:1')
        ax.set(xscale='log', yscale='log', xlim=limits, ylim=limits)
        ax.set_aspect('equal', adjustable='box')
        ax.grid(which='major', color='#555555', alpha=.13, lw=.7)
        ax.grid(which='minor', color='#555555', alpha=.045, lw=.5)
        ax.set_title(f'{LABELS[scenario]} (n={len(s):,})', color=COLORS[scenario], fontsize=12, weight='semibold', pad=9)
        ax.set_xlabel(f'Baseline {xlabel}', fontsize=11, labelpad=8)
        for spine in ax.spines.values():
            spine.set_color('#777777')
            spine.set_alpha(.35)
    axes[0].set_ylabel(f'Mutant {xlabel}', fontsize=11, labelpad=8)
    fig.suptitle(f'Figure {number}. {title}: Mutant versus Baseline', fontsize=15.5, weight='semibold', y=.975)
    fig.text(.5, .924, 'hand-to-mouth-drought • Surface-return correction • 1980–2024 full histories', ha='center', fontsize=10.5)
    handles, _ = axes[0].get_legend_handles_labels()
    if peak:
        handles += [Line2D([], [], marker='x', ls='none', color='#777777', label='No surface return in either run')]
        handles += [Line2D([], [], marker='x', ls='none', color=COLORS[s], label=f'{LABELS[s]}: surface return') for s in COLORS]
    handles += [Line2D([], [], marker=m, ls='none', markerfacecolor='none', markeredgecolor='#444444', label=MUTATIONS[k]) for k, m in MARKERS.items()]
    handles += [Line2D([], [], marker='x', ls='none', color='#444444', alpha=a, label=l) for a, l in [(.2, 'Inverse response (α=0.2)'), (.6, 'Same direction or unchanged (α=0.6)')]]
    axes[1].legend(handles=handles, loc='upper left', bbox_to_anchor=(1.04, 1), borderaxespad=0,
                   frameon=True, facecolor=bg, edgecolor='#bbbbbb', fontsize=9)
    fig.text(.99, .016, 'Both baseline and mutant use the corrected build; no rrinit / depression-storage changes.', ha='right', fontsize=8.5, color='#666666')
    outside = int(((frame[['x', 'y']] < limits[0]) | (frame[['x', 'y']] > limits[1])).any(axis=1).sum())
    if outside:
        fig.text(.99, -.008, f'{outside:,} eligible pairs fall outside the original axis limits; included in n and statistics.',
                 ha='right', fontsize=8.5, color='#666666')
    fig.subplots_adjust(left=.07, right=.76, bottom=.12, top=.86, wspace=.10)
    fig.savefig(output / f'figure-{number}.png', dpi=220, bbox_inches='tight', facecolor=bg)
    plt.close(fig)
    stats = {'all': statistics(frame), 'by_scenario': {s: statistics(frame.loc[frame.scenario.eq(s)]) for s in COLORS},
             'by_family': {s: statistics(frame.loc[frame.family.eq(s)]) for s in ('ksat', 'cover')},
             'outside_axis_limits': outside}
    return stats


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=True)
    events = pd.read_parquet(a.root / 'event-pairs.parquet')
    sediment = pd.read_parquet(a.root / 'sediment-pairs.parquet')
    both = events.baseline_event_present & events.mutant_event_present
    result = {}
    for num, key, scale, floor, title, label, limits in [
        (1, 'runoff_post_m', 1000, 1e-5, 'Event Runoff', 'event runoff depth (mm)', [.008, 200]),
        (3, 'peak_m_s', 3.6e6, 1e-7, 'Hillslope Peak Flow', 'peak flow (mm/h)', [.3, 800])]:
        f = events.loc[both & events[f'{key}_baseline'].ge(floor) & events[f'{key}_mutant'].gt(0)].copy()
        f['x'], f['y'] = f[f'{key}_baseline'] * scale, f[f'{key}_mutant'] * scale
        f['has_surdra'] = f.surdra_realized_m_baseline.gt(0) | f.surdra_realized_m_mutant.gt(0)
        result[str(num)] = plot(f, num, title, label, np.array(limits), a.output, peak=num == 3)
        if num == 3:
            stable = (f.runoff_post_m_mutant / f.runoff_post_m_baseline - 1).abs().lt(.05)
            ratio = f.y / f.x
            result['3']['volume_stable_twofold'] = int((stable & ((ratio < .5) | (ratio > 2))).sum())
            result['3']['surface_return_rows'] = int(f.has_surdra.sum())
            for scenario in COLORS:
                s = f.loc[f.scenario.eq(scenario) & f.family.eq('ksat') & f.x.ge(30) & f.x.lt(100) & ratio.ge(.5) & ratio.le(2)]
                result['3'].setdefault('ksat_30_100_central', {})[scenario] = statistics(s)
    f = sediment.loc[sediment.sediment_kg_m_baseline.gt(0) & sediment.sediment_kg_m_mutant.gt(0)].copy()
    f['x'], f['y'] = f.sediment_kg_m_baseline, f.sediment_kg_m_mutant
    limits = np.array([10**np.floor(np.log10(f[['x', 'y']].min().min())), 10**np.ceil(np.log10(f[['x', 'y']].max().max()))])
    result['2'] = plot(f, 2, 'Event Sediment Delivery', 'event sediment delivery (kg/m)', limits, a.output)
    result['2']['baseline_positive_only'] = int((sediment.sediment_kg_m_baseline.gt(0) & ~sediment.sediment_kg_m_mutant.gt(0)).sum())
    result['2']['mutant_positive_only'] = int((~sediment.sediment_kg_m_baseline.gt(0) & sediment.sediment_kg_m_mutant.gt(0)).sum())
    (a.output / 'figure-statistics.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
