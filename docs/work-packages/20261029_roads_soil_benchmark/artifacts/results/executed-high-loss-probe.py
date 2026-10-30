"""Revisit the original long paved-silt stress geometry, outside fswepp2 API bounds."""
from pathlib import Path
import json
import shutil
import subprocess
import benchmark as b
from tests.roads.roads_matrix import Case, prepare, DATA
from wepppy.nodb.mods.roads import Roads


def main():
    destination=b.DEFAULT_ROOT/'high-loss-probe-v2'
    destination.mkdir(exist_ok=False)
    rows=[]
    for arrangement in ('bare_direct','bare_buffer','rutted'):
        for label,binary in [('legacy',b.DEFAULT_ROOT/'reference/bin/wepp2010'),
                             ('modern',b.REPO/'wepp_runner/bin/wepp_261026')]:
            root=destination/f'{arrangement}-{label}'
            runs=root/'wepp/roads/runs';output=root/'wepp/roads/output'
            runs.mkdir(parents=True);output.mkdir()
            for p in (DATA/'shared').iterdir():shutil.copy2(p,runs/p.name)
            record=prepare(object.__new__(Roads),root,Case('long','silt','paved','high',arrangement),1)
            lines=(runs/'p1.run').read_text().splitlines();lines[6]='2'
            (runs/'p1.run').write_text('\n'.join(lines)+'\n')
            inputs={p.name:b.digest(p) for p in runs.iterdir() if p.is_file()}
            with (runs/'stdout').open('w') as out,(runs/'stderr').open('w') as err,(runs/'p1.run').open() as stdin:
                result=subprocess.run([str(binary)],cwd=runs,stdin=stdin,stdout=out,stderr=err,timeout=90)
            if result.returncode or 'WEPP COMPLETED HILLSLOPE SIMULATION SUCCESSFULLY' not in (runs/'stdout').read_text():
                raise ValueError(f'Native high-loss probe failure: {root}')
            metrics=b.parse_loss(output/'H1.loss.dat',record['emitted']['width_m'])
            calendar=json.loads((b.DEFAULT_ROOT/'inputs/manifest.json').read_text())['climates']['site']
            count=b.validate_wat(output/'H1.wat.dat',calendar,nofe=len(record['ofe_order']))
            area=record['emitted']['width_m']*sum(record['emitted']['lengths_m'])
            rows.append(dict(arrangement=arrangement,binary=label,binary_sha256=b.digest(binary),
                prepared=record,inputs=inputs,outputs={p.name:b.digest(p) for p in output.iterdir() if p.is_file()},
                metrics=metrics,wat_rows=count,area_m2=area,
                net_loss_t_ha_yr=metrics['spatial_net_loss_kg_yr']/area*10,
                export_t_ha_yr=metrics['sediment_export_kg_yr']/area*10))
            print(arrangement,label,rows[-1]['net_loss_t_ha_yr'],metrics['sediment_export_kg_yr'],flush=True)
    b.dump(destination/'summary.json',dict(script_sha256=b.digest(__file__),rows=rows,
        qualification='Native stress controls exceed fswepp2 300 m API limit; not admitted fswepp2 validation cases'))
    shutil.copy2(__file__,destination/'execution-script.py')


if __name__=='__main__':main()
