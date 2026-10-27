"""Serial bounded profiling; all path-bearing files remain in private /tmp."""
import hashlib,json,os,subprocess,sys,time
from pathlib import Path
assert (os.getuid(),os.getgid())==(1002,130)
private=Path(__file__).parent
source=Path('/tmp/qcat-capacity-profile-20261027')
samples_raw=(source/'samples.json').read_bytes();summary=json.loads((source/'summary.json').read_text())
samples=json.loads(samples_raw)
(private/'samples-private.json').write_bytes(samples_raw)
assert summary['profiled']==summary['discovered'] and all(summary['inventory_completed']), 'classification incomplete'
prior=json.loads((Path(sys.argv[1])/'aggregate.json').read_text())
completed={r['digest']:r for r in prior['results'] if r['exit_code']==0}
manifest=dict(sample_snapshot_sha256=hashlib.sha256(samples_raw).hexdigest(),profile_summary=summary,snapshot_epoch=time.time(),selection='final classified population; 12 smallest writable path digests per namespace',sample_digests={k:[x['digest'] for x in rows] for k,rows in samples.items()},per_process_seconds=300,overall_seconds=1800)
(private/'manifest.json').write_text(json.dumps(manifest,indent=2))
items=[dict(namespace=ns,**rows[i]) for i in range(max(map(len,samples.values()))) for ns,rows in samples.items() if i<len(rows)]
reused=[dict(completed[i['digest']],measurement_origin='exploratory_completed') for i in items if i['digest'] in completed]
selected=len(items)
items=[i for i in items if i['digest'] not in completed]
results=[];start=time.monotonic()
for item in items:
 if time.monotonic()-start>=1800:break
 began=time.monotonic();timeout=min(300,1800-(began-start));status='completed'
 try:
  r=subprocess.run([sys.executable,str(private/'probe.py')],input=json.dumps(item),capture_output=True,text=True,timeout=timeout)
  stdout=r.stdout;stderr=r.stderr;code=r.returncode
 except subprocess.TimeoutExpired as exc:
  stdout=exc.stdout or b'';stderr=exc.stderr or b''
  if isinstance(stdout,bytes):stdout=stdout.decode(errors='replace')
  if isinstance(stderr,bytes):stderr=stderr.decode(errors='replace')
  code=None;status='timeout'
 # Raw output may contain native paths. It stays only in the private host directory.
 (private/(item['digest']+'.stdout')).write_text(stdout)
 (private/(item['digest']+'.stderr')).write_text(stderr)
 events=[]
 for line in stdout.splitlines():
  try:event=json.loads(line)
  except json.JSONDecodeError:continue
  if isinstance(event,dict) and event.get('marker')=='component-profile':events.append(event)
 result=dict(namespace=item['namespace'],digest=item['digest'],execution_status=status,measurement_origin='final_followup',exit_code=code,wall_seconds=time.monotonic()-began,events=events,stderr_bytes=len(stderr.encode()),stderr_sha256=hashlib.sha256(stderr.encode()).hexdigest())
 results.append(result)
 output=dict(manifest=manifest,results=results,reused=reused,selected=selected,followup_selected=len(items),attempted=len(results),elapsed_seconds=time.monotonic()-start)
 (private/'aggregate.json').write_text(json.dumps(output,indent=2));print(json.dumps(dict(event='progress',attempted=len(results),selected=len(items),namespace=item['namespace'],digest=item['digest'],wall_seconds=result['wall_seconds'],exit_code=code,status=status)),flush=True)
print(json.dumps(dict(event='completed',attempted=len(results),selected=len(items),elapsed_seconds=time.monotonic()-start)),flush=True)
