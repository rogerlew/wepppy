"""Extend exact-parity U12 capacity observations to all development matrix cells."""
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import hashlib,json,shutil,subprocess,time
P=Path('/workdir/wepppy/out/roads-parameterization-program-20261031')
CANDIDATE=P/'param-sign-u12-combined'
ROOT=P/'param-sign-matrix-observe-u12'
BINARY=P/'param-sign-observe-u12/build/src/wepp'
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def execute(source):
    source=Path(source);deadline=time.monotonic()+7200
    while not (source/'record.json').exists():
        if time.monotonic()>deadline:raise TimeoutError(str(source))
        time.sleep(5)
    row=json.loads((source/'record.json').read_text())
    folder=ROOT/source.relative_to(CANDIDATE);runs=folder/'runs';out=folder/'output'
    runs.mkdir(parents=True,exist_ok=False);out.mkdir()
    for name,d in row['inputs'].items():
        assert sha(source/'runs'/name)==d
        shutil.copy2(source/'runs'/name,runs/name)
    with (runs/'p1.run').open() as inp,(runs/'stdout').open('w') as stdout,(runs/'stderr').open('w') as stderr:
        proc=subprocess.run([str(BINARY)],cwd=runs,stdin=inp,stdout=stdout,stderr=stderr,timeout=300)
    outputs={p.name:sha(p) for p in out.iterdir() if p.is_file()}
    assert proc.returncode==0 and outputs==row['outputs'],str(source)
    for name,d in row['inputs'].items():assert sha(runs/name)==d
    lines=[line.strip() for line in (runs/'stdout').read_text().splitlines() if line.strip().startswith(('NC_','PC_'))]
    trace=folder/'trace.txt';trace.write_text('\n'.join(lines)+'\n')
    receipt=dict(source=str(source),source_record_sha256=sha(source/'record.json'),inputs=row['inputs'],outputs=outputs,binary_sha256=sha(BINARY),exact_output_parity=True,trace_sha256=sha(trace),negative_capacity_calls=sum(line.startswith('NC_DEP') for line in lines))
    (folder/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return receipt

def main():
    tasks=[]
    for panel in ['downstream','roads']:
        declaration=json.loads((CANDIDATE/(panel+'-declaration.json')).read_text())
        for source,old,label,binarysha in declaration['tasks']:
            tasks.append(str(CANDIDATE/label/Path(source).name))
    assert len(tasks)==1188 and len(set(tasks))==1188
    ROOT.mkdir(exist_ok=False)
    (ROOT/'declaration.json').write_text(json.dumps(dict(tasks=tasks,binary_sha256=sha(BINARY),script_sha256=sha(Path(__file__))),indent=2)+'\n')
    results=[]
    with ProcessPoolExecutor(max_workers=8) as pool:
        for row in pool.map(execute,tasks):
            results.append(row)
            if len(results)%32==0:print(len(results),'of1188 exact parity; negative calls',sum(r['negative_capacity_calls'] for r in results),flush=True)
    (ROOT/'results.json').write_text(json.dumps(results,indent=2)+'\n')
    print('1188 full-period observations complete',flush=True)
if __name__=='__main__':main()
