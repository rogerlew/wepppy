"""Predeclared r7 production-template sensitivity plus one isolated generated lane."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path
import shutil
import subprocess

from tests.roads import roads_matrix as matrix
from tests.roads import roads_sensitivity as h
import rebaseline_r7_seeds as seeds

ART = Path(__file__).resolve().parent
ROOT = Path('/wc1/runs/ro/roads-parameterization-program-20261103/revised-sensitivity-v1')
DECLARATION = ROOT / 'declaration.json'
REPO = ART.parents[3]
PROTOCOL = ART / 'revised-sensitivity-protocol.md'
NATIVE_SOURCE = ROOT.parent / 'revised-sensitivity-native-source-v1'
BINS = {'wepp_261029': seeds.EXPECTED['r7'],
        'wepp_261029_hill': '210d48da09ff60707ba2404dd32af1f0a74e95437d2cb900c5408121141a1936'}
CONTEXTS = {
    'H': matrix.Case('median', 'silt', 'gravel', 'none', 'rutted'),
    'L': matrix.Case('median', 'sand', 'paved', 'none', 'rutted'),
    'P': matrix.Case('median', 'loam', 'gravel', 'low', 'rutted'),
    'U': matrix.Case('median', 'silt', 'paved', 'high', 'unrutted_three'),
}
ARMS = {'baseline': {}, 'width2': {'width_m': 2.}, 'width8': {'width_m': 8.},
        'fill10': {'fill_length_m': 10.}, 'fill60': {'fill_length_m': 60.},
        'slope2': {'fill_slope_pct': 2.}, 'slope30': {'fill_slope_pct': 30.},
        'width8_fill60': {'width_m': 8., 'fill_length_m': 60.}}
G_ARMS = ('exact', 'baseline', 'width2', 'width8', 'fill10', 'fill60', 'width8_fill60')


def dependencies():
    result = seeds.dependencies()
    for path in (Path(__file__), Path(h.__file__), Path(matrix.__file__), PROTOCOL,
                 REPO / 'tests/roads/matrix_results_current.json'):
        result[str(path.resolve())] = h.digest(path)
    for relative, digest in matrix.execution_identity()['source_sha256'].items():
        result[str((REPO / relative).resolve())] = digest
    for name, expected in BINS.items():
        path = REPO / 'wepp_runner/bin' / name
        if h.digest(path) != expected:
            raise ValueError('Installed binary identity changed')
        result[str(path.resolve())] = expected
    source = seeds.read(NATIVE_SOURCE / 'source-receipt.json')
    if source['source_commit'] != 'e0abe0581f77c6f66917e90daf8f8f429e9315c8':
        raise ValueError('Native source snapshot identity changed')
    h.verify(NATIVE_SOURCE, source['files'])
    for path in NATIVE_SOURCE.iterdir():
        result[str(path)] = h.digest(path)
    calendar_sources = [REPO / 'wepppy/climates/cli_parquet.py',
                        *(REPO / 'wepppy/climates/cligen').glob('*.py')]
    for path in calendar_sources:
        result[str(path.resolve())] = h.digest(path)
    return result


def verify_dependencies(bindings):
    for name, digest in bindings.items():
        if h.digest(name) != digest:
            raise ValueError(f'Dependency drift: {name}')


def generated(root, arm):
    """Preserve compatible road/fill/buffer material; explicit writer bridge only."""
    from wepppy.nodb.mods.roads import Roads
    from wepppy.wepp.soils.utils import WeppSoilUtil

    declaration = seeds.read(seeds.ROOT / 'declaration.json')
    task = next(r for r in declaration['tasks'] if r['stratum'] == 'underprediction_other_geometry'
                and r['version'] == 'r7' and r['lane'] == 'modern')
    source = Path(task['folder'])
    seeds.common.verify_files(source, task)
    original = seeds.read(source / 'record.json')
    seeds.common.verify_files(source, original)
    if task['case']['soil'] != '2711184' or task['case']['design'] != 'outrut':
        raise ValueError('Generated context identity changed')
    record = h.prepare(root, matrix.Case('median', 'loam', 'gravel', 'high', 'rutted'))
    runs = root / 'wepp/roads/runs'
    for name in task['inputs']:
        shutil.copyfile(source / 'runs' / name, runs / name)
    shutil.copyfile(source / 'runs/reference.sol', runs / 'reference.sol')
    if set(h.inventory(runs)) != set(task['inputs']) | {'reference.sol'}:
        raise ValueError('Generated runtime membership differs from retained capsule')
    values = dict(width_m=3.96, road_length_m=60.96, road_slope_pct=4.,
                  fill_length_m=4.57, fill_slope_pct=50., buffer_length_m=39.62, buffer_slope_pct=25.)
    if arm != 'exact':
        values.update(ARMS[arm])
        Roads._write_routed_three_ofe_slope_file(runs / 'p1.slp', **values)
    lines = [s for s in (runs / 'p1.slp').read_text().splitlines() if s and not s.startswith('#')]
    ofes = WeppSoilUtil(str(runs / 'p1.sol')).obj['ofes']
    if [o['luse'] for o in ofes] != ['bare', 'bare', 'forest']:
        raise ValueError('Generated road/fill/buffer material ownership changed')
    for field in ('management_readback', 'template_sha256'):
        del record[field]
    record.update(requested=values, effective_geometry=values, parity=None,
                  case=dict(task['case'], variant='sensitivity_' + arm),
                  name='generated-underprediction-' + arm, segment_id='generated-underprediction-' + arm,
                  soil_texture=None, rfg_pct=None,
                  clipping=dict(road_grade=False, unrutted_length=False, unrutted_width=False),
                  management_readback=matrix.read_management(runs / 'p1.man', runs / 'p1.man', (1, 2, 3)),
                  road_width_m=values['width_m'], segment_length_m=values['road_length_m'],
                  slope_pct_clamped=values['road_slope_pct'],
                  aspect_degrees=float(lines[2].split()[0]),
                  ofe_order=[1, 2, 3], soil_readback=ofes,
                  generated_source=task, original_outputs=original['outputs'],
                  source_record_sha256=h.digest(source / 'record.json'),
                  emitted=dict(width_m=float(lines[2].split()[1]),
                      lengths_m=[float(lines[i].split()[1]) for i in (3, 5, 7)],
                      slope_lines=[lines[i] for i in (4, 6, 8)]),
                  input_sha256={f'wepp/roads/runs/{name}': h.digest(runs / name) for name in task['inputs']},
                  prepared_files=h.inventory(runs),
                  requested_contrast={'geometry': ARMS.get(arm, {}), 'traffic': None})
    # h.prepare's original receipt remains as builder provenance; final input is
    # explicit and separately bound, never silently passed as that earlier deck.
    h.save_new(root / 'final-prepared.json', record)
    return record


def declare():
    dep = dependencies()
    ROOT.mkdir(parents=True, exist_ok=False)
    historical = seeds.read(REPO / 'tests/roads/matrix_results_current.json')['cases']
    rows = []
    selected = {}
    for label, case in CONTEXTS.items():
        selected[label] = next(row for row in historical if row['case'] == asdict(case))
        arms = [(arm, geometry, None) for arm, geometry in ARMS.items()]
        arms += [('traffic_' + traffic, {}, traffic) for traffic in ('high', 'low', 'none') if traffic != case.traffic]
        for arm, geometry, traffic in arms:
            root = ROOT / 'cases' / label / arm
            record = h.prepare(root, case, geometry=geometry, traffic=traffic)
            rows.append(dict(context=label, arm=arm, root=str(root), record=record, climate='site', generated=False))
    for arm in G_ARMS:
        root = ROOT / 'cases/G' / arm
        rows.append(dict(context='G', arm=arm, root=str(root), record=generated(root, arm), climate='denver', generated=True))
    generated_record = rows[-1]['record']
    source = Path(generated_record['generated_source']['folder'])
    dep[str(source / 'record.json')] = generated_record['source_record_sha256']
    for name, digest in generated_record['generated_source']['inputs'].items():
        dep[str(source / 'runs' / name)] = digest
    dep[str(source / 'runs/reference.sol')] = h.digest(source / 'runs/reference.sol')
    for name, digest in generated_record['original_outputs'].items():
        dep[str(source / 'output' / name)] = digest
    aliases = []
    for arrangement in ('bare_direct', 'rocked_direct', 'bare_buffer', 'rocked_buffer'):
        case = matrix.Case('median', 'loam', 'gravel', 'low', arrangement)
        for arm, geometry, traffic in [('baseline', {}, None), ('fill60', {'fill_length_m': 60.}, None), ('traffic_none', {}, 'none')]:
            root = ROOT / 'aliases' / arrangement / arm
            aliases.append(dict(arrangement=arrangement, arm=arm, root=str(root),
                                record=h.prepare(root, case, geometry=geometry, traffic=traffic)))
    if len(rows) != 47 or len(aliases) != 12:
        raise ValueError('Declared case count changed')
    verify_dependencies(dep)
    native_head = seeds.read(NATIVE_SOURCE / 'source-receipt.json')['release_head']
    if not native_head.startswith('547b9e7eb'):
        raise ValueError('Selected native release checkout changed')
    h.save_new(DECLARATION, dict(tasks=rows, aliases=aliases,
        historical_selection=selected, dependencies=dep, native_release_head=native_head,
        native_source='e0abe0581f77c6f66917e90daf8f8f429e9315c8', binaries=BINS,
        calls=47, withheld_materials_used=False, uid=os.getuid(), gid=os.getgid()))
    print('Prepared 47 native profiles and 12 alias probes; no native calls', flush=True)


def climate_for(row):
    if row['generated']:
        return seeds.read(seeds.common.c.BATCH / 'inputs/manifest.json')['climates'][row['climate']]
    from tests.roads.extract_fixture import DATA, climate_dates
    dates = climate_dates(DATA / 'site.cli')
    return dict(first=str(dates[0]), last=str(dates[-1]), days=len(dates),
                years=len({d.year for d in dates}), sha256=h.digest(DATA / 'site.cli'))


def audit(row):
    root = Path(row['root'])
    record = row['record']
    capsule = root / 'wepp/roads'
    climate = climate_for(row)
    parsed = dict(case=dict(climate=row['climate'], soil='2711184' if row['generated'] else record['case']['texture'],
                           design='outrut' if record['design'] == 'outslope_rutted' else 'outunrut',
                           surface=record['surface'], traffic=record['traffic'], variant=row['arm'], runtime='project'),
                  inputs={name: digest for name, digest in record['prepared_files'].items() if name != 'reference.sol'},
                  outputs={Path(k).name: v for k, v in record['output_sha256'].items()},
                  soil_readback=record['soil_readback'], width_m=record['emitted']['width_m'])
    parsed['metrics'] = seeds.common.c.b.parse_loss(capsule / 'output/H1.loss.dat', parsed['width_m'],
                                                  require_annual=row['generated'])
    h.save_new(capsule / 'record.json', parsed)
    physical = seeds.common.c.audit(capsule, parsed['case'], parsed)
    complete = seeds.pass_completeness.audit(capsule / 'record.json', climate)
    particle = seeds.particles.audit(capsule / 'record.json')
    stdout = (capsule / 'runs/stdout').read_text()
    markers = {key: marker in stdout for key, marker in {
        'ui': 'WEPP hourly water seepage update set (UI code)',
        'groundwater': 'Gwcoeff parameters set',
        'pmet': 'FAO Penman-Monteith ET Method Implemented'}.items()}
    if not all(markers.values()):
        raise ValueError('Native runtime activation differs from declaration')
    h.save_new(root / 'audits.json', dict(physical=physical, completeness=complete, particles=particle))
    return dict(physical_pass=physical['physical_pass'], calendar_pass=complete['passed'],
                particle_pass=particle['passed'], particle_flags=particle['flags'],
                role_water=physical['water'], role_sediment=physical['sediment'], runtime_markers=markers)


def run():
    d = seeds.read(DECLARATION)
    review = seeds.read(ROOT / 'execution-review.json')
    if review['declaration_sha256'] != h.digest(DECLARATION) or not review['passed']:
        raise ValueError('Independent execution review is absent or mismatched')
    verify_dependencies(d['dependencies'])
    h.save_new(ROOT / 'execution-start.json', {'declaration_sha256': h.digest(DECLARATION)})
    results = []
    for row in d['tasks']:
        root = Path(row['root'])
        try:
            row['record'] = h.execute(root, row['record'])
            if row['context'] == 'G' and row['arm'] == 'exact':
                actual = {Path(k).name: v for k, v in row['record']['output_sha256'].items()}
                if actual != row['record']['original_outputs']:
                    raise ValueError('Exact generated baseline failed seven-output reproduction')
            diagnostics = audit(row)
            climate = climate_for(row)
            response = h.summarize(root, row['record'], start_year=int(climate['first'][:4]), years=climate['years'])
        except Exception as exc:
            # Experiment boundary retains post-execution audit/parser failures.
            if not (root / 'failure.json').exists():
                h.save_new(root / 'failure.json', dict(exception=type(exc).__name__, message=str(exc),
                    artifacts=h.inventory(root / 'wepp/roads')))
            raise
        result = dict(context=row['context'], arm=row['arm'], root=str(root),
                      diagnostics=diagnostics, response=response)
        h.save_new(root / 'result.json', result)
        results.append(result)
        verify_dependencies(d['dependencies'])
        print(row['context'], row['arm'], response['summary']['sediment_yield_kg'],
              {k:v for k,v in diagnostics.items() if k.endswith('_pass')}, flush=True)
    h.save_new(ROOT / 'results.json', results)


def analyze():
    d = seeds.read(DECLARATION)
    verify_dependencies(d['dependencies'])
    results = seeds.read(ROOT / 'results.json')
    expected = {(r['context'], r['arm']) for r in d['tasks']}
    lookup = {(r['context'], r['arm']): r for r in results}
    if set(lookup) != expected or len(results) != len(expected):
        raise ValueError('Missing or duplicate sensitivity outcomes')
    prepared = {(r['context'], r['arm']): r['record'] for r in d['tasks']}
    metrics = ('sediment_yield_kg', 'runoff_volume_m3', 'soil_loss_kg',
               'modeled_area_m2', 'sediment_yield_density_kg_m2', 'runoff_depth_mm')
    pairs, interactions = [], []
    for (context, arm), result in lookup.items():
        if result != seeds.read(Path(result['root']) / 'result.json'):
            raise ValueError('Case result differs from retained outcome')
        h.verify(result['root'], result['response']['event_tables'])
        if h.digest(Path(result['root']) / 'annual.parquet') != result['response']['annual_sha256']:
            raise ValueError('Annual response artifact changed')
        base = lookup[(context, 'baseline')]
        before, after = prepared[(context, 'baseline')], prepared[(context, arm)]
        h.verify(Path(result['root']) / 'wepp/roads/runs', after['prepared_files'])
        native_result = seeds.read(Path(result['root']) / 'native-result.json')
        h.verify(result['root'], native_result['output_sha256'])
        changes = h.paired_input_changes(before, after)
        allowed = ({'wepp/roads/runs/p1.sol', 'wepp/roads/runs/p1.man'} if arm.startswith('traffic_')
                   else {'wepp/roads/runs/p1.slp'})
        if not set(changes) <= allowed:
            raise ValueError(f'Undeclared paired input change: {context}/{arm}')
        pairs.append(dict(context=context, arm=arm, input_changes=changes, no_op=not changes,
            requested=after['requested'], effective=after['effective_geometry'], emitted=after['emitted'],
            delta={key:result['response']['summary'][key]-base['response']['summary'][key] for key in metrics},
            event_response=h.paired_events(base['root'], result['root']),
            role_boundary_delta_kg_yr=[a['boundary_kg_yr']-b['boundary_kg_yr'] for a,b in zip(
                result['response']['role_boundary'],base['response']['role_boundary'],strict=True)],
            diagnostics=result['diagnostics']))
    for context in sorted({r['context'] for r in results}):
        arms = [lookup[(context, arm)]['response']['summary'] for arm in ('baseline', 'width8', 'fill60', 'width8_fill60')]
        interactions.append(dict(context=context, response={key:h.interaction(*(r[key] for r in arms)) for key in metrics}))
    aliases = []
    for row in d['aliases']:
        before = next(r['record'] for r in d['aliases'] if r['arrangement'] == row['arrangement'] and r['arm'] == 'baseline')
        aliases.append(dict(arrangement=row['arrangement'], arm=row['arm'],
                            input_changes=h.paired_input_changes(before, row['record'])))
    signatures = [h.signature(r['record']) for r in d['tasks']]
    h.save_new(ROOT / 'analysis.json', dict(declaration_sha256=h.digest(DECLARATION),
        results_sha256=h.digest(ROOT / 'results.json'), planned=len(expected), completed=len(results),
        distinct_input_signatures=len(set(signatures)), pairs=pairs, interactions=interactions, aliases=aliases,
        all_physical_checks_pass=all(r['diagnostics']['physical_pass'] for r in results),
        all_calendar_checks_pass=all(r['diagnostics']['calendar_pass'] for r in results),
        all_strict_particle_checks_pass=all(r['diagnostics']['particle_pass'] for r in results),
        defaults_adopted=False, field_calibration_claim=False))
    print('Analyzed', len(results), 'declared outcomes', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('declare', 'run', 'analyze'))
    parser.add_argument('--declaration', default='declaration.json', choices=('declaration.json', 'declaration-v2.json'))
    args = parser.parse_args()
    DECLARATION = ROOT / args.declaration
    {'declare': declare, 'run': run, 'analyze': analyze}[args.action]()
