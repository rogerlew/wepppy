"""Diagnostic native partition experiment: only baseline profile width changes."""
import json, shutil
from pathlib import Path
import pyarrow.parquet as pq
from wepp_runner.wepp_runner import run_hillslope
from wepppy.wepp.interchange.hill_pass_interchange import run_wepp_hillslope_pass_interchange
from wepppy.nodb.mods.roads import Roads
root=Path('/wc1/runs/ru/rupc-misty-validation')
r=Roads.getInstance(str(root))
result={}
for mode, scale in [('full',1.0),('half',0.5)]:
    base=root/'validation-no-road'/mode
    shutil.copytree(root/'wepp/runs',base/'runs')
    (base/'output').mkdir()
    for identifier in (5,31):
        path=base/'runs'/f'p{identifier}.slp'
        lines=path.read_text().splitlines()
        bearing,width=lines[2].split()
        lines[2]=f'{bearing} {float(width)*scale:.12f}'
        path.write_text('\n'.join(lines)+'\n')
        run_hillslope(identifier,str(base/'runs'),wepp_bin=r.wepp_instance.wepp_bin)
    table=pq.read_table(run_wepp_hillslope_pass_interchange(base/'output')).to_pandas()
    table['sediment_kg']=table['runvol']*table[[f'sedcon_{i}' for i in range(1,6)]].sum(axis=1)
    result[mode]={}
    for identifier,group in table.groupby('wepp_id'):
        result[mode][str(identifier)]={'rows':len(group),'years':sorted(map(int,group.year.unique())),
            'runoff_m3':float(group.runvol.sum()),'sediment_kg':float(group.sediment_kg.sum()),
            'annual':{str(int(year)):{'runoff_m3':float(g.runvol.sum()),'sediment_kg':float(g.sediment_kg.sum())}
                      for year,g in group.groupby('year')}}
comparison={}
for identifier,full in result['full'].items():
    half=result['half'][identifier]
    assert full['rows']==half['rows'] and full['years']==half['years']
    comparison[identifier]={}
    for metric in ('runoff_m3','sediment_kg'):
        delta=2*half[metric]-full[metric]
        comparison[identifier][metric]={'full':full[metric],'two_halves':2*half[metric],
            'absolute_difference':delta,'relative_difference':delta/full[metric] if full[metric] else None}
result['comparison']=comparison
(root/'validation-no-road/result.json').write_text(json.dumps(result,indent=2))
print(json.dumps(comparison),flush=True)
