import copy,json,os,socket,subprocess
from pathlib import Path
assert socket.gethostname().split('.')[0]=='wepp1'
root=Path('/var/tmp/wepppy-production-cutover-20261106')
before=json.loads((root/'compose-before-scheduler-mount.json').read_text())
expected=copy.deepcopy(before)
for mount in expected['services']['scheduler']['volumes']:
 if mount['target']=='/wc1':mount['source']='/geodata/wc1'
 if mount['target']=='/geodata':mount['source']='/geodata'
after=json.loads(subprocess.check_output(['wctl','docker','compose','config','--format','json']))
# WCTL renders a fresh temporary env-file path in this unused extension.
for value in (expected,after):
 paths=value['x-wepppy-service']['env_file']
 assert len(paths)==1 and Path(paths[0]).name.startswith('wctl2-env-') and Path(paths[0]).suffix=='.env'
expected['x-wepppy-service']['env_file']=after['x-wepppy-service']['env_file']
assert after==expected,'Unexpected effective Compose change'
fd=os.open(root/'compose-after-scheduler-mount.json',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
with os.fdopen(fd,'w') as f:json.dump(after,f,indent=2)
print(json.dumps({'host':'wepp1','only_changes':['scheduler /wc1 source /wc1 -> /geodata/wc1','scheduler /geodata source /wc1/geodata -> /geodata'],'other_effective_compose_fields_unchanged':True,'render_only_difference':'x-wepppy-service.env_file contains a new WCTL temporary path; every expanded service environment is unchanged'}))
