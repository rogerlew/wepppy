"""Exercise the production sender unchanged against isolated real TLS sockets."""
import json
import os
import time
from pathlib import Path
from wepppy.rq.webhook_http import deliver

results = {}
for path in ('ack', 'redirect', 'retry', 'deny', 'oversize', 'hang', 'slow'):
    deadline = 1.5 if path in {'hang', 'slow'} else 10
    started = time.monotonic()
    result = deliver('https://webhook.test/' + path, '{"event":"controlled-test"}', 'test-event', seconds=deadline)
    elapsed = time.monotonic() - started
    results[path] = {**result, 'elapsed_seconds': elapsed}
    assert elapsed < deadline + 1, (path, elapsed)
assert results['ack']['status'] == 204
assert results['redirect']['status'] == 302
assert results['retry']['status'] == 503 and results['retry']['retry_after'] == 300
assert results['deny']['status'] == 403
assert results['oversize']['error'] == 'response_headers'
assert results['hang']['error'] == results['slow']['error'] == 'timeout'
results['invalid_tls'] = deliver('https://wrong.webhook.test/ack', '{}', 'test-event')
assert results['invalid_tls']['error'] == 'tls'
results['mixed_dns'] = deliver('https://mixed.webhook.test/ack', '{}', 'test-event')
assert results['mixed_dns']['error'] == 'unsafe_destination'
results['provenance'] = {'uid': os.getuid(), 'gid': os.getgid(), 'groups': os.getgroups(),
                         'network': 'isolated internal Docker network; no public egress',
                         'sender': 'production deliver subprocess, unchanged DNS/TLS/address policy',
                         'trust': 'disposable test CA via SSL_CERT_FILE; no production trust changes'}
Path('/evidence/https_probe.json').write_text(json.dumps(results, indent=2) + '\n')
print(json.dumps(results, indent=2))
