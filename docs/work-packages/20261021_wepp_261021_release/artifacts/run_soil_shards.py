from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import subprocess,json
root=Path('/workdir/wepppy/docs/work-packages/20261021_wepp_261021_release/artifacts')
nodes=[line.strip() for line in (root/'soil-collection.log').read_text().splitlines() if line.startswith('tests/') and '::test_' in line]
assert len(nodes)==230, len(nodes)
shards=[nodes[i::4] for i in range(4)]
(root/'soil-shards.json').write_text(json.dumps(shards,indent=2)+'\n')
def run(i):
 with (root/f'soil-shard-{i}.log').open('w') as log:
  proc=subprocess.run(['wctl','run-pytest',*shards[i],'-q','--maxfail=1'],cwd='/workdir/wepppy',stdout=log,stderr=subprocess.STDOUT)
 return {'shard':i,'collected':len(shards[i]),'returncode':proc.returncode}
with ThreadPoolExecutor(max_workers=4) as pool:
 results=list(pool.map(run,range(4)))
(root/'soil-shards-results.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(results))
raise SystemExit(0 if all(r['returncode']==0 for r in results) else 1)
