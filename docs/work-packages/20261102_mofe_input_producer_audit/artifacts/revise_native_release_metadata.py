"""Bind undeployed revision6 sidecars without inheriting prior validation claims."""
from pathlib import Path
import hashlib,json,subprocess

NATIVE=Path('/workdir/wepp-forest-release-20261009')
EVIDENCE=Path('/wc1/holdouts/mipa-native-r6-20261102')

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    names=['wepp_261029','wepp_261029_hill']
    pair={name:sha(NATIVE/'release'/name) for name in names}
    # Explicit direct comparison avoids including sidecar hashes as binary roles.
    staged=json.loads((EVIDENCE/'staging-provenance.json').read_text())['pair']
    assert all(pair[name]==staged[name] for name in names)
    branch=subprocess.check_output(['git','branch','--show-current'],cwd=NATIVE,text=True).strip()
    default=subprocess.check_output(['git','symbolic-ref','refs/remotes/origin/HEAD'],cwd=NATIVE,text=True).strip().removeprefix('refs/remotes/origin/')
    assert branch==default
    testlog=(EVIDENCE/'native-pytest-v1.log').read_text()
    assert '1416 passed' in testlog and 'failed' not in testlog.lower(),testlog[-1000:]
    assert 'passed=31\tfailed=0' in (EVIDENCE/'watchlist.log').read_text()
    for role in ('hill','watershed'):
        assert 'success=1' in (EVIDENCE/f'smoke-{role}.log').read_text()
    assert json.loads((EVIDENCE/'ownership-comparison.json').read_text())['passed']
    for name in names:
        path=NATIVE/'release'/f'{name}.json'
        data=json.loads(path.read_text())
        old=json.loads((EVIDENCE/'baseline-r5'/f'vendored-{name}.json').read_text())
        assert data['features']==old['features']
        assert data['sha256']==pair[name]
        data['artifact_revision']=6
        data['matched_pair_sha256']=pair
        data['capacity']=old['capacity']
        data['execution_calendar']=old['execution_calendar']
        data['math_runtime']=old['math_runtime']
        data['release_status']='local_undeployed_bounded_ownership_repair'
        data['supersedes']={'artifact_revision':5,'sha256':old['sha256'],'source_commit':old['source_commit']}
        data['build']={'canonical_builder':'tools/build_wepp_dated_release.sh',
            'command':'TARGET_TAG=261029 tools/build_wepp_dated_release.sh',
            'path_prefix':'/usr/bin:/bin','source_commit':data['source_commit'],
            'source_preceded_build':True,'build_log_sha256':sha(EVIDENCE/'build-r6-v1.log')}
        data['validation']={'native_pytest':'1416 passed; four additional guarded-HK sentinel cases pass separately',
            'host_smoke':'both roles pass','hillslope_watchlist':'31 passed, 0 failed',
            'artifact_policy':'pass','ownership':'four full16year histories; first-consumer wrong-owner samples20/30 to0/30; exact seven-output observer parity',
            'controls':'six single/repeated-material cases preserve exact outputs',
            'pmet':'both role capacities; three distinct pairs and48 actual crop-year mappings; reordered table exact parity',
            'application':'actual runner pair and72-hill copied project execute; final post-vendor validation recorded separately'}
        data['known_limitations']=[
            'No specialized9005 soil/revegetation or RAP cancov.txt/.cov reader support; SOIL-02/COVER-01 native acceptance remains separate HOLD.',
            'Ownership observers record first stage/OFE/layer consumers, not all-time tracing. Drain/lateral probes cover expressions, not complete tile-drain control flow.',
            'No new tillage/density refresh schedule, retention default, frost recalibration or missing-density generalization.',
            'Prior Roads screen remains unmet:744/840 passed (96failed). Other scientific limitations remain unresolved; prior counts are not fresh revision6 campaign evidence.',
            'No deployment, default switch, Windows release or universal physical-validity claim. Regenerate matched hill/watershed outputs; do not reuse old PASS files.']
        data['validation_evidence']={name:sha(EVIDENCE/name) for name in ['ownership-comparison.json','pmet-comparison.json','controls-bound-v1/receipt.json','application-pair-v1/receipt.json','actual-project-v1/receipt.json']}
        tmp=path.with_suffix('.json.mipa.tmp');tmp.write_text(json.dumps(data,indent=2,sort_keys=True)+'\n');tmp.replace(path)
    print(json.dumps(pair))


if __name__=='__main__':main()
