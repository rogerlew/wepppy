#!/usr/bin/env python3
"""Offline paired WEPP dewpoint study; never modifies source projects."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
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

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
ROOT = Path('/home/workdir/wepppy-scratch/dewpoint-openet-20261008')
BINARY = REPO / 'wepp_runner/bin/wepp_260803_hill'
SLUGS = ['hand-to-mouth-drought', 'apostolic-saw', 'cryptic-beechnut']
LABELS = ['Topanga', 'Tiger-Mill', 'Cascade foothills']
MODELS = ['Ensemble', 'eeMETRIC', 'PTJPL', 'SSEBop']
START, END = '2016-01-01', '2022-12-31'
ANCILLARY = ['wepp_ui.txt', 'pmetpara.txt', 'snow.txt', 'gwcoeff.txt', 'tc.txt', 'chntyp.txt']


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def load_manifest():
    return json.loads((HERE / 'manifest.json').read_text())


def cli_rows(path):
    lines = path.read_text().splitlines(keepends=True)
    rows = [line.split() for line in lines[15:]]
    if any(len(row) != 13 for row in rows):
        raise ValueError(f'Unexpected climate row: {path}')
    dates = pd.to_datetime([f'{r[2]}-{r[1]}-{r[0]}' for r in rows], format='%Y-%m-%d')
    return lines, rows, dates


def prepare():
    from metpy.calc import dewpoint_from_relative_humidity
    from metpy.units import units
    import metpy
    from shapely.geometry import shape

    if (HERE / 'manifest.json').exists():
        raise FileExistsError('Preparation already frozen; verify/reuse it.')
    metadata = json.loads(BINARY.with_suffix('.json').read_text())
    assert digest(BINARY) == metadata['sha256']
    manifest = {'created_utc': datetime.now(timezone.utc).isoformat(),
                'root': str(ROOT), 'binary': str(BINARY), 'binary_metadata': metadata,
                'metpy_version': metpy.__version__, 'assessment': [START, END],
                'selection': 'Dominant cover 52 (Topanga) or 42 (forests), area >=27000 m2; nearest 20/50/80% elevation quantiles, unique IDs; no response-based selection.',
                'sites': [], 'source_reconstruction': []}
    ROOT.mkdir(parents=True, exist_ok=True)
    for slug, label in zip(SLUGS, LABELS):
        source = Path('/wc1/runs') / slug[:2] / slug
        scenario = source / '_pups/omni/scenarios/undisturbed' if slug == SLUGS[0] else source
        source_runs = scenario / 'wepp/runs'
        gridpath = next((source / 'climate').glob('gridmet_*.parquet'))
        df = pd.read_parquet(gridpath)
        assert df.index.equals(pd.date_range(df.index.min(), df.index.max()))
        raw = dewpoint_from_relative_humidity(df['tavg(degc)'].to_numpy() * units.degC,
                                              df['ravg(%)'].to_numpy() * units.percent).magnitude
        clipped = np.maximum(raw, df['tmmn(degc)'].to_numpy())
        np.testing.assert_array_equal(clipped, df['tdew(degc)'].to_numpy())
        df['raw_tdew(degc)'] = raw
        df.to_parquet(HERE / f'{slug}-forcing.parquet')
        manifest['source_reconstruction'].append({'slug': slug, 'source': str(gridpath),
            'sha256': digest(gridpath), 'days': len(df), 'clipped_days': int(sum(raw < clipped)),
            'max_floor_c': float(np.max(clipped - raw)), 'reclip_max_difference_c': 0.0})
        hills = pd.read_parquet(source / 'watershed/hillslopes.parquet')
        cover = json.loads((scenario / 'landuse.nodb').read_text())['py/state']['domlc_d']
        hills['cover'] = hills.topaz_id.astype(str).map(cover)
        eligible = hills[(hills.area >= 27000) & (hills.cover == ('52' if slug == SLUGS[0] else '42'))].copy()
        geo = source / ('dem/topaz/SUBCATCHMENTS.WGS.JSON' if slug == SLUGS[0]
                        else 'dem/wbt/subcatchments.WGS.geojson')
        features = {int(f['properties']['TopazID']): f for f in json.loads(geo.read_text())['features']}
        selected = set()
        for quantile in [.2, .5, .8]:
            target = eligible.elevation.quantile(quantile)
            ordered = eligible.assign(distance=abs(eligible.elevation - target)).sort_values(['distance', 'wepp_id'])
            row = next(r for _, r in ordered.iterrows() if int(r.wepp_id) not in selected)
            hill = int(row.wepp_id)
            selected.add(hill)
            site = f'{slug}-h{hill}'
            fixture = ROOT / 'fixtures' / site
            fixture.mkdir(parents=True)
            names = [f'p{hill}.{ext}' for ext in ['run', 'man', 'slp', 'sol', 'cli']] + ANCILLARY
            hashes = {}
            for name in names:
                src = source_runs / name
                shutil.copy2(src, fixture / name)
                hashes[name] = digest(src)
            assert int((fixture / f'p{hill}.man').read_text().splitlines()[1].split()[0]) == 1
            lines, rows, dates = cli_rows(fixture / f'p{hill}.cli')
            control_years = int((fixture / f'p{hill}.run').read_text().splitlines()[-2])
            # Actual observed daily record, not the CLIGEN header's nominal 100 years.
            assert dates.equals(df.index), (site, len(dates), len(df))
            assert dates[-1].year - dates[0].year + 1 == control_years
            np.testing.assert_allclose([float(r[-1]) for r in rows], np.round(clipped, 1), atol=.000001)
            geometry = features[int(row.topaz_id)]['geometry']
            assert shape(geometry).is_valid and not shape(geometry).is_empty
            record = {'site': site, 'watershed': label, 'slug': slug, 'hill': hill,
                      'topaz_id': int(row.topaz_id), 'cover': row.cover,
                      'elevation_m': float(row.elevation), 'aspect_deg': float(row.aspect),
                      'area_m2': float(row.area), 'approx_30m_pixels': float(row.area / 900),
                      'lon': float(row.centroid_lon), 'lat': float(row.centroid_lat),
                      'selection_quantile': quantile, 'source_runs': str(source_runs),
                      'source_hashes': hashes, 'geometry': geometry,
                      'start': str(dates.min().date()), 'end': str(dates.max().date()),
                      'days': len(dates), 'control_years': control_years,
                      'management_plant': (fixture / f'p{hill}.man').read_text().splitlines()[8]}
            record['assessment_changed_days'] = int(sum((np.round(raw, 1) != np.round(clipped, 1)) & (dates >= START) & (dates <= END)))
            record['changed_days'] = int(sum(np.round(raw, 1) != np.round(clipped, 1)))
            record['assessment_mean_dewpoint_reduction_c'] = float(np.mean((clipped - raw)[(dates >= START) & (dates <= END)]))
            for arm in ['clipped', 'raw']:
                runs = ROOT / site / arm / 'runs'
                runs.mkdir(parents=True)
                (runs.parent / 'output').mkdir()
                for name in names:
                    shutil.copy2(fixture / name, runs / name)
                if arm == 'raw':
                    changed = lines[:15]
                    for line, value, old in zip(lines[15:], raw, clipped):
                        # Preserve identical bytes on days unaffected by upstream flooring.
                        if round(value, 1) != round(old, 1):
                            line = re.sub(r'\S+(\s*)$', lambda m: f'{value:.1f}' + m[1], line)
                        changed.append(line)
                    (runs / f'p{hill}.cli').write_text(''.join(changed))
            manifest['sites'].append(record)
    save(HERE / 'manifest.json', manifest)
    with tarfile.open(HERE / 'fixtures.tar.gz', 'w:gz') as archive:
        archive.add(ROOT / 'fixtures', arcname='fixtures')
    save(HERE / 'fixtures-archive.json', {'sha256': digest(HERE / 'fixtures.tar.gz')})
    print('Prepared', len(manifest['sites']), 'sites; frozen manifest and input archive.')


def run_case(site, arm):
    case = ROOT / site['site'] / arm
    result = case / 'execution.json'
    if result.exists():
        prior = json.loads(result.read_text())
        if prior['returncode'] != 0:
            raise RuntimeError(f'Prior failure retained at {case}; resolve explicitly.')
        return prior
    start = time.monotonic()
    with (case / 'runs' / f"p{site['hill']}.run").open('rb') as stdin, (case / 'stdout.log').open('wb') as out, (case / 'stderr.log').open('wb') as err:
        completed = subprocess.run([str(BINARY)], cwd=case / 'runs', stdin=stdin,
                                   stdout=out, stderr=err, timeout=240, check=False)
    terminal = (case / 'stdout.log').read_text(errors='replace')
    info = {'site': site['site'], 'arm': arm, 'returncode': completed.returncode,
            'seconds': time.monotonic() - start, 'binary_sha256': digest(BINARY),
            'normal_completion': 'WEPP COMPLETED' in terminal.upper(),
            'output_hashes': {p.name: digest(p) for p in (case / 'output').iterdir() if p.is_file()}}
    save(result, info)
    print(site['site'], arm, completed.returncode, round(info['seconds'], 2), flush=True)
    if completed.returncode:
        raise RuntimeError(f'Model failure: {case}')
    return info


def run():
    manifest = load_manifest()
    assert digest(BINARY) == manifest['binary_metadata']['sha256']
    jobs = [(s, arm) for s in manifest['sites'] for arm in ['clipped', 'raw']]
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(lambda args: run_case(*args), jobs))
    save(HERE / 'executions.json', results)


def request_openet(site, model, key):
    import requests
    path = HERE / 'openet' / f"{site['site']}-{model}.json"
    payload = {'date_range': [START, END], 'interval': 'monthly',
               'geojson': {'type': 'FeatureCollection', 'features': [
                   {'type': 'Feature', 'properties': {}, 'geometry': site['geometry']}]},
               'model': model, 'variable': 'ET', 'reference_et': 'gridMET',
               'reducer': 'mean', 'units': 'mm', 'file_format': 'JSON', 'version': 2.1}
    if path.exists():
        prior = json.loads(path.read_text())
        assert prior['request'] == payload
        if prior['status'] != 200:
            raise RuntimeError(f'Prior API failure retained at {path}')
        return
    started = time.monotonic()
    try:
        response = requests.post('https://openet-api.org/raster/timeseries/polygon',
                                 json=payload, headers={'Authorization': key},
                                 timeout=180, allow_redirects=False)
    except requests.RequestException as error:
        # Credential boundary: record exception type, never request headers or repr.
        save(path.with_name(path.stem + '-transport-failure.json'), {
            'request': payload, 'exception_type': type(error).__name__,
            'retrieved_utc': datetime.now(timezone.utc).isoformat(),
            'seconds': time.monotonic() - started})
        raise RuntimeError(f'OpenET transport failure for {site["site"]}/{model}') from None
    # Never persist request headers, exceptions containing them, or credential echoes.
    body = response.text.replace(key, '[REDACTED]')
    evidence = {'request': payload, 'status': response.status_code,
                'retrieved_utc': datetime.now(timezone.utc).isoformat(),
                'seconds': time.monotonic() - started, 'body': body}
    save(path, evidence)
    print(site['site'], model, response.status_code, round(evidence['seconds'], 2), flush=True)
    if response.status_code != 200:
        raise RuntimeError(f'OpenET status {response.status_code}; evidence {path}')


def openet(probe=False):
    key = Path('~/openet.key').expanduser().read_text().strip()
    assert key
    sites = load_manifest()['sites']
    jobs = [(s, m) for s in sites for m in MODELS]
    if probe:
        jobs = jobs[:1]
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda job: request_openet(*job, key), jobs))


def water(site, arm):
    path = ROOT / site['site'] / arm / 'output' / f"H{site['hill']}.wat.dat"
    data = []
    for line in path.read_text().splitlines():
        fields = line.split()
        if len(fields) == 25 and fields[0].isdigit():
            data.append([float(x) for x in fields])
    names = ['ofe', 'jday', 'year', 'p', 'rain_melt', 'q', 'ep', 'es', 'er', 'dp',
             'runon', 'subrunon', 'lat', 'sw', 'frozen', 'swe', 'qofe', 'drain',
             'irrigation', 'area', 'total_soil_water', 'profile_depth', 'porosity', 'fc', 'wp']
    df = pd.DataFrame(data, columns=names)
    assert len(df) == site['days'], (site['site'], arm, len(df), site['days'])
    assert np.isfinite(df.to_numpy()).all()
    assert (df.ofe == 1).all()
    dates = pd.to_datetime(df.year.astype(int).astype(str)) + pd.to_timedelta(df.jday - 1, unit='D')
    df.index = pd.DatetimeIndex(dates)
    assert df.index.equals(pd.date_range(site['start'], site['end']))
    df['et'] = df.ep + df.es + df.er
    return df


def verify():
    from pyproj import Geod
    from shapely.geometry import shape

    manifest = load_manifest()
    checks, spatial, quality, quality_events = [], [], [], []
    for site in manifest['sites']:
        area = abs(Geod(ellps='WGS84').geometry_area_perimeter(shape(site['geometry']))[0])
        assert abs(area / site['area_m2'] - 1) < .01
        spatial.append({'site': site['site'], 'model_area_m2': site['area_m2'],
                        'polygon_area_m2': area, 'relative_difference': area / site['area_m2'] - 1,
                        'approx_30m_pixels': area / 900})
        a = ROOT / site['site'] / 'clipped/runs'
        b = ROOT / site['site'] / 'raw/runs'
        for name, expected in site['source_hashes'].items():
            assert digest(a / name) == expected
            assert digest(Path(site['source_runs']) / name) == expected
            if not name.endswith('.cli'):
                assert digest(b / name) == expected
        al, ar, ad = cli_rows(a / f"p{site['hill']}.cli")
        bl, br, bd = cli_rows(b / f"p{site['hill']}.cli")
        assert al[:15] == bl[:15]
        assert ad.equals(bd)
        assert all(x[:-1] == y[:-1] for x, y in zip(ar, br))
        assert sum(x[-1] != y[-1] for x, y in zip(ar, br)) == site['changed_days']
        forcing = pd.read_parquet(HERE / f"{site['slug']}-forcing.parquet")
        np.testing.assert_allclose([float(r[-1]) for r in br], np.round(forcing['raw_tdew(degc)'], 1), atol=.000001)
        for arm in ['clipped', 'raw']:
            case = ROOT / site['site'] / arm
            evidence = json.loads((case / 'execution.json').read_text())
            assert evidence['returncode'] == 0 and evidence['normal_completion']
            assert evidence['binary_sha256'] == manifest['binary_metadata']['sha256']
            for name, expected in evidence['output_hashes'].items():
                assert digest(case / 'output' / name) == expected
            df = water(site, arm)
            assert ((df.loc[START:END].groupby(df.loc[START:END].index.year).size()) >= 365).all()
            climate = np.array(ar if arm == 'clipped' else br, dtype=float)
            assessment = (ad >= START) & (ad <= END)
            climate = climate[assessment]
            quality.append({'site': site['site'], 'arm': arm,
                            'assessment_days': int(assessment.sum()),
                            'dewpoint_below_local_tmin_days': int(sum(climate[:, 12] < climate[:, 8])),
                            'dewpoint_above_local_tmax_days': int(sum(climate[:, 12] > climate[:, 7])),
                            'tmin_above_tmax_days': int(sum(climate[:, 8] > climate[:, 7])),
                            'negative_reported_et_days': int(sum(df.loc[START:END].et < 0)),
                            'negative_surface_runoff_days': int(sum(df.loc[START:END].q < 0))})
            for date, values in zip(ad[assessment], climate):
                if values[12] > values[7] or values[8] > values[7]:
                    quality_events.append({'site': site['site'], 'arm': arm,
                        'date': str(date.date()), 'tmin_c': values[8], 'tmax_c': values[7],
                        'tdew_c': values[12], 'dewpoint_excess_c': values[12] - values[7],
                        'temperature_inversion_c': max(values[8] - values[7], 0)})
            checks.append({'site': site['site'], 'arm': arm, 'daily_rows': len(df),
                           'assessment_days': len(df.loc[START:END]),
                           'finite': True, 'input_isolation': True})
    for source in manifest['source_reconstruction']:
        assert digest(source['source']) == source['sha256']
    save(HERE / 'validation.json', checks)
    pd.DataFrame(spatial).to_csv(HERE / 'spatial-support.csv', index=False)
    pd.DataFrame(quality).to_csv(HERE / 'climate-quality.csv', index=False)
    pd.DataFrame(quality_events).to_csv(HERE / 'climate-quality-events.csv', index=False)
    print('Verified', len(checks), 'daily series and paired input isolation.')


def analyze():
    manifest = load_manifest()
    monthly = []
    for site in manifest['sites']:
        for arm in ['clipped', 'raw']:
            full = water(site, arm)
            df = full.loc[START:END]
            fluxes = df[['p', 'q', 'lat', 'dp', 'ep', 'es', 'er', 'et', 'rain_melt']].resample('MS').sum()
            fluxes['sw_mean'] = df.total_soil_water.resample('MS').mean()
            fluxes['swe_mean'] = df.swe.resample('MS').mean()
            fluxes['swe_max'] = df.swe.resample('MS').max()
            fluxes['snow_days'] = (df.swe > 1).resample('MS').sum()
            fluxes['sw_end'] = df.total_soil_water.resample('MS').last()
            fluxes['swe_end'] = df.swe.resample('MS').last()
            fluxes['site'] = site['site']
            fluxes['watershed'] = site['watershed']
            fluxes['arm'] = arm
            monthly.append(fluxes.rename_axis('date').reset_index())
    monthly = pd.concat(monthly, ignore_index=True)
    monthly.to_csv(HERE / 'wepp-monthly.csv', index=False)
    observations = []
    for site in manifest['sites']:
        for model in MODELS:
            evidence = json.loads((HERE / 'openet' / f"{site['site']}-{model}.json").read_text())
            assert evidence['status'] == 200
            body = json.loads(evidence['body'])
            df = pd.DataFrame(body)
            df['date'] = pd.to_datetime(df.time)
            assert pd.DatetimeIndex(df.date).equals(pd.date_range(START, END, freq='MS'))
            df['site'], df['model'] = site['site'], model
            assert np.isfinite(pd.to_numeric(df.et).dropna()).all()
            observations.append(df[['site', 'model', 'date', 'et']])
    obs = pd.concat(observations, ignore_index=True)
    obs.to_csv(HERE / 'openet-monthly.csv', index=False)
    metrics, annual, sensitivity, quality_sensitivity = [], [], [], []
    flags = pd.read_csv(HERE / 'climate-quality-events.csv')
    flagged_months = set(zip(flags.site, pd.to_datetime(flags.date).dt.to_period('M').astype(str)))
    snow = monthly.groupby(['site', 'date']).swe_max.max().rename('paired_swe_max').reset_index()
    for (site, arm), group in monthly.groupby(['site', 'arm']):
        for model in MODELS:
            matched = group.merge(obs[(obs.site == site) & (obs.model == model)], on=['site', 'date'], suffixes=('_wepp', '_openet'))
            matched = matched.merge(snow, on=['site', 'date'], validate='one_to_one')
            usable = matched[['et_wepp', 'et_openet']].notna().all(axis=1)
            residual = matched.loc[usable, 'et_wepp'] - matched.loc[usable, 'et_openet']
            low_snow = usable & (matched.paired_swe_max <= 1)
            low_snow_residual = matched.loc[low_snow, 'et_wepp'] - matched.loc[low_snow, 'et_openet']
            unflagged = [
                (site, str(date.to_period('M'))) not in flagged_months for date in matched.date
            ]
            quality_errors = matched.loc[unflagged, 'et_wepp'] - matched.loc[unflagged, 'et_openet']
            quality_sensitivity.append({'site': site, 'arm': arm, 'model': model,
                'retained_months': int(quality_errors.notna().sum()),
                'monthly_mae_mm': quality_errors.abs().mean(),
                'monthly_rmse_mm': np.sqrt((quality_errors ** 2).mean())})
            metrics.append({'site': site, 'arm': arm, 'model': model, 'months': int(usable.sum()),
                'monthly_bias_mm': residual.mean(), 'monthly_mae_mm': residual.abs().mean(),
                'monthly_rmse_mm': np.sqrt((residual ** 2).mean()),
                'mean_annual_wepp_et_mm': group.et.sum() / 7,
                'mean_annual_openet_et_mm': matched.et_openet.sum(min_count=len(matched)) / 7,
                'mean_annual_p_mm': group.p.sum() / 7,
                'low_snow_months': int(low_snow.sum()),
                'low_snow_mae_mm': low_snow_residual.abs().mean(),
                'low_snow_rmse_mm': np.sqrt((low_snow_residual ** 2).mean())})
            for year, year_data in matched.groupby(matched.date.dt.year):
                errors = year_data.et_wepp - year_data.et_openet
                annual.append({'site': site, 'arm': arm, 'model': model, 'year': year,
                               'months': int(errors.notna().sum()),
                               'wepp_et_mm': year_data.et_wepp.sum(min_count=12),
                               'openet_et_mm': year_data.et_openet.sum(min_count=12),
                               'p_mm': year_data.p.sum(), 'monthly_mae_mm': errors.abs().mean(),
                               'monthly_rmse_mm': np.sqrt((errors ** 2).mean())})
            if model == 'Ensemble' and not site.startswith(SLUGS[0]):
                for factor in [1.20, 1.25]:
                    errors = matched.et_wepp - matched.et_openet / factor
                    sensitivity.append({'site': site, 'arm': arm, 'factor': factor,
                        'monthly_mae_mm': errors.abs().mean(),
                        'monthly_rmse_mm': np.sqrt((errors ** 2).mean()),
                        'low_snow_mae_mm': errors[low_snow].abs().mean()})
    metrics = pd.DataFrame(metrics)
    annual = pd.DataFrame(annual)
    sensitivity = pd.DataFrame(sensitivity)
    metrics.to_csv(HERE / 'comparison-metrics.csv', index=False)
    annual.to_csv(HERE / 'annual-comparison.csv', index=False)
    sensitivity.to_csv(HERE / 'ensemble-bias-sensitivity.csv', index=False)
    pd.DataFrame(quality_sensitivity).to_csv(HERE / 'climate-quality-sensitivity.csv', index=False)
    comparisons = metrics.pivot(index=['site', 'model'], columns='arm')
    year_comparisons = annual[annual.model == 'Ensemble'].pivot(index=['site', 'year'], columns='arm')
    conclusions = {'sites': len(manifest['sites']), 'watersheds': 3,
                   'openet_series': len(observations), 'openet_monthly_values': int(obs.et.count()),
                   'missing_openet_values': int(obs.et.isna().sum()), 'comparisons': len(comparisons),
                   'clipped_lower_annual_monthly_mae_count': int(sum(year_comparisons.monthly_mae_mm.clipped < year_comparisons.monthly_mae_mm.raw)),
                   'annual_ensemble_comparisons': len(year_comparisons)}
    for metric in ['monthly_mae_mm', 'monthly_rmse_mm', 'low_snow_mae_mm', 'low_snow_rmse_mm']:
        conclusions[f'clipped_lower_{metric}_count'] = int(sum(comparisons[metric].clipped < comparisons[metric].raw))
    save(HERE / 'conclusions.json', conclusions)
    summaries = []
    for site in manifest['sites']:
        clipped = monthly[(monthly.site == site['site']) & (monthly.arm == 'clipped')].set_index('date')
        raw = monthly[(monthly.site == site['site']) & (monthly.arm == 'raw')].set_index('date')
        record = {k: site[k] for k in ['site', 'watershed', 'hill', 'topaz_id', 'elevation_m', 'aspect_deg', 'area_m2', 'assessment_changed_days', 'assessment_mean_dewpoint_reduction_c']}
        for name in ['p', 'et', 'q', 'lat', 'dp']:
            record[f'clipped_{name}_mm_y'] = clipped[name].sum() / 7
            record[f'raw_{name}_mm_y'] = raw[name].sum() / 7
            record[f'delta_{name}_mm_y'] = (raw[name] - clipped[name]).sum() / 7
        record['delta_sw_mean_mm'] = (raw.sw_mean - clipped.sw_mean).mean()
        record['delta_swe_mean_mm'] = (raw.swe_mean - clipped.swe_mean).mean()
        record['delta_snow_days_per_year'] = (raw.snow_days - clipped.snow_days).sum() / 7
        record['max_abs_monthly_et_change_mm'] = (raw.et - clipped.et).abs().max()
        for arm in ['clipped', 'raw']:
            full = water(site, arm)
            previous = full.loc['2015-12-31']
            last = full.loc[END]
            period = full.loc[START:END]
            storage_change = last.total_soil_water + last.swe - previous.total_soil_water - previous.swe
            # Residual includes unreported interception-storage change and snow sublimation.
            residual = period.p.sum() - period.et.sum() - period.q.sum() - period.lat.sum() - period.dp.sum() - storage_change
            record[f'{arm}_accounting_residual_mm_y'] = residual / 7
        summaries.append(record)
    summary = pd.DataFrame(summaries)
    summary.to_csv(HERE / 'paired-summary.csv', index=False)
    plots(monthly, obs, manifest['sites'])
    print(summary[['watershed', 'hill', 'clipped_et_mm_y', 'raw_et_mm_y', 'delta_et_mm_y']].to_string(index=False))


def plots(monthly, obs, sites):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(3, 3, figsize=(16, 10), sharex=True, constrained_layout=True)
    for ax, site in zip(axes.flat, sites):
        observed = obs[obs.site == site['site']].pivot(index='date', columns='model', values='et')
        ax.fill_between(observed.index, observed[['eeMETRIC', 'PTJPL', 'SSEBop']].min(axis=1),
                        observed[['eeMETRIC', 'PTJPL', 'SSEBop']].max(axis=1), color='0.8', label='3-model range')
        ax.plot(observed.index, observed.Ensemble, color='black', lw=1, label='OpenET ensemble')
        for arm, color in [('clipped', '#2563eb'), ('raw', '#ea580c')]:
            group = monthly[(monthly.site == site['site']) & (monthly.arm == arm)]
            ax.plot(group.date, group.et, color=color, lw=1, label=arm)
        ax.set_title(f"{site['watershed']} H{site['hill']} · {site['elevation_m']:.0f} m")
        ax.set_ylabel('ET (mm/month)')
        ax.grid(alpha=.2)
    axes[0, 0].legend(fontsize=8)
    fig.suptitle('Dewpoint clipping: paired WEPP and hillslope-mean OpenET, 2016–2022\nGray range is three component models, not a confidence interval')
    fig.savefig(HERE / 'monthly-et.png', dpi=160)
    fig.savefig(HERE / 'monthly-et.svg')
    plt.close(fig)
    fig, axes = plt.subplots(1, 3, figsize=(14, 4), constrained_layout=True)
    for ax, label in zip(axes, LABELS):
        for site in [s for s in sites if s['watershed'] == label]:
            group = monthly[monthly.site == site['site']].pivot(index='date', columns='arm', values='et')
            delta = group.raw - group.clipped
            ax.plot(delta.groupby(delta.index.month).mean(), marker='o', label=f"H{site['hill']}")
        ax.axhline(0, color='0.4', lw=.7)
        ax.set_title(label)
        ax.set_xlabel('Month')
        ax.set_ylabel('Raw − clipped ET (mm/month)')
        ax.legend()
        ax.grid(alpha=.2)
    fig.savefig(HERE / 'seasonal-effect.png', dpi=160)
    fig.savefig(HERE / 'seasonal-effect.svg')
    plt.close(fig)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=['prepare', 'run', 'probe', 'openet', 'analyze', 'verify'])
    phase = parser.parse_args().phase
    if phase == 'probe':
        openet(probe=True)
    else:
        globals()[phase]()
