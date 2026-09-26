"""Disposable development acceptance; run with wctl run-python, never on production.

Creates no shared services. Uses the existing Builder project at the fixed
acceptance run and the real default RQ queue. Synthetic hillslope topology is
explicit: this is input/worker/native acceptance, not DEM delineation evidence.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil

import numpy as np
from osgeo import gdal, osr
from fastapi.testclient import TestClient
import redis
from rq.job import Job
from rq import Queue, Worker

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.nodb.core import Landuse, Soils, Watershed
from wepppy.nodb.single_input_sources import read_source
from wepppy.topo.peridot.flowpath import PeridotHillslope
from wepppy.microservices.rq_engine import app
from wepppy.weppcloud.utils.auth_tokens import issue_token

RUNID = 'single-input-acceptance-20260925'
WD = Path('/wc1/runs/si') / RUNID
EVIDENCE = WD / 'single-input-acceptance.json'
ROOT = Path('/workdir/wepppy')


def raster(path, values):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    ds = gdal.GetDriverByName('GTiff').Create(str(path), len(values), 1, 1, gdal.GDT_Int32)
    ds.SetGeoTransform((500000, 10, 0, 5000000, 0, -10))
    crs = osr.SpatialReference(); crs.ImportFromEPSG(32610)
    ds.SetProjection(crs.ExportToWkt()); ds.GetRasterBand(1).WriteArray(np.array([values], dtype=np.int32))
    ds.FlushCache(); ds = None


def prepare():
    watershed = Watershed.getInstance(str(WD))
    counts = {'101': 2, '102': 12}
    with watershed.locked():
        watershed._mofe_nsegments = counts
        watershed._subs_summary = {hill: PeridotHillslope.from_dict(dict(
            topaz_id=hill, wepp_id=str(index), area=count * 0.01, direction=180, aspect=180,
            elevation=500, length=count * 10, slope_scalar=0.1, width=10,
            centroid_lon=-123, centroid_lat=45, centroid_px=index, centroid_py=0,
        )) for index, (hill, count) in enumerate(counts.items(), 1)}
        watershed._chns_summary = {}
        watershed._sub_area_lookup = {hill: count * 0.01 for hill, count in counts.items()}
    raster(watershed.subwta, [101] * 2 + [102] * 12)
    raster(watershed.mofe_map, [1, 2] + list(range(1, 13)))
    for hill, count in counts.items():
        slope = WD / f'watershed/slope_files/hillslopes/hill_{hill}.mofe.slp'
        slope.parent.mkdir(parents=True, exist_ok=True)
        slope.write_text(f'97.5\n{count}\n180 10\n' + '2 10\n0, 0.1 1, 0.1\n' * count)
    print(json.dumps({'prepared': str(WD), 'uid': os.getuid(), 'gid': os.getgid(), 'groups': os.getgroups(), 'topology': counts}))


def submit(kind):
    token = issue_token('single-input-local-acceptance', scopes=['rq:enqueue', 'rq:status'],
                        runs=[RUNID], audience='rq-engine', expires_in=900, extra_claims={'token_class': 'service'})['token']
    source = (ROOT / 'wepppy/wepp/management/data/GeoWEPP/grass.man' if kind == 'landuse'
              else ROOT / 'wepppy/wepp/soils/soilsdb/data/Forest/Forest loam.sol')
    field = 'input_upload_single_landuse' if kind == 'landuse' else 'input_upload_single_soil'
    data = {'landuse_mode': '5'} if kind == 'landuse' else {'soil_mode': '5', 'initial_sat': '0.42'}
    with TestClient(app) as client:
        response = client.post(f'/api/runs/{RUNID}/config/build-{kind}', data=data,
            files={field: ('Acceptance.MAN' if kind == 'landuse' else 'Acceptance.SOL', source.read_bytes(), 'text/plain')},
            headers={'Authorization': 'Bearer ' + token})
    record = {'status': response.status_code, 'body': response.json(), 'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest()}
    evidence = json.loads(EVIDENCE.read_text()) if EVIDENCE.exists() else {}
    evidence[kind] = record
    EVIDENCE.write_text(json.dumps(evidence, indent=2) + '\n')
    print(json.dumps(record))
    assert response.status_code == 200


def retry_failed():
    """Execute only this disposable run's failed jobs in a fresh worker process."""
    evidence = json.loads(EVIDENCE.read_text())
    with redis.Redis(**redis_connection_kwargs(RedisDB.RQ)) as connection:
        for kind, record in evidence.items():
            job = Job.fetch(record['body']['job_id'], connection=connection)
            assert RUNID in job.args, job.args
            assert job.func_name in {'wepppy.rq.project_rq.build_landuse_rq', 'wepppy.rq.project_rq.build_soils_rq'}
            if job.get_status(refresh=True) == 'finished':
                continue
            assert job.get_status(refresh=True) == 'failed'
            queue = Queue(job.origin, connection=connection)
            worker = Worker([queue], connection=connection, name='single-input-acceptance-fresh-process')
            assert worker.perform_job(job, queue), job.exc_info
            queue.failed_job_registry.remove(job, delete_job=False)
            record['fresh_worker'] = {'uid': os.getuid(), 'gid': os.getgid(), 'groups': os.getgroups()}
    EVIDENCE.write_text(json.dumps(evidence, indent=2) + '\n')


