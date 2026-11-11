"""Read final API/file/handler outputs with synthetic, per-test source metadata."""
import asyncio
import io
import json
import logging
from logging.handlers import QueueHandler
import queue
import sys
from types import SimpleNamespace

import pytest

from wepppy.observability import safe_logging, safe_traceback as safe



@pytest.fixture
def diagnostic_source(tmp_path, monkeypatch):
    # Import real application adapters before selecting this test's source.
    # Their install lifecycle remains active and modules are never cached with a skipped hook.
    from wepppy.microservices.rq_engine import responses
    from wepppy.query_engine.app import server
    canary = 'f5-final-sink-canary-39bd8171'
    path = tmp_path / 'secret'
    path.write_text(canary)
    monkeypatch.setenv('SECRET_KEY_FILE', str(path))
    profile = safe.SecretSourceProfile('test', (safe.SecretSourceSpec('SECRET_KEY', 'SECRET_KEY_FILE'),))
    monkeypatch.setattr(safe_logging, '_PROFILE', profile)
    return canary, profile


@pytest.mark.unit
def test_final_formatter_and_queue_output(diagnostic_source):
    canary, profile = diagnostic_source
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(safe_logging.SafeFormatter(logging.Formatter('%(levelname)s %(message)s'), profile))
    try:
        raise RuntimeError('context ' + canary)
    except RuntimeError:
        record = logging.LogRecord('test', logging.ERROR, __file__, 1, 'message %s', (canary,), sys.exc_info())
    record.exc_text = 'stale cached ' + canary
    record.stack_info = 'stack ' + canary
    handler.handle(record)
    output = stream.getvalue()
    assert canary not in output and 'RuntimeError' in output and 'context' in output
    assert record.exc_text == 'stale cached ' + canary  # no shared-record mutation
    q = queue.Queue()
    queue_handler = QueueHandler(q)
    queue_handler.setFormatter(safe_logging.SafeFormatter(None, profile))
    queue_handler.handle(record)
    prepared = q.get_nowait()
    assert prepared.exc_info is None
    assert canary not in prepared.getMessage()
    assert 'RuntimeError' in prepared.getMessage()


@pytest.mark.unit
def test_normal_formatter_never_opens_files(diagnostic_source, monkeypatch):
    _, profile = diagnostic_source
    def forbidden(*args):
        raise AssertionError('normal logging read a secret')
    monkeypatch.setattr(safe_logging, '_snapshot', forbidden)
    formatter = safe_logging.SafeFormatter(logging.Formatter('%(message)s'), profile)
    record = logging.LogRecord('test', logging.INFO, __file__, 1, 'normal %s', ('progress',), None)
    assert formatter.format(record) == 'normal progress'


@pytest.mark.unit
def test_flask_api_log_and_file(diagnostic_source, monkeypatch, tmp_path):
    from flask import Flask
    from wepppy.weppcloud.utils import helpers
    canary, profile = diagnostic_source
    monkeypatch.setattr(helpers, 'get_wd', lambda _: str(tmp_path))
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(safe_logging.SafeFormatter(None, profile))
    helpers.logger.addHandler(handler)
    try:
        with Flask(__name__).test_request_context('/'):
            try:
                raise ValueError('context ' + canary)
            except ValueError as exc:
                response = helpers.exception_factory(exc, runid='test', details=str(exc))
        outputs = [response.get_data(as_text=True), stream.getvalue(), (tmp_path / 'exception_factory.log').read_text()]
    finally:
        helpers.logger.removeHandler(handler)
    assert all(canary not in output for output in outputs)
    assert all('context' in output for output in outputs)
    assert 'ValueError' in outputs[-1]
    assert response.status_code == 500


@pytest.mark.unit
def test_rq_engine_api(diagnostic_source):
    from wepppy.microservices.rq_engine.responses import error_response_with_traceback
    canary, _ = diagnostic_source
    try:
        raise ValueError('context ' + canary)
    except ValueError as exc:
        response = error_response_with_traceback(str(exc))
    payload = json.loads(response.body)
    assert canary not in response.body.decode()
    assert 'ValueError' in payload['error']['details']
    assert payload['error_id'] and response.status_code == 500


