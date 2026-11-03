"""Audit generated artifacts, retaining the inherited graphics field-width limit."""
from pathlib import Path
import collections,hashlib,json,math
import duckdb
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

BASE=Path('/wc1/holdouts/mipa-native-r7-20261103')
WD=Path('/wc1/runs/mi/mipa-rap-20261103')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    output=WD/'wepp/output';runs=WD/'wepp/runs'
    for p in runs.glob('p*.err'):
        text=p.read_text()
        for required in ['->Gwcoeff parameters set','->WEPP hourly water seepage update set (UI code)',
                         '->RAP cover read:', 'binary_sha256=210d48da09ff60707ba2404dd32af1f0a74e95437d2cb900c5408121141a1936',
                         'WEPP COMPLETED HILLSLOPE SIMULATION SUCCESSFULLY']:
            assert required in text,(p,required)
    water=output/'interchange/H.wat.parquet'
    with duckdb.connect() as con:
        summary=con.execute('SELECT count(*),count(distinct (wepp_id,ofe_id,year,julian)),count(distinct (wepp_id,ofe_id)), min(year),max(year),min(sim_day_index),max(sim_day_index),min(water_year),max(water_year) FROM read_parquet(?)',[str(water)]).fetchone()
    assert summary==(3004240,3004240,235,1986,2020,1,12784,1986,2021),summary
    pf=pq.ParquetFile(water)
    water_fields=[f.name for f in pf.schema_arrow if pa.types.is_floating(f.type) and f.name!='InterceptionStorage']
    for batch in pf.iter_batches(columns=water_fields):
        for col in batch.columns:
            assert col.null_count==0 and pc.all(pc.is_finite(col)).as_py()
    optional=pf.read(columns=['InterceptionStorage']).column('InterceptionStorage')
    assert optional.null_count==pf.metadata.num_rows
    graphics={};all_stars=collections.Counter()
    for path in sorted(output.glob('H*.grph.dat')):
        names=[];count=0;stars=collections.Counter();first=None;last=None;summary_rows=0;in_summary=False
        with path.open() as stream:
            for line in stream:
                stripped=line.strip()
                if 'Minimum/Maximum values:' in line:in_summary=True
                if stripped.startswith('{'):names.append(stripped.strip('{}'))
                elif stripped and stripped.split(maxsplit=1)[0].isdigit():
                    fields=line.split();assert len(fields)==len(names),(path,len(fields),len(names))
                    day=int(fields[0])
                    if in_summary:summary_rows+=1
                    else:
                        count+=1;first=day if first is None else first;last=day
                    for i,value in enumerate(fields):
                        if '*' in value:stars[names[i]]+=1
                        else:assert math.isfinite(float(value)),(path,value)
        planes=(len((runs/(path.name.split('.')[0].replace('H','p')+'.cov')).read_text().splitlines())-1)//6
        assert count==planes*12784 and summary_rows==2 and first==1 and last==12784,(path,count,planes,first,last)
        assert set(stars)<= {'Days since last disturbance'},(path,stars)
        graphics[path.name]={'daily_rows':count,'summary_rows':summary_rows,'ofes':planes,'overflow_cells':dict(stars),'sha256':sha(path)}
        all_stars.update(stars)
    assert len(graphics)==72
    source=Path('/wc1/runs/mi/mipa-awake-20261102')
    before=json.loads((BASE/'configured-project/source-before.json').read_text())
    after={str(p.relative_to(source)):sha(p) for p in sorted(source.rglob('*')) if p.is_file() and not p.is_symlink()}
    assert before==after
    result={'water_summary':summary,'finite_water_columns':water_fields,'optional_unemitted_water_columns':{'InterceptionStorage':'All null; optional schema field is not emitted by this native .wat writer'},'graphics':graphics,'graphics_overflow_cells':dict(all_stars),
       'graphics_limit':'Inherited BIGOUT F10.5 renders daydis beyond9999.99999 as stars; field is not used by installed water report/interchange. Output formats preserved per task scope.',
       'report_years':'Water years1986..2021; simulation calendar remains1986..2020 (35years).',
       'all_72_logs_confirm_companions_and_final_binary':True,'source_unchanged':True}
    (BASE/'configured-execution-v1/artifact-audit-v3.json').write_text(json.dumps(result,indent=2)+'\n')
    print('PASS finite complete water records and declared graphics calendar; inherited graphics field overflow retained',dict(all_stars))
if __name__=='__main__':main()
