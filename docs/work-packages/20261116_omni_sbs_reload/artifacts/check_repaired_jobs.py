"""Read only the new browser job tree; retain status and generated report evidence."""
import json
from pathlib import Path
import time
import redis
from rq.job import Job
from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.nodb.mods.omni import Omni

artifacts = Path('/workdir/wepppy/docs/work-packages/20261116_omni_sbs_reload/artifacts')
root_id = json.loads((artifacts/'browser_repaired.json').read_text())['job_id']
connection = redis.Redis(**redis_connection_kwargs(RedisDB.RQ))
deadline = time.monotonic() + 600
while True:
    pending = [root_id]
    jobs = {}
    while pending:
        job_id = pending.pop()
        if job_id in jobs:
            continue
        job = Job.fetch(job_id, connection=connection)
        children = {k:v for k,v in job.meta.items() if k.startswith('jobs:')}
        jobs[job_id] = {'status': job.get_status().value, 'children': children}
        pending.extend(children.values())
    statuses = [j['status'] for j in jobs.values()]
    if all(s == 'finished' for s in statuses):
        break
    if any(s in ('failed', 'stopped', 'canceled') for s in statuses):
        raise RuntimeError(jobs)
    assert time.monotonic() < deadline, jobs
    time.sleep(3)
omni = Omni.getInstance('/wc1/runs/qa/qa-omni-reload-20261116')
report = omni.scenarios_report()
assert not report.empty
report.to_csv(artifacts/'browser_repaired_report.csv', index=False)
(artifacts/'browser_repaired_jobs.json').write_text(json.dumps({'status':'passed', 'jobs':jobs, 'report_rows':len(report)}, indent=2)+'\n')
print('BROWSER_JOB_TREE_PASS', len(jobs), 'report rows', len(report))
