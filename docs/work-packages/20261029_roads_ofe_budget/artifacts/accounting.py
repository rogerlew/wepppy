"""Audited boundary fluxes for the frozen 66-case Roads study; no fitting."""
from __future__ import annotations

import argparse
import calendar
from copy import deepcopy
import hashlib
import importlib.util
import itertools
import json
import math
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
ROLES = ('road', 'fill', 'buffer')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def grouped(rows, fields, expected_dates=None):
    """Require finite audited fields and exactly three unique OFEs per date."""
    result = {}
    for row in rows:
        key = (row['year'], row['julian'])
        if not 1 <= key[1] <= 365 + calendar.isleap(key[0]):
            raise ValueError('Invalid date')
        ofe = row['OFE']
        if ofe not in (1, 2, 3) or ofe in result.setdefault(key, {}):
            raise ValueError('Duplicate or invalid OFE')
        if any(row[k] is None or not math.isfinite(row[k]) for k in fields):
            raise ValueError('Nonfinite budget field')
        result[key][ofe] = row
    if not result or any(set(v) != {1, 2, 3} for v in result.values()):
        raise ValueError('Missing OFE')
    if expected_dates is not None and set(result) != set(expected_dates):
        raise ValueError('Calendar mismatch')
    return result


def sediment_budget(rows, width, years, report_export, *, strict=True):
    days = grouped(rows, ('SedLeave',))
    totals = [dict(boundary_kg_yr=0., net_kg_yr=0., positive_daily_net_kg_yr=0., negative_daily_net_kg_yr=0.) for _ in ROLES]
    for day in days.values():
        upstream = 0.
        for ofe in (1, 2, 3):
            flux = day[ofe]['SedLeave'] * width / years
            if flux < 0:
                raise ValueError('Negative boundary sediment')
            net = flux - upstream
            for key, value in [('boundary_kg_yr', flux), ('net_kg_yr', net),
                               ('positive_daily_net_kg_yr', max(net, 0)), ('negative_daily_net_kg_yr', min(net, 0))]:
                totals[ofe - 1][key] += value
            upstream = flux
    # ELEMENT f8.3 per event; report f12.3 annual kg/m. Floating accumulation
    # allowance matches the preceding common-report validation (1e-6 relative).
    bound = (len(days) * .0005 / years + .0005) * width + abs(report_export) * 1e-6
    delta = totals[-1]['boundary_kg_yr'] - report_export
    if strict and abs(delta) > bound:
        raise ValueError(f'ELEMENT/report mismatch: {delta} > {bound}')
    return dict(ofes=totals, dates=len(days), report_delta_kg_yr=delta, report_bound_kg_yr=bound, report_reconciled=abs(delta)<=bound), days


def ebe_check(rows, elements, *, strict=True):
    seen, maximum = set(), 0.
    mismatches = []
    for row in rows:
        key = (row['year'], row['julian'])
        if key in seen or key not in elements:
            raise ValueError('EBE date missing or duplicate')
        seen.add(key)
        value = row['Sed.Del']
        if value is None or not math.isfinite(value):
            raise ValueError('Nonfinite EBE sediment')
        delta = abs(value - elements[key][3]['SedLeave'])
        if delta > .0505 + abs(value) * 1e-6:
            mismatches.append(dict(date=key, ebe_kg_m=value, element_kg_m=elements[key][3]['SedLeave'], delta_kg_m=delta))
            if strict:
                raise ValueError(f'EBE/ELEMENT mismatch: {key}, {delta}')
        maximum = max(maximum, delta)
    if not seen or any(day[3]['SedLeave'] != 0 for key, day in elements.items() if key not in seen):
        raise ValueError('Missing EBE sediment event')
    return dict(dates=len(seen), max_delta_kg_m=maximum, mismatches=mismatches)


