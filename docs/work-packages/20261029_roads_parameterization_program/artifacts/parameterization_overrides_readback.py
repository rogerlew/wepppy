"""Retain native event-adjusted coefficient ranges beside input baselines."""
import json
from pathlib import Path
import pyarrow.parquet as pq
from tests.roads import roads_sensitivity as h
ROOT=Path('/wc1/runs/ro/roads-parameterization-program-20261103/parameterization-overrides-v1')
rows=[]
for result in json.loads((ROOT/'results.json').read_text()):
    root=Path(result['root']);record=json.loads((root/'prepared.json').read_text())
    element=root/'wepp/roads/output/interchange/H.element.parquet'
    table=pq.read_table(element).to_pylist()
    roles=[]
    for i,soil in enumerate(record['soil_readback'],1):
        selected=[r for r in table if r['OFE']==i]
        values={key:dict(minimum=min(r[key]*factor for r in selected),maximum=max(r[key]*factor for r in selected))
                for key,factor in [('Keff',1),('Ki',1e6),('Kr',.001),('Tcrit',1)]}
        roles.append(dict(ofe=i,role=soil['slid'],input={key:soil[key] for key in ('avke','ki','kr','shcrit')},
                          native_event_adjusted=values,event_rows=len(selected)))
    rows.append(dict(context=result['context'],arm=result['arm'],roles=roles,element_sha256=h.digest(element)))
h.save_new(ROOT/'runtime-coefficient-readback.json',dict(rows=rows,units={'Keff':'mm/h','Ki':'kg s/m4','Kr':'s/m','Tcrit':'Pa'},
    interpretation='ELEMENT adjusted event values are distinct from supplied soil baselines; ranges do not promise all internal hourly values.',
    native_print_scaling='sedout.for:510-512 prints Ki/1000000 and Kr*1000; this readback restores baseline-compatible units.',
    script_sha256=h.digest(__file__)))
