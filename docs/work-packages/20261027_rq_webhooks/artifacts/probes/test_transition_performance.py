"""Run explicitly through run_container_tests.py; isolated worker timing evidence."""
import json
import os
from pathlib import Path
import statistics
import time
from uuid import uuid4

from tests.rq.test_rq212_lifecycle import lifecycle
from tests.rq.webhook_tasks import transition_batch
from wepppy.rq.webhook_tracking import WebhookStore
from wepppy.rq.webhook_hooks import admission, install


def test_transition_baseline(lifecycle, monkeypatch):
    monkeypatch.setenv("WEPPCLOUD_RUN_CATALOG_WRITE_MODE", "timestamp_only")
    monkeypatch.setenv("WEPPCLOUD_RUN_CATALOG_READ_MODE", "legacy")
    install()
    store = WebhookStore(lifecycle.connection, 'benchmark-' + str(uuid4()))
    evidence = {}
    count = int(os.getenv("RQ_WEBHOOK_PROBE_TRANSITIONS", "1000"))
    for enabled in (False, True):
        lifecycle.connection.delete(lifecycle.queue.name + ':transition-samples')
        if enabled:
            _, root = store.reserve(principal='benchmark', key='benchmark-intent-1', digest='benchmark',
                                    operation='run-wepp', resource={'type': 'run', 'id': 'synthetic'},
                                    url='https://example.com/unused', job_id=str(uuid4()))
            with lifecycle.connection.pipeline() as pipe:
                with admission(root['job_id'], store.environment):
                    lifecycle.queue.enqueue_call(transition_batch, args=(count + 1,), job_id=root['job_id'], pipeline=pipe)
                store.published(root['job_id'], {'job_id': root['job_id']}, pipeline=pipe)
                pipe.execute()
        else:
            lifecycle.queue.enqueue_call(transition_batch, args=(count + 1,))
        started = time.monotonic()
        with lifecycle.worker(burst=True) as process:
            assert process.wait(timeout=600) == 0
        samples = [float(value) for value in lifecycle.connection.lrange(lifecycle.queue.name + ':transition-samples', 0, -1)]
        assert len(samples) == count + 1
        intervals = [right - left for left, right in zip(samples, samples[1:])]
        evidence['tracked' if enabled else 'baseline'] = {
            'transitions': len(intervals), 'p95_seconds': statistics.quantiles(intervals, n=100)[94],
            'median_seconds': statistics.median(intervals), 'elapsed_seconds': time.monotonic() - started,
        }
    base = evidence['baseline']['p95_seconds']
    delta = evidence['tracked']['p95_seconds'] - base
    evidence.update(delta_seconds=delta, relative_delta=delta / base,
                    threshold_pass=delta <= .05 and delta <= base * .05,
                    scope='Synthetic idle receiver transition baseline; not backlog or model artifact acceptance',
                    uid=os.getuid(), gid=os.getgid())
    Path('/workdir/wepppy/docs/work-packages/20261027_rq_webhooks/artifacts/transition_performance.json').write_text(json.dumps(evidence, indent=2) + '\n')
    print(json.dumps(evidence))
    if os.getenv('RQ_WEBHOOK_PROFILE_HOOKS'):
        timings = {}
        for log in lifecycle.logs:
            for line in log.read_text().splitlines():
                if line.startswith('WEBHOOK_TIMING '):
                    record = json.loads(line.removeprefix('WEBHOOK_TIMING '))
                    timings.setdefault(record['hook'], []).append(record['seconds'])
        print(json.dumps({key: {'mean': statistics.mean(values), 'max': max(values), 'count': len(values)} for key, values in timings.items()}))
