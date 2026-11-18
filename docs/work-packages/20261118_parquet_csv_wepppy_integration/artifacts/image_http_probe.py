import base64,concurrent.futures,fcntl,hashlib,http.client,json,os,socket,subprocess,time
from pathlib import Path
root=Path('/tmp/wepppy-parquet-csv')
log=open('/tmp/browse-acceptance.log','w+')
server=subprocess.Popen(['/opt/venv/bin/gunicorn','--workers','8','--timeout','120','--bind','127.0.0.1:19009','-k','uvicorn.workers.UvicornWorker','wepppy.microservices.browse:app'],stdout=log,stderr=log)
base='/weppcloud/runs/csv-acceptance/cfg/download/'
records=[]
def get(path,query='?as_csv=1'):
 c=http.client.HTTPConnection('127.0.0.1',19009,timeout=160);c.request('GET',base+path+query);r=c.getresponse();h=hashlib.sha256();n=0;start=time.monotonic()
 while b:=r.read(65536):h.update(b);n+=len(b)
 result=dict(file=path,status=r.status,bytes=n,sha256=h.hexdigest(),seconds=time.monotonic()-start,request_id=r.getheader('X-Request-Id'));c.close();return result
try:
 for _ in range(240):
  log.flush()
  if Path(log.name).read_text().count('Application startup complete.')>=8:break
  if server.poll() is not None:raise RuntimeError('server exited')
  time.sleep(.25)
 else:raise RuntimeError('not all eight workers started')
 records.append(dict(workers_ready=8,uid=os.getuid(),gid=os.getgid(),groups=os.getgroups(),umask=oct(os.umask(0o22))))
 # Two real slow readers retain both slots after headers. Do not drain bodies.
 sockets=[]
 for _ in range(2):
  s=socket.socket();s.setsockopt(socket.SOL_SOCKET,socket.SO_RCVBUF,4096);s.settimeout(160);s.connect(('127.0.0.1',19009));s.sendall(('GET '+base+'H.wat.parquet?as_csv=1 HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n').encode());head=b''
  while b'\r\n\r\n' not in head:head+=s.recv(1)
  assert head.startswith(b'HTTP/1.1 200'),head
  sockets.append(s)
 busy=get('flowpaths.parquet');assert busy['status']==503,busy;records.append(dict(slow_readers=2,busy=busy))
 for s in sockets:s.close()
 for _ in range(400):
  if not any(root.glob('slot-[01]')):break
  time.sleep(.025)
 else:raise RuntimeError('disconnect scratch not reclaimed')
 records.append(dict(disconnect_cleanup=True,lock_files=len(list(root.glob('*.lock')))))
 # Full response digest is the accepted legacy maximum-size oracle.
 big=get('H.wat.parquet');assert big['status']==200 and big['bytes']==444752939 and big['sha256']=='3b46f65692f3fbab2db74891eb1ce647114c640f021c36cc3e3a156c969c7231',big;records.append(big)
 raw=get('H.wat.parquet','');assert raw['sha256']==hashlib.sha256(Path('/wc1/runs/cs/csv-acceptance/H.wat.parquet').read_bytes()).hexdigest();records.append(dict(raw_readback=raw))
 flow=get('flowpaths.parquet');assert flow['status']==200;records.append(flow)
 bad=get('invalid.parquet');assert bad['status']==422,bad;records.append(dict(invalid=bad))
 rawbad=get('invalid.parquet','');assert rawbad['status']==200;records.append(dict(invalid_raw=rawbad))
 assert not any(root.glob('slot-[01]'))
 log.flush()
 observed=Path(log.name).read_text()
 assert 'outcome=served' in observed and big['sha256'] in observed, 'successful CSV diagnostics missing'
 records.append(dict(success_hash_retained_in_service_log=True))
 print(json.dumps(dict(status='ok',records=records),indent=2),flush=True)
finally:
 server.terminate()
 try:server.wait(timeout=15)
 except subprocess.TimeoutExpired:server.kill();server.wait()
 log.flush();print(Path(log.name).read_text(),file=__import__('sys').stderr)
