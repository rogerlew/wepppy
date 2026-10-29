"""Diagnostic-only hook timing; never used for acceptance thresholds."""
import functools
import gc
import json
import sys
import time
import redis
from rq import Queue
from wepppy.rq.rq_worker import WepppyRqWorker
from wepppy.rq import webhook_hooks

collections = {}

def collection_timing(phase, info):
    generation = info['generation']
    if phase == 'start':
        collections[generation] = time.monotonic()
    elif generation in collections:
        elapsed = time.monotonic() - collections.pop(generation)
        print('WEBHOOK_TIMING ' + json.dumps({
            'hook': 'gc_generation_' + str(generation), 'seconds': elapsed}), flush=True)

gc.callbacks.append(collection_timing)

for name in ('begin_attempt', 'execution_returned', 'execution_exited', '_append_receipt', '_bounded_connection', '_record', 'producers_exited'):
    original = getattr(webhook_hooks, name)
    def timed(function, label):
        @functools.wraps(function)
        def measured(*args, **kwargs):
            started = time.monotonic()
            try:
                return function(*args, **kwargs)
            finally:
                print('WEBHOOK_TIMING ' + json.dumps({'hook': label, 'seconds': time.monotonic()-started}), flush=True)
        return measured
    setattr(webhook_hooks, name, timed(original, name))
connection = redis.Redis(host='redis', db=9)
WepppyRqWorker([Queue(sys.argv[1], connection=connection)], connection=connection).work(burst=True)
