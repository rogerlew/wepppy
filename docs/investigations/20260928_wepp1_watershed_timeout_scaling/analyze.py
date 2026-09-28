"""Reproduce the read-only wepp1 timing assessment from retained observations.

Run from the repository root with .venv/bin/python <this file>. Uses existing
NumPy/SciPy/matplotlib dependencies; does not contact production or alter jobs.
"""
from pathlib import Path
import csv
import json

import numpy as np
from scipy.stats import spearmanr
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
with (ROOT / 'timings.csv').open() as stream:
    rows = list(csv.DictReader(stream))
valid = [r for r in rows if r['status'] == 'finished' and r['native_success'] == 'True'
         and r['years'] == r['last_reported_year'] and int(r['hillslopes']) > 0]
results = {}
for binary in ('all', 'wepp_dcc52a6'):
    sample = [r for r in valid if binary == 'all' or r['binary'] == binary]
    years = np.array([int(r['years']) for r in sample])
    hills = np.array([int(r['hillslopes']) for r in sample])
    channels = np.array([int(r['channels']) for r in sample])
    seconds = np.array([float(r['elapsed_s']) for r in sample])
    groups = [(int(h), int(c)) for h, c in zip(hills, channels)]
    result = {'n': len(sample), 'size_groups': len(set(groups)),
              'hills_channels_spearman': float(spearmanr(hills, channels).statistic),
              'seconds_per_hillslope_year_q50_q90_q95_max':
                  np.quantile(seconds / (years * hills), [.5, .9, .95, 1]).tolist(),
              'models': {}}
    target = np.log(seconds)
    for name, columns in [('years', [years]), ('years_hills', [years, hills]),
                          ('years_channels', [years, channels]),
                          ('years_combined_size', [years, hills + channels])]:
        design = np.column_stack([np.ones(len(sample))] + [np.log(v) for v in columns])
        coefficients = np.linalg.lstsq(design, target, rcond=None)[0]
        predictions = design @ coefficients
        cv = np.zeros(len(sample))
        for group in set(groups):
            test = np.array([g == group for g in groups])
            cv[test] = design[test] @ np.linalg.lstsq(design[~test], target[~test], rcond=None)[0]
        factors = np.exp(np.abs(cv - target))
        group_factors = [np.median(factors[[g == group for g in groups]]) for group in set(groups)]
        result['models'][name] = {
            'log_coefficients': coefficients.tolist(),
            'log_r2': float(1 - np.sum((predictions-target)**2) / np.sum((target-target.mean())**2)),
            'held_out_size_group_median_error_factor_q50_q90':
                np.quantile(group_factors, [.5, .9]).tolist()}
    result['100_year_bins'] = []
    for low, high in [(0, 100), (100, 300), (300, 700), (700, 1500), (1500, 3000)]:
        selected = (years == 100) & (hills > low) & (hills <= high)
        if selected.any():
            result['100_year_bins'].append({'hillslope_range': [low + 1, high],
                'n': int(selected.sum()), 'median_seconds': float(np.median(seconds[selected]))})
    results[binary] = result
(ROOT / 'analysis.json').write_text(json.dumps(results, indent=2) + '\n')

sample = [r for r in valid if r['binary'] == 'wepp_dcc52a6' and int(r['years']) == 100]
hills = np.array([int(r['hillslopes']) for r in sample])
seconds = np.array([float(r['elapsed_s']) for r in sample])
fig, ax = plt.subplots(figsize=(8, 4.8), layout='constrained')
ax.scatter(hills, seconds / 60, s=32, alpha=.65, color='#126b87', edgecolors='none')
x = np.geomspace(hills.min(), hills.max(), 150)
ax.plot(x, .02801 * 100 * x / 60, color='#a84d12', linestyle='--',
        label='Typical rate: 0.028 seconds per hillslope-year')
ax.set(xscale='log', yscale='log', xlabel='Hillslopes in the consumed watershed input',
       ylabel='Watershed elapsed time (minutes)',
       title='wepp1: 96 completed 100-year runs, same WEPP binary')
ax.grid(True, which='both', alpha=.16)
ax.legend(loc='upper left', fontsize=9)
fig.savefig(ROOT / 'runtime_vs_hillslopes.svg')
plt.close(fig)
print(json.dumps(results, indent=2))
