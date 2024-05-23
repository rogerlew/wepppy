import os
from os.path import join as _join
from os.path import split as _split
from os.path import exists as _exists

import redis

import rq
from rq import Worker
from rq.job import Job
from rq.registry import StartedJobRegistry

from wepppy.weppcloud.utils.helpers import get_wd
from wepppy.nodb.status_messenger import StatusMessenger


REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
RQ_DB = 9


shared_redis = None


def _get_redis_conn():
    global shared_redis
    if shared_redis is None:
        shared_redis = redis.Redis(host=REDIS_HOST, port=6379, db=RQ_DB)
    return shared_redis


def get_job(job_id):
    job = Job.fetch(job_id, connection=_get_redis_conn())
    print(job.is_started)
    print(job.get_status())

if __name__ == "__main__":
    import sys
    get_job(sys.argv[-1])

