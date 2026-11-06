import json,os,socket,subprocess,time
from pathlib import Path
if not __debug__:
 raise RuntimeError('Optimized Python is forbidden for hold verification')
host=socket.gethostname().split('.')[0]
services={'wepp1':['weppcloud','rq-engine','scheduler','rq-worker','rq-worker-batch'],'wepp2':['rq-worker','rq-worker-batch'],'wepp3':['rq-worker-fork-archive']}[host]
root=Path('/var/tmp/wepppy-production-cutover-20261106')
config=json.loads((root/'compose-private-before.json').read_text())
baseline=json.loads((root/'containers-private-before.json').read_text())
current_ids=subprocess.check_output(['docker','ps','-aq','--filter','label=com.docker.compose.project='+config['name']],text=True).split()
assert current_ids
current_inventory=json.loads(subprocess.check_output(['docker','inspect',*current_ids]))
rows=[]
for service in services:
 candidates=[c for c in baseline if c['Config']['Labels'].get('com.docker.compose.project')==config['name'] and c['Config']['Labels'].get('com.docker.compose.service')==service]
 assert len(candidates)==1
 old=candidates[0]
 matching=[c for c in current_inventory if c['Config']['Labels'].get('com.docker.compose.service')==service]
 assert len(matching)==1 and matching[0]['Id']==old['Id'], 'Replacement or duplicate service exists'
 current=json.loads(subprocess.check_output(['docker','inspect',old['Id']]))[0]
 assert current['Id']==old['Id'] and current['Image']==old['Image']
 assert current['State']['Status']=='exited' and current['State']['Pid']==0
 assert current['HostConfig']['RestartPolicy']['Name']=='unless-stopped'
 rows.append({'host':host,'service':service,'id':current['Id'],'image':current['Image'],'state':current['State']['Status'],'pid':current['State']['Pid'],'finished_at':current['State']['FinishedAt'],'restart_policy':current['HostConfig']['RestartPolicy']['Name']})
result={'host':host,'observed_at':time.time(),'containers':rows}
p=root/('holds-'+host+'.json');p.write_text(json.dumps(result,indent=2));p.chmod(0o600)
print(json.dumps(result))
