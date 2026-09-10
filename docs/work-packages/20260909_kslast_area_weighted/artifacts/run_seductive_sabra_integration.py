"""Run via wctl container Python. Explicit phases; no credentials or config edits."""
import argparse
import hashlib
import json
from pathlib import Path
import time

RUNID = 'seductive-sabra'
WD = Path('/wc1/runs/se') / RUNID
EVIDENCE = Path('/workdir/wepppy/docs/work-packages/20260909_kslast_area_weighted/artifacts')


def sha(path):
    with open(path, 'rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def save(name, data):
    (EVIDENCE / name).write_text(json.dumps(data, indent=2, default=str) + '\n')


def connection():
    from redis import Redis
    from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
    return Redis(**redis_connection_kwargs(RedisDB.RQ))


def baseline():
    from wepppy.nodb.core import Wepp, Watershed, Climate
    w=Wepp.getInstance(str(WD)); ws=Watershed.getInstance(str(WD)); c=Climate.getInstance(str(WD))
    files={str(p.relative_to(WD)):dict(sha256=sha(p),mtime_ns=p.stat().st_mtime_ns,size=p.stat().st_size)
           for root in ['wepp/runs','wepp/output'] for p in (WD/root).rglob('*') if p.is_file()}
    inventory=Path('/tmp/kslast-area-weighted-run-files.json')
    inventory.write_text(json.dumps(files,indent=2)+'\n')
    save('run-baseline.json',dict(kslast=w.kslast,source=w.kslast_map,source_hash=sha(w.kslast_map),
         grid=ws.subwta,grid_hash=sha(ws.subwta),hillslopes=len(ws.subs_summary),years=c.input_years,
         model=w.wepp_bin,multi_ofe=w.multi_ofe,watershed=w.run_wepp_watershed,file_inventory_path=str(inventory),file_inventory_sha256=sha(inventory),file_count=len(files)))
    print('baseline recorded',len(files),'files')


def submit():
    from rq import Queue
    from wepppy.rq.wepp_rq import run_wepp_rq
    conn=connection()
    for name in ['default','batch','fork-archive']:
        queue=Queue(name,connection=conn)
        assert queue.count == 0 and not queue.started_job_registry.get_job_ids(), f'Queue busy: {name}'
    assert not (EVIDENCE/'integration-submission.json').exists(), 'Submission already recorded; inspect before rerun'
    submitted=time.time()
    job=Queue('default',connection=conn).enqueue(run_wepp_rq,RUNID,job_timeout=86400,result_ttl=604800)
    save('integration-submission.json',dict(parent_id=job.id,submitted_epoch=submitted,runid=RUNID))
    print('submitted full run_wepp_rq',job.id)


def poll():
    from rq.job import Job
    parent=json.loads((EVIDENCE/'integration-submission.json').read_text())['parent_id']
    conn=connection(); pending=[parent]; jobs={}
    while pending:
        ident=pending.pop()
        if ident in jobs: continue
        j=Job.fetch(ident,connection=conn)
        status=j.get_status(refresh=True)
        jobs[ident]=dict(function=j.func_name,status=status,created=j.created_at,started=j.started_at,
                         ended=j.ended_at,dependencies=j.dependency_ids,children={k:v for k,v in j.meta.items() if k.startswith('jobs:')},
                         exception=j.exc_info if status=='failed' else None)
        pending.extend(jobs[ident]['children'].values())
    save('integration-jobs.json',jobs)
    print(json.dumps({ident:(j['function'].split('.')[-1],j['status']) for ident,j in jobs.items()},indent=2))
    if any(j['status'] in ('failed','stopped','canceled') for j in jobs.values()): raise SystemExit(1)
    if len(jobs)==1 or any(j['status']!='finished' for j in jobs.values()): raise SystemExit(2)
    assert any(j['function'].endswith('_run_hillslopes_rq') for j in jobs.values())
    assert any(j['function'].endswith('run_watershed_rq') for j in jobs.values())
    print('complete job tree',len(jobs))


def verify():
    poll()  # A finished parent alone is not a full-model success.
    import math
    import numpy as np
    import rasterio
    import pyarrow.parquet as pq
    from wepppy.nodb.core import Wepp, Watershed, Climate
    from wepppy.wepp.soils.utils import WeppSoilUtil
    w=Wepp.getInstance(str(WD)); ws=Watershed.getInstance(str(WD)); c=Climate.getInstance(str(WD))
    baseline=json.loads((EVIDENCE/'run-baseline.json').read_text())
    start=json.loads((EVIDENCE/'integration-submission.json').read_text())['submitted_epoch']
    assert (w.wepp_bin,c.input_years,w.kslast,w.multi_ofe)==(baseline['model'],baseline['years'],baseline['kslast'],baseline['multi_ofe'])
    summary=json.loads((WD/'soils/kslast_summary.json').read_text())
    assert sha(WD/'soils/kslast.tif')==summary['map_sha256']
    assert sha(ws.subwta)==baseline['grid_hash']==summary['grid']['sha256']
    assert sha(w.kslast_map)==baseline['source_hash']==summary['source']['sha256']
    with rasterio.open(ws.subwta) as keys, rasterio.open(WD/'soils/kslast.tif') as values:
        assert keys.crs==values.crs and keys.transform==values.transform and keys.shape==values.shape
        assert values.nodata==-9999 and values.dtypes==('float64',)
        key_data=keys.read(1,masked=True); data=values.read(1,masked=True)
        # Separate oracle: math.fsum of cells, without the native reducer.
        comparisons={}
        for key,record in summary['hillslopes'].items():
            selected=(key_data.data==int(key)) & ~np.ma.getmaskarray(key_data)
            valid=selected & ~np.ma.getmaskarray(data) & np.isfinite(data.data) & (data.data>0)
            n=int(selected.sum()); v=int(valid.sum()); missing=n-v
            expected=(math.fsum(data.data[valid].tolist())+missing*w.kslast)/n
            assert math.isclose(expected,record['mean'],rel_tol=1e-12,abs_tol=1e-12),(key,expected,record)
            assert (v,missing,n)==tuple(record[k] for k in ['valid_cell_count','missing_cell_count','total_cell_count'])
            comparisons[key]=expected
    translator=ws.translator_factory(); ofes=0; exempt=[]
    for key,expected in comparisons.items():
        path=WD/'wepp/runs'/f'p{translator.wepp(top=int(key))}.sol'
        assert path.stat().st_mtime>start
        soil=WeppSoilUtil(str(path))
        source=WeppSoilUtil(str(WD/'soils'/f'hill_{key}.mofe.sol'))
        developed='developed' in (source.obj['ofes'][0]['luse'] or '').lower()
        if developed: exempt.append(key)
        for index,ofe in enumerate(soil.obj['ofes']):
            actual=float(ofe['res_lyr']['kslast'])
            target=float(source.obj['ofes'][index]['res_lyr']['kslast']) if developed else expected
            assert math.isclose(actual,target,rel_tol=1e-12,abs_tol=1e-12),(key,index,actual,target)
            ofes+=1
        if not developed: assert 'project_cell_area_mean' in path.read_text()
    tables={}
    for path in (WD/'wepp/output').rglob('*.parquet'):
        assert path.stat().st_mtime>start, f'stale table {path}'
        parquet=pq.ParquetFile(path); finite_columns=0
        for batch in parquet.iter_batches():
            for col in batch.columns:
                import pyarrow as pa
                if pa.types.is_floating(col.type):
                    vals=col.drop_null().to_numpy()
                    assert np.isfinite(vals).all(), f'nonfinite {path}'
                    finite_columns+=1
        tables[str(path.relative_to(WD))]=dict(rows=parquet.metadata.num_rows,sha256=sha(path),finite_batches=finite_columns)
    assert tables, 'no new interchange tables'
    save('integration-verification.json',dict(hillslopes=len(comparisons),ofes=ofes,developed_exemptions=exempt,
        defaulted_hillslopes=sum(r['missing_cell_count']>0 for r in summary['hillslopes'].values()),
        aggregation_rtol=1e-12,aggregation_atol=1e-12,soil_tolerance=1e-12,tables=tables,model=w.wepp_bin,years=c.input_years))
    print('verified',len(comparisons),'hillslopes',ofes,'OFEs',len(tables),'fresh tables')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['baseline','submit','poll','verify'])
    globals()[parser.parse_args().phase]()
