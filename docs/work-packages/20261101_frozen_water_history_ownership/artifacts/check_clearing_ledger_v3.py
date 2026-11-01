import json,sys
from pathlib import Path
pub=Path('docs/work-packages/20261101_frozen_water_history_ownership/artifacts').resolve();sys.path.insert(0,str(pub))
from check_history_reader import trace
from read_clearing_ownership_v3 import extract
out=Path('out/frozen-water-history-20261101/supplement-controls-v3');out.mkdir()
base=trace(stale_frozen=.02,clearing=True)
base=base.replace('C 1 1 1 1 0.1 0.05 0.04 0.02','C 1 1 1 1 0.1 0.05 0.04 -0.1')
second=[]
for line in trace(clearing=True).splitlines()[1:-1]:
 c=line.split()
 if c[0]=='E':c[2]=str(int(c[2])+7);c[3]='2';c[5]='2'
 else:c[1]=str(int(c[1])+7)
 second.append(' '.join(c))
text=base.rsplit('FH_END',1)[0]+'\n'.join(second)+'\nFH_END 14 2\n'
p=out/'two-clears.txt';p.write_text(text)
r=extract(p,out/'ledger.jsonl')
assert r['actual_clearings']==2 and r['unresolved_ids']==['1:1','2:1']
assert r['clears'][0]['before']['negative_coarse_components']==['coarse_liquid']
assert len(r['next_mappings'])==1 and r['next_mappings'][0]['id']=='1:1'
assert r['next_mappings'][0]['event']['map']==2
# Initialization before any later map must explicitly censor that map endpoint.
text=base.rsplit('FH_END',1)[0]
for seq,tag in [(8,'INIT_PRE'),(9,'INIT_POST')]:
 text+=f'E {tag} {seq} 1 1 1 1 1 -1 1 0 1\n'
 text+=f'C {seq} 1 1 1 0.1 0.05 0.04 0.02 0 0 0.025 0.02 0 0.25\n'
 text+=f'F {seq} 1 1 0 0.25 0 0.1\n'
text+='FH_END 9 1\n';p=out/'init-before-map.txt';p.write_text(text)
r=extract(p,out/'init-ledger.jsonl')
assert len(r['endpoints'])==1 and r['endpoints'][0]['next_mapping_censored_by_initialization']
assert not r['next_mappings'] and not r['unresolved_ids']
(out/'receipt.json').write_text(json.dumps(dict(passed=True,all_clears_retained=True,coarse_inconsistency_preserved=True,multiple_pending_ids_preserved=True,next_mapping_join=True,initialization_censor_explicit=True),indent=2)+'\n')
print('supplement v3 controls passed')
