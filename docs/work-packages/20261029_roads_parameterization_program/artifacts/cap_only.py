"""Complete the minimal-rule ablation: conductivity treatment without erosion overrides."""
from concurrent.futures import ProcessPoolExecutor
from copy import deepcopy
import json
from pathlib import Path
import shutil
import continuation as c
b=c.b
ROOT=c.ROOT/'cap-only-v1'


def main():
    from wepppy.wepp.soils.utils import WeppSoilUtil
    ROOT.mkdir(exist_ok=False)
    (ROOT/'inputs').symlink_to(c.BATCH/'inputs',target_is_directory=True)
    c.BATCH=ROOT
    source=c.PRIOR/'project-runtime-screen-v2'
    rows=[r for r in json.loads((source/'results.json').read_text()) if r['case']['variant']=='roles']
    if len(rows)!=96:raise ValueError('Incomplete source panel')
    b.dump(ROOT/'declaration.json',dict(cases=[r['case'] for r in rows],script_sha256=b.digest(__file__),
        binary_sha256=c.SHA,hypothesis='Retain generated bare-role erosion coefficients; only disable road conductivity adjustment and cap upper200mm conductivity at matched legacy avke.',
        limits='Development ablation; no withheld materials. Same frozen96 panel and acceptance rules.'))
    shutil.copy2(__file__,ROOT/'executed-cap-only.py')
    tasks=[]
    for row in rows:
        old=source/'matrix-v1'/'-'.join(row['case'].values())
        oldfile=old/('record.json' if (old/'record.json').exists() else 'failure.json')
        record=json.loads(oldfile.read_text())
        staged=ROOT/'prepared'/'-'.join(row['case'].values());(staged/'runs').mkdir(parents=True)
        for name,sha in record['inputs'].items():
            if b.digest(old/'runs'/name)!=sha:raise ValueError('Source drift')
            shutil.copy2(old/'runs'/name,staged/'runs'/name)
        shutil.copy2(old/'runs/reference.sol',staged/'runs/reference.sol')
        soil=WeppSoilUtil(str(staged/'runs/p1.sol'))
        reference=WeppSoilUtil(str(staged/'runs/reference.sol')).obj['ofes'][0]
        soil.obj['ofes']=c.e.transform(soil.obj['ofes'],reference,'road_cap')
        expected=deepcopy(soil.obj['ofes']);soil.write(str(staged/'runs/p1.sol'))
        if WeppSoilUtil(str(staged/'runs/p1.sol')).obj['ofes']!=expected:raise ValueError('Readback drift')
        record['inputs']={p.name:b.digest(p) for p in (staged/'runs').iterdir() if p.name!='reference.sol'}
        record['soil_readback']=expected
        b.dump(staged/'record.json',record)
        tasks.append((str(staged),row['case'],'cap_only'))
    results=[]
    with ProcessPoolExecutor(max_workers=8) as pool:
        for r in pool.map(c.execute,tasks):
            results.append(r);b.dump(ROOT/'partial-results.json',results)
            print(len(results),96,r['case'],r['status'],r.get('within'),r.get('physical_pass'),flush=True)
    b.dump(ROOT/'results.json',results)
    summary=dict(cases=len(results),numerical_pass=sum(r['within'] for r in results),physical_pass=sum(r['physical_pass'] for r in results))
    b.dump(ROOT/'summary.json',summary);b.dump(c.HERE/'cap-only-v1-summary.json',summary)
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
