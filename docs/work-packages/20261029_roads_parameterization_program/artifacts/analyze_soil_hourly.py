"""Verify all four cells and quantify paired soil/hourly effects without fitting."""
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from collections import defaultdict
import json
import math
import statistics
import soil_hourly_interaction as study

HERE, ROOT = study.HERE, study.ROOT
FIELDS = ('surface_out_m3_yr', 'surface_in_m3_yr', 'et_m3_yr', 'deep_percolation_m3_yr', 'lateral_out_m3_yr')

def one(cell):
    folder = Path(cell['folder']); record = study.read(folder / 'record.json')
    if cell['reused']:
        assert study.base.prior.digest(folder / 'record.json') == cell['record_sha256']
    assert record['binary_sha256'] == study.base.prior.SHA
    for category, subdir in (('inputs','runs'), ('outputs','output')):
        for name, sha in record[category].items():
            assert study.base.prior.digest(folder / subdir / name) == sha, (folder,name)
    assert ('wepp_ui.txt' in record['inputs']) == cell['hourly']
    assert all(name in record['inputs'] for name in ('pmetpara.txt','snow.txt'))
    result = dict(cell, record_sha256=study.base.prior.digest(folder / 'record.json'),
                  inputs=record['inputs'], status=record['status'], physical_pass=False, within=False)
    if record['status'] != 'completed':
        result['terminal_output'] = (folder / 'runs/stdout').read_text().splitlines()[-1]
        return result
    audit = study.base.c.audit(folder, record['case'], record)
    assert audit == record['audit'], folder
    value = record['metrics']['sediment_export_kg_yr']; ref = cell['reference_kg_yr']
    result.update(physical_pass=audit['physical_pass'], export_kg_yr=value,
                  within=(.1 <= value/ref <= 10 if ref > 1 else value <= max(1,10*ref)),
                  boundary_kg_yr=[r['boundary_kg_yr'] for r in audit['sediment']['ofes']],
                  water=[{k:r[k] for k in FIELDS} for r in audit['water']['ofes']])
    return result

def median(values):
    return statistics.median(values) if values else None

def main():
    declaration = study.read(ROOT / 'declaration.json')
    with ProcessPoolExecutor(max_workers=8) as pool:
        cells=list(pool.map(one, declaration['cells']))
    pairs=defaultdict(dict)
    for cell in cells:
        key=f"{cell['soil']}-{'on' if cell['hourly'] else 'off'}"
        pairs['-'.join(cell['case'].values())][key]=cell
    rows=[]
    for name, p in pairs.items():
        assert len(p)==4
        for soil in ('generated','legacy'):
            on,off=p[f'{soil}-on'],p[f'{soil}-off']
            assert off['inputs']=={k:v for k,v in on['inputs'].items() if k!='wepp_ui.txt'}
        for mode in ('on','off'):
            g,l=p[f'generated-{mode}'],p[f'legacy-{mode}']
            assert {k:v for k,v in g['inputs'].items() if k!='p1.sol'}=={k:v for k,v in l['inputs'].items() if k!='p1.sol'}
        row=dict(case=p['generated-on']['case'],group=p['generated-on']['group'], cells=p)
        if all(c['physical_pass'] for c in p.values()):
            gd=p['generated-off']['export_kg_yr']-p['generated-on']['export_kg_yr']
            ld=p['legacy-off']['export_kg_yr']-p['legacy-on']['export_kg_yr']
            row.update(generated_mode_delta_kg_yr=gd,legacy_mode_delta_kg_yr=ld, interaction_kg_yr=gd-ld)
            row['water_mode_deltas']={soil:[{f:p[f'{soil}-off']['water'][i][f]-p[f'{soil}-on']['water'][i][f] for f in FIELDS} for i in range(3)] for soil in ('generated','legacy')}
        rows.append(row)
    grouped={}
    for group in sorted({r['group'] for r in rows}):
        selected=[r for r in rows if r['group']==group]
        grouped[group]={key:dict(cases=len(selected),physical_pass=sum(r['cells'][key]['physical_pass'] for r in selected),within=sum(r['cells'][key]['physical_pass'] and r['cells'][key]['within'] for r in selected)) for key in next(iter(pairs.values()))}
    valid=[r for r in rows if 'interaction_kg_yr' in r]
    summary=dict(cases=len(rows),cells=len(cells),physical_pass=sum(c['physical_pass'] for c in cells),
                 groups=grouped, complete_physical_pairs=len(valid),
                 interaction_median_kg_yr=median([r['interaction_kg_yr'] for r in valid]),
                 interaction_median_absolute_kg_yr=median([abs(r['interaction_kg_yr']) for r in valid]),
                 water_median_mode_deltas={soil:[{f:median([r['water_mode_deltas'][soil][i][f] for r in valid]) for f in FIELDS} for i in range(3)] for soil in ('generated','legacy')},
                 generated_recovered=sum(not r['cells']['generated-on']['within'] and r['cells']['generated-off']['within'] and r['cells']['generated-off']['physical_pass'] for r in rows),
                 generated_regressions=sum(r['cells']['generated-on']['within'] and not (r['cells']['generated-off']['within'] and r['cells']['generated-off']['physical_pass']) for r in rows),
                 declaration_sha256=study.base.prior.digest(ROOT/'declaration.json'), script_sha256=study.base.prior.digest(Path(__file__)),
                 limitations='Selected 111 diagnostic cases, not full matrix acceptance. All four cells re-audited from native files; water residual is not a complete closure. Signed off-minus-on differences. Whole-soil contrasts do not isolate a single property.')
    study.base.dump(ROOT/'analysis.json',dict(summary=summary,rows=rows))
    study.base.dump(HERE/'soil-hourly-interaction-v1-analysis.json',dict(summary=summary,rows=rows))
    print(json.dumps(summary,indent=2),flush=True)

if __name__=='__main__':
    main()
