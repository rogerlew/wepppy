import os
from os.path import join as _join
from os.path import split as _split
from os.path import exists as _exists

import signal

import logging

import json
import traceback

import redis

import rq
from rq import Worker, Queue, Connection
from rq.job import Job
from rq.registry import StartedJobRegistry
from rq.exceptions import NoSuchJobError

from wepppy.weppcloud.utils.helpers import get_wd
from wepppy.nodb.status_messenger import StatusMessenger

from dotenv import load_dotenv
_thisdir = os.path.dirname(__file__)

load_dotenv(_join(_thisdir, '.env'))

REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
RQ_DB = 9

DEFAULT_RESULT_TTL = 604_800  # 1 week


class JobCancelledException(Exception):
    """Custom exception raised when a job is cancelled."""
    pass


class WepppyRqWorker(Worker):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set the signal handler for SIGUSR1
        signal.signal(signal.SIGUSR1, self.handle_cancel_signal)
        
    def perform_job(self, job: 'Job', queue: 'Queue') -> bool:
        self.default_result_ttl = DEFAULT_RESULT_TTL
        runid = job.args[0]
        job.meta['pid'] = os.getpid()
        job.meta['runid'] = runid
        job.save()

        wd = get_wd(runid)
        file_handler = None

        if wd:
            file_handler = logging.FileHandler(_join(wd, 'rq.log'))
            self.log.addHandler(file_handler)

        try:
            print(f"Starting job {job.id}")
            return super().perform_job(job, queue)
        finally:
            if file_handler:
                self.log.removeHandler(file_handler)
                
    def handle_job_failure(self, job: 'Job', queue: 'Queue', started_job_registry=None, exc_string=''):
        super().handle_job_failure(job, queue, started_job_registry)
        StatusMessenger.publish('f{runid}:rq', json.dumps({'job': job.id, 'status': 'failed'}))
        print(f"Job {job.id} Failed")

    def handle_job_success(self, job: 'Job', queue: 'Queue', started_job_registry: StartedJobRegistry):
        super().handle_job_success(job, queue, started_job_registry)
        StatusMessenger.publish('f{runid}:rq', json.dumps({'job': job.id, 'status': 'success'}))
        print(f"Finished job {job.id}")

    def handle_cancel_signal(self, signum, frame):
        """Handle SIGUSR1 by raising an exception to stop the job."""
        raise JobCancelledException("Job was cancelled")
        
    def handle_exception(self, job: 'Job', *exc_info):
        super().handle_exception(job, *exc_info)
        StatusMessenger.publish('f{runid}:rq', json.dumps({'job': job.id, 'status': 'exception'}))
        print(f"Job {job.id} Raised Exception")
        exc_string = ''.join(traceback.format_exception(*exc_info))
        job.meta['exc_string'] = exc_string
        job.save()


def start_worker():
    with Connection(redis.Redis(host=REDIS_HOST, port=6379, db=RQ_DB)):
        qs = [Queue('high'), Queue('default'), Queue('low')]
        w = WepppyRqWorker(qs)
        w.work()


if __name__ == '__main__':
    num_workers = 5
    workers = []

    for _ in range(num_workers):
        p = Process(target=start_worker)
        p.start()
        workers.append(p)

    for p in workers:
        p.join()

