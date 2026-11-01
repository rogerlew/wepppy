"""Read-only native incident, declaration-count, checksum and policy review."""
from pathlib import Path
from collections import Counter
import argparse,csv,hashlib,json,subprocess

REPO=Path('/workdir/wepppy').resolve()
ART=REPO/'docs/work-packages/20261029_roads_parameterization_program/artifacts'
NATIVE=Path('/workdir/wepp-forest-release-20261009').resolve()
INC=NATIVE/'docs/ablation/20261031_roads_buffer_roughness_counterfactual'

def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(p):return json.loads(Path(p).read_text())

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();assert not args.output.exists()
    evidence=read(INC/'artifacts/logs/completed-hillslope-response.json')
    for p,h in evidence['source_free_bindings'].items():assert sha(p)==h,p
    declarations={p:h for p,h in evidence['source_free_bindings'].items() if p.endswith('/execution-declaration.json')};assert len(declarations)==5
    tasks={}
    for path in declarations:
        declaration=read(path)
        for t in declaration['tasks']:
            run=str((Path(t['folder'])/'runs/p1.run').resolve());assert run not in tasks;tasks[run]=t
    rows=list(csv.DictReader((INC/'matrix.csv').open(newline='')));assert len(rows)==len(tasks)==148
    assert len({r['case_id'] for r in rows})==148
    assert {str(Path(r['run_file']).resolve()) for r in rows}==set(tasks)
    counts=Counter();attempt_counts={}
    for r in rows:
        key=str(Path(r['run_file']).resolve());t=tasks[key];folder=Path(t['folder']);attempt=r['case_id'].split('--',1)[0]
        count=attempt_counts.setdefault(attempt,Counter());count['declared']+=1
        executed=(folder/'execution-result.json').exists();assert executed==(r['pass_fail']!='NOT_RUN')
        if executed:
            result=read(folder/'execution-result.json');assert result['returncode']==0 and result['completed']
            assert r['exit_code']=='0' and r['success_marker_found']=='true'
            assert r['configured_simulation_years']==r['simulated_years_completed']=='16'
            assert Path(r['stdout_path']).resolve()==(folder/'runs/stdout').resolve()
            assert Path(r['stderr_tail_path']).resolve()==(folder/'runs/stderr').resolve()
            assert 'WEPP COMPLETED HILLSLOPE SIMULATION SUCCESSFULLY' in (folder/'runs/stdout').read_text()
            assert sha(r['binary_path'])==result['binary_sha256'];count['executed']+=1
        else:
            assert r['simulated_years_completed']=='0' and not (folder/'runs/stdout').exists()
            assert not any((folder/'output').glob('H1.*.dat'));count['not_executed']+=1
        counts['executed' if executed else 'not_executed']+=1
    normalized={k:{name:v.get(name,0) for name in ('declared','executed','not_executed')} for k,v in attempt_counts.items()}
    assert normalized==evidence['attempts'];assert counts==Counter(executed=49,not_executed=99)
    assert evidence['accepted_dataset_histories']==36 and not evidence['accepted_parameterization'] and not evidence['sufficient_remedy']
    sums={}
    for line in (INC/'artifacts/checksums.sha256').read_text().splitlines():
        digest,name=line.split(None,1);name=name.strip();assert name not in sums and sha(INC/name)==digest;sums[name]=digest
    files={str(p.relative_to(INC)):sha(p) for p in INC.rglob('*') if p.is_file()}
    assert set(files)==set(sums)|{'artifacts/checksums.sha256'}
    assert all(Path(p).suffix in {'.md','.csv','.json','.sha256'} for p in files)
    status=subprocess.run(['git','status','--porcelain'],cwd=NATIVE,text=True,capture_output=True,check=True).stdout
    assert status.strip()=='?? docs/ablation/20261031_roads_buffer_roughness_counterfactual/'
    policy=subprocess.run(['python','tools/check_ablation_artifact_policy.py'],cwd=NATIVE,text=True,capture_output=True)
    assert policy.returncode==0,(policy.stdout,policy.stderr)
    assert {str(p.relative_to(INC)):sha(p) for p in INC.rglob('*') if p.is_file()}==files
    report=dict(accepted_native_source_free_incident=True,blocking_findings=[],declared_tasks=148,native_executions=49,declared_unexecuted=99,accepted_dataset_histories=36,attempt_counts=normalized,exact_declaration_row_coverage=True,all_executed_success_and_binary_bindings_checked=True,checksummed_files=len(sums),native_tracked_source_and_binary_changes=False,artifact_policy=dict(returncode=0,stdout=policy.stdout,stderr=policy.stderr,script_sha256=sha(NATIVE/'tools/check_ablation_artifact_policy.py')),disclosure='Original incident prose, numeric tables, hashes and metadata only; no private native source implementation copied.',scope='Research evidence publication. Original isolation remains failed; no parameter, source/binary release, or physical-validity promotion.',native_public_allowlist=[dict(path=n,sha256=h) for n,h in sorted(files.items())],script_sha256=sha(__file__),native_model_runs_by_reviewer=0)
    args.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'accepted':True,'rows':148,'executed':49,'not_executed':99,'receipt_sha256':sha(args.output)}))

if __name__=='__main__':main()
