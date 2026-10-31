"""Bind completed unchanged shard coverage; retain and exclude failed attempts."""
from pathlib import Path
import hashlib,json,re,shutil
A=Path(__file__).resolve().parent
RAW=Path('/workdir/wepppy/out/roads-native-funding-20261031/r3-application-evidence')
RAW.mkdir(exist_ok=True)
main=Path('/tmp/roads-native-funding-r3-application-full-v2.log');replay=Path('/tmp/roads-native-funding-r3-application-shard3-replay-v2.log')
def counts(s):
 return {key:int(m.group(1)) if (m:=re.search(r'(\d+) '+key,s)) else 0 for key in ['passed','skipped','failed','errors']}
text=main.read_text();shards={};collected={}
for line in text.splitlines():
 m=re.match(r'\[pytest-shard ([1-4])\].*=.*\d+ passed',line)
 if m:shards[m[1]]=counts(line)
 m=re.match(r'\[pytest-shard ([1-4])\].*collected (\d+) items',line)
 if m:collected[m[1]]=int(m[2])
assert set(shards)==set(collected)==set('1234'),(shards,collected)
assert shards['3']['failed']==1
assert all(shards[k]['failed']==shards[k]['errors']==0 for k in '14')
assert shards['2']['failed']==1 and shards['2']['errors']==0
assert 'tests/weppcloud/test_run_catalog_reader.py .......F' in text
lines=[s for s in replay.read_text().splitlines() if re.match(r'=.*\d+ passed',s)]
assert lines,'replay incomplete'
r=counts(lines[-1]);assert r['failed']==r['errors']==0 and 'FAILED ' not in replay.read_text()
assert r['passed']+r['skipped']==collected['3'],(r,collected)
tail=Path('/tmp/roads-native-funding-r3-application-shard2-tail.log').read_text()
tail_lines=[s for s in tail.splitlines() if re.match(r'=.*\d+ passed',s)];assert tail_lines,'tail incomplete'
t=counts(tail_lines[-1]);assert t['failed']==t['errors']==0 and 'FAILED ' not in tail
s2=dict(passed=shards['2']['passed']+t['passed']-7,skipped=shards['2']['skipped']+t['skipped'],failed=0,errors=0)
assert s2['passed']+s2['skipped']==collected['2'],(s2,collected)
accepted=[shards[k] for k in '14']+[r,s2];total={k:sum(x[k] for x in accepted) for k in r}
assert total['passed']+total['skipped']==sum(collected.values())
logs={}
for p in Path('/tmp').glob('roads-native-funding-r3-*'):
 if p.is_file() and ('application' in p.name or 'isolated-preflight' in p.name):
  shutil.copy2(p,RAW/p.name);logs[p.name]=hashlib.sha256(p.read_bytes()).hexdigest()
receipt=dict(scope='Committed isolated application base plus final binary pair; provisional sidecars. Final enriched sidecars and public artifacts separately checked after vendoring.',original_shards=shards,original_collected=collected,replayed_whole_shard3=r,replayed_shard2_tail=t,completed_shard2=s2,completed_segmented_coverage=total,logs_sha256=logs,failed_attempts=['Initial partial staging rejected by binary registry; excluded.','Original shard3 mocked deployment renewal timeout124; excluded entire shard from accepted count.','Original shard2 browser executable absent from incorrectly configured /ms-playwright. Canonical existing browser path restored; failed module and complete tail replayed unchanged. Seven prior module passes counted once.','First full shard3 replay AF_UNIX path too long due evidence-directory basetemp; excluded. Second unchanged replay uses short /tmp/r3s3.'],accounting='Complete original shard1+4, shard2 passing prefix plus unchanged failed-module/tail replay minus seven duplicated passes, and complete unchanged shard3 replay; no waived assertions. Not one uninterrupted green suite.')
(A/'application-disposition.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(total))
