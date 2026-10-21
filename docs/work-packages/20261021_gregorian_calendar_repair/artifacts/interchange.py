"""Regenerate and audit downstream interchange for an isolated completed replay."""
from pathlib import Path
import argparse,json,shutil,time
import duckdb
from wepppy.wepp.interchange import run_wepp_hillslope_interchange,run_wepp_watershed_interchange


def main(root,family):
    while not (root/'execution.json').exists():time.sleep(10)
    execution=json.loads((root/'execution.json').read_text())
    assert all(r['success'] for r in execution['results'])
    out=root/'output'
    for name in ('chan.out','chanwb.out','tc_out.txt','chntyp.txt'):
        if (root/'runs'/name).exists():shutil.copy2(root/'runs'/name,out/name)
    run_wepp_hillslope_interchange(out,pass_family=family,start_year=1,delete_after_interchange=False,max_workers=4)
    run_wepp_watershed_interchange(out,pass_family=family,start_year=1,delete_after_interchange=False)
    con=duckdb.connect();result={}
    climate_days=sum(1 for line in (root/'runs/p1.cli').read_text().splitlines()[15:] if len(line.split())==13)
    hills=len(list((root/'runs').glob('p[0-9]*.run')))
    for p in sorted((out/'interchange').glob('*.parquet')):
        rel=con.read_parquet(str(p));cols=rel.columns
        info={'rows':len(rel),'columns':cols}
        if 'year' in cols and 'julian' in cols:
            con.register('calendar_rows',rel)
            invalid=con.execute('''select count(*) from calendar_rows where julian < 1 or
             julian > case when year % 4 = 0 and (year % 100 != 0 or year % 400 = 0) then 366 else 365 end''').fetchone()[0]
            assert invalid==0,(p,invalid)
            info['year_day_bounds']=con.execute('select min(year),max(year),min(julian),max(julian) from calendar_rows').fetchone()
        if p.name == 'H.pass.parquet':
            assert len(rel)==climate_days*hills,(p,len(rel),climate_days,hills)
            con.register('pass_rows',rel)
            invalid=con.execute('select count(*) from pass_rows where month is null or day_of_month is null').fetchone()[0]
            assert invalid==0,(p,'missing calendar dates',invalid)
            distinct=con.execute('select count(*) from (select distinct wepp_id,year,julian from pass_rows)').fetchone()[0]
            assert distinct==len(rel),(p,'duplicate daily keys')
            bounds=con.execute('select min(sim_day_index),max(sim_day_index) from pass_rows').fetchone()
            assert bounds==(1,climate_days),(p,bounds,climate_days)
            info['unique_daily_keys']=distinct
        result[p.name]=info
    (root/'interchange-audit.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('root',type=Path);parser.add_argument('family');a=parser.parse_args();main(a.root,a.family)
