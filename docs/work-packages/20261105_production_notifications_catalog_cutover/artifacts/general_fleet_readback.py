import json,subprocess,socket
host=socket.gethostname().split('.')[0]
assert host in ('wepp1','wepp2','wepp3')
config=json.loads(subprocess.check_output(['wctl','docker','compose','config','--format','json']))
ids=subprocess.check_output(['docker','ps','-aq','--filter','label=com.docker.compose.project='+config['name']],text=True).split()
rows=[]
for c in json.loads(subprocess.check_output(['docker','inspect',*ids])):
 service=c['Config']['Labels'].get('com.docker.compose.service')
 if service not in config['services'] or c['Config']['Labels'].get('com.docker.compose.oneoff')=='True':continue
 env=dict(v.split('=',1) for v in c['Config']['Env'] if '=' in v)
 expected=config['services'][service].get('environment',{})
 if 'QUERY_CATALOG_ROOTS_JSON' not in expected:continue
 keys=['QUERY_CATALOG_REFRESH_ENABLED','QUERY_CATALOG_ROOTS_JSON','WEPPCLOUD_NOTIFICATIONS_SWEEP_ENABLED','WEPPCLOUD_RUN_CATALOG_READ_MODE','WEPPCLOUD_RUN_CATALOG_WRITE_MODE','WEPPCLOUD_RUN_CATALOG_SWEEP_ENABLED']
 for key in keys:assert env.get(key)==expected.get(key),(service,key)
 assert env['QUERY_CATALOG_REFRESH_ENABLED']=='true'
 roots=json.loads(env['QUERY_CATALOG_ROOTS_JSON']);assert len(roots)==7 and len({x['namespace'] for x in roots})==4
 assert env.get('WEPPCLOUD_RUN_CATALOG_READ_MODE')=='legacy' and env.get('WEPPCLOUD_RUN_CATALOG_WRITE_MODE')=='timestamp_only' and env.get('WEPPCLOUD_RUN_CATALOG_SWEEP_ENABLED')=='false'
 assert c['State']['Running'] or (host=='wepp1' and service=='scheduler')
 rows.append({'service':service,'id':c['Id'],'image':c['Image'],'state':c['State']['Status'],'started_at':c['State']['StartedAt'],'flags':{k:env.get(k) for k in keys}})
assert rows
print(json.dumps({'host':host,'participants':rows},indent=2))