def execute_artifacts():
    from wepppy.nodb.core.wepp import prep_multi_ofe_hillslope
    from wepppy.wepp.single_input import read_uploaded_management, validate_soil_text
    from wepp_runner.wepp_runner import make_hillslope_run, run_hillslope
    runs = WD / 'wepp/runs'; runs.mkdir(parents=True, exist_ok=True)
    (WD / 'wepp/output').mkdir(parents=True, exist_ok=True)
    records = []
    for wepp_id, (hill, count) in enumerate(Watershed.getInstance(str(WD)).mofe_nsegments.items(), 1):
        prep_multi_ofe_hillslope((hill, wepp_id, str(WD), str(runs), 2,
                                 None, 0.42, False, None, False, None, False, None, None, True))
        management = read_uploaded_management(runs / f'p{wepp_id}.man', max_ofes=32)
        assert management.nofe == count
        soil_path = runs / f'p{wepp_id}.sol'
        validate_soil_text(soil_path.read_text(), max_ofes=32)
        shutil.copyfile(ROOT / 'tests/disturbed/data/test_climate.cli', runs / f'p{wepp_id}.cli')
        make_hillslope_run(wepp_id, 2, str(runs), reveg=False, wepp_bin='wepp_260803')
        success, returned_id, elapsed = run_hillslope(wepp_id, str(runs), wepp_bin='wepp_260803')
        assert success and returned_id == wepp_id
        output = WD / f'wepp/output/H{wepp_id}.loss.dat'
        assert output.stat().st_size > 0
        files = [runs / f'p{wepp_id}.{ext}' for ext in ('man', 'sol', 'slp', 'cli', 'run')]
        records.append({'hill': hill, 'ofes': count, 'native_success': success,
                        'elapsed_seconds': elapsed, 'output_bytes': output.stat().st_size,
                        'files': {str(path.relative_to(WD)): hashlib.sha256(path.read_bytes()).hexdigest()
                                  for path in files}})
    artifact = {'uid': os.getuid(), 'gid': os.getgid(), 'groups': os.getgroups(),
                'binary': 'wepp_260803', 'synthetic_topology': True, 'hillslopes': records}
    (WD / 'single-input-artifacts.json').write_text(json.dumps(artifact, indent=2) + '\n')
    print(json.dumps(artifact))


