import concurrent.futures,json,subprocess,sys
services=['browse','download','dtale','elevationquery','metquery','profile-playback','query-engine','rq-engine','rq-worker','rq-worker-batch','rq-worker-fork-archive','scheduler','shape-converter','weppcloud','wmesque','wmesque2','rq-dashboard']
program='''import json,os,sys,socket,importlib.metadata as m
mask=os.umask(0);os.umask(mask)
print(json.dumps(dict(rq=m.version("rq"),redis=m.version("redis"),croniter=m.version("croniter"),python=sys.version,uid=os.getuid(),gid=os.getgid(),groups=os.getgroups(),umask=oct(mask),hostname=socket.gethostname())))'''
def run(args):return subprocess.check_output(args,text=True)
def one(service):
 cid=run(['wctl','docker','compose','ps','-q',service]).strip()
 inspected=json.loads(run(['docker','inspect',cid]))[0]
 py='python' if service=='rq-dashboard' else '/opt/venv/bin/python'
 runtime=json.loads(run(['wctl','exec','-T',service,py,'-c',program]))
 assert runtime['rq']=='2.12.0',(service,runtime)
 return service,dict(runtime=runtime,container_id=cid,image_id=inspected['Image'],configured_user=inspected['Config']['User'],supplementary_groups=inspected['HostConfig'].get('GroupAdd'),restart_count=inspected['RestartCount'],state={k:inspected['State'][k] for k in ('Status','Running','StartedAt')},mounts=[{k:m[k] for k in ('Type','Source','Destination','RW')} for m in inspected['Mounts']])
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
 result=dict(pool.map(one,services))
print(json.dumps(result,indent=2,sort_keys=True))
