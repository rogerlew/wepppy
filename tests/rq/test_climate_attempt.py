from contextlib import nullcontext
from datetime import datetime, timedelta, timezone

import pytest

from wepppy.rq import climate_attempt


BUILD = 'build_climate_rq'
UPLOAD = 'upload_cli_rq'
START = datetime(2026, 11, 19, tzinfo=timezone.utc)


def _job(key, job_id, age=0, runid='run-1'):
    job = climate_attempt.Job.create(f'wepppy.rq.project_rq.{key}', id=job_id, args=(runid,),
                                     meta={'runid': runid}, connection=object())
    job.created_at = START + timedelta(seconds=age)
    return {field.encode(): value if isinstance(value, bytes) else str(value).encode()
            for field, value in job.to_dict().items()}


@pytest.fixture
def records(monkeypatch):
    jobs = {}

    class Pipeline:
        def __init__(self):
            self.keys = []

        def hgetall(self, key):
            self.keys.append(key)

        def execute(self):
            return [jobs.get(key.split(':')[-1], {}) for key in self.keys]

    class Connection:
        def pipeline(self, *, transaction):
            return nullcontext(Pipeline())

    monkeypatch.setattr(climate_attempt.redis, 'Redis', lambda **_kwargs: nullcontext(Connection()))
    return jobs


@pytest.mark.parametrize(('upload_age', 'latest'), [(1, 'upload'), (-1, 'build'), (0, None)])
def test_two_completed_or_failed_attempts_follow_creation_order(records, upload_age, latest):
    records.update(build=_job(BUILD, 'build'), upload=_job(UPLOAD, 'upload', upload_age))
    records['build'][b'status'] = b'failed'
    records['upload'][b'status'] = b'finished'
    assert climate_attempt.resolve_climate_attempt('run-1', {BUILD: 'build', UPLOAD: 'upload'}) == (latest, latest is None)


def test_single_verified_reference_and_empty_project(records):
    records['upload'] = _job(UPLOAD, 'upload')
    records['upload'][b'status'] = b'queued'
    assert climate_attempt.resolve_climate_attempt('run-1', {}) == (None, False)
    assert climate_attempt.resolve_climate_attempt('run-1', {UPLOAD: 'upload'}) == ('upload', False)


@pytest.mark.parametrize('unavailable', [{}, _job(BUILD, 'upload'), _job(UPLOAD, 'upload', runid='other')])
def test_does_not_restore_the_surviving_build_when_upload_cannot_be_verified(records, unavailable):
    records.update(build=_job(BUILD, 'build'), upload=unavailable)
    records['build'][b'status'] = b'failed'
    if unavailable:
        records['upload'][b'status'] = b'finished'
    assert climate_attempt.resolve_climate_attempt('run-1', {BUILD: 'build', UPLOAD: 'upload'}) == (None, True)


@pytest.mark.parametrize('missing_field', [b'created_at', b'data'])
def test_malformed_rq_record_is_not_selected(records, missing_field):
    records.update(build=_job(BUILD, 'build'), upload=_job(UPLOAD, 'upload', 1))
    records['build'][b'status'] = b'failed'
    records['upload'][b'status'] = b'finished'
    del records['upload'][missing_field]
    assert climate_attempt.resolve_climate_attempt('run-1', {BUILD: 'build', UPLOAD: 'upload'}) == (None, True)


def test_rq_lookup_error_is_neutral(records, monkeypatch):
    def unavailable(*args, **kwargs):
        raise climate_attempt.redis.RedisError('unavailable')

    monkeypatch.setattr(climate_attempt.redis, 'Redis', unavailable)
    assert climate_attempt.resolve_climate_attempt('run-1', {UPLOAD: 'upload'}) == (None, True)
