"""Read-only scientific interpretation of the frozen diagnostic factorial."""
import hashlib
import itertools
import json
import math
from collections import Counter
from pathlib import Path
from statistics import median

ROOT = Path('/workdir/wepppy/out/roads-parameterization-program-20261031/combined-hydraulics-r4-v2')
ARTIFACTS = Path('/workdir/wepppy/docs/work-packages/20261029_roads_parameterization_program/artifacts')
KEYS = ('climate', 'soil', 'design', 'surface', 'traffic')
FACTORS = ('road_coupled', 'fill_fixed', 'buffer_cap')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
key = lambda r: tuple(r['case'][n] for n in KEYS)
rows = json.loads((ROOT / 'results.json').read_text())
summary = json.loads((ROOT / 'summary.json').read_text())
contrasts = json.loads((ROOT / 'continuous-contrasts.json').read_text())
by_case = {}
for row in rows:
    bits = (int(row['road_on']), int(row['downstream_lane'] in ('fill_fixed', 'both')), int(row['downstream_lane'] in ('buffer_cap', 'both')))
    assert bits not in by_case.setdefault(key(row), {})
    by_case[key(row)][bits] = row
assert len(by_case) == 116 and all(len(v) == 8 for v in by_case.values())
assert all(r['completed'] and r['physical_pass'] for r in rows)
for field, name in [('results_sha256', 'results.json'), ('paired_cells_sha256', 'paired-cells.json'), ('continuous_contrasts_sha256', 'continuous-contrasts.json')]:
    assert summary[field] == sha(ROOT / name)

def vector(row):
    result = {n: row['metrics'][n] for n in ('sediment_export_kg_yr', 'runoff_mm_yr')}
    for i, role in enumerate(('road', 'fill', 'buffer')):
        for n in ('boundary_kg_yr', 'net_kg_yr'):
            result[role + '_' + n] = row['audit']['sediment']['ofes'][i][n]
        for n in ('surface_out_m3_yr', 'lateral_out_m3_yr', 'deep_percolation_m3_yr'):
            result[role + '_' + n] = row['audit']['water']['ofes'][i][n]
    return result

count, max_error = 0, 0
for contrast in contrasts:
    active = [FACTORS.index(n) for n in contrast['factors']]
    terms = []
    for states in itertools.product((0, 1), repeat=len(active)):
        bits = [contrast['background'].get(n, 0) for n in FACTORS]
        for i, state in zip(active, states):
            bits[i] = state
        terms.append(((-1) ** (len(active) - sum(states)), vector(by_case[key(contrast)][tuple(bits)])))
    assert contrast['complete']
    for name, reported in contrast['differences'].items():
        values = [sign * v[name] for sign, v in terms]
        expected = math.fsum(values)
        error = abs(reported - expected)
        unit_roundoff = 2 ** -53
        bound = len(values) * unit_roundoff / (1 - len(values) * unit_roundoff) * math.fsum(abs(x) for x in values)
        assert error <= bound
        max_error = max(max_error, error)
        count += 1

small = [v for v in by_case.values() if v[(0, 0, 0)]['group'] == 'small_exceedance']
small_effects = {}
for label, bits in [('road', (1, 0, 0)), ('fill', (0, 1, 0)), ('buffer', (0, 0, 1))]:
    differences = [v[bits]['export_kg_yr'] - v[(0, 0, 0)]['export_kg_yr'] for v in small]
    small_effects[label] = dict(median_paired_kg_yr=median(differences), increases=sum(x > 0 for x in differences), decreases=sum(x < 0 for x in differences), unchanged=sum(x == 0 for x in differences))
controls = []
for k, cells in by_case.items():
    base = cells[(0, 0, 0)]
    if base['group'].endswith('_pass') and any(not r['within'] for r in cells.values()):
        controls.append(dict(case=dict(zip(KEYS, k)), reference_kg_yr=base['reference_kg_yr'], lanes={r['lane']:dict(export_kg_yr=r['export_kg_yr'], within=r['within']) for r in cells.values()}))