def water_budget(rows, areas, dates, years):
    fields = ('Area', 'P', 'RM', 'Q', 'UpStrmQ', 'SubRIn', 'latqcc', 'Dp', 'Ep', 'Es', 'Er', 'Tile', 'SoilWaterTotal')
    days = grouped(rows, fields, dates)
    cumulative = [sum(areas[:i + 1]) for i in range(3)]
    totals = [dict(surface_out_m3_yr=0., surface_in_m3_yr=0., lateral_out_m3_yr=0., lateral_in_m3_yr=0.,
                   precipitation_m3_yr=0., rain_melt_m3_yr=0., et_m3_yr=0., deep_percolation_m3_yr=0.,
                   apparent_soil_residual_m3=0.) for _ in ROLES]
    max_surface = max_lateral = 0.
    previous_stock = None
    for date in sorted(days):
        day = days[date]
        stocks = []
        surface, lateral = 0., 0.
        for i, area in enumerate(areas):
            r = day[i + 1]
            if abs(r['Area'] - area) > .0051:
                raise ValueError('WAT area disagrees with emitted geometry')
            q = r['Q'] * cumulative[i] / 1000
            incoming = r['UpStrmQ'] * area / 1000
            sub = r['SubRIn'] * area / 1000
            lat = r['latqcc'] * area / 1000
            surface_delta, lateral_delta = abs(incoming - surface), abs(sub - lateral)
            # e15.7 output plus native single-precision length/flux arithmetic.
            if surface_delta > 5e-6 * max(abs(incoming), abs(surface)) + 1e-7:
                raise ValueError(f'Surface transfer mismatch: {surface_delta}')
            if lateral_delta > .005 * (area + (areas[i-1] if i else 0)) / 1000 + 1e-7:
                raise ValueError('Lateral transfer mismatch')
            max_surface, max_lateral = max(max_surface, surface_delta), max(max_lateral, lateral_delta)
            et = sum(r[k] for k in ('Ep', 'Es', 'Er')) * area / 1000
            rm, dp = r['RM'] * area / 1000, r['Dp'] * area / 1000
            stock = r['SoilWaterTotal'] * area / 1000
            stocks.append(stock)
            values = dict(surface_out_m3_yr=q, surface_in_m3_yr=incoming,
                          lateral_out_m3_yr=lat, lateral_in_m3_yr=sub,
                          precipitation_m3_yr=r['P'] * area / 1000, rain_melt_m3_yr=rm,
                          et_m3_yr=et, deep_percolation_m3_yr=dp)
            for key, value in values.items():
                totals[i][key] += value / years
            if previous_stock is not None:
                totals[i]['apparent_soil_residual_m3'] += rm + incoming + sub - q - lat - et - dp - r['Tile'] * area / 1000 - (stock - previous_stock[i])
            else:
                totals[i]['first_reported_stock_m3'] = stock
            totals[i]['last_reported_stock_m3'] = stock
            surface, lateral = q, lat
        previous_stock = stocks
    return dict(ofes=totals, days=len(days), max_surface_transfer_delta_m3=max_surface, max_lateral_transfer_delta_m3=max_lateral,
                residual_days=len(days)-1, residual_is_complete_water_closure=False)


def invariant_soil(ofes):
    fixed = deepcopy(ofes)
    for ofe in fixed:
        for key in ('ksatadj', 'ksatfac', 'ksatrec'):
            del ofe[key]
        for h in ofe['horizons']:
            del h['ksat']
    return fixed


def validate_factorial(records):
    variants = {r['case']['variant']: r for r in records if r['case']['variant'] in {''.join(v) for v in itertools.product('01', repeat=3)}}
    if len(variants) != 8:
        raise ValueError('Incomplete factorial')
    reference = variants['000']['soil_readback']
    for variant, record in variants.items():
        ofes = record['soil_readback']
        if invariant_soil(ofes) != invariant_soil(reference):
            raise ValueError('Nonhydraulic factorial change')
        for i, ofe in enumerate(ofes):
            if 200 not in [h['solthk'] for h in ofe['horizons']]:
                raise ValueError('Missing normalized boundary')
            endpoint = variants['111' if variant[i]=='1' else '000']['soil_readback'][i]
            if ofe != endpoint:
                raise ValueError('Factorial toggle leaked across OFEs')
            for h, neutral in zip(ofe['horizons'], reference[i]['horizons']):
                if h['solthk'] > 200 and h != neutral:
                    raise ValueError('Deeper horizon changed')


