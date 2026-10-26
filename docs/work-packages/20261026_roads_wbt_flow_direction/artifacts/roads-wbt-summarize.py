from pathlib import Path
import json,re,hashlib
root=Path('/tmp/roads-wbt-segmented');base=Path('/workdir/wepppy')
collection=Path('/tmp/roads-wbt-collection.log')
nodes=[s.strip() for s in collection.read_text().splitlines() if re.match(r'^tests/\S+\.py::',s)]
assert len(nodes)==len(set(nodes))==11947
reports=[base/'.pytest_cache/roads-wbt-full.jsonl',*sorted((base/'.pytest_cache/roads-wbt-segmented').glob('*.jsonl'))]
outcomes={};failures={};by={};collection_skips=set()
for p in reports:
 phases={}
 for line in p.read_text().splitlines():
  x=json.loads(line)
  if x.get('$report_type')=='CollectReport' and x.get('outcome')=='skipped':collection_skips.add(x['nodeid'])
  if x.get('$report_type')=='TestReport':
   phases.setdefault(x['nodeid'],{})[x['when']]=x
   if x['outcome']=='failed':failures[x['nodeid']]=max(failures.get(x['nodeid'],0),x['stop'])
 valid={}
 for n,v in phases.items():
  if v.get('teardown',{}).get('outcome')!='passed':continue
  phase=v.get('call',v.get('setup',{}))
  if phase.get('outcome') not in ('passed','skipped'):continue
  if 'call' not in v and phase['outcome']!='skipped':continue
  result=dict(outcome=phase['outcome'],stop=v['teardown']['stop']);valid[n]=result
  if result['stop']>outcomes.get(n,{}).get('stop',0):outcomes[n]=result
 by[p.name]=dict(passed=sum(x['outcome']=='passed' for x in valid.values()),skipped=sum(x['outcome']=='skipped' for x in valid.values()),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
missing=sorted(set(nodes)-outcomes.keys())
unresolved=sorted(n for n,t in failures.items() if outcomes.get(n,{}).get('stop',0)<=t or outcomes[n]['outcome']!='passed')
s=dict(collected=len(nodes),covered=len(set(nodes)&outcomes.keys()),unique_passes=sum(v['outcome']=='passed' for n,v in outcomes.items() if n in nodes),unique_test_skips=sum(v['outcome']=='skipped' for n,v in outcomes.items() if n in nodes),collection_import_skips=sorted(collection_skips),missing_nodes=missing,observed_failures=sorted(failures),unresolved_failures=unresolved,failures_with_later_pass=sorted(set(failures)-set(unresolved)),reports=by,collection_sha256=hashlib.sha256(collection.read_bytes()).hexdigest(),covered_node_set_sha256=hashlib.sha256(('\n'.join(sorted(set(nodes)&outcomes.keys()))+'\n').encode()).hexdigest(),all_collected_nodes_covered=not missing and not unresolved,scope='Segmented execution after canonical run interruption; no test exclusions')
(root/'coverage-summary.json').write_text(json.dumps(s,indent=2)+'\n')
print({k:v for k,v in s.items() if k not in ['missing_nodes','reports','observed_failures','failures_with_later_pass']})