def boundaries():
    from wepppy.nodb.redis_prep import RedisPrep
    token = issue_token('single-input-local-acceptance', scopes=['rq:enqueue', 'rq:status'],
                        runs=[RUNID], audience='rq-engine', expires_in=900, extra_claims={'token_class': 'service'})['token']
    prep = RedisPrep.getInstance(str(WD))
    records = []
    with TestClient(app) as client:
        for kind, cls, extension in [('landuse', Landuse, 'MAN'), ('soils', Soils, 'SOL')]:
            controller = cls.getInstance(str(WD))
            before = dict(controller._single_user_defined_source)
            raw, _ = read_source(controller, kind)
            field = 'input_upload_single_landuse' if kind == 'landuse' else 'input_upload_single_soil'
            modefield = 'landuse_mode' if kind == 'landuse' else 'soil_mode'
            def request_source():
                return client.post(f'/api/runs/{RUNID}/config/build-{kind}', data={modefield: '5', 'initial_sat': '0.42'},
                    files={field: ('Rejected.' + extension, raw + b'\n# contention\n', 'text/plain')},
                    headers={'Authorization': 'Bearer ' + token})
            controller.lock()
            try:
                response = request_source()
                assert response.status_code == 409, response.text
                assert response.json()['error']['code'] == 'conflict', response.text
                records.append({'kind': kind, 'case': 'real_nodb_lock', 'status': response.status_code})
            finally:
                controller.unlock()
            readonly = WD / 'READONLY'
            assert not readonly.exists()
            readonly.touch()
            try:
                response = request_source()
                assert response.status_code == 403, response.text
                records.append({'kind': kind, 'case': 'readonly', 'status': response.status_code})
            finally:
                readonly.unlink()
            with redis.Redis(**redis_connection_kwargs(RedisDB.RQ)) as connection:
                pending = Job.create('wepppy.rq.project_rq.build_landuse_rq', args=(RUNID,), connection=connection)
                pending.save(); pending.set_status('queued')
                key = 'single_input_acceptance_pending'
                assert prep.get_rq_job_id(key) is None
                prep.set_rq_job_id(key, pending.id)
                try:
                    response = request_source()
                    assert response.status_code == 409, response.text
                    assert response.json()['error']['code'] == 'job_active', response.text
                    records.append({'kind': kind, 'case': 'active_receipt', 'status': response.status_code})
                    for action, data in [('archive', {}), ('fork', {'target_runid': RUNID + '-blocked-fork'})]:
                        blocked = client.post(f'/api/runs/{RUNID}/config/{action}', json=data,
                            headers={'Authorization': 'Bearer ' + token})
                        assert blocked.status_code == 409, blocked.text
                        records.append({'kind': kind, 'case': 'active_build_blocks_' + action, 'status': blocked.status_code})
                finally:
                    prep.redis.hdel(prep.run_id, 'rq:' + key); prep.dump(); pending.delete()
            with redis.Redis(**redis_connection_kwargs(RedisDB.RQ)) as connection:
                pending = Job.create('wepppy.rq.project_rq.restore_archive_rq', args=(RUNID, 'fixture.zip'), connection=connection)
                pending.save(); pending.set_status('queued')
                old_archive = prep.get_archive_job_id()
                prep.set_archive_job_id(pending.id)
                try:
                    response = request_source()
                    assert response.status_code == 409, response.text
                    assert response.json()['error']['code'] == 'job_active', response.text
                    records.append({'kind': kind, 'case': 'active_archive_blocks_upload', 'status': response.status_code})
                finally:
                    if old_archive: prep.set_archive_job_id(old_archive)
                    else: prep.clear_archive_job_id()
                    pending.delete()
            current = cls.load_detached(str(WD))
            assert current._single_user_defined_source == before
            assert read_source(current, kind)[0] == raw
    (WD / 'single-input-boundaries.json').write_text(json.dumps(records, indent=2) + '\n')
    print(json.dumps(records))


