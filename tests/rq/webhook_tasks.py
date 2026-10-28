"""Synthetic producer graphs run by the real WepppyRqWorker integration harness."""
from rq import Queue, get_current_job
from rq.job import Dependency


def leaf(mode='success'):
    if mode == 'uncaught':
        raise RuntimeError('Controlled execution failure')
    if mode == 'caught':
        return {'domain_status': 'failed'}
    return {'domain_status': 'succeeded'}


def graph(mode):
    parent = get_current_job()
    queue = Queue(parent.origin, connection=parent.connection)
    first = queue.enqueue_call(leaf, args=(mode,))
    second = queue.enqueue_call(leaf)
    final = queue.enqueue_call(leaf, depends_on=Dependency([first, second], allow_failure=True))
    parent.meta['jobs:1'] = first.id
    parent.meta['jobs:2'] = second.id
    parent.meta['jobs:3'] = final.id
    parent.save_meta()
    return {'children': [first.id, second.id, final.id]}


def callback_child(job, connection, result, *args, **kwargs):
    child = Queue(job.origin, connection=connection).enqueue_call(leaf)
    job.meta['jobs:callback'] = child.id
    job.save_meta()


def transition_sample():
    import time
    job = get_current_job()
    job.connection.rpush(job.origin + ':transition-samples', time.time())


def transition_batch(count):
    job = get_current_job()
    queue = Queue(job.origin, connection=job.connection)
    queue.enqueue_many([Queue.prepare_data(transition_sample) for _ in range(count)])


def surviving_producer():
    import subprocess
    import sys
    job = get_current_job()
    child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])
    job.connection.set(job.id + ':surviving-producer', child.pid)
    return child.pid


def threaded_child():
    import threading
    from rq import Queue, get_current_job
    parent = get_current_job()
    thread = threading.Thread(target=lambda: Queue(parent.origin, connection=parent.connection).enqueue(leaf))
    thread.start()
    thread.join()


def surviving_thread():
    import threading
    import time
    thread = threading.Thread(target=lambda: time.sleep(30), daemon=True)
    thread.start()


def forked_notification_failure():
    import os
    from rq import Queue, get_current_job
    from wepppy.rq.webhook_tracking import WebhookStore
    parent = get_current_job()
    pid = os.fork()
    if pid == 0:
        def unavailable(*args, **kwargs):
            raise ValueError('Injected notification receipt failure')
        WebhookStore.record_member = unavailable
        Queue(parent.origin, connection=parent.connection).enqueue(leaf)
        os._exit(0)
    os.waitpid(pid, 0)


def after_return_thread(fail=False):
    """Force helper publication after the workhorse has sent its completion byte."""
    import threading
    from rq import Queue, get_current_job
    from wepppy.rq import webhook_hooks
    from wepppy.rq.webhook_tracking import WebhookStore
    parent = get_current_job()
    release = threading.Event()
    original_record = WebhookStore.record_member
    def produce():
        release.wait()
        if fail:
            def unavailable(*args, **kwargs):
                raise ValueError('Injected after-return receipt failure')
            WebhookStore.record_member = unavailable
        try:
            Queue(parent.origin, connection=parent.connection).enqueue(leaf)
        finally:
            WebhookStore.record_member = original_record
    thread = threading.Thread(target=produce)
    thread.start()
    original_returned = webhook_hooks.execution_returned
    def returned(job, token):
        original_returned(job, token)
        release.set()
        thread.join()
    webhook_hooks.execution_returned = returned


def after_return_thread_failure():
    return after_return_thread(True)
