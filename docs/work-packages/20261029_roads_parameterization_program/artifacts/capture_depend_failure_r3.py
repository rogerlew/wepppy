"""Retain exact failing inputs and observe released DEPEND through gdb."""
from pathlib import Path
import hashlib,json,shutil,subprocess,tarfile
HERE=Path(__file__).resolve().parent
PARENT=Path('/workdir/wepppy/out/roads-parameterization-program-20261031')
ROOT=PARENT/'depend-failure-r3'
BINARY=Path('/workdir/wepppy/wepp_runner/bin/wepp_261029')
SHA='1d07f5e47692a543e653f449feea23cf298093a9fd664d7a01a1b71dc5e01531'

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    results=PARENT/'downstream-hydraulics-r3/results.json';rows=json.loads(results.read_text());failed=[r for r in rows if not r['physical_pass']]
    assert len(failed)==1;old=failed[0];assert old['returncode']==-8 and old['status']=='native_failure'
    source=Path(old['folder']);ROOT.mkdir(exist_ok=False)
    assert digest(BINARY)==SHA
    for lane in ('released-replay','gdb'):
        runs=ROOT/lane/'runs';runs.mkdir(parents=True);out=ROOT/lane/'output';out.mkdir()
        for n,d in old['inputs'].items():assert digest(source/'runs'/n)==d;shutil.copy2(source/'runs'/n,runs/n)
        if lane=='released-replay':
            with (runs/'p1.run').open() as inp,(runs/'stdout').open('w') as stdout,(runs/'stderr').open('w') as stderr:
                proc=subprocess.run([str(BINARY)],cwd=runs,stdin=inp,stdout=stdout,stderr=stderr,timeout=300)
            assert proc.returncode==-8
            actual={p.name:digest(p) for p in out.iterdir() if p.is_file()};assert actual==old['outputs']
        else:
            commands=['set pagination off','set confirm off','run < p1.run > stdout','info args','info locals','bt']
            args=['/usr/bin/gdb','-q','-batch']
            for command in commands:args+=['-ex',command]
            args+=[str(BINARY)]
            with (ROOT/'gdb.txt').open('w') as output:subprocess.run(args,cwd=runs,stdout=output,stderr=subprocess.STDOUT,timeout=300,check=True)
    fixture=HERE/'depend-failure-r3-inputs.tar.gz'
    with tarfile.open(fixture,'w:gz') as archive:
        for n in sorted(old['inputs']):archive.add(ROOT/'released-replay/runs'/n,arcname='runs/'+n)
    report=dict(case=old['case'],source_record_sha256=digest(source/'record.json'),source_results_sha256=digest(results),binary_sha256=SHA,
        exact_failed_output_replay=True,returncode=-8,inputs=old['inputs'],fixture=str(fixture),fixture_sha256=digest(fixture),
        fixture_execution='Create sibling output/ beside extracted runs/; from runs/ execute pinned binary with stdin p1.run. The fixture intentionally reproduces SIGFPE, not a passing simulation.',
        gdb_sha256=digest(ROOT/'gdb.txt'),script_sha256=digest(Path(__file__)))
    text=json.dumps(report,indent=2)+'\n';(ROOT/'receipt.json').write_text(text);(HERE/'depend-failure-r3-receipt.json').write_text(text)
    shutil.copy2(ROOT/'gdb.txt',HERE/'depend-failure-r3-gdb.txt')
    print((ROOT/'gdb.txt').read_text()[-7000:])
if __name__=='__main__':main()
