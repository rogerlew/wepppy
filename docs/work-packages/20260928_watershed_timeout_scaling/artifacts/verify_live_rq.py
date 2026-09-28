"""Run manually with wctl run-python: inspect disposable, unconsumed RQ graphs."""
import hashlib
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from uuid import uuid4

import redis
from rq import Queue
from rq.job import Job

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.rq import wepp_rq as tasks
from wepppy.rq import wepp_rq_pipeline as pipeline
from wepppy.rq.job_info import get_wepppy_rq_job_info
from wepp_runner.wepp_runner import make_watershed_run


def main():
    conn = redis.Redis(**redis_connection_kwargs(RedisDB.RQ))
    queue = Queue('wrt-validation-' + uuid4().hex, connection=conn, default_timeout=180)
    job_ids = []
    evidence = {'queue': queue.name, 'uid': os.getuid(), 'gid': os.getgid(),
                'graphs_executed': False, 'cases': []}
    try:
        with TemporaryDirectory(prefix='wrt-validation-') as directory:
            source = Path(directory) / 'pw0.run'
            for name in ('enqueue_wepp_pipeline', 'enqueue_wepp_noprep_pipeline',
                         'enqueue_watershed_pipeline', 'enqueue_watershed_noprep_pipeline'):
                make_watershed_run(1000, list(range(1, 1909)), directory, wepp_bin='wepp_dcc52a6')
                before = hashlib.sha256(source.read_bytes()).hexdigest()
                wepp = SimpleNamespace(
                    runs_dir=directory, wepp_bin='wepp_dcc52a6', multi_ofe=False,
                    run_wepp_watershed=True, mods=[],
                    prep_details_on_run_completion=False, dss_export_on_run_completion=False,
                    legacy_arc_export_on_run_completion=False, arc_export_on_run_completion=False,
                    watershed_instance=SimpleNamespace(sub_n=1908))
                climate = SimpleNamespace(input_years=1000, is_single_storm=False,
                                          climate_mode=tasks.ClimateMode.Vanilla)
                if 'noprep' in name:
                    climate.input_years = 1
                    wepp.watershed_instance.sub_n = 1
                parent = queue.enqueue_call(tasks._log_complete_rq, args=('wrt-validation',),
                    meta={'fork_failure': {'target_runid': 'wrt-validation', 'source_runid': 'source'}})
                job_ids.append(parent.id)
                extra = {'has_hillslope_outputs': True} if name.startswith('enqueue_watershed') else {}
                getattr(pipeline, name)(queue, parent, 'wrt-validation', wepp=wepp,
                    climate=climate, tasks=tasks, timeout=43200, **extra)
                children = [value for key, value in parent.meta.items() if key.startswith('jobs:')]
                job_ids.extend(children)
                jobs = [Job.fetch(jid, connection=conn) for jid in children]
                leaf = next(j for j in jobs if j.func_name.endswith('.run_watershed_rq'))
                assert leaf.timeout == 97200
                assert leaf.meta['watershed_timeout']['years'] == 1000
                assert leaf.meta['watershed_timeout']['hillslopes'] == 1908
                assert leaf.meta['fork_failure'] == parent.meta['fork_failure']
                assert leaf.failure_callback.__name__ == 'report_fork_failure'
                assert all(j.timeout in (14400, 43200, 180) for j in jobs if j.id != leaf.id)
                tree = get_wepppy_rq_job_info(parent.id)
                observed = {child['job_id'] for group in tree['children'].values() for child in group}
                assert observed == set(children)
                after = hashlib.sha256(source.read_bytes()).hexdigest()
                assert before == after
                evidence['cases'].append({'pipeline': name, 'parent_id': parent.id,
                    'source_sha256_before': before, 'source_sha256_after': after,
                    'leaf_id': leaf.id, 'timeout': leaf.timeout, 'meta': leaf.meta,
                    'jobs': [{'id': j.id, 'func': j.func_name, 'timeout': j.timeout,
                              'dependencies': j.dependency_ids} for j in jobs], 'job_info': tree})
    finally:
        # Only this unique queue and this harness's own records are removed.
        for jid in reversed(job_ids):
            Job.fetch(jid, connection=conn).delete(remove_from_queue=True, delete_dependents=False)
        queue.delete(delete_jobs=False)
    evidence['cleanup_verified'] = all(not conn.exists(Job.key_for(jid)) for jid in job_ids)
    assert evidence['cleanup_verified']
    Path(__file__).with_name('live_rq.json').write_text(json.dumps(evidence, indent=2, default=str) + '\n')
    print(f'Validated {len(evidence["cases"])} live graphs; removed {len(job_ids)} disposable jobs.')


if __name__ == '__main__':
    main()
