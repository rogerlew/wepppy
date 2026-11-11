"""Run the opt-in synthetic Docker mount acceptance from the repository host."""
from pathlib import Path
import json, os, subprocess, tempfile, time, uuid
repo=Path(__file__).resolve().parents[2]
root=Path(tempfile.mkdtemp(prefix='f5-mounted-',dir='/tmp'));root.chmod(0o755)
for name in ('web','control','serviceaccount','scratch'):
    (root/name).mkdir(mode=0o755)
(root/'scratch').chmod(0o777)
values={
 'web/secret_key':'f5-mounted-web-'+uuid.uuid4().hex,
 'web/salt':'f5-mounted-salt-'+uuid.uuid4().hex,
 'web/key_ring':'f5-ring-one-'+uuid.uuid4().hex+',f5-ring-two-'+uuid.uuid4().hex,
 'web/redis_password':'f5-redis-'+uuid.uuid4().hex,
 'control/token':'f5-control-'+uuid.uuid4().hex,
 'control/key':'-----BEGIN PRIVATE KEY-----\n'+uuid.uuid4().hex+uuid.uuid4().hex+'\n-----END PRIVATE KEY-----',
 'serviceaccount/token':'eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJmNSJ9.'+uuid.uuid4().hex,
}
for name,value in values.items():
    path=root/name;path.write_text(value);path.chmod(0o444)
command=['docker','run','--rm','--name','f5-traceback-mounted','--network','none','--read-only','--user','1000:993',
 '-e','PYTHONPATH=/workdir/wepppy','-e','PYTHONDONTWRITEBYTECODE=1',
 '-v',str(repo)+':/workdir/wepppy:ro',
 '-v',str(root/'web')+':/run/secrets/weppcloud:ro',
 '-v',str(root/'control')+':/run/secrets/weppcloudr:ro',
 '-v',str(root/'serviceaccount')+':/var/run/secrets/kubernetes.io/serviceaccount:ro',
 '-v',str(root/'scratch')+':/probe',
 '--entrypoint','/opt/venv/bin/python','wepppy-dev:latest','/workdir/wepppy/tests/docker/safe_traceback_probe.py']
proc=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
try:
    deadline=time.monotonic()+20
    while not (root/'scratch/ready').exists() and proc.poll() is None:
        if time.monotonic()>deadline: raise RuntimeError('container readiness timeout')
        time.sleep(.05)
    replacement='f5-replacement-'+uuid.uuid4().hex
    temp=root/'web/new-secret';temp.write_text(replacement);temp.chmod(0o444);temp.replace(root/'web/secret_key')
    (root/'scratch/replaced').touch()
    stdout,stderr=proc.communicate(timeout=30)
    for value in [*values.values(),*values['web/key_ring'].split(','),replacement,values['control/key'].splitlines()[1]]:
        assert value not in stdout+stderr, 'synthetic credential leaked'
    assert proc.returncode==0, stdout+stderr
    artifacts=repo / 'docs/work-packages/20261111_safe_traceback_sanitization/artifacts'
    (artifacts/'20261111_container_output.txt').write_text((stdout+stderr).rstrip()+'\n')
    image=subprocess.check_output(['docker','image','inspect','wepppy-dev:latest','--format','{{.Id}}'],text=True).strip()
    print(json.dumps({'status':'PASS','image':image,'uid':1000,'gid':993,'network':'none','readonly_secret_mode':'0444','same_process_replacement':True}))
finally:
    if proc.poll() is None:
        subprocess.run(['docker','stop','-t','1','f5-traceback-mounted'],stdout=subprocess.DEVNULL)
    import shutil
    shutil.rmtree(root)
