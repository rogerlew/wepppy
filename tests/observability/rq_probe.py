"""Real owned worker probe, isolated from deployment Redis and real secrets."""
import os
import sys


def fail_job():
    exc = ValueError('rq-context ' + os.environ['F5_CHILD'])
    exc.add_note('note ' + os.environ['F5_CHILD'])
    raise exc


def spawn_log():
    import logging
    try:
        fail_job()
    except ValueError:
        logging.exception('spawn-context')
    return 42


def fail_acquisition(output):
    fail_job()


def failure_callback(job, connection, exc_type, exc_value, tb):
    connection.set(job.id + ':callback-type', exc_type.__name__)


def exception_handler(job, exc_type, exc_value, tb):
    job.connection.set(job.id + ':handler-type', exc_type.__name__)
    return True


if __name__ == '__main__':
    from wepppy.observability.safe_logging import install
    from wepppy.observability.safe_traceback import SecretSourceProfile, SecretSourceSpec
    install(SecretSourceProfile('rq-probe', (SecretSourceSpec('F5_CHILD', 'F5_CHILD_FILE'),)))
    import redis
    from rq import Queue
    from wepppy.config import redis_settings
    socket, queue_name = sys.argv[1:3]

    def isolated_kwargs(_db, *, decode_responses=None, extra=None, for_pool=False):
        options = {'db': 2, 'decode_responses': bool(decode_responses)}
        if extra is not None:
            options.update({key: value for key, value in extra.items()
                            if key not in {'socket_keepalive', 'socket_keepalive_options', 'socket_connect_timeout'}})
        if for_pool:
            options.update(connection_class=redis.UnixDomainSocketConnection, path=socket)
        else:
            options['unix_socket_path'] = socket
        return options

    redis_settings.redis_connection_kwargs = isolated_kwargs
    from wepppy.nodb.status_messenger import StatusMessenger
    from wepppy.rq.rq_worker import WepppyRqWorker
    connection = redis.Redis(unix_socket_path=socket, db=2)
    StatusMessenger._client = connection
    worker = WepppyRqWorker([Queue(queue_name, connection=connection)], connection=connection,
                            exception_handlers=[exception_handler])
    worker.work(burst=True)

    # Actual upstream RQ worker-pool target and owned PFDF process boundary.
    from rq.worker_pool import WorkerPool
    class BrokenWorker(WepppyRqWorker):
        def work(self, *args, **kwargs):
            fail_job()
    pool = WorkerPool([Queue(queue_name, connection=connection)], connection=connection,
                      num_workers=1, worker_class=BrokenWorker)
    child = pool.get_worker_process(name='f5-failing-pool', burst=True)
    child.start()
    child.join(10)
    assert child.exitcode == 1
    from pathlib import Path
    import multiprocessing
    from wepppy.nodb.mods.postfire_debris_flow.source_acquisition import _acquisition_worker
    output = Path(os.environ['F5_OUTPUT_DIR'])
    child = multiprocessing.get_context('fork').Process(
        target=_acquisition_worker, args=('f5', fail_acquisition, (), output, None))
    child.start()
    child.join(10)
    assert child.exitcode == 1
    from wepppy.nodb.base import createProcessPoolExecutor
    with createProcessPoolExecutor(1) as executor:
        assert executor.submit(spawn_log).result(timeout=20) == 42
    from wepppy.soils.ssurgo.ssurgo import _create_process_pool_executor
    with _create_process_pool_executor(1) as executor:
        assert executor.submit(spawn_log).result(timeout=20) == 42
    print('canonical-process-boundaries-pass')


def partial_result_job():
    """Successful task whose result contains a controlled migration failure."""
    from unittest.mock import patch
    from wepppy.tools.migrations.cache import invalidate_redis_cache
    import redis
    with patch('redis.Redis', side_effect=redis.RedisError('partial-context ' + os.environ['F5_CHILD'])):
        result = invalidate_redis_cache('/tmp/f5-nonexistent-run')
    return {'result': result}