@pytest.mark.unit
def test_query_api_and_file(diagnostic_source, tmp_path):
    from starlette.requests import Request
    from wepppy.query_engine.app import server
    canary, _ = diagnostic_source
    request = Request({'type': 'http', 'method': 'GET', 'path': '/diagnostics/test',
                       'headers': [], 'query_string': b'', 'server': ('test', 80)})
    request.state.query_target = SimpleNamespace(path=tmp_path.resolve(), runid='test')
    try:
        raise RuntimeError('context ' + canary)
    except RuntimeError as exc:
        response = asyncio.run(server.query_engine_exception_handler(request, exc))
    assert canary not in response.body.decode()
    payload = json.loads(response.body)
    assert payload['stacktrace'] == payload['exc_info']
    assert payload['stacktrace_lines'] == payload['stacktrace'].strip('\n').splitlines()
    written = (tmp_path / 'exceptions.log').read_text()
    assert canary not in written and 'RuntimeError' in written and 'context' in written


@pytest.mark.unit
def test_status_handler_final_publication(diagnostic_source, monkeypatch):
    from wepppy.nodb.status_messenger import StatusMessenger, StatusMessengerHandler
    canary, _ = diagnostic_source
    sent = []
    # The publisher is captured after the real handler builds its final message.
    monkeypatch.setattr(StatusMessenger, 'publish', lambda channel, message: sent.append((channel, message)))
    try:
        raise ValueError(canary)
    except ValueError:
        record = logging.LogRecord('test', logging.ERROR, __file__, 1, 'context %s', (canary,), sys.exc_info())
    StatusMessengerHandler('run:status').emit(record)
    assert sent == [('run:status', 'context ' + safe.REDACTED)]


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.parametrize('mode', ['logging', 'uncaught', 'stderr-failure', 'multiprocessing'])
def test_actual_process_output(tmp_path, mode):
    import os
    from pathlib import Path
    import subprocess
    canary = 'f5-process-canary-2739abc'
    path = tmp_path / 'secret'
    path.write_text(canary)
    result = subprocess.run([sys.executable, str(Path(__file__).with_name('process_probe.py')), mode],
                            env={**os.environ, 'F5_CHILD': canary, 'F5_CHILD_FILE': str(path)},
                            capture_output=True, text=True, timeout=30)
    output = result.stdout + result.stderr
    assert canary not in output
    assert 'Original exception was' not in output
    assert result.returncode == (1 if mode in ('uncaught', 'stderr-failure') else 0)
    if mode != 'stderr-failure':
        assert safe.REDACTED in output


@pytest.mark.unit
def test_missing_source_preserves_generated_api_log_id(diagnostic_source, monkeypatch, tmp_path):
    from flask import Flask
    from wepppy.weppcloud.utils import helpers
    _, profile = diagnostic_source
    monkeypatch.setenv('SECRET_KEY_FILE', str(tmp_path / 'missing'))
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(safe_logging.SafeFormatter(None, profile))
    helpers.logger.addHandler(handler)
    try:
        with Flask(__name__).test_request_context('/'):
            response = helpers.exception_factory('unsafe detail', details='unsafe detail')
    finally:
        helpers.logger.removeHandler(handler)
    assert response.get_json()['error_id'] in stream.getvalue()
    assert safe.UNAVAILABLE in stream.getvalue()
    assert 'unsafe detail' not in stream.getvalue()


