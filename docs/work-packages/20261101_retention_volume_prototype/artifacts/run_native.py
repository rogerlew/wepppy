"""Six predeclared paired complete histories using an unchanged research binary."""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import time
import read_native

PANEL=['84543623','84543461','84543462','87913598','85179904','85179901']
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,obj):
    with p.open('x') as f: json.dump(obj,f,indent=2,allow_nan=False); f.write('\n')

def main(repo,fixtures,out):
    out.mkdir()
    helper_hashes={str(p):sha(p) for p in [Path(__file__),Path(read_native.__file__)]}
    probe=repo/'out/roads-parameterization-program-20261031/buffer-storage-ownership-r4/native-probe'
    build_receipt=probe/'build-receipt.json'
    if sha(build_receipt)!='ab8c57fc6a1786864cc581907e40aaa11673fe15cc925cad44b04786cbe27036': raise ValueError('Build receipt drift')
    built=json.loads(build_receipt.read_text())['inventory']
    if len(built)!=978: raise ValueError('Build inventory support')
    for name,r in built.items():
        src=probe/'build'/name
        if sha(src)!=r['sha256']: raise ValueError('Build drift '+name)
        dst=out/'build-evidence'/name; dst.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(src,dst)
    shutil.copy2(build_receipt,out/'build-receipt.json')
    binary=out/'build-evidence/src/wepp'
    if sha(binary)!='5f6bcebac1c82111a6a7c9685cd0d2a04f2e6c3066a3637e533a1a8054ff38b1': raise ValueError('Binary drift')
    if os.environ.get('LD_PRELOAD') or os.environ.get('LD_LIBRARY_PATH'): raise ValueError('Unexpected loader override')
    linked=subprocess.run(['/usr/bin/ldd',str(binary)],capture_output=True,text=True,check=True)
    (out/'ldd.txt').write_text(linked.stdout)
    libraries={str(Path(p).resolve()):sha(p) for p in re.findall(r'(/[^\s()]+)',linked.stdout)}
    if not libraries or 'not found' in linked.stdout: raise ValueError('Unresolved runtime libraries')
    if sha(probe/'freeze.json')!='cf56799cdbde04a0eb9a2f10a79b8ed8af728fdf3444ceda3cb31e736dfab2c5': raise ValueError('Accepted runtime freeze drift')
    accepted_runtime=json.loads((probe/'freeze.json').read_text())['baseline_runtime']['sha256']
    if libraries!=accepted_runtime: raise ValueError('Runtime differs from accepted observer')
    save(out/'runtime-libraries.json',libraries)
    original=probe/'cases/small_paved_dry_legacy/modern/O4'
    original_decl=json.loads((original/'execution-declaration.json').read_text())
    inputs=original_decl['inputs']
    for name,r in inputs.items():
        if sha(original/'runs'/name)!=r['sha256']: raise ValueError('Runtime input drift '+name)
    fixture_receipt=fixtures/'receipt.json'; fixture_hash=sha(fixture_receipt)
    prepared=json.loads(fixture_receipt.read_text())
    if prepared['panel']!=PANEL or not prepared['passed']: raise ValueError('Unaccepted fixture panel')
    if (fixtures/'native-admission.json').is_file():
        admission=json.loads((fixtures/'native-admission.json').read_text())
        if admission['fixture_receipt_sha256']!=fixture_hash or admission['panel']!=PANEL: raise ValueError('Admission mismatch')
    else: raise ValueError('Missing reviewed fixture admission')
    save(out/'declaration.json',dict(fixture_receipt_sha256=fixture_hash,panel=PANEL,
        helper_hashes=helper_hashes,original_runtime_declaration_sha256=sha(original/'execution-declaration.json'),
        binary_sha256=sha(binary),build_members=len(built),full_years=16,
        native_source_changed=False,observations='storage and full existing wepp_observe; no frost-only filter',
        expected_native_layers={'84543623':3,'84543461':3,'84543462':3,'87913598':3,'85179904':3,'85179901':8}))
    results=[]
    for chkey in PANEL:
        fixture=next(r for r in prepared['cases'] if r['id']=='source-'+chkey)
        if fixture['reason']!='eligible': raise ValueError('Ineligible selected case')
        for lane in ['baseline','candidate']:
            root=out/(chkey+'-'+lane); runs=root/'runs'; runs.mkdir(parents=True); (root/'output').mkdir()
            for name in inputs: shutil.copy2(original/'runs'/name,runs/name)
            src=fixtures/fixture['id']/lane/'audit.sol'
            if sha(src)!=fixture[lane]['sha256']: raise ValueError('Fixture soil drift')
            shutil.copy2(src,root/'source.sol')
            lines=src.read_text().splitlines(); index=lines.index('1 0')
            (runs/'p1.sol').write_text('\n'.join(lines[:index]+['3 0']+lines[index+1:]*3)+'\n')
            (runs/'wepp_observe.on').touch(exist_ok=False)
            if (runs/'wepp_observe_frost.on').exists(): raise ValueError('Unexpected frost-only filter')
            before={p.name:sha(p) for p in runs.iterdir() if p.is_file()}
            if {n for n in before if n not in inputs or before[n]!=inputs[n]['sha256']}!={'p1.sol','wepp_observe.on'}: raise ValueError('Runtime non-soil drift')
            evidence=dict(chkey=chkey,lane=lane,inputs=before,source_soil_sha256=sha(src),
                fixture_receipt_sha256=fixture_hash,binary_sha256=sha(binary),helper_hashes=helper_hashes,
                command=[str(binary)],environment=dict(PATH='/usr/bin:/bin',FC='/usr/bin/gfortran'),
                configured_years=16,mutation='Only retention pair differs between lanes; observation marker identical')
            save(root/'pre-execution.json',evidence)
            start=time.monotonic()
            with (runs/'p1.run').open('rb') as stdin,(runs/'stdout').open('xb') as stdout,(runs/'stderr').open('xb') as stderr:
                try:
                    process=subprocess.run([str(binary)],cwd=runs,stdin=stdin,stdout=stdout,stderr=stderr,
                        env={**os.environ,'PATH':'/usr/bin:/bin','FC':'/usr/bin/gfortran'},timeout=300)
                    evidence.update(returncode=process.returncode,status='completed')
                except subprocess.TimeoutExpired:
                    evidence.update(returncode=None,status='timeout')
            evidence['stdout_sha256']=sha(runs/'stdout'); evidence['stderr_sha256']=sha(runs/'stderr')
            evidence['seconds']=time.monotonic()-start
            evidence['completion']='WEPP COMPLETED' in (runs/'stdout').read_text()
            save(root/'execution-result.json',evidence)
            try:
                if evidence['returncode']!=0 or not evidence['completion']: raise ValueError('Native execution incomplete')
                if any(sha(runs/n)!=v for n,v in before.items()): raise ValueError('Input changed during execution')
                evidence.update(read_native.read(root,fixture[lane]))
            except (ValueError,KeyError,OSError,ZeroDivisionError,OverflowError) as error:
                evidence.update(passed=False,validation_error=str(error))
            save(root/'receipt.json',evidence); results.append(evidence)
            print(json.dumps(dict(chkey=chkey,lane=lane,passed=evidence['passed'],error=evidence.get('validation_error'))),flush=True)
    for name,r in built.items():
        if sha(probe/'build'/name)!=r['sha256'] or sha(out/'build-evidence'/name)!=r['sha256']: raise ValueError('Build changed')
    if any(sha(original/'runs'/n)!=r['sha256'] for n,r in inputs.items()): raise ValueError('Original input changed')
    if sha(fixture_receipt)!=fixture_hash or any(sha(p)!=v for p,v in helper_hashes.items()): raise ValueError('Helper/fixture drift')
    comparisons=[]
    for key in PANEL:
        pair=[r for r in results if r['chkey']==key]
        changed=None
        if all(r['passed'] for r in pair):
            changed=[n for n,v in pair[0]['output_hashes'].items() if pair[1]['output_hashes'][n]!=v]
            if key=='84543623' and changed: raise ValueError('Zero-rock output drift')
        comparisons.append(dict(chkey=key,changed_outputs=changed))
    if any(sha(p)!=v for p,v in libraries.items()): raise ValueError('Runtime library drift')
    passed=all(r['passed'] for r in results)
    save(out/'receipt.json',dict(passed=passed,cases=results,comparisons=comparisons,original_inputs_unchanged=True,build_unchanged=True))
    if not passed: raise SystemExit(1)
if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--repo',type=Path,required=True); p.add_argument('--fixtures',type=Path,required=True); p.add_argument('--out',type=Path,required=True)
    a=p.parse_args(); main(a.repo.resolve(),a.fixtures.resolve(),a.out.resolve())
