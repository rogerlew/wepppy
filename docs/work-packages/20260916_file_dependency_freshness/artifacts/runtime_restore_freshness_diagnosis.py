"""Read-only accepted/current dependency comparison after the live restore."""
import json
from copy import deepcopy
from pathlib import Path
from wepppy.nodb.mods.postfire_debris_flow import production as p

root = Path('/wc1/runs/qa/qa-freshness-runtime-7e24c8d1')
accepted = p.state_at(root)['last_successful_run']
before = accepted['snapshot']['inputs']
current = p.sources(root, frequency='cli', model='M3')[4]
differences = {}
for key in before:
    if before[key] == current.get(key):
        continue
    if isinstance(before[key], dict) and isinstance(current.get(key), dict):
        differences[key] = {name: {'accepted': value, 'current': current[key].get(name)}
                            for name, value in before[key].items() if value != current[key].get(name)}
        for name in current[key].keys()-before[key].keys():
            differences[key][name] = {'accepted': None, 'current': current[key][name]}
    else:
        differences[key] = {'accepted': before[key], 'current': current.get(key)}
control = deepcopy(current)
control['selections']['soil_inputs'] = before['selections']['soil_inputs']
result = {'accepted_result': accepted['id'], 'source_snapshot_current': p._source_snapshots_current(before,current),
          'comparison_only_control_with_accepted_soil_inventory': p._source_snapshots_current(before, control),
          'artifacts_current': p.artifacts_current(root, accepted, strong=True),
          'different_groups': list(differences), 'differences': differences}
Path(__file__).with_suffix('.json').write_text(json.dumps(result, indent=2)+'\n')
print('Changed groups:', list(differences))
print('Changed selections:', list(differences.get('selections', {})))
print('Accepted artifacts current:', result['artifacts_current'])
