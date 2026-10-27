"""Serialize trials on one stable guard; preserve every stdout/stderr and result."""
import concurrent.futures
import json
from pathlib import Path
import subprocess
import time

HERE = Path(__file__).resolve().parent
OUT = HERE/'rollout-lock-receipt-logs'
OUT.mkdir(exist_ok=True)
script = (HERE/'rollout-lock-receipt-probe.py').read_text()
targets = {'wepp1':'docker-rq-worker-batch-1', 'wepp2':'docker-rq-worker-batch-1', 'wepp3':'docker-rq-worker-fork-archive-1'}
results=[]
def run(trial, host, role):
    stem=f'{trial}-{host}-{role}'
    output=OUT/(stem+'.jsonl'); error=OUT/(stem+'.stderr')
    begin=time.time()
    with output.open('w') as o, error.open('w') as e:
        try:
            r=subprocess.run(['ssh',host,'docker','exec','-i',targets[host],'python','-',role], input=script, text=True, stdout=o, stderr=e, timeout=115)
            code=r.returncode; failure=None
        except subprocess.TimeoutExpired as exc:
            code=None; failure=str(exc)
    events=[]
    for line in output.read_text().splitlines():
        try: events.append(json.loads(line))
        except json.JSONDecodeError: events.append({'non_json':line})
    data=dict(trial=trial,host=host,role=role,exit_code=code,driver_error=failure,driver_start_epoch=begin,driver_end_epoch=time.time(),events=events,stderr=error.read_text())
    (OUT/(stem+'-result.json')).write_text(json.dumps(data,indent=2))
    return data

def record(items):
    results.extend(items)
    (OUT/'results.json').write_text(json.dumps(results,indent=2))
    print(json.dumps([dict(trial=r['trial'],host=r['host'],role=r['role'],exit_code=r['exit_code']) for r in items]),flush=True)
    if any(r['exit_code'] != 0 for r in items): raise RuntimeError('trial failed; results preserved; stop before further trials')

trials=[('receipt-wepp2-wepp1','wepp2','wepp1','receipt')]
for trial,holder_host,peer_host,peer_role in trials:
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        holder=pool.submit(run,trial,holder_host,'holder')
        path=OUT/f'{trial}-{holder_host}-holder.jsonl'
        until=time.monotonic()+100
        while time.monotonic()<until:
            if path.exists() and '"event": "acquired"' in path.read_text(): break
            if holder.done():
                record([holder.result()]); raise RuntimeError('holder exited before acquisition')
            time.sleep(.05)
        else:
            record([holder.result()]); raise TimeoutError('holder startup')
        peer=pool.submit(run,trial,peer_host,peer_role)
        record([holder.result(),peer.result()])
