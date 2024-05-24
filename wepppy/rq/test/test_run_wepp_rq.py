import os
import redis
from rq import Queue
from rq.job import Job

from wepppy.rq.wepp_rq import run_wepp_rq

REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
RQ_DB = 9
print(REDIS_HOST, RQ_DB)
redis_conn = redis.Redis(host=REDIS_HOST, port=6379, db=RQ_DB)
q = Queue(connection=redis_conn)
job = q.enqueue(run_wepp_rq, 'orphaned-dioxide')
print(job.id)

