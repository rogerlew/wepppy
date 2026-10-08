#!/usr/bin/env python3
"""Paired native/floored stochastic CLIGEN research at frozen study hillslopes."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import time

import numpy as np
import pandas as pd
from scipy.stats import wasserstein_distance

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
OLD = HERE.parents[1] / '20261008_dewpoint_openet/artifacts'
ROOT = Path('/home/workdir/wepppy-scratch/stochastic-dewpoint-20261008')
WEPP = REPO / 'wepp_runner/bin/wepp_260803_hill'
CLIGEN = REPO / 'wepppy/climates/cligen/bin/cligen532'
SEEDS = list(range(1001, 1011))
MODELS = ['Ensemble', 'eeMETRIC', 'PTJPL', 'SSEBop']
PARS = {'hand-to-mouth-drought': 'ca041484.par', 'apostolic-saw': 'wa458928.par',
        'cryptic-beechnut': 'wa459074.par'}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + '\n')


def manifest():
    return json.loads((HERE / 'manifest.json').read_text())


def climate(path):
    lines = path.read_text().splitlines(keepends=True)
    rows = [line.split() for line in lines[15:] if line.strip()]
    assert all(line.strip() for line in lines[15:15 + len(rows)])
    assert all(len(r) == 13 for r in rows)
    values = np.array(rows, dtype=float)
    dates = pd.to_datetime([f'{r[2]}-{r[1]}-{r[0]}' for r in rows], format='%Y-%m-%d')
    assert np.isfinite(values).all()
    assert dates.equals(pd.date_range(dates[0], dates[-1]))
    return lines, rows, values, dates


def generate(site, seed, root):
    root.mkdir(parents=True, exist_ok=True)
    cmd = [str(CLIGEN), '-istation.par', '-ooutput.cli', '-t5',
           f"-y{site['control_years']}", f"-b{site['start'][:4]}", f'-r{seed}', '-I2', '-F']
    started = time.monotonic()
    if not (root / 'output.cli').exists():
        shutil.copy2(HERE / 'stations' / PARS[site['slug']], root / 'station.par')
        with (root / 'stdout.log').open('wb') as out, (root / 'stderr.log').open('wb') as err:
            proc = subprocess.run(cmd, cwd=root, stdout=out, stderr=err, timeout=120, check=False)
        save(root / 'process.json', {'returncode': proc.returncode, 'command': cmd})
        assert proc.returncode == 0, root
    else:
        # Resume already-emitted records after the documented terminal-blank parser fix.
        assert sha(root / 'station.par') == sha(HERE / 'stations' / PARS[site['slug']])
    _, _, data, dates = climate(root / 'output.cli')
    assert len(data) == site['days'] and str(dates[-1].date()) == site['end']
    diagnostic_count = (root / 'stdout.log').read_text().count('Could not produce desired')
    return {'slug': site['slug'], 'seed': seed, 'command': cmd,
            'process_record_available': (root / 'process.json').exists(),
            'seconds_for_generation_or_validation': time.monotonic() - started,
            'days': len(data), 'sha256': sha(root / 'output.cli'),
            'daily_values_sha256': hashlib.sha256(data.tobytes()).hexdigest(),
            'unmet_random_deviate_quality_targets': diagnostic_count}


def prepare():
    assert not (HERE / 'manifest.json').exists(), 'Already frozen.'
    prior = json.loads((OLD / 'manifest.json').read_text())
    assert sha(WEPP) == prior['binary_metadata']['sha256']
    cligen_meta = json.loads(CLIGEN.with_suffix('.json').read_text())
    assert sha(CLIGEN) == cligen_meta['binary']['sha256']
    m = {'created_utc': datetime.now(timezone.utc).isoformat(), 'root': str(ROOT),
         'source_manifest_sha256': sha(OLD / 'manifest.json'), 'seeds': SEEDS,
         'wepp_metadata': prior['binary_metadata'], 'cligen_metadata': cligen_meta,
         'sites': prior['sites'], 'station_files': {}, 'generations': [],
         'observation_sha256': sha(OLD / 'openet-monthly.csv'),
         'policy': 'Unchanged station generation versus max(native Td, native Tmin); no localization.'}
    (HERE / 'stations').mkdir(parents=True, exist_ok=True)
    for slug, name in PARS.items():
        source = Path('/wc1/runs') / slug[:2] / slug / 'climate' / name
        shutil.copy2(source, HERE / 'stations' / name)
        m['station_files'][slug] = {'path': str(source), 'sha256': sha(source)}
    representatives = [next(s for s in m['sites'] if s['slug'] == slug) for slug in PARS]
    jobs = [(s, seed, ROOT / 'climates' / s['slug'] / str(seed)) for s in representatives for seed in SEEDS]
    with ThreadPoolExecutor(max_workers=3) as pool:
        m['generations'] = list(pool.map(lambda args: generate(*args), jobs))
    assert len({g['daily_values_sha256'] for g in m['generations']}) == 30
    replay = generate(representatives[0], SEEDS[0], ROOT / 'replay')
    assert replay['sha256'] == m['generations'][0]['sha256']
    m['replay'] = replay
    for s in m['sites']:
        fixture = Path(prior['root']) / 'fixtures' / s['site']
        for name, expected in s['source_hashes'].items():
            assert sha(fixture / name) == expected
        for seed in SEEDS:
            native = ROOT / 'climates' / s['slug'] / str(seed) / 'output.cli'
            lines, rows, values, _ = climate(native)
            clipped = lines[:15] + [re.sub(r'\S+(\s*)$', lambda match: f'{max(v[12], v[8]):.1f}' + match[1], line)
                if v[12] < v[8] else line for line, v in zip(lines[15:], values)]
            clipped += lines[15 + len(values):]
            for arm in ['native', 'clipped']:
                case = ROOT / s['site'] / str(seed) / arm
                (case / 'runs').mkdir(parents=True)
                (case / 'output').mkdir()
                for name in s['source_hashes']:
                    if not name.endswith('.cli'):
                        shutil.copy2(fixture / name, case / 'runs' / name)
                target = case / 'runs' / f"p{s['hill']}.cli"
                if arm == 'native':
                    shutil.copy2(native, target)
                else:
                    target.write_text(''.join(clipped))
    save(HERE / 'manifest.json', m)
    with tarfile.open(HERE / 'generated-climates.tar.gz', 'w:gz') as archive:
        archive.add(ROOT / 'climates', arcname='climates')
    print('Frozen 30 climates and 180 cases; exact CLIGEN replay passed.', flush=True)


def run_one(s, seed, arm):
    case = ROOT / s['site'] / str(seed) / arm
    record = case / 'execution.json'
    if record.exists():
        info = json.loads(record.read_text())
        assert info['returncode'] == 0 and info['normal_completion']
        return info
    start = time.monotonic()
    with (case / 'runs' / f"p{s['hill']}.run").open('rb') as inp, (case / 'stdout.log').open('wb') as out, (case / 'stderr.log').open('wb') as err:
        proc = subprocess.run([str(WEPP)], cwd=case / 'runs', stdin=inp,
                              stdout=out, stderr=err, timeout=240, check=False)
    info = {'site': s['site'], 'seed': seed, 'arm': arm, 'returncode': proc.returncode,
            'seconds': time.monotonic() - start,
            'normal_completion': 'WEPP COMPLETED HILLSLOPE SIMULATION SUCCESSFULLY' in (case / 'stdout.log').read_text(),
            'binary_sha256': sha(WEPP),
            'output_hashes': {p.name: sha(p) for p in (case / 'output').iterdir() if p.is_file()}}
    save(record, info)
    assert info['returncode'] == 0 and info['normal_completion'], case
    print(s['site'], seed, arm, 'ok', flush=True)
    return info


def run():
    m = manifest()
    assert sha(WEPP) == m['wepp_metadata']['sha256']
    jobs = [(s, seed, arm) for s in m['sites'] for seed in SEEDS for arm in ['native', 'clipped']]
    with ThreadPoolExecutor(max_workers=3) as pool:
        info = list(pool.map(lambda job: run_one(*job), jobs))
    save(HERE / 'executions.json', info)


def water(s, seed, arm):
    path = ROOT / s['site'] / str(seed) / arm / 'output' / f"H{s['hill']}.wat.dat"
    rows = [line.split() for line in path.read_text().splitlines() if len(line.split()) == 25 and line.split()[0].isdigit()]
    names = ['ofe', 'jday', 'year', 'p', 'rain_melt', 'q', 'ep', 'es', 'er', 'dp',
             'runon', 'subrunon', 'lat', 'sw', 'frozen', 'swe', 'qofe', 'drain',
             'irrigation', 'area', 'total_soil_water', 'profile_depth', 'porosity', 'fc', 'wp']
    df = pd.DataFrame(np.array(rows, dtype=float), columns=names)
    assert len(df) == s['days'] and np.isfinite(df.to_numpy()).all()
    df.index = pd.DatetimeIndex(pd.to_datetime(df.year.astype(int).astype(str)) + pd.to_timedelta(df.jday - 1, unit='D'))
    assert df.index.equals(pd.date_range(s['start'], s['end'])) and (df.ofe == 1).all()
    df['et'] = df.ep + df.es + df.er
    return df


def verify():
    m = manifest()
    evidence, quality = [], []
    assert sha(CLIGEN) == m['cligen_metadata']['binary']['sha256']
    assert sha(WEPP) == m['wepp_metadata']['sha256']
    assert sha(OLD / 'openet-monthly.csv') == m['observation_sha256']
    generation_quality = []
    for g in m['generations']:
        generated = ROOT / 'climates' / g['slug'] / str(g['seed'])
        assert sha(generated / 'output.cli') == g['sha256']
        assert sha(generated / 'station.par') == m['station_files'][g['slug']]['sha256']
        names = re.findall(r'Could not produce desired level of quality in\s*<<\s*(.*?)\s*>>', (generated / 'stdout.log').read_text())
        assert len(names) == g['unmet_random_deviate_quality_targets']
        generation_quality.append({'slug': g['slug'], 'seed': g['seed'], 'unmet_targets': len(names),
            'parameters': {name: names.count(name) for name in sorted(set(names))}})
    save(HERE / 'generation-quality.json', generation_quality)
    for s in m['sites']:
        for seed in SEEDS:
            base = ROOT / s['site'] / str(seed)
            al, ar, a, dates = climate(base / 'native/runs' / f"p{s['hill']}.cli")
            assert sha(base / 'native/runs' / f"p{s['hill']}.cli") == sha(ROOT / 'climates' / s['slug'] / str(seed) / 'output.cli')
            bl, br, b, bd = climate(base / 'clipped/runs' / f"p{s['hill']}.cli")
            assert al[:15] == bl[:15] and dates.equals(bd)
            assert all(x[:-1] == y[:-1] for x, y in zip(ar, br))
            np.testing.assert_array_equal(b[:, 12], np.maximum(a[:, 12], a[:, 8]))
            mask = (dates >= '2016-01-01') & (dates <= '2022-12-31')
            quality.append({'site': s['site'], 'seed': seed, 'assessment_days': int(mask.sum()),
                            'floored_days': int(sum(a[mask, 12] < a[mask, 8])),
                            'mean_floor_c': float(np.mean(b[mask, 12] - a[mask, 12])),
                            'max_floor_c': float(np.max(b[mask, 12] - a[mask, 12])),
                            'tmin_above_tmax_days': int(sum(a[mask, 8] > a[mask, 7])),
                            'native_td_above_tmax_days': int(sum(a[mask, 12] > a[mask, 7]))})
            for arm in ['native', 'clipped']:
                case = base / arm
                for name, expected in s['source_hashes'].items():
                    if not name.endswith('.cli'):
                        assert sha(case / 'runs' / name) == expected
                info = json.loads((case / 'execution.json').read_text())
                assert info['returncode'] == 0 and info['normal_completion']
                assert info['binary_sha256'] == m['wepp_metadata']['sha256']
                for name, expected in info['output_hashes'].items():
                    assert sha(case / 'output' / name) == expected
                df = water(s, seed, arm)
                np.testing.assert_allclose(df.p, a[:, 3], atol=.011)
                assert (df.et >= 0).all()
                evidence.append({'site': s['site'], 'seed': seed, 'arm': arm,
                                 'days': len(df), 'finite': True, 'precip_readback': True,
                                 'treatment_isolation': True})
    save(HERE / 'validation.json', evidence)
    pd.DataFrame(quality).to_csv(HERE / 'climate-quality.csv', index=False)
    print('Verified', len(evidence), 'cases and', sum(e['days'] for e in evidence), 'daily rows.')


def compare(group, observed):
    gen_mean = group.groupby('month').et.mean()
    obs_mean = observed.groupby('month').et.mean()
    error = gen_mean - obs_mean
    distances = [wasserstein_distance(group[group.month == month].et, observed[observed.month == month].et) for month in range(1, 13)]
    return {'cycle_mae_mm': float(error.abs().mean()), 'cycle_rmse_mm': float(np.sqrt((error ** 2).mean())),
            'monthly_distribution_distance_mm': float(np.mean(distances)),
            'annual_et_mm': float(gen_mean.sum()), 'openet_annual_et_mm': float(obs_mean.sum())}


def analyze():
    m = manifest()
    months, climatology, humidity = [], [], []
    for s in m['sites']:
        for seed in SEEDS:
            native_path = ROOT / 'climates' / s['slug'] / str(seed) / 'output.cli'
            _, _, a, dates = climate(native_path)
            mask = (dates >= '2016-01-01') & (dates <= '2022-12-31')
            c = pd.DataFrame(a[mask], index=dates[mask])
            climatology.append({'site': s['site'], 'seed': seed, 'annual_p_mm': c[3].sum()/7,
                                'mean_tmax_c': c[7].mean(), 'mean_tmin_c': c[8].mean(), 'native_mean_td_c': c[12].mean()})
            for arm in ['native', 'clipped']:
                td = c[12] if arm == 'native' else np.maximum(c[12], c[8])
                vapor = .6108 * np.exp(17.27 * td / (td + 237.3))
                saturation = .5 * (.6108 * np.exp(17.27*c[7]/(c[7]+237.3)) + .6108 * np.exp(17.27*c[8]/(c[8]+237.3)))
                humidity.append({'site': s['site'], 'seed': seed, 'arm': arm,
                    'mean_td_c': float(np.mean(td)), 'td_p05_c': float(np.quantile(td, .05)),
                    'td_p95_c': float(np.quantile(td, .95)),
                    'mean_actual_vapor_kpa': float(vapor.mean()),
                    'mean_vpd_kpa': float(np.mean(saturation - vapor))})
            for arm in ['native', 'clipped']:
                df = water(s, seed, arm).loc['2016':'2022']
                agg = df[['p', 'et', 'ep', 'es', 'er', 'q', 'lat', 'dp']].resample('MS').sum()
                agg['sw_mean'] = df.total_soil_water.resample('MS').mean()
                agg['swe_mean'] = df.swe.resample('MS').mean()
                agg['snow_days'] = (df.swe > 1).resample('MS').sum()
                agg['site'], agg['watershed'], agg['seed'], agg['arm'] = s['site'], s['watershed'], seed, arm
                months.append(agg.rename_axis('date').reset_index())
    months = pd.concat(months, ignore_index=True)
    months['month'] = months.date.dt.month
    months.to_csv(HERE / 'wepp-monthly.csv', index=False)
    climates = pd.DataFrame(climatology)
    climates.to_csv(HERE / 'generated-climate-summary.csv', index=False)
    previous = json.loads((OLD / 'manifest.json').read_text())
    suitability = []
    for s in m['sites']:
        c = climates[climates.site == s['site']]
        _, _, a, dates = climate(Path(previous['root']) / 'fixtures' / s['site'] / f"p{s['hill']}.cli")
        a = a[(dates >= '2016-01-01') & (dates <= '2022-12-31')]
        suitability.append({'site': s['site'], 'watershed': s['watershed'],
            'station_p_mm_y': c.annual_p_mm.mean(), 'gridmet_hill_p_mm_y': a[:, 3].sum()/7,
            'precip_ratio': c.annual_p_mm.mean()/(a[:, 3].sum()/7),
            'station_tmax_c': c.mean_tmax_c.mean(), 'gridmet_hill_tmax_c': a[:, 7].mean(),
            'station_tmin_c': c.mean_tmin_c.mean(), 'gridmet_hill_tmin_c': a[:, 8].mean()})
    pd.DataFrame(suitability).to_csv(HERE / 'station-site-mismatch.csv', index=False)
    pd.DataFrame(humidity).to_csv(HERE / 'humidity-summary.csv', index=False)
    obs = pd.read_csv(OLD / 'openet-monthly.csv', parse_dates=['date'])
    obs['month'] = obs.date.dt.month
    metrics = []
    for (site, arm), group in months.groupby(['site', 'arm']):
        for model in MODELS:
            reference = obs[(obs.site == site) & (obs.model == model)]
            metrics.append({'site': site, 'arm': arm, 'model': model, 'seed': 'pooled', **compare(group, reference)})
            for seed, sub in group.groupby('seed'):
                metrics.append({'site': site, 'arm': arm, 'model': model, 'seed': str(seed), **compare(sub, reference)})
    metrics = pd.DataFrame(metrics)
    metrics.to_csv(HERE / 'comparison-metrics.csv', index=False)
    quality_metrics = []
    diagnostic_free = {(g['slug'], g['seed']) for g in m['generations'] if not g['unmet_random_deviate_quality_targets']}
    for s in m['sites']:
        seeds = [seed for seed in SEEDS if (s['slug'], seed) in diagnostic_free]
        if not seeds:
            continue
        for arm in ['native', 'clipped']:
            group = months[(months.site == s['site']) & (months.arm == arm) & months.seed.isin(seeds)]
            for model in MODELS:
                reference = obs[(obs.site == s['site']) & (obs.model == model)]
                quality_metrics.append({'site': s['site'], 'arm': arm, 'model': model,
                    'seeds': ','.join(map(str, seeds)), **compare(group, reference)})
    pd.DataFrame(quality_metrics).to_csv(HERE / 'diagnostic-free-metrics.csv', index=False)
    annual = months.groupby(['site', 'watershed', 'seed', 'arm'])[['p', 'et', 'q', 'lat', 'dp', 'snow_days']].sum()/7
    means = months.groupby(['site', 'watershed', 'seed', 'arm'])[['sw_mean', 'swe_mean']].mean()
    annual = annual.join(means).reset_index()
    annual.to_csv(HERE / 'annual-summary.csv', index=False)
    pairs = annual.pivot(index=['site', 'watershed', 'seed'], columns='arm')
    delta = pd.DataFrame({name: pairs[name].clipped - pairs[name].native for name in ['et', 'q', 'lat', 'dp', 'snow_days', 'sw_mean', 'swe_mean']})
    delta.reset_index().to_csv(HERE / 'paired-effects.csv', index=False)
    pooled = metrics[metrics.seed == 'pooled'].pivot(index=['site', 'model'], columns='arm')
    seedwise = metrics[metrics.seed != 'pooled'].pivot(index=['site', 'model', 'seed'], columns='arm')
    conclusions = {'cases': 180, 'pooled_comparisons': len(pooled), 'seed_comparisons': len(seedwise)}
    for metric in ['cycle_mae_mm', 'cycle_rmse_mm', 'monthly_distribution_distance_mm']:
        conclusions[f'clipped_better_{metric}'] = int(sum(pooled[metric].clipped < pooled[metric].native))
        conclusions[f'seedwise_clipped_better_{metric}'] = int(sum(seedwise[metric].clipped < seedwise[metric].native))
    save(HERE / 'conclusions.json', conclusions)
    plots(months, obs, m['sites'])
    print(json.dumps(conclusions, indent=2))


def plots(months, obs, sites):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(3, 3, figsize=(14, 10), constrained_layout=True, sharex=True)
    for ax, s in zip(axes.flat, sites):
        ref = obs[obs.site == s['site']].groupby(['model', 'month']).et.mean().unstack(0)
        ax.fill_between(ref.index, ref[MODELS[1:]].min(axis=1), ref[MODELS[1:]].max(axis=1), color='0.85', label='3-component range')
        ax.plot(ref.index, ref.Ensemble, color='black', label='OpenET ensemble')
        for arm, color in [('native', '#2563eb'), ('clipped', '#ea580c')]:
            g = months[(months.site == s['site']) & (months.arm == arm)].groupby(['seed', 'month']).et.mean().unstack(0)
            ax.fill_between(g.index, g.min(axis=1), g.max(axis=1), color=color, alpha=.12)
            ax.plot(g.index, g.mean(axis=1), color=color, label=arm)
        ax.set_title(f"{s['watershed']} H{s['hill']}")
        ax.set_ylabel('Mean ET (mm/month)')
        ax.set_xlabel('Month of year')
        ax.grid(alpha=.2)
    axes[0, 0].legend(fontsize=8)
    fig.suptitle('Stochastic station CLIGEN: native versus dewpoint floor\nLines: ten-seed mean; colored bands: seed range; OpenET: 2016–2022 climatology')
    fig.savefig(HERE / 'seasonal-et.png', dpi=160)
    fig.savefig(HERE / 'seasonal-et.svg')
    plt.close(fig)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=['prepare', 'run', 'verify', 'analyze'])
    globals()[parser.parse_args().phase]()
