import concurrent.futures,json,subprocess,shlex
from pathlib import Path
b=Path('docs/work-packages/20261023_query_catalog_async_refresh/artifacts')
roles=json.loads((b/'20261026_production_preflight.json').read_text())['containers'];script=Path('/tmp/qcat_rollout_state_readback.py').read_text()
def check(r):
 result=subprocess.run(['ssh',r['host'],'docker exec -i -u 1002:130 '+shlex.quote(r['container'])+' python -'],input=script,text=True,capture_output=True,timeout=60)
 return {'host':r['host'],'container':r['container'],'returncode':result.returncode,'data':json.loads(result.stdout) if result.returncode==0 else None,'error_type':None if result.returncode==0 else 'container_readback_failed'}
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:results=list(pool.map(check,roles))
(b/'20261027_final_rollout_state.json').write_text(json.dumps({'containers':results},indent=2)+'\n')
print(json.dumps({'checked':len(results),'failures':sum(r['returncode']!=0 for r in results),'enabled_values':[r['data']['refresh_enabled_environment'] for r in results if r['data']],'roots_set':[r['data']['explicit_roots_set'] for r in results if r['data']]}))
