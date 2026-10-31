"""Independent raw verification of the no-detected-boundary flag experiment."""
from concurrent.futures import ProcessPoolExecutor
from copy import deepcopy
from pathlib import Path
import statistics
import no_detected_boundary as study

FIELDS=('surface_out_m3_yr','lateral_out_m3_yr','deep_percolation_m3_yr','et_m3_yr')
def verify(task):
    source=Path(task['source']);folder=study.ROOT/'matrix-v1'/source.name
    old=study.read(source/'record.json');new=study.read(folder/'record.json')
    assert study.b.prior.digest(source/'record.json')==task['source_record_sha256']
    for directory,record in ((source,old),(folder,new)):
        for category,subdir in (('inputs','runs'),('outputs','output')):
            for name,sha in record[category].items():assert study.b.prior.digest(directory/subdir/name)==sha
        if record['status']=='completed':assert study.b.c.audit(directory,record['case'],record)==record['audit']
    before=study.b.WeppSoilUtil(str(source/'runs/p1.sol')).obj
    actual=study.b.WeppSoilUtil(str(folder/'runs/p1.sol')).obj
    expected=deepcopy(before)
    for ofe in expected['ofes']:ofe['res_lyr']['slflag']=0
    assert actual==expected
    assert {k:v for k,v in old['inputs'].items() if k!='p1.sol'}=={k:v for k,v in new['inputs'].items() if k!='p1.sol'}
    result=dict(case=new['case'],group=new['group'],status=new['status'],physical_pass=new['physical_pass'],within=new['within'],baseline_within=new['baseline_within'],reference_kg_yr=new['reference_kg_yr'],source_record_sha256=task['source_record_sha256'],record_sha256=study.b.prior.digest(folder/'record.json'))
    if new['status']=='completed':
        result.update(before_kg_yr=old['metrics']['sediment_export_kg_yr'],after_kg_yr=new['metrics']['sediment_export_kg_yr'],
            water_deltas=[{k:new['audit']['water']['ofes'][i][k]-old['audit']['water']['ofes'][i][k] for k in FIELDS} for i in range(3)],
            boundary_deltas_kg_yr=[new['audit']['sediment']['ofes'][i]['boundary_kg_yr']-old['audit']['sediment']['ofes'][i]['boundary_kg_yr'] for i in range(3)])
    return result

def main():
    d=study.read(study.ROOT/'declaration.json')
    with ProcessPoolExecutor(max_workers=8) as pool:rows=list(pool.map(verify,d['tasks']))
    complete=[r for r in rows if r['physical_pass']]
    result=dict(cases=len(rows),raw_pairs_verified=len(rows),physical_pass=len(complete),
        median_water_deltas=[{k:statistics.median(r['water_deltas'][i][k] for r in complete) for k in FIELDS} for i in range(3)] if complete else None,
        rows=rows,script_sha256=study.b.prior.digest(Path(__file__)),
        limits='No-detected-class diagnostic endmember only. Independent native audits and exact only-flag soil mutation. Water residual is not complete closure; median internal flows must not be summed.')
    study.b.dump(study.ROOT/'analysis.json',result);study.b.dump(study.HERE/'no-detected-boundary-v1-analysis.json',result)
    print({k:v for k,v in result.items() if k!='rows'})
if __name__=='__main__':main()