@pytest.mark.integration
@pytest.mark.slow
def test_real_rq_persistence_and_callbacks(f5_redis_socket, tmp_path):
    import os
    from pathlib import Path
    import subprocess
    from uuid import uuid4
    import redis
    from rq import Queue
    from rq.job import Job
    from tests.observability.rq_probe import fail_job, failure_callback, partial_result_job
    canary = 'f5-rq-persistence-canary-319bed'
    secret = tmp_path / 'secret'
    secret.write_text(canary)
    client = redis.StrictRedis(unix_socket_path=f5_redis_socket, db=2)
    queue = Queue('f5-' + uuid4().hex, connection=client)
    job = queue.enqueue(fail_job, on_failure=failure_callback)
    partial = queue.enqueue(partial_result_job)
    result = subprocess.run([sys.executable, '-m', 'tests.observability.rq_probe', f5_redis_socket, queue.name],
                            env={**os.environ, 'F5_CHILD': canary, 'F5_CHILD_FILE': str(secret), 'F5_OUTPUT_DIR': str(tmp_path),
                                 'WEPPPY_PROJECT_COMMIT_MODE': 'disabled', 'ENABLE_PROFILE_COVERAGE': 'false'},
                            capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    retained = Job.fetch(job.id, connection=client)
    assert retained.get_status(refresh=True) == 'failed'
    strings = [retained.exc_info, retained.meta['exc_string'], retained.latest_result().exc_string,
               result.stdout, result.stderr]
    assert all(canary not in value for value in strings)
    assert 'ValueError' in retained.exc_info and 'rq-context' in retained.exc_info
    assert client.get(job.id + ':callback-type') == b'ValueError'
    assert client.get(job.id + ':handler-type') == b'ValueError'
    partial = Job.fetch(partial.id, connection=client)
    assert partial.get_status(refresh=True) == 'finished'
    partial_text = json.dumps(partial.return_value())
    assert canary not in partial_text and 'partial-context' in partial_text
    assert 'canonical-process-boundaries-pass' in result.stdout
    for name in ('f5_failure.json', 'f5_worker.log'):
        persisted = (tmp_path / name).read_text()
        assert canary not in persisted and 'ValueError' in persisted
    client.close()


@pytest.mark.unit
def test_browse_existing_debug_fields_and_file(diagnostic_source, monkeypatch, tmp_path):
    from starlette.requests import Request
    from wepppy.microservices.browse import browse
    canary, _ = diagnostic_source
    monkeypatch.setattr(browse, 'BROWSE_DEBUG_ERRORS', True)
    monkeypatch.setattr(browse, 'BROWSE_WRITE_RUN_EXCEPTIONS_LOG', True)
    monkeypatch.setattr(browse, 'get_wd', lambda _: str(tmp_path))
    request = Request({'type': 'http', 'method': 'GET', 'path': '/runs/test/config/browse/test',
                       'headers': [(b'accept', b'application/json')], 'query_string': b'',
                       'path_params': {'runid': 'test', 'config': 'config'}, 'server': ('test', 80)})
    try:
        raise ValueError('browse-context ' + canary)
    except ValueError as exc:
        response = asyncio.run(browse.browse_exception_handler(request, exc))
    assert canary not in response.body.decode()
    assert 'ValueError' in json.loads(response.body)['error']['details']
    text = (tmp_path / 'exceptions.log').read_text()
    assert canary not in text and 'browse-context' in text


@pytest.mark.unit
def test_flask_failure_keeps_errors_list(diagnostic_source, monkeypatch, tmp_path):
    from flask import Flask
    from wepppy.weppcloud.utils import helpers
    monkeypatch.setenv('SECRET_KEY_FILE', str(tmp_path / 'missing'))
    with Flask(__name__).test_request_context('/'):
        for factory in (helpers.error_factory, helpers.upload_error_factory):
            response = factory('failure', errors=[{'message': 'secret diagnostic'}])
            assert isinstance(response.get_json()['errors'], list)


@pytest.mark.unit
def test_model_failure_status_files(diagnostic_source, tmp_path, monkeypatch):
    from wepppy.climates.cli_parquet import _CliParquetAttempt
    from wepppy.climates.prism.bulk_client import PrismBulkClient
    from wepppy.wepp.reports._cache_freshness import _CacheBuild
    from wepppy.nodb.mods.geneva.collaborators._cache_freshness import _Attempt
    canary, _ = diagnostic_source
    source = tmp_path / 'source.cli'
    source.write_text('synthetic input')
    geneva = SimpleNamespace(wd=str(tmp_path), artifact_io=SimpleNamespace(
        resolve_path=lambda wd, rel: tmp_path / rel))
    attempts = [_CliParquetAttempt(tmp_path, source, tmp_path / 'cli.parquet', 'climate'),
                _CacheBuild(tmp_path / 'report.parquet', 'report'),
                _Attempt(geneva, 'geneva/result.tif', 'test')]
    for attempt in attempts:
        error = ValueError('retained-context ' + canary)
        with pytest.raises(ValueError) as caught:
            with attempt:
                raise error
        assert caught.value is error
        payload = json.loads((attempt.root / 'status.json').read_text())
        assert payload['status'] == 'failed'
        assert canary not in json.dumps(payload)
        assert 'retained-context' in payload['error']
    client = PrismBulkClient(tmp_path / 'prism')
    def fail(*args):
        raise ValueError('prism-context ' + canary)
    monkeypatch.setattr(client, '_extract_or_reuse', fail)
    with pytest.raises(ValueError):
        client._attempt([], '2020-01-01', '2020-01-02')
    payload = json.loads((client.attempt_directories[0] / 'status.json').read_text())
    assert payload['state'] == 'failed' and payload['error_type'] == 'ValueError'
    assert canary not in json.dumps(payload) and 'prism-context' in payload['error']


@pytest.mark.integration
@pytest.mark.slow
def test_real_status_and_agent_publications(diagnostic_source, f5_redis_socket, monkeypatch):
    import redis
    from uuid import uuid4
    from wepppy.nodb.status_messenger import StatusMessenger
    from wepppy.rq import agent_rq
    canary, _ = diagnostic_source
    client = redis.StrictRedis(unix_socket_path=f5_redis_socket, db=2, decode_responses=True)
    monkeypatch.setattr(StatusMessenger, '_client', client)
    monkeypatch.setattr(agent_rq, '_redis_client', client)
    channel = 'f5-pubsub-' + uuid4().hex
    with client.pubsub() as subscription:
        subscription.subscribe(channel)
        assert subscription.get_message(timeout=5)['type'] == 'subscribe'
        try:
            raise ValueError('publication-context ' + canary)
        except ValueError as exc:
            StatusMessenger.publish(channel, f'rq:test STATUS {exc}')
        agent_rq._publish(channel, {'type': 'error', 'content': 'agent-context ' + canary})
        values = [subscription.get_message(timeout=5)['data'] for _ in range(2)]
        assert all(canary not in value for value in values)
        assert 'publication-context' in values[0]
        assert json.loads(values[1])['type'] == 'error'
        assert 'agent-context' in values[1]
    client.close()


@pytest.mark.unit
def test_playback_result_and_stdout(diagnostic_source, monkeypatch, capsys, tmp_path):
    from collections import deque
    import requests
    from wepppy.profile_recorder.playback import PlaybackSession
    canary, _ = diagnostic_source
    playback = PlaybackSession.__new__(PlaybackSession)
    playback.events = [{'stage': 'response', 'id': '1', 'ok': True}]
    playback.requests = {'1': {'method': 'GET', 'endpoint': '/test'}}
    playback.results = []
    playback.run_dir = tmp_path
    playback.base_url = 'https://example.invalid'
    playback.execute = playback.verbose = True
    playback._logger = None
    playback._pending_jobs = deque()
    monkeypatch.setattr(playback, '_remap_run_path', lambda path: path)
    monkeypatch.setattr(playback, '_guard_sandbox_target', lambda *args: None)
    def fail(*args, **kwargs):
        raise requests.RequestException('playback-context ' + canary)
    monkeypatch.setattr(playback, '_execute_request', fail)
    playback.run()
    path = tmp_path / 'playback-result.json'
    path.write_text(json.dumps({'report': playback.report(), 'requests': playback.results}))
    for output in (capsys.readouterr().out, path.read_text()):
        assert canary not in output and 'playback-context' in output


@pytest.mark.unit
def test_migration_append_logs_and_jsonl(diagnostic_source, tmp_path, monkeypatch):
    from dataclasses import asdict
    from wepppy.tools.migrations import migrate_ashpost_pickles as ash
    from wepppy.tools.migrations import unroll_root_resources_batch as unroll
    canary, _ = diagnostic_source
    path = tmp_path / 'migration.log'
    with path.open('w') as stream:
        ash._log(stream, tmp_path, 'failed', 0, {}, 'migration-context ' + canary)
    assert canary not in path.read_text() and 'migration-context' in path.read_text()
    (tmp_path / 'ron.nodb').write_text('{}')
    def fail(*args):
        raise ValueError('unroll-context ' + canary)
    monkeypatch.setattr(unroll, '_load_ron_cfg_spec', fail)
    result = unroll.resolve_apply_nodir(tmp_path)
    record = asdict(result)
    unroll._append_jsonl(tmp_path / 'records.jsonl', [record])
    unroll._write_summary(tmp_path / 'summary.json', record)
    for name in ('records.jsonl', 'summary.json'):
        output = (tmp_path / name).read_text()
        assert canary not in output and 'unroll-context' in output


@pytest.mark.unit
def test_direct_api_bypasses_and_fail_closed_metadata(diagnostic_source, monkeypatch, tmp_path):
    from contextlib import contextmanager
    from flask import Flask
    from werkzeug.exceptions import HTTPException
    from wepppy.wepp.interchange import _roads_lifecycle as lifecycle
    from wepppy.query_engine.app.mcp.router import _error_response
    canary, profile = diagnostic_source
    @contextmanager
    def fail(*args):
        raise lifecycle.RoadsResultsUnavailable('roads-context ' + canary)
        yield
    monkeypatch.setattr(lifecycle, 'current_read', fail)
    with Flask(__name__).test_request_context('/'):
        with pytest.raises(HTTPException) as caught:
            lifecycle.protect_flask_response(tmp_path)
        response = caught.value.response
        assert response.status_code == 409
        assert response.headers['Cache-Control'] == 'no-store'
        assert canary not in response.get_data(as_text=True)
        assert 'roads-context' in response.get_data(as_text=True)
    response = _error_response(400, 'test', 'mcp-context ' + canary, {'diagnostic': canary})
    assert canary.encode() not in response.body
    monkeypatch.setenv('SECRET_KEY_FILE', str(tmp_path / 'missing-source'))
    response = _error_response(400, 'test', canary, {'diagnostic': canary})
    error = json.loads(response.body)['errors'][0]
    assert error['meta'] == {} and error['detail'] == safe.UNAVAILABLE


@pytest.mark.unit
def test_delayed_openet_log_and_pre_raise_eu_publication(diagnostic_source, monkeypatch, tmp_path):
    from contextlib import nullcontext
    from wepppy.nodb.mods.openet import openet_ts
    from wepppy.eu.soils import soil_build
    canary, _ = diagnostic_source
    stream = io.StringIO()
    logger = logging.Logger('f5-delayed-openet')
    logger.addHandler(logging.StreamHandler(stream))
    source = tmp_path / 'subcatchments.json'
    source.write_text('{}')
    monkeypatch.setattr(openet_ts.Climate, 'getInstance', lambda wd: object())
    monkeypatch.setattr(openet_ts.Watershed, 'getInstance', lambda wd: SimpleNamespace(subwta_shp=str(source)))
    monkeypatch.setattr(openet_ts, '_load_api_key', lambda: 'synthetic-api-key')
    monkeypatch.setattr(openet_ts, '_load_subcatchments', lambda *args, **kw: [('11', [])])
    monkeypatch.setattr(openet_ts, 'OPENET_VARIABLES', {'test': 'test'})
    def fail(*args, **kwargs):
        raise ValueError('delayed-context ' + canary)
    controller = SimpleNamespace(wd=str(tmp_path), logger=logger,
        _validate_climate=lambda climate: (2020, 2020), _openet_start_year=2020,
        _openet_end_year=2020, locked=lambda: nullcontext(), _purge_cache=lambda: None,
        openet_individual_dir=str(tmp_path / 'openet'), _fetch_one=fail)
    openet_ts.OpenET_TS.acquire_timeseries(controller, max_workers=1)
    assert canary not in stream.getvalue() and 'delayed-context' in stream.getvalue()
    class BatchError(RuntimeError):
        def __init__(self, *args):
            super().__init__('eu-context ' + canary)
    monkeypatch.setattr(soil_build, 'ESDACSoilBatchError', BatchError)
    messages = []
    monkeypatch.setattr(soil_build.StatusMessenger, 'publish', lambda channel, text: messages.append(text))
    with pytest.raises(BatchError):
        soil_build._raise_batch_error([], tmp_path / 'report.json', status_channel='test')
    assert len(messages) == 1 and canary not in messages[0] and 'eu-context' in messages[0]


@pytest.mark.unit
def test_optional_model_reports_and_batch_metadata(diagnostic_source, monkeypatch, tmp_path):
    import numpy as np
    from wepppy.nodb.mods.rusle import c_integration, k_integration
    from wepppy.nodb.batch_runner import BatchRunner
    canary, _ = diagnostic_source
    def fail(*args, **kwargs):
        raise OSError('model-context ' + canary)
    monkeypatch.setattr(c_integration, '_exists', lambda path: True)
    monkeypatch.setattr(c_integration, '_aligned_band', fail)
    monkeypatch.setattr(k_integration, '_resolve_optional_cfvo_layer_paths', fail)
    reports = [c_integration._load_cfvo_surface_proxy_from_raster(
        wd=str(tmp_path), dem_profile={}, valid_mask=np.ones((1, 1), dtype=bool))[1],
        k_integration._load_optional_cfvo_near_surface(str(tmp_path), statistic='mean', depth_weights_cm={})[1]]
    controller = BatchRunner.__new__(BatchRunner)
    metadata = tmp_path / controller.RUN_METADATA_FILENAME
    metadata.write_text('{}')
    # The exception producer is JSON decoding; retain the real returned report envelope.
    with monkeypatch.context() as patch:
        patch.setattr(json, 'load', lambda *args: (_ for _ in ()).throw(
            json.JSONDecodeError('metadata-context ' + canary, '{}', 0)))
        payload, error = controller._read_run_metadata(str(tmp_path))
    assert payload is None
    reports.append({'error': error})
    output = json.dumps(reports)
    assert canary not in output and 'model-context' in output and 'metadata-context' in output


@pytest.mark.integration
@pytest.mark.slow
def test_playback_profile_and_wojak_entrypoint_sources(tmp_path):
    import os
    from pathlib import Path
    import subprocess
    canary = 'f5-owned-source-canary-482ab'
    source = tmp_path / 'admin-password'
    source.write_text(canary)
    # Only metadata-owned synthetic sources, without inheriting deployment secrets.
    env = {key: value for key, value in os.environ.items() if key in {'PATH', 'PYTHONPATH', 'VIRTUAL_ENV'}}
    env.update(F5_CHILD=canary, ADMIN_PASSWORD_FILE=str(source))
    probe = Path(__file__).with_name('process_probe.py')
    result = subprocess.run([sys.executable, str(probe), 'playback'], env=env,
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0 and canary not in result.stdout + result.stderr
    assert '[REDACTED]' in result.stderr and 'log-context' in result.stderr
    env.pop('ADMIN_PASSWORD_FILE')
    env.update(AGENT_JWT_SECRET=canary, WOJAK_REDIS_PORT=canary)
    script = Path(__file__).resolve().parents[2] / 'services/cao/scripts/wojak_bootstrap.py'
    result = subprocess.run([sys.executable, str(script)], env=env,
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 1 and canary not in result.stdout + result.stderr
    assert 'ValueError' in result.stderr and '[REDACTED]' in result.stderr


@pytest.mark.unit
@pytest.mark.parametrize('shape', ['text', 'dict', 'list'])
@pytest.mark.parametrize('source_failure', [False, True])
def test_browse_http_4xx_output(diagnostic_source, shape, source_failure, monkeypatch, tmp_path):
    from starlette.requests import Request
    from fastapi import HTTPException
    from wepppy.microservices.browse import browse
    canary, _ = diagnostic_source
    detail = 'browse-context ' + canary
    if shape == 'dict':
        detail = {'error': detail}
    elif shape == 'list':
        detail = [detail]
    request = Request({'type': 'http', 'method': 'GET', 'path': '/browse/test',
                       'headers': [], 'query_string': b''})
    if source_failure:
        monkeypatch.setenv('SECRET_KEY_FILE', str(tmp_path / 'missing'))
    response = asyncio.run(browse.browse_http_exception_handler(request,
        HTTPException(status_code=409, detail=detail, headers={'X-Test': 'preserved'})))
    assert response.status_code == 409 and response.headers['X-Test'] == 'preserved'
    assert canary.encode() not in response.body
    if not source_failure:
        assert b'browse-context' in response.body
    if shape != 'text':
        assert response.headers['content-type'] == 'application/json'
        assert isinstance(json.loads(response.body), dict if shape == 'dict' else list)
        if source_failure:
            assert json.loads(response.body) == ({} if shape == 'dict' else [])
