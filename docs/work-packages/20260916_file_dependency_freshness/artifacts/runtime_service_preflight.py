"""Read-only runtime identity and active-job snapshot, run inside a service."""
import inspect
import json
import os
from pathlib import Path
import platform
import stat
import sys
from datetime import datetime, timezone

import redis
from rq import Queue
from rq.job import Job
from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs

connection = redis.Redis(**redis_connection_kwargs(RedisDB.RQ))
queues = []
for name in ('default', 'batch', 'fork-archive'):
    queue = Queue(name, connection=connection)
    registry = queue.started_job_registry
    kwargs = {'start': 0, 'end': -1}
    if 'cleanup' in inspect.signature(registry.get_job_ids).parameters:
        kwargs['cleanup'] = False
    started = registry.get_job_ids(**kwargs)
    jobs = []
    for job in Job.fetch_many(started, connection=connection):
        if job is not None:
            jobs.append({'id': job.id, 'function': job.func_name, 'status': str(job.get_status(refresh=True))})
    queues.append({'queue': name, 'queued': queue.count, 'started': jobs})
old_umask = os.umask(0)
os.umask(old_umask)
from osgeo import gdal
import rasterio
result = {'utc': datetime.now(timezone.utc).isoformat(), 'uid': os.getuid(), 'gid': os.getgid(),
          'groups': os.getgroups(), 'umask': oct(old_umask), 'python': platform.python_version(),
          'gdal': gdal.VersionInfo(), 'rasterio': rasterio.__version__, 'queues': queues,
          'paths': {name: {'resolved': str(Path(name).resolve()), 'mode': oct(stat.S_IMODE(Path(name).stat().st_mode))}
                    for name in ('/workdir/wepppy', '/wc1', '/geodata')}}
print(json.dumps(result, indent=2))
if any(item['queued'] or item['started'] for item in queues):
    sys.exit(2)
