import json,time,datetime
import redis
from rq.job import Job
from rq.registry import FinishedJobRegistry,FailedJobRegistry,StartedJobRegistry
from wepppy.config.redis_settings import RedisDB,redis_connection_kwargs
c=redis.Redis(**redis_connection_kwargs(RedisDB.RQ));now=time.time();window=now-86400
counts={};ids=set()
for cls in [FinishedJobRegistry,FailedJobRegistry]:
 r=cls('batch',connection=c);n=c.zcard(r.key);raw=c.zrange(r.key,max(0,n-3000),-1);counts[cls.__name__]={'registry_count':n,'sampled':len(raw),'truncated':n>3000};ids.update(raw)
# RQ v1 started entries are job IDs; no registry cleanup is called.
r=StartedJobRegistry('batch',connection=c);ids.update(c.zrange(r.key,0,-1))
def timestamp(raw):
 if not raw:return None
 return datetime.datetime.fromisoformat(raw.decode().replace('Z','+00:00')).replace(tzinfo=datetime.timezone.utc).timestamp()
seconds=0;overlap=0;missing=0;earliest_end=None;latest_end=None;finished_24h=0;active=0
for raw in ids:
 key=Job.key_for(raw.decode());start,end,status=c.hmget(key,'started_at','ended_at','status');a=timestamp(start);b=timestamp(end)
 if a is None:missing+=1;continue
 if b is not None:
  earliest_end=b if earliest_end is None else min(earliest_end,b);latest_end=b if latest_end is None else max(latest_end,b)
  finished_24h+=int(b>=window)
 elif status==b'started':b=now;active+=1
 else:continue
 duration=max(0,min(now,b)-max(window,a));seconds+=duration;overlap+=int(duration>0)
print(json.dumps({'window_end':now,'window_seconds':86400,'registries':counts,'observed_worker_seconds_in_window':seconds,'observed_average_busy_workers':seconds/86400,'overlapping_jobs':overlap,'finished_in_window':finished_24h,'active_with_start':active,'missing_start_or_expired':missing,'sample_earliest_end':earliest_end,'sample_latest_end':latest_end,'limitation':'retained job attempts only; expired history and earlier retry attempts are not reconstructed; raw read without cleanup'}))
