"""Three full-period observation replays with exact ordinary-output parity."""
from pathlib import Path
import hashlib,json,shutil,subprocess
P=Path('/workdir/wepppy/out/roads-parameterization-program-20261031')
ROOT=P/'particle-observe-g1'
BINARY=ROOT/'build/src/wepp'
CASE='site-1718465-outunrut-gravel-low-erosion_road_cap-project'
SEEDS={'ordinary':P/'depend-bounded-g1/roads/site-1718465-inveg-paved-high-erosion_road_cap-project',
       'buffer_cap':P/'depend-bounded-g1/downstream-buffer_cap'/CASE,
       'buffer_control':P/'depend-bounded-g1/roads'/CASE}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    results=[]
    for label,source in SEEDS.items():
        r=json.loads((source/'record.json').read_text());folder=ROOT/label;runs=folder/'runs';runs.mkdir(parents=True,exist_ok=False);out=folder/'output';out.mkdir()
        for name,d in r['inputs'].items():
            assert sha(source/'runs'/name)==d;shutil.copy2(source/'runs'/name,runs/name)
        with (runs/'p1.run').open() as inp,(runs/'stdout').open('w') as stdout,(runs/'stderr').open('w') as stderr:
            proc=subprocess.run([str(BINARY)],cwd=runs,stdin=inp,stdout=stdout,stderr=stderr,timeout=300)
        outputs={p.name:sha(p) for p in out.iterdir() if p.is_file()}
        assert proc.returncode==0 and outputs==r['outputs'],label
        for name,d in r['inputs'].items():assert sha(runs/name)==d
        traces=[line.strip() for line in (runs/'stdout').read_text().splitlines() if line.strip().startswith('PM_')]
        (folder/'trace.txt').write_text('\n'.join(traces)+'\n')
        row=dict(label=label,source=str(source),source_record_sha256=sha(source/'record.json'),inputs=r['inputs'],outputs=outputs,trace_sha256=sha(folder/'trace.txt'),exact_output_parity=True,returncode=proc.returncode,binary_sha256=sha(BINARY))
        (folder/'receipt.json').write_text(json.dumps(row,indent=2)+'\n');results.append(row)
        print(label,'exact output parity',len(traces),'trace records',flush=True)
    (ROOT/'results.json').write_text(json.dumps(results,indent=2)+'\n')
if __name__=='__main__':main()
