"""Stage private files, coordinate host holder with private ASGI interpreter."""
import concurrent.futures
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import threading
import time

HERE=Path(__file__).resolve().parent
OUT=HERE/'http-production-canary-logs';OUT.mkdir(exist_ok=True)
container='docker-rq-worker-fork-archive-1'
repo=HERE.parents[3]
files={'probe.py':(HERE/'http-production-canary-probe.py').read_text(),
       'server.py':(repo/'wepppy/query_engine/app/server.py').read_text(),
       'router.py':(repo/'wepppy/query_engine/app/mcp/router.py').read_text()}
stage='''import json,os,sys,tempfile
from pathlib import Path
assert (os.getuid(),os.getgid())==(1002,130)
p=Path(tempfile.mkdtemp(prefix="qcat-http-canary-"))
for name,text in json.load(sys.stdin).items():
 f=p/name;f.write_text(text);f.chmod(0o600)
print(p)
'''
command='docker exec -i '+container+' python -c '+shlex.quote(stage)
r=subprocess.run(['ssh','wepp3',command],input=json.dumps(files),text=True,capture_output=True,timeout=25)
assert r.returncode==0,r.stderr
private=r.stdout.strip();assert private.startswith('/tmp/qcat-http-canary-')
(OUT/'staging.json').write_text(json.dumps(dict(host='wepp3',private_directory=private,source_sha256={k:hashlib.sha256(v.encode()).hexdigest() for k,v in files.items()}),indent=2))
holder_source=(HERE/'rollout-lock-acceptance-probe.py').read_text().replace("time.sleep(8)","time.sleep(12)")
results=[]
for mode in ['schema','mcp']:
    p=subprocess.Popen(['ssh','wepp3','docker','exec','-i',container,'python','-u',private+'/probe.py',mode],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    events=[];ready=threading.Event()
    def collect():
        with (OUT/(mode+'.jsonl')).open('w') as out:
            for line in p.stdout:
                out.write(line);out.flush()
                try:event=json.loads(line)
                except json.JSONDecodeError:event={'non_json':line.strip()}
                events.append(event)
                if event.get('event')=='ready':ready.set()
    thread=threading.Thread(target=collect);thread.start()
    if not ready.wait(100):
        p.terminate();p.wait(timeout=10);thread.join();(OUT/(mode+'.stderr')).write_text(p.stderr.read());raise RuntimeError('private interpreter failed readiness; outputs retained')
    held=threading.Event();holder_events=[]
    def holder():
        h=subprocess.Popen(['ssh','wepp2','docker','exec','-i','docker-rq-worker-batch-1','python','-','holder'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        h.stdin.write(holder_source);h.stdin.close()
        with (OUT/(mode+'-holder.jsonl')).open('w') as out:
            for line in h.stdout:
                out.write(line);out.flush();event=json.loads(line);holder_events.append(event)
                if event.get('event')=='acquired':held.set()
        code=h.wait(timeout=110);stderr=h.stderr.read();(OUT/(mode+'-holder.stderr')).write_text(stderr)
        return code
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future=pool.submit(holder)
        assert held.wait(25),'holder failed to acquire'
        p.stdin.write('go\n');p.stdin.flush();p.stdin.close()
        code=p.wait(timeout=110);thread.join();stderr=p.stderr.read();(OUT/(mode+'.stderr')).write_text(stderr)
        holder_code=future.result()
    data=dict(mode=mode,exit_code=code,holder_exit_code=holder_code,events=events,holder_events=holder_events)
    results.append(data);(OUT/'results.json').write_text(json.dumps(results,indent=2))
    assert code==0 and holder_code==0,stderr
    release=next(e['epoch'] for e in holder_events if e['event']=='release_start')
    assert all(e['epoch']<release for e in events if e.get('event')=='unrelated_response')
    print(json.dumps(dict(mode=mode,status='passed')),flush=True)
