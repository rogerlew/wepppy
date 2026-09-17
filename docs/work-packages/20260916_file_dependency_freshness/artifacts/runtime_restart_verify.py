"""Read-only filtered container identity evidence; never retain environment secrets."""
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess

root = Path(__file__).parent
before = json.loads((root/'runtime_service_identity_before.json').read_text())
ids = subprocess.check_output(['docker', 'ps', '-q'], text=True).split()
containers = json.loads(subprocess.check_output(['docker', 'inspect', *ids], text=True))
selected = {row['service']: row for row in before}
after = []
for item in containers:
    service = item['Config'].get('Labels', {}).get('com.docker.compose.service')
    if service not in selected:
        continue
    row = {'service': service, 'container': item['Name'].lstrip('/'),
           'container_id': item['Id'], 'image_id': item['Image'],
           'user': item['Config']['User'], 'group_add': item['HostConfig']['GroupAdd'],
           'started_at': item['State']['StartedAt'], 'status': item['State']['Status'],
           'health': item['State'].get('Health', {}).get('Status'),
           'mounts': [{'source': mount['Source'], 'destination': mount['Destination'], 'rw': mount['RW']}
                      for mount in item['Mounts']]}
    old = selected[service]
    row['preserved_user_groups'] = row['user'] == old['user'] and row['group_add'] == old['group_add']
    key = lambda mount: mount['destination']
    row['preserved_mounts'] = sorted(row['mounts'], key=key) == sorted(old['mounts'], key=key)
    row['recreated'] = row['container_id'] != old['container_id']
    after.append(row)
result = {'utc': datetime.now(timezone.utc).isoformat(),
          'source_revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
          'expected_image': 'sha256:00a3e43a88a5c9079a7e58a8423432d69f22b7b09c0a9288078b67abbca1d3f8',
          'services': after}
(root/'runtime_restart_verification.json').write_text(json.dumps(result, indent=2)+'\n')
assert {row['service'] for row in after} == selected.keys()
assert all(row['preserved_user_groups'] and row['preserved_mounts'] and row['recreated']
           and row['image_id'] == result['expected_image'] and row['status'] == 'running'
           and row['health'] in (None, 'healthy') for row in after), 'See retained identity evidence'
print('Recreated', len(after), 'services; image, runtime user/groups and mounts verified')