def analyze(root, batch, destination):
    import pyarrow.parquet as pq
    import wepppyo3
    from wepppy.wepp.interchange.hill_element_interchange import run_wepp_hillslope_element_interchange
    from wepppy.wepp.interchange.hill_wat_interchange import run_wepp_hillslope_wat_interchange
    from wepppy.wepp.interchange.hill_ebe_interchange import run_wepp_hillslope_ebe_interchange
    spec = importlib.util.spec_from_file_location('frozen_roads_study', HERE / 'study.py')
    study = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(study)
    from wepppy.wepp.soils.utils import WeppSoilUtil

    destination.mkdir(exist_ok=False)
    shutil.copyfile(__file__, destination / 'executed-accounting.py')
    manifest = json.loads((root/'inputs/manifest.json').read_text())
    declaration = json.loads((root/'declaration.json').read_text())
    for name, sha in declaration['native_source_sha256'].items():
        if digest(root/'native-source'/name) != sha:
            raise ValueError('Native source drift')
    records = json.loads((root/batch/'summary.json').read_text())
    expected = json.loads((root/batch/'cases.json').read_text())
    if len(records) != 66 or [r['case'] for r in records] != expected or len({r['name'] for r in records}) != 66:
        raise ValueError('Incomplete case matrix')
    hashes = {str(Path(__file__).resolve()): digest(__file__), str(Path(wepppyo3.__file__).resolve()): digest(wepppyo3.__file__)}
    for fn in (run_wepp_hillslope_element_interchange, run_wepp_hillslope_wat_interchange, run_wepp_hillslope_ebe_interchange):
        p = Path(fn.__globals__['__file__']); hashes[str(p)] = digest(p)
    for p in Path(wepppyo3.__file__).parent.glob('*.so'):
        hashes[str(p)] = digest(p)
    dump(destination/'provenance.json', dict(root=str(root), batch=batch, hashes=hashes, source_commit=declaration['source_commit']))
    result = []
    for index, record in enumerate(records):
        folder = root/batch/record['name']
        if record['status'] != 'completed' or json.loads((folder/'record.json').read_text()) != record:
            raise ValueError('Record drift')
        for subdir, key in [('runs','inputs'),('output','outputs')]:
            for name, sha in record[key].items():
                if digest(folder/subdir/name) != sha:
                    raise ValueError(f'Artifact drift: {folder}/{subdir}/{name}')
        if digest(record['binary']['path']) != record['binary']['sha256']:
            raise ValueError('Binary drift')
        if record['soil_readback'] is not None and WeppSoilUtil(str(folder/'runs/p1.sol')).obj['ofes'] != record['soil_readback']:
            raise ValueError('Soil readback drift')
        if study.b.parse_loss(folder/'output/H1.loss.dat', record['width_m']) != record['metrics']:
            raise ValueError('Report metric drift')
        out = dict(name=record['name'], case=record['case'], metrics=record['metrics'])
        climate = manifest['climates'][record['case']['climate']]
        first_year = int(climate['first'].split('-')[0])
        last_year = int(climate['last'].split('-')[0])
        study.b.validate_wat(folder/'output/H1.wat.dat', climate)
        if record['case']['binary'] == 'modern':
            readers = [(run_wepp_hillslope_element_interchange,dict(start_year=first_year)),
                       (run_wepp_hillslope_wat_interchange,{}),
                       (run_wepp_hillslope_ebe_interchange,dict(start_year=first_year))]
            tables = [pq.read_table(fn(folder/'output', expected_hillslopes=1, **kw)).to_pylist() for fn,kw in readers]
            out['sediment'], elements = sediment_budget(tables[0], record['width_m'], 16, record['metrics']['sediment_export_kg_yr'], strict=False)
            out['ebe'] = ebe_check(tables[2], elements, strict=False)
            dates = {(y,j) for y in range(first_year,last_year+1) for j in range(1,366+calendar.isleap(y))}
            if not set(elements) <= dates:
                raise ValueError('ELEMENT dates outside climate')
            slope = [line for line in (folder/'runs/p1.slp').read_text().splitlines() if line and not line.startswith('#')]
            width = float(slope[2].split()[1])
            areas = [width * float(slope[i].split()[1]) for i in (3,5,7)]
            out['areas_m2'] = areas
            out['water'] = water_budget(tables[1], areas, dates, 16)
            out['pass'] = study.e.native_diagnostics(folder/'output/H1.pass.dat', destination/(record['name']+'-pass.parquet'))
            out['element_state_ranges'] = [{key: [min(r[key] for r in tables[0] if r['OFE']==i), max(r[key] for r in tables[0] if r['OFE']==i)] for key in ('Keff','Ki','Kr','Tcrit','IntCov','RilCov')} for i in (1,2,3)]
        result.append(out)
        dump(destination/(record['name']+'.json'),out)
        print(f'{index+1}/66 accounted', flush=True)
    effects = []
    for profile in study.PANEL:
        prefix = '-'.join(profile)+'-'
        selected = [r for r in records if r['name'].startswith(prefix)]
        validate_factorial(selected)
        controls = [r for r in selected if r['case']['variant']=='legacy']
        for key in ('p1.run','p1.sol','p1.man','p1.cli','p1.slp'):
            if controls[0]['inputs'][key] != controls[1]['inputs'][key]:
                raise ValueError('Unmatched binary controls')
        for key in ('p1.man','p1.cli','p1.slp','p1.run'):
            if len({r['inputs'][key] for r in selected}) != 1:
                raise ValueError('Unmatched profile inputs')
        variants = {r['case']['variant']:r for r in result if r['name'].startswith(prefix) and r['case']['binary']=='modern'}
        baseline = next(r for r in result if r['name']==prefix+'legacy-legacy')['metrics']['sediment_export_kg_yr']
        for r in variants.values():
            r['report_ratio_to_2010'] = r['metrics']['sediment_export_kg_yr']/baseline if baseline>0 else None
        effect = dict(profile='-'.join(profile), legacy_2010_export_kg_yr=baseline, factors={})
        for i,role in enumerate(ROLES):
            pairs=[]
            for bits in itertools.product('01',repeat=3):
                if bits[i]=='1':continue
                a=''.join(bits);on=list(bits);on[i]='1';z=''.join(on)
                pairs.append(dict(off=a,on=z,export_delta_kg_yr=variants[z]['metrics']['sediment_export_kg_yr']-variants[a]['metrics']['sediment_export_kg_yr'],
                                  net_delta_kg_yr=[variants[z]['sediment']['ofes'][j]['net_kg_yr']-variants[a]['sediment']['ofes'][j]['net_kg_yr'] for j in range(3)]))
            values=[p['export_delta_kg_yr'] for p in pairs]
            effect['factors'][role]=dict(mean_delta_kg_yr=sum(values)/4,min_delta_kg_yr=min(values),max_delta_kg_yr=max(values),pairs=pairs)
        exports={v:r['metrics']['sediment_export_kg_yr'] for v,r in variants.items()}
        effect['all_on_minus_off_kg_yr']=exports['111']-exports['000']
        effect['nonadditivity_kg_yr']=effect['all_on_minus_off_kg_yr']-sum(exports[v]-exports['000'] for v in ('100','010','001'))
        effects.append(effect)
    dump(destination/'results.json',result)
    dump(destination/'effects.json',effects)
    dump(destination/'acceptance.json',dict(cases=66,modern_budgets=60,legacy_report_controls=6,factorials=6,structural_checks_passed=True,report_reconciled=sum(r.get("sediment",{}).get("report_reconciled",False) for r in result),ebe_mismatch_events=sum(len(r.get("ebe",{}).get("mismatches",[])) for r in result)))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--batch',default='factorial-v1')
    parser.add_argument('--destination',type=Path,required=True)
    args=parser.parse_args()
    analyze(args.root,args.batch,args.destination)
