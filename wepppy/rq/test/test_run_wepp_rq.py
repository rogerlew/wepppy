import redis
from rq import Queue
from rq.job import Job

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs, redis_host
from wepppy.rq.wepp_rq import run_wepp_rq

REDIS_HOST = redis_host()
RQ_DB = int(RedisDB.RQ)
print(REDIS_HOST, RQ_DB)
conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
redis_conn = redis.Redis(**conn_kwargs)
q = Queue(connection=redis_conn)
job = q.enqueue(run_wepp_rq, 'orphaned-dioxide')
print(job.id)