def archive_roundtrip():
    import zipfile
    from wepppy.rq.project_rq import archive_rq, restore_archive_rq
    before = {kind: dict(cls.getInstance(str(WD))._single_user_defined_source)
              for kind, cls in [('landuse', Landuse), ('soils', Soils)]}
    archive_rq(RUNID, comment='Single-input disposable acceptance')
    archive = max((WD / 'archives').glob('*.zip'), key=lambda p: p.stat().st_mtime_ns)
    with zipfile.ZipFile(archive) as saved:
        for kind, metadata in before.items():
            assert hashlib.sha256(saved.read(kind + '/' + metadata['relative_path'])).hexdigest() == metadata['sha256']
    restore_archive_rq(RUNID, archive.name)
    for kind, cls in [('landuse', Landuse), ('soils', Soils)]:
        controller = cls.getInstance(str(WD))
        assert controller._single_user_defined_source == before[kind]
        assert hashlib.sha256(read_source(controller, kind)[0]).hexdigest() == before[kind]['sha256']
    record = {'archive': archive.name, 'source_metadata_and_hashes_preserved': True,
              'uid': os.getuid(), 'gid': os.getgid()}
    (WD / 'single-input-archive.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(record))


def fork_roundtrip():
    from wepppy.microservices.rq_engine.fork_archive_routes import FORK_ARCHIVE_QUEUE
    from wepppy.weppcloud.utils.helpers import get_wd
    target = 'single-input-copy-20260925'
    target_wd = Path(get_wd(target, prefer_active=False))
    assert not target_wd.exists(), 'Use a fresh disposable target'
    with redis.Redis(**redis_connection_kwargs(RedisDB.RQ)) as connection:
        queue = Queue(FORK_ARCHIVE_QUEUE, connection=connection)
        job = Job.create('wepppy.rq.project_rq.fork_rq', args=(RUNID, target, False, False, False),
                         connection=connection, origin=queue.name, result_ttl=86400, timeout=300)
        job.save()
        worker = Worker([queue], connection=connection, name='single-input-fork-acceptance')
        assert worker.perform_job(job, queue), job.exc_info
        record = {'job_id': job.id, 'rq_status': job.get_status(refresh=True),
                  'target': target, 'origin': queue.name, 'uid': os.getuid(), 'gid': os.getgid()}
    for kind, cls in [('landuse', Landuse), ('soils', Soils)]:
        source = cls.getInstance(str(WD))
        copied = cls.getInstance(str(target_wd))
        assert copied._single_user_defined_source == source._single_user_defined_source
        assert read_source(copied, kind)[0] == read_source(source, kind)[0]
        assert copied.single_user_defined_uploads
        if kind == 'landuse':
            for summary in copied.managements.values():
                assert summary.get_management().nofe == 1
        else:
            for summary in copied.soils.values():
                assert (Path(summary.soils_dir) / summary.fname).is_file()
    record['sources_and_policy_preserved'] = True
    (WD / 'single-input-fork.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(record))


def publication_failures():
    from copy import deepcopy
    from wepppy.rq.single_input_admission import input_submission
    from wepppy.nodb.single_input_sources import accept_source
    from wepppy.wepp.single_input import SingleInputError
    copyid = 'single-input-copy-20260925'
    copywd = Path('/wc1/runs/si') / copyid
    records = []
    for kind, cls, extension in [('landuse', Landuse, 'MAN'), ('soils', Soils, 'SOL')]:
        for phase in ('before', 'after'):
            controller = cls.getInstance(str(copywd))
            old = deepcopy(controller._single_user_defined_source)
            raw = read_source(controller, kind)[0] + ('\n# real publication ' + phase + '\n').encode()
            original_dump = cls.dump
            def fail_dump(self, *args, **kwargs):
                if phase == 'after': original_dump(self, *args, **kwargs)
                raise OSError('injected publication boundary failure')
            cls.dump = fail_dump
            try:
                with input_submission(controller, kind, copyid):
                    try:
                        accept_source(controller, kind, raw, 'Failure-' + phase + '.' + extension)
                    except SingleInputError as exc:
                        assert exc.status_code == 500
                    else:
                        raise AssertionError('Injected failure was not reported')
            finally:
                cls.dump = original_dump
            durable = cls.load_detached(str(copywd))
            selected = durable._single_user_defined_source
            assert controller._single_user_defined_source == selected
            if phase == 'before': assert selected == old
            else: assert selected['sha256'] == hashlib.sha256(raw).hexdigest()
            assert (copywd / kind / old['relative_path']).exists()
            assert hashlib.sha256(read_source(durable, kind)[0]).hexdigest() == selected['sha256']
            records.append({'kind': kind, 'phase': phase, 'error_status': 500,
                            'durable_pointer_readable': True, 'cache_matches_durable': True,
                            'previous_generation_retained': True})
    (WD / 'single-input-publication-failures.json').write_text(json.dumps(records, indent=2) + '\n')
    print(json.dumps(records))


def browse_download():
    from wepppy.microservices.browse.browse import create_app, SITE_PREFIX
    token = issue_token('single-input-local-acceptance', scopes=['rq:status'],
                        runs=[RUNID], audience='rq-engine', expires_in=900,
                        extra_claims={'token_class': 'service', 'roles': ['User']})['token']
    records = []
    with TestClient(create_app()) as client:
        for kind, cls in [('landuse', Landuse), ('soils', Soils)]:
            metadata = cls.getInstance(str(WD))._single_user_defined_source
            relative = kind + '/' + metadata['relative_path']
            headers = {'Authorization': 'Bearer ' + token}
            download = client.get(f'{SITE_PREFIX}/runs/{RUNID}/config/download/{relative}', headers=headers)
            assert download.status_code == 200, download.text[:200]
            assert hashlib.sha256(download.content).hexdigest() == metadata['sha256']
            listing = client.get(f'{SITE_PREFIX}/runs/{RUNID}/config/browse/{kind}/single-user-defined/', headers=headers)
            assert listing.status_code == 200, listing.text[:200]
            assert Path(relative).name in listing.text
            records.append({'kind': kind, 'download_status': 200, 'listing_status': 200,
                            'download_sha256': metadata['sha256']})
    (WD / 'single-input-download.json').write_text(json.dumps(records, indent=2) + '\n')
    print(json.dumps(records))


def check():
    evidence = json.loads(EVIDENCE.read_text())
    with redis.Redis(**redis_connection_kwargs(RedisDB.RQ)) as connection:
        for kind, record in evidence.items():
            job = Job.fetch(record['body']['job_id'], connection=connection)
            status = job.get_status(refresh=True)
            print(json.dumps({'kind': kind, 'job_id': job.id, 'status': str(status), 'origin': job.origin}))
            record['rq_status'] = str(getattr(status, 'value', status))
            record['origin'] = job.origin
            record['ended_at'] = job.ended_at.isoformat() if job.ended_at else None
            assert record['rq_status'] == 'finished', job.exc_info
            cls = Landuse if kind == 'landuse' else Soils
            controller = cls.getInstance(str(WD))
            raw, _ = read_source(controller, kind)
            assert hashlib.sha256(raw).hexdigest() == record['source_sha256']
            print(json.dumps({'kind': kind, 'filename': controller.single_user_defined_filename, 'source_size': len(raw)}))
    EVIDENCE.write_text(json.dumps(evidence, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('action', choices=['prepare', 'landuse', 'soils', 'check', 'retry', 'execute', 'boundaries', 'archive', 'fork', 'failures', 'download'])
    action = parser.parse_args().action
    if action == 'prepare': prepare()
    elif action == 'check': check()
    elif action == 'retry': retry_failed()
    elif action == 'execute': execute_artifacts()
    elif action == 'boundaries': boundaries()
    elif action == 'archive': archive_roundtrip()
    elif action == 'fork': fork_roundtrip()
    elif action == 'failures': publication_failures()
    elif action == 'download': browse_download()
    else: submit(action)