seeds = [
    ('denver', '1718465', 'outunrut', 'paved', 'high'),
    ('flagstaff', '1718465', 'outunrut', 'gravel', 'high'),
    ('charleston', '1718465', 'outunrut', 'paved', 'none'),
    ('denver', '1718465', 'outunrut', 'paved', 'none'),
    ('flagstaff', '1718465', 'outunrut', 'paved', 'none'),
    ('site', '1718465', 'outunrut', 'gravel', 'high'),
    ('flagstaff', '2711184', 'outunrut', 'paved', 'high'),
    ('denver', '1718494', 'outunrut', 'gravel', 'high'),
]
reference_boundaries = {key(r):r for r in json.loads((ARTIFACTS / 'role-boundary-assessment-r3.json').read_text())['rows']}
seed_evidence = []
for k in seeds:
    row = by_case[k][(0, 0, 0)]
    texture = {'1718465':'sand', '2711184':'loam', '1718494':'loam'}[k[1]]
    folder = Path('/wc1/runs/ro/roads-soil-benchmark-20261029/validation-v4') / '-'.join((k[0], texture, *k[2:], 'legacy', 'legacy'))
    ref = json.loads((folder / 'record.json').read_text())
    ref_boundary = reference_boundaries[k]
    assert sha(folder / 'record.json') == ref_boundary['reference_record_sha256']
    assert sha(folder / 'output/H1.element.dat') == ref['outputs']['H1.element.dat']
    for name in ('p1.cli', 'p1.man', 'p1.slp'):
        assert row['inputs'][name] == ref['inputs'][name] == sha(folder / 'runs' / name)
    seed_evidence.append(dict(case=dict(zip(KEYS,k)), reference_kg_yr=row['reference_kg_yr'], candidate_kg_yr=row['export_kg_yr'], candidate_boundary_kg_yr=[o['boundary_kg_yr'] for o in row['audit']['sediment']['ofes']], reference_boundary_kg_yr=ref_boundary['reference_boundary_kg_yr'], reference_record_sha256=sha(folder / 'record.json'), reference_element_sha256=ref['outputs']['H1.element.dat'], candidate_record_sha256=sha(Path(row['folder'])/'record.json'), matched_climate_management_slope=True))
result = dict(
    disposition='No production parameterization accepted. Downstream combinations regress original controls; road-only package remains a component hypothesis. Final full artifact verification and the new strict fraction flag remain separate pending gates.',
    evidence_sha256={str(ROOT / name):sha(ROOT / name) for name in ('declaration.json', 'results.json', 'summary.json', 'paired-cells.json', 'continuous-contrasts.json')},
    role_reference_evidence_sha256=sha(ARTIFACTS / 'role-boundary-assessment-r3.json'),
    script_sha256=sha(Path(__file__)),
    recomputed_contrasts=dict(contrasts=len(contrasts), scalar_values=count, maximum_difference_from_independent_fsum=max_error),
    groups=summary['groups'],
    small_original_misses=dict(cases=len(small), designs=dict(Counter(v[(0,0,0)]['case']['design'] for v in small)), climates=dict(Counter(v[(0,0,0)]['case']['climate'] for v in small)), zero_references=sum(v[(0,0,0)]['reference_kg_yr']==0 for v in small), unresolved_all_eight=sum(not any(r['within'] for r in v.values()) for v in small), original_and_road_on_positive_fill_negative_buffer=all(v[b]['audit']['sediment']['ofes'][1]['net_kg_yr']>0 and v[b]['audit']['sediment']['ofes'][2]['net_kg_yr']<0 for v in small for b in ((0,0,0),(1,0,0))), paired_effects=small_effects),
    control_regressions=controls,
    next_study_seed_evidence=seed_evidence,
    limitations=['Selected diagnostic panel is not a population estimate or broad success estimate.', 'Boundary net exchange is not tagged source attribution; gross local source and deposition may coexist.', 'Comparing legacy WEPP2010 to modern generated soils confounds engine and soil state; add exact-R4 legacy-soil seed anchors before attribution.', 'The tested factors do not exhaust hydraulic mechanisms; these results do not prove a new native defect or justify changing generated texture/erodibility to match templates.', 'No holdout, production default, coefficient search, or UI implementation is approved.'])
out=Path('/tmp/combined-hydraulics-r4-scientific-results-review.json');out.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');print(out);print(sha(out))
