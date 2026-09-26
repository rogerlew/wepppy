"""Development-only acceptance on the existing disposable single-input run.

Uses authenticated upload, real Redis/NoDb/RQ, normal preparation entry points,
and native execution. No service restart or production deployment. Retains JSON
and generated inputs beneath the disposable run for browse/download inspection.
"""
from pathlib import Path
import hashlib
import json
import os
import re
import shutil
import time

from fastapi.testclient import TestClient
import redis
from rq import Queue, Worker
from rq.job import Job

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.microservices.rq_engine import app
from wepppy.nodb.core import Soils, Watershed, Wepp
from wepppy.nodb.single_input_sources import read_source
from wepppy.wepp.soils.utils import WeppSoilUtil
from wepppy.weppcloud.utils.auth_tokens import issue_token
from wepp_runner.wepp_runner import make_hillslope_run, run_hillslope

ROOT = Path('/workdir/wepppy')
RUNID = 'single-input-acceptance-20260925'
WD = Path('/wc1/runs/si') / RUNID


def job_status(job):
    value = job.get_status(refresh=True)
    return getattr(value, 'value', value)


def main():
    assert WD.is_dir() and WD.name == RUNID
    token = issue_token('soil-format-local-acceptance', scopes=['rq:enqueue', 'rq:status'],
                        runs=[RUNID], audience='rq-engine', expires_in=1800,
                        extra_claims={'token_class': 'service', 'roles': ['User']})['token']
    headers = {'Authorization': 'Bearer ' + token}
    records = []
    current_umask = os.umask(0); os.umask(current_umask)
    with TestClient(app) as client, redis.Redis(**redis_connection_kwargs(RedisDB.RQ)) as connection:
        for version in ('2006', '2006.2', '9002'):
            raw = (ROOT / f'tests/data/single_input_soils/{version}.sol').read_bytes()
            deadline = time.monotonic() + 180
            while True:
                response = client.post(f'/api/runs/{RUNID}/config/build-soils',
                    data={'soil_mode': '5', 'initial_sat': '0.42'},
                    files={'input_upload_single_soil': (f'Acceptance {version}.SOL', raw, 'text/plain')},
                    headers=headers)
                if response.status_code != 409 or time.monotonic() >= deadline:
                    break
                time.sleep(1)
            assert response.status_code == 200, response.text
            job = Job.fetch(response.json()['job_id'], connection=connection)
            deadline = time.monotonic() + 180
            while job_status(job) not in ('finished', 'failed') and time.monotonic() < deadline:
                time.sleep(1)
            fresh_worker = False
            if job_status(job) == 'failed':
                # Old long-lived development workers may retain pre-amendment modules.
                # Retry only this run's failed soil build using this freshly imported process.
                assert RUNID in job.args and job.func_name == 'wepppy.rq.project_rq.build_soils_rq'
                queue = Queue(job.origin, connection=connection)
                worker = Worker([queue], connection=connection, name='soil-formats-acceptance-fresh-process')
                assert worker.perform_job(job, queue), job.exc_info
                queue.failed_job_registry.remove(job, delete_job=False)
                fresh_worker = True
            assert job_status(job) == 'finished', job.exc_info
            soils = Soils.getInstance(str(WD))
            accepted, _canonical = read_source(soils, 'soils')
            metadata = soils._single_user_defined_source
            assert accepted == raw and metadata['version'] == version
            wepp = Wepp.getInstance(str(WD))
            watershed = Watershed.getInstance(str(WD))
            translator = watershed.translator_factory()
            # Use actual service/controller wiring, not a manually supplied preserve flag.
            wepp._prep_multi_ofe(translator, max_workers=1)
            runs = WD / 'wepp/runs'
            original = WeppSoilUtil(str(WD / 'soils' / metadata['relative_path']), preserve_input_format=True)
            original.obj['ofes'][0]['sat'] = soils.initial_sat
            artifacts = []
            for hill, count in watershed.mofe_nsegments.items():
                wepp_id = translator.wepp(top=int(hill))
                path = runs / f'p{wepp_id}.sol'
                prepared = WeppSoilUtil(str(path), preserve_input_format=True)
                assert prepared.obj['datver'] == float(version)
                assert len(prepared.obj['ofes']) == count
                assert all(ofe == original.obj['ofes'][0] for ofe in prepared.obj['ofes'])
                shutil.copyfile(ROOT / 'tests/disturbed/data/test_climate.cli', runs / f'p{wepp_id}.cli')
                make_hillslope_run(wepp_id, 2, str(runs), reveg=False, wepp_bin='wepp_260803')
                assert run_hillslope(wepp_id, str(runs), wepp_bin='wepp_260803')[0]
                output = WD / f'wepp/output/H{wepp_id}.loss.dat'
                content = output.read_text()
                assert content and not re.search(r'\b(?:nan|inf(?:inity)?)\b', content, re.IGNORECASE)
                retained = WD / 'soil-format-acceptance' / version / f'p{wepp_id}.sol'
                retained.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, retained)
                artifacts.append({'hill': hill, 'ofes': count, 'native_success': True,
                                  'input_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                                  'output_bytes': output.stat().st_size, 'retained_input': str(retained)})
            # Actual single-OFE service worker wiring must also preserve the source.
            wepp._prep_soils(translator, max_workers=1)
            for hill in watershed.mofe_nsegments:
                path = runs / f'p{translator.wepp(top=int(hill))}.sol'
                prepared = WeppSoilUtil(str(path), preserve_input_format=True)
                assert prepared.obj['ofes'] == original.obj['ofes']
                assert prepared.obj['datver'] == float(version)
            # Restore topology-consistent prepared files for project browse inspection.
            wepp._prep_multi_ofe(translator, max_workers=1)
            assert read_source(Soils.getInstance(str(WD)), 'soils')[0] == raw
            from wepppy.microservices.browse.browse import create_app, SITE_PREFIX
            with TestClient(create_app()) as browse:
                relative = 'soils/' + metadata['relative_path']
                download = browse.get(f'{SITE_PREFIX}/runs/{RUNID}/config/download/{relative}', headers=headers)
                assert download.status_code == 200 and download.content == raw
            records.append({'version': version, 'upload_status': 200, 'job_id': job.id,
                            'job_status': 'finished', 'fresh_worker_retry': fresh_worker,
                            'single_ofe_service_preserved': True, 'download_status': 200,
                            'source_sha256': metadata['sha256'], 'hillslopes': artifacts})
            print(json.dumps(records[-1]), flush=True)
    evidence = {'uid': os.getuid(), 'gid': os.getgid(), 'groups': os.getgroups(),
                'umask': oct(current_umask), 'binary': 'wepp_260803', 'synthetic_topology': True,
                'run': str(WD), 'versions': records}
    (WD / 'soil-format-acceptance.json').write_text(json.dumps(evidence, indent=2) + '\n')


if __name__ == '__main__':
    main()
