"""Bind revision 7 only after final native gates, without inheriting old passes."""
from pathlib import Path
import hashlib,json,re
NATIVE=Path('/home/workdir/wepp-forest-release-20261009')
EVIDENCE=Path('/wc1/holdouts/mipa-native-r7-20261103')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    names=['wepp_261029','wepp_261029_hill']
    pair={name:sha(NATIVE/'release'/name) for name in names}
    log=(EVIDENCE/'native-pytest-v2.log').read_text()
    summary=log.strip().splitlines()[-1]
    match=re.fullmatch(r'=+ (\d+) passed(?:, \d+ warnings)? in .* =+',summary)
    assert match,log[-1500:]
    assert 'passed=31\tfailed=0' in (EVIDENCE/'watchlist-v2.log').read_text()
    assert 'artifact policy OK' in (EVIDENCE/'artifact-policy-v2.log').read_text()
    for role in ['hill','watershed']:assert 'success=1' in (EVIDENCE/f'smoke-{role}-v2.log').read_text()
    assert json.loads((EVIDENCE/'controls-final-v1/receipt.json').read_text())['passed']
    histories=json.loads((EVIDENCE/'histories-final-v1/receipt.json').read_text())
    assert histories['binary_sha256']==pair['wepp_261029_hill'] and len(histories['cases'])==8
    for name in names:
        p=NATIVE/'release'/f'{name}.json';data=json.loads(p.read_text())
        old=json.loads((EVIDENCE/'baseline-r6'/f'native-{name}.json').read_text())
        assert data['features']==old['features']
        assert data['sha256']==pair[name]
        data.update(artifact_revision=7,matched_pair_sha256=pair,release_status='local_undeployed_specialized_reference_compatibility')
        for key in ['capacity','execution_calendar','math_runtime']:data[key]=old[key]
        data['supersedes']={'artifact_revision':6,'sha256':old['sha256'],'source_commit':old['source_commit']}
        data['build']={'canonical_builder':'tools/build_wepp_dated_release.sh','command':'TARGET_TAG=261029 tools/build_wepp_dated_release.sh',
            'path_prefix':'/usr/bin:/bin','source_commit':data['source_commit'],'source_preceded_build':True,
            'build_log_sha256':sha(EVIDENCE/'build-r7-v2.log')}
        data['specialized_reference']={'model_source_commit':'2e5928702edd5526a119216bd6be5997729ec72e',
            'historical_binary_sha256':'2c79a5ecb392a6ed7f70102ff7b6caac888d0cb9df1ce303c93eb10d447740a0',
            'contract':'docs/contracts/specialized-revegetation-consumer.md','decision':'ADR-0134'}
        data['validation']={'native_pytest':f'{match[1]} passed',
            'additional_combined_mode':'10 mode tests pass; includes actual final watershed hillslope-to-routing execution',
            'host_smoke':'both roles pass','hillslope_watchlist':'31 passed, 0 failed','artifact_policy':'pass',
            'specialized':'8 complete 16-year daily/hourly histories; 17532 finite water rows each; exact observer parity',
            'reference_consumers':'295 direct compiled reference/candidate checks plus25 reader tests',
            'controls':'6 ordinary daily/hourly cases exact against revision6',
            'application':'post-vendor evidence recorded separately'}
        data['known_limitations']=[
            'Reference fire anniversary, differing canopy comparison/assignment, crop-wide root-depth mutation and logarithm domain behavior deliberately preserved; no field-calibration claim.',
            'RAP supports continuous daily/hourly hillslope simulation; single-event RAP is explicitly rejected. Routing consumes matched passes without RAP reapplied.',
            'No new FC/HK refresh schedule, retention default, thermal recalibration or full water-conservation claim.',
            'Prior Roads screen remains unmet:744/840 passed,96failed. Historical counts are not fresh revision7 campaign results.',
            'No deployment, executable-default switch, Windows release, installed Rust promotion or bulk project regeneration. Regenerate matched hill/watershed outputs.']
        data['validation_evidence']={str(rel):sha(EVIDENCE/rel) for rel in ['native-pytest-v2.log','watchlist-v2.log',
             'controls-final-v1/receipt.json','histories-final-v1/receipt.json','mode-history-qa/pytest-v2.log']}
        data['validation']['reference_consumers']='295 compiled-reference/candidate suite checks plus27 reader checks;2reader cases added after1750full-suite pass'
        data['validation']['application']='Installed matched9005/RAP hill-to-watershed runners pass; complete72hill235OFE35year configured preparation/execution/interchange/report;576declaredoutputs,3004240unique finite raw water rows; sourceproject unchanged'
        data['validation']['configured_observation']='3isolated local-disk service-identity probes(1,11,2OFEs);84bandrows/2940values/14soilheaders;all24ordinaryoutputs exactagainstnormal NFS workflow; retainedNFSdiagnostic attempt timedout300s'
        data['validation']['post_vendor']='8runner/output tests;bothsmokes;provenance pass'
        data['known_limitations'] += [
            'Inherited graphics BIGOUT F10.5 disturbance-age field overflows at10000days;734107asterisk cells in configured72hill graphics,solelythatfield. Formats preserved; installed water reports/interchange do not consume that field.',
            'Optional InterceptionStorage is not emitted by this native water writer and remains null in interchange; dense diagnostic traces require isolated directories and can exceed NFS timeouts.']
        for rel in ['application-pair-v1/receipt.json','configured-execution-v1/receipt.json','configured-execution-v1/artifact-audit-v3.json','configured-observation-v2/receipt.json','configured-independent-qa/audit.json','post-vendor-tests.log','native-producer-reader-v2.log','histories-9005-no-rap-v1/receipt.json']:
            data['validation_evidence'][rel]=sha(EVIDENCE/rel)
        p.write_text(json.dumps(data,indent=2,sort_keys=True)+'\n')
    print(json.dumps(pair,indent=2))
if __name__=='__main__':main()
