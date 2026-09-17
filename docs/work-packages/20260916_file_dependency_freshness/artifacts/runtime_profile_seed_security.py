"""Read-only verification of actual disposable draft/promoted S02 seed records."""
import hashlib
import json
import os
from pathlib import Path
import stat

from runtime_archive_acceptance import profiles
from wepppy.profile_recorder.sbs_seed import MARKER, read_event_seed


base = Path(__file__).parent
capture = json.loads((base / 'runtime_profile_capture.json').read_text())
profile = Path(capture['promotion']['profile']['profile_root'])
assert capture['runid'].startswith('qa-freshness-')
assert profile.name.startswith('qa-freshness-')
draft = profile.parent / '_drafts' / capture['runid'] / 'freshness-http'
roots = [draft / 'seed/uploads', profile / 'capture/seed/uploads']
before = profiles(roots)
events = {}
for root in roots:
    response_events = [json.loads(line) for line in (root.parent.parent / 'events.jsonl').read_text().splitlines()
                       if json.loads(line).get('stage') == 'response']
    assert len(response_events) == 2
    assert all(event.get(MARKER) == 1 for event in response_events)
    observed = []
    for expected in capture['uploads']:
        seed = read_event_seed(root, expected['event_id'], required=True)
        digest = hashlib.sha256(seed.payload).hexdigest()
        assert digest == expected['sha256']
        observed.append({'event_id': expected['event_id'], 'name': seed.name,
                         'bytes': len(seed.payload), 'sha256': digest})
    assert observed[0]['sha256'] != observed[1]['sha256']
    events[str(root)] = {'events': observed, 'response_markers': [event[MARKER] for event in response_events],
                         'event_modes': {str(path.relative_to(root)): oct(stat.S_IMODE(path.stat().st_mode))
                                         for path in (root / 'sbs/events').rglob('*')}}
after = profiles(roots)
assert before == after
draft_inventory, promoted_inventory = (before[str(root.resolve())]['inventory'] for root in roots)
assert draft_inventory == promoted_inventory
result = {'status': 'passed', 'uid': os.geteuid(), 'gid': os.getegid(), 'groups': os.getgroups(),
          'roots': events, 'byte_mode_inventory': before,
          'read_only_noninterference': True, 'draft_promotion_parity': True,
          'external_profile_archival': 'Not executed or implied by project archive',
          'failed_event_runtime_scope': 'No failed event in this actual capture; implementation failure probes remain separate'}
(base / 'runtime_profile_seed_security.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'status': 'passed', 'roots': [str(root) for root in roots],
                  'verified_events_per_root': 2, 'draft_promotion_byte_mode_parity': True}))
