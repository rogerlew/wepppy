"""Separate legacy horizon normalization from generated material and modern runtime."""
from concurrent.futures import ProcessPoolExecutor
import json
from pathlib import Path
import shutil
import continuation as c
b=c.b
ROOT=Path('/workdir/wepppy/out/roads-parameterization-program-20261030/exact-legacy-v1')


def main():
    ROOT.mkdir(parents=True,exist_ok=False)
    (c.ROOT/'exact-legacy-v1').symlink_to(ROOT,target_is_directory=True)
    (ROOT/'inputs').symlink_to(c.BATCH/'inputs',target_is_directory=True)
    source=c.BATCH
    rows=[r for r in json.loads((source/'results.json').read_text()) if r['case']['variant']=='legacy_soil']
    if len(rows)!=96:raise ValueError('Incomplete control panel')
    b.dump(ROOT/'declaration.json',dict(cases=[dict(r['case'],variant='legacy_exact') for r in rows],
        script_sha256=b.digest(__file__),binary_sha256=c.SHA,
        hypothesis='Copy exact frozen2010 p1.sol; compare against normalizedlegacy lane under identical modernengine/projectruntime. This isolates normalization within modernruntime, not enginealone versus2010.',
        limits='Project runtime differs from2010 runtime by explicit design. No generated-material or acceptance claim.'))
    shutil.copy2(__file__,ROOT/'executed-exact-legacy-control.py')
    tasks=[]
    for row in rows:
        old=source/'matrix-v1'/'-'.join(row['case'].values())
        stage=ROOT/'prepared'/'-'.join(row['case'].values());(stage/'runs').mkdir(parents=True)
        for name,sha in row['inputs'].items():
            if b.digest(old/'runs'/name)!=sha:raise ValueError('Source drift')
            shutil.copy2(old/'runs'/name,stage/'runs'/name)
        profile='-'.join(row['case'][k] for k in ('climate','soil','design','surface','traffic'))
        ref=b.DEFAULT_ROOT/'validation-v4'/f'{profile}-legacy-legacy'
        rr=json.loads((ref/'record.json').read_text());c.e.a.s.check_files(ref,rr)
        shutil.copy2(ref/'runs/p1.sol',stage/'runs/p1.sol')
        shutil.copy2(ref/'runs/p1.sol',stage/'runs/reference.sol')
        record=dict(row,inputs={p.name:b.digest(p) for p in (stage/'runs').iterdir() if p.name!='reference.sol'})
        b.dump(stage/'record.json',record)
        tasks.append((str(stage),row['case'],'legacy_exact'))
    c.BATCH=ROOT
    results=[]
    with ProcessPoolExecutor(max_workers=8) as pool:
        for r in pool.map(c.execute,tasks):
            results.append(r)
            if len(results)%16==0:print(len(results),96,r['status'],flush=True)
    b.dump(ROOT/'results.json',results)
    summary=dict(cases=len(results),numerical_pass=sum(r['within'] for r in results),physical_pass=sum(r['physical_pass'] for r in results))
    b.dump(ROOT/'summary.json',summary);b.dump(c.HERE/'exact-legacy-v1-summary.json',summary)
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
