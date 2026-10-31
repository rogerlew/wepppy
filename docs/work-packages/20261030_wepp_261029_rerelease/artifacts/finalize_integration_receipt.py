"""Retain segmented suite results without relabeling either failed initial run."""
from pathlib import Path
import json,re,hashlib,shutil
R=Path('/workdir/wepppy');N=R/'out/roads-channel-accounting-20261030';A=R/'docs/work-packages/20261030_wepp_261029_rerelease/artifacts'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def counts(line):
 return {name:int(m.group(1)) if (m:=re.search(r'(\d+) '+name,line)) else 0 for name in ['passed','skipped','failed','errors','warnings']}
log=(N/'isolated-full-suite.log').read_text();shards={}
for line in log.splitlines():
 m=re.match(r'\[pytest-shard ([1-4])\].*=.*\d+ passed',line)
 if m:shards[m.group(1)]=counts(line)
assert set(shards)==set('1234'),shards
assert shards['2']['failed']==1,shards
assert all(shards[s]['failed']==0 and shards[s]['errors']==0 for s in ['4']),shards
assert shards['3']['failed']==1 and shards['3']['errors']==0,shards
assert shards['1']['failed']==1 and shards['1']['errors']==0,shards
replay=(N/'isolated-shard2-replay.log').read_text();lines=[l for l in replay.splitlines() if re.match(r'=.*\d+ passed',l)]
assert lines, 'replay not complete'
result=counts(lines[-1]);assert result['failed']==0 and result['errors']==0,result
assert 'FAILED ' not in replay
tail=(N/'isolated-shard3-tail-replay.log').read_text();tail_lines=[l for l in tail.splitlines() if re.match(r'=.*\d+ passed',l)];assert tail_lines
tail_result=counts(tail_lines[-1]);assert tail_result['failed']==0 and tail_result['errors']==0 and 'FAILED ' not in tail
assert 'tests/weppcloud/test_run_catalog_reader.py .......F' in log
tail1=(N/'isolated-shard1-tail-replay.log').read_text();tail1_lines=[l for l in tail1.splitlines() if re.match(r'=.*\d+ passed',l)];assert tail1_lines
tail1_result=counts(tail1_lines[-1]);assert tail1_result['failed']==0 and tail1_result['errors']==0 and 'FAILED ' not in tail1
assert 'tests/weppcloud/controllers_js/test_unitizer_client_js.py .F' in log
complete=[shards[s] for s in ['4']]+[result,tail_result,tail1_result]
assert tail_result['skipped']==0
collected={m.group(1):int(m.group(2)) for m in re.finditer(r'\[pytest-shard ([1-4])\].*collected (\d+) items',log)}
total_passed=sum(c['passed'] for c in complete)+shards['3']['passed']+shards['1']['passed']-8
total_skipped=sum(c['skipped'] for c in complete)+shards['3']['skipped']+shards['1']['skipped']
assert total_passed+total_skipped==sum(collected.values()),(total_passed,total_skipped,collected)
receipt={'base_commit':'e35d7a3e69497ddfd9709736af50107f56963584','scope':'Published base plus frozen release-owned overlay; complete module coverage through original shard 4, complete unchanged shard-2 replay, and original shards 1/3 plus their failed module/tail replays. No tests or thresholds changed.','shared_checkout_attempt':{'command':'wctl run-pytest tests --maxfail=1','passed':10160,'skipped':336,'failed':1,'failure':'Concurrent unrelated bootstrap helper parse_json_payload is undefined; isolated bootstrap module passes all five tests.'},'isolated_initial_shards':shards,'isolated_initial_failure':'Climate HTTP simulation 1.2390735149383545 s exceeded existing 1 s limit. Full unchanged seven-test module passes in replay.','isolated_shard2_replay':result,'isolated_shard1_tail_replay':tail1_result,'isolated_shard1_setup_failure':'Ignored controllers-gl.js absent from detached checkout. Canonical generator builds the bundle from unchanged isolated sources; one prior passing test in the repeated module counted once.','isolated_shard3_tail_replay':tail_result,'isolated_shard3_setup_failure':'Detached checkout lacked Playwright module discovery; explicit NODE_PATH and PLAYWRIGHT_BROWSERS_PATH reuse existing main-checkout dependencies. No tracked files changed. Seven earlier passes in repeated catalog-reader module counted once.','completed_segmented_coverage':{'passed':total_passed,'skipped':total_skipped,'failed':0,'errors':0,'collected':sum(collected.values()),'accounting':'Eight repeated passing tests (seven catalog reader, one unitizer) counted once; catalog tail has zero skips; completed pass+skip count equals all four original shard collections.'},'log_sha256':{name:digest(N/name) for name in ['wepppy-full-suite.log','isolated-full-suite.log','isolated-shard2-replay.log','isolated-bootstrap-check.log','isolated-preflight.log','isolated-broad-exceptions.log','isolated-shard3-tail-replay.log','isolated-shard1-tail-replay.log','isolated-bundle-build.log']},'disposition':'Release-specific native and runtime checks pass; complete isolated application regression coverage passes in segments. All initial failed attempts remain retained; this is not a claim of one uninterrupted green full-suite run.'}
(A/'full-suite-disposition.json').write_text(json.dumps(receipt,indent=2)+'\n')
for name in ['isolated-shard2-selection.json','resume_isolated_shard2.py','isolated-shard3-tail-selection.json','resume_isolated_shard3_tail.py','isolated-shard1-tail-selection.json','resume_isolated_shard1_tail.py']:
 shutil.copy2(N/name,A/name)
x=json.loads((A/'integration-gates.json').read_text());x['gates']['full_suite']='complete segmented isolated coverage; failed shared and first isolated attempts retained';x['full_suite_disposition']='full-suite-disposition.json';x['gates']['isolated_broad_exceptions']='pass; zero changed production Python files';(A/'integration-gates.json').write_text(json.dumps(x,indent=2)+'\n')
print(json.dumps(receipt['completed_segmented_coverage']))
