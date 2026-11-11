import copy, json, os, secrets, subprocess, tempfile
from pathlib import Path
root=Path(__file__).resolve().parents[4]
os.chdir(root)
if subprocess.check_output(['docker','ps','-aq','--filter','label=com.docker.compose.project=redis-transport-acceptance'], text=True).strip():
 raise SystemExit('Acceptance project already exists; do not rotate its credential.')
work=Path(tempfile.mkdtemp(prefix='wepppy-redis-transport-acceptance-'))
config=json.loads(subprocess.run(['wctl','config','--format','json'],capture_output=True,text=True,check=True).stdout)
# Retain config privately: it may contain unrelated runtime environment settings.
(work/'canonical.json').write_text(json.dumps(config)); (work/'canonical.json').chmod(0o600)
password=secrets.token_urlsafe(32)+':@ %é'
(work/'redis_password').write_text(password+'\n'); (work/'redis_password').chmod(0o600)
(work/'signing').write_text('transport-signing-fixture'); (work/'signing').chmod(0o600)
services={}
for name in ['redis','rq-worker','status','preflight','rq-dashboard','weppcloud','status-build']:
 s=copy.deepcopy(config['services'][name])
 for key in ['container_name','ports','depends_on','profiles','build','links','extra_hosts','cpuset','deploy','restart']:
  s.pop(key,None)
 s['networks']={'isolated':None}
 s['restart']='no'
 if not s.get('image'):
  s['image']=subprocess.check_output(['docker','inspect',config['services'][name]['container_name'],'--format','{{.Config.Image}}'],text=True).strip()
 s['environment']={k:v for k,v in s.get('environment',{}).items() if k not in ['REDIS_PASSWORD','RQ_REDIS_URL','SESSION_REDIS_URL']}
 for key in list(s['environment']):
  if key in ['REDIS_URL','STATUS_REDIS_URL','PREFLIGHT_REDIS_URL']:
   s['environment'][key]='redis://redis:6379/'+('2' if key=='STATUS_REDIS_URL' else '0')
 if name=='redis':
  s['volumes']=[v for v in s['volumes'] if v['target']!='/data']
  (work/'data').mkdir(exist_ok=True)
  s['volumes'].append({'type':'bind','source':str(work/'data'),'target':'/data'})
 if name in ['status','preflight']:
  s['image']='redis-transport-'+name+':candidate'
  s['build']=config['services'][name]['build']
  s['environment'][name.upper()+'_ALLOWED_ORIGINS']='https://example.test'
 if name=='weppcloud':
  s.pop('healthcheck',None)
  s['entrypoint']=['/opt/venv/bin/python']
  s['command']=['-c','print("acceptance client")']
 if name=='status-build':
  s['environment']['REDIS_TRANSPORT_TEST_ADDR']='redis:6379'
  s['environment']['REDIS_TRANSPORT_TEST_PASSWORD_FILE']='/run/secrets/redis_password'
  s['secrets']=[{'source':'redis_password','target':'redis_password'}]
 services[name]=s
secrets_cfg=copy.deepcopy(config['secrets'])
secrets_cfg['redis_password']={'file':str(work/'redis_password')}
secrets_cfg['wepp_auth_jwt_secrets']={'file':str(work/'signing')}
model={'name':'redis-transport-acceptance','services':services,'networks':{'isolated':{'internal':True}},'secrets':secrets_cfg,'volumes':config.get('volumes',{})}
# Cache-only named volumes may retain their existing names; data binds are isolated.
model['volumes']={k:{'external':True,'name':v.get('name',k)} for k,v in model['volumes'].items()}
(work/'compose.json').write_text(json.dumps(model)); (work/'compose.json').chmod(0o600)
assert password not in json.dumps(model)
print('Prepared private isolated canonical Compose model; canary absent from rendered configuration.')

print("Private Compose model:", work/"compose.json")
