import os,json,hashlib,sys
import requests

def expand(seed,length):
 h=2166136261
 for char in seed:
  h ^= ord(char)
  h=(h+(h<<1)+(h<<4)+(h<<7)+(h<<8)+(h<<24)) & 0xffffffff
 out=''
 while len(out)<length:
  h ^= (h<<13) & 0xffffffff
  h ^= h>>17
  h ^= (h<<5) & 0xffffffff
  h &= 0xffffffff
  out+=f'{h:08x}'
 return out[:length]

def mint():
 base='http://cap:3000/cap/'+os.environ['CAP_SITE_KEY']
 response=requests.post(base+'/challenge',json={},timeout=10);response.raise_for_status()
 p=response.json();c=p['challenge'];token=p['token'];solutions=[]
 assert 1<=c['c']<=8 and 1<=c['s']<=64 and 1<=c['d']<=6
 for i in range(1,c['c']+1):
  salt=expand(token+str(i),c['s']);target=expand(token+str(i)+'d',c['d'])
  for nonce in range(2000001):
   if hashlib.sha256((salt+str(nonce)).encode()).hexdigest().startswith(target):
    solutions.append(nonce);break
  else: raise RuntimeError('Canary work bound exceeded')
 response=requests.post(base+'/redeem',json={'token':token,'solutions':solutions},timeout=10);response.raise_for_status()
 result=response.json();assert result['success'];return result['token']

if sys.argv[1]=='web':
 from wepppy.weppcloud.app import app
 from wepppy.weppcloud.utils.cap_verify import verify_cap_token,_resolve_cap_config,CapVerificationError
 with app.test_request_context('/login',base_url='https://forest.tail305ec9.ts.net/'):
  assert _resolve_cap_config()[0]=='http://cap:3000/cap'
  assert not verify_cap_token('invalid-notification-canary').get('success')
  try: verify_cap_token('')
  except CapVerificationError: pass
  else: raise AssertionError('Missing token accepted')
  token=mint();assert verify_cap_token(token)['success'];assert not verify_cap_token(token).get('success')
 print(json.dumps({'web':{'fresh_token':True,'replay_rejected':True,'invalid_rejected':True,'missing_rejected':True,'internal_transport':True}}))
else:
 from starlette.requests import Request
 from wepppy.microservices.rq_engine import project_routes as project,fork_archive_routes as fork
 request=Request({'type':'http','scheme':'https','server':('forest.tail305ec9.ts.net',443),'path':'/','headers':[(b'host',b'forest.tail305ec9.ts.net')],'query_string':b''})
 results={}
 for module,name in [(project,'project'),(fork,'fork')]:
  assert module._resolve_cap_config(request)[0]=='http://cap:3000/cap'
  def rejected(value):
   try: result=module._verify_cap_token(request,value)
   except fork.AuthError as exc:
    assert name=='fork' and exc.status_code==403
    return True
   return name=='project' and not result.get('success')
  try: module._verify_cap_token(request,'')
  except (project.CapVerificationError,fork.AuthError): pass
  else: raise AssertionError('Missing token accepted')
  assert rejected('invalid-notification-canary')
  token=mint();result=module._verify_cap_token(request,token)
  assert result is None if name=='fork' else result['success']
  assert rejected(token)
  results[name]={'fresh_token':True,'replay_rejected':True,'invalid_rejected':True,'missing_rejected':True,'internal_transport':True}
 print(json.dumps(results))
