"""Real HTTP/SQLite boundaries for explicit source selection and provenance."""
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import socket
import sqlite3
import threading
import time

import pytest

from wepppy.soils.ssurgo import ssurgo
from wepppy.soils.ssurgo import source

pytestmark = pytest.mark.unit


@contextmanager
def soil_server(responder):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            responder(self)
        def do_POST(self):
            self.request_body = self.rfile.read(int(self.headers.get('Content-Length', 0)))
            responder(self)
        def log_message(self, *args):
            pass
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f'http://127.0.0.1:{server.server_port}/Tabular/post.rest'
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def reply(handler, body, *, release='r1', encoding=None, status=200):
    payload = json.dumps(body).encode()
    handler.send_response(status)
    handler.send_header('Content-Type', 'application/json')
    handler.send_header('X-Soil-Profile', source.JSON_PROFILE)
    handler.send_header('X-Soil-Release', release)
    handler.send_header('Content-Length', str(len(payload)))
    if encoding:
        handler.send_header('Content-Encoding', encoding)
    handler.end_headers()
    handler.wfile.write(payload)


def metadata():
    return {'service': 'soil-data-access', 'official': False, 'ready': True, 'contract_version': source.JSON_PROFILE, 'code_revision': 'a' * 40,
            'active_release': {'id': 'r1', 'datasets': [{'dataset': 'WEPPPY_CACHE_REPLAY', 'release_id': 'r1', 'scope': 'authored', 'source_url': 'https://example.com/source', 'sha256': 'b' * 64}]}}


def test_exact_keys_and_first_wins_without_float_rounding():
    columns = ['mukey', 'cokey', 'name']
    body = {'Table': [columns, ['9007199254740993', '2', 'first'], ['9007199254740993', '2', 'second']]}
    assert source.parse_table(body, columns, {9007199254740993}) == [(9007199254740993, 2, 'first')]
    for invalid in ('9007199254740993.0', '2e3', '-1', '9223372036854775808', '1' * 5000, None):
        with pytest.raises(source.SoilDataSourceError):
            source.parse_table({'Table': [columns, ['1', invalid, 'name']]}, columns, {1})
    for invalid in ('NaN', 'Infinity'):
        with pytest.raises(source.SoilDataSourceError):
            source.parse_table({'Table': [['chkey', 'fragvol_r'], ['1', invalid]]}, ['chkey', 'fragvol_r'], {1})


@pytest.mark.parametrize('endpoint', ['http://user:secret@host/Tabular/post.rest', 'https://host/Tabular/post.rest?token=x',
                                    'https://host/Tabular/post.rest#x', 'file:///Tabular/post.rest', 'https://host/Tabular/post.rest\n'])
def test_endpoint_rejects_credentials_and_ambiguous_identity(endpoint):
    with pytest.raises(source.SoilDataSourceError):
        source.SoilDataSource(endpoint, source.JSON_PROFILE, 'r1')


def test_empty_json_fetch_persists_negative_and_warm_reuse_has_no_network(tmp_path):
    calls = []
    def responder(handler):
        calls.append(handler.path)
        reply(handler, metadata() if handler.command == 'GET' else {'Table': component_columns})
    with soil_server(responder) as endpoint:
        path = str(tmp_path / 'cache.sqlite')
        probe = ssurgo.SurgoSoilCollection([])
        component_columns = [[row[1] for row in probe.conn.execute('PRAGMA table_info(component)')]]
        probe._disconnect()
        c = ssurgo.SurgoSoilCollection([123], cache_db_path=path, endpoint=endpoint, profile=source.JSON_PROFILE, release='r1')
        evidence = source.cache_evidence(c.conn)
        assert c.conn.execute('SELECT mukey FROM bad_component_mukey').fetchone()[0] == 123
        assert len(evidence['fetches']) == 1
        assert evidence['fetches'][0]['row_count'] == 0
        assert evidence['fetches'][0]['metadata']['server_code_revision_observed'] == 'a' * 40
        c._disconnect()
    # Server is gone; a fully cached negative still requires no network.
    c = ssurgo.SurgoSoilCollection([123], cache_db_path=path, endpoint=endpoint, profile=source.JSON_PROFILE, release='r1')
    assert source.cache_evidence(c.conn) == evidence
    c._disconnect()
    assert len(calls) == 2
    with pytest.raises(source.SoilDataSourceError, match='identity mismatch'):
        ssurgo.SurgoSoilCollection([], cache_db_path=path, endpoint=endpoint, profile=source.JSON_PROFILE, release='r2')
    with sqlite3.connect(path) as conn:
        assert json.loads(conn.execute('SELECT binding FROM soil_data_source').fetchone()[0]) == evidence['binding']


def test_unknown_negative_only_cache_and_partial_provenance_rejected(tmp_path):
    path = tmp_path / 'legacy.sqlite'
    with sqlite3.connect(path) as conn:
        conn.execute('CREATE TABLE bad_component_mukey(mukey INTEGER)')
        conn.execute('INSERT INTO bad_component_mukey VALUES(123)')
    with pytest.raises(source.SoilDataSourceError, match='unknown populated'):
        ssurgo.SurgoSoilCollection([], cache_db_path=str(path), endpoint='http://localhost/Tabular/post.rest', profile=source.JSON_PROFILE, release='r1')
    with sqlite3.connect(path) as conn:
        assert conn.execute('SELECT mukey FROM bad_component_mukey').fetchone()[0] == 123
        assert not conn.execute("SELECT name FROM sqlite_master WHERE name='soil_data_source'").fetchall()
    c = ssurgo.SurgoSoilCollection([], cache_db_path=str(path))
    assert source.cache_evidence(c.conn)['binding']['historical_rows_unknown'] is True
    c._disconnect()
    with sqlite3.connect(path) as conn:
        conn.execute('DROP TABLE soil_data_fetch')
    with pytest.raises(source.SoilDataSourceError, match='Partial'):
        ssurgo.SurgoSoilCollection([], cache_db_path=str(path))


def test_failed_identity_response_does_not_write_rows_or_event(tmp_path):
    def responder(handler):
        reply(handler, metadata() if handler.command == 'GET' else {'Table': []}, release='changed')
    path = str(tmp_path / 'cache.sqlite')
    with soil_server(responder) as endpoint, pytest.raises(source.SoilDataSourceError, match='changed'):
        ssurgo.SurgoSoilCollection([123], cache_db_path=path, endpoint=endpoint, profile=source.JSON_PROFILE, release='r1')
    with sqlite3.connect(path) as conn:
        for table in ('component', 'bad_component_mukey', 'soil_data_fetch'):
            assert conn.execute(f'SELECT count(*) FROM {table}').fetchone()[0] == 0


@pytest.mark.parametrize('mode', ['oversized', 'compressed', 'redirect', 'slow_headers', 'slow_body'])
def test_bounded_http_response_failures(monkeypatch, mode):
    monkeypatch.setattr(source, 'MAX_RESPONSE_BYTES', 64)
    monkeypatch.setattr(source, 'REQUEST_DEADLINE_SECONDS', 0.15)
    def responder(handler):
        try:
            if mode == 'slow_headers':
                for byte in b'HTTP/1.1 200 OK\r\n':
                    handler.wfile.write(bytes([byte])); handler.wfile.flush(); time.sleep(0.04)
            elif mode == 'slow_body':
                handler.send_response(200); handler.send_header('Content-Type', 'application/json'); handler.send_header('Content-Length', '100'); handler.end_headers()
                for _ in range(20):
                    handler.wfile.write(b' '); handler.wfile.flush(); time.sleep(0.04)
            else:
                reply(handler, {'data': 'x' * 100}, encoding='gzip' if mode == 'compressed' else None, status=302 if mode == 'redirect' else 200)
        except (BrokenPipeError, ConnectionResetError):
            pass
    with soil_server(responder) as endpoint:
        started = time.monotonic()
        with pytest.raises(source.SoilDataSourceError):
            source._request_json(endpoint)
        assert time.monotonic() - started < 1


def test_sidecar_hash_rejects_changed_soil(tmp_path):
    path = tmp_path / '1.sol'
    path.write_text('soil bytes')
    source.write_artifact_provenance(str(path), {'source': 'observed'})
    assert source.read_artifact_provenance(str(path))['source'] == 'observed'
    path.write_text('changed')
    with pytest.raises(source.SoilDataSourceError, match='hash'):
        source.read_artifact_provenance(str(path))


def test_sqlite_failure_rolls_back_records_markers_and_event(tmp_path):
    c = ssurgo.SurgoSoilCollection([], cache_db_path=str(tmp_path / 'cache.sqlite'),
                                  endpoint='http://localhost/Tabular/post.rest', profile=source.JSON_PROFILE, release='r1')
    # Abort provenance insertion after rows have been inserted in the transaction.
    c.conn.execute("CREATE TRIGGER fail_event BEFORE INSERT ON soil_data_fetch BEGIN SELECT RAISE(ABORT, 'fault injection'); END")
    c.conn.commit()
    def fetched(keys, *, client):
        return [(next(iter(keys)), 12.5)]
    try:
        with pytest.raises(sqlite3.IntegrityError, match='fault injection'):
            c._sync('chfrags', fetched, 'chkey', [1, 2])
        for table in ('chfrags', 'bad_chfrags_chkey', 'soil_data_fetch'):
            assert c.conn.execute(f'SELECT count(*) FROM {table}').fetchone()[0] == 0
    finally:
        c._disconnect()


def test_equal_bytes_new_identity_cannot_leave_old_sidecar_on_failure(tmp_path, monkeypatch):
    class WrittenSoil:
        mukey = 1
        majorComponent = None
        def write(self, wd, overwrite, **kwargs):
            path = Path(wd) / '1.sol'
            path.write_text('identical model bytes')
            return type('Summary', (), {'mukey': 1, 'path': str(path)})()
    c = ssurgo.SurgoSoilCollection([])
    c.weppSoils = {1: WrittenSoil()}
    c.writeWeppSoils(str(tmp_path))
    path = tmp_path / '1.sol'
    old = Path(str(path) + '.provenance.json').read_bytes()
    # Preserving an existing artifact must also preserve its provenance.
    c.writeWeppSoils(str(tmp_path), overwrite=False)
    assert Path(str(path) + '.provenance.json').read_bytes() == old
    def fail(*args, **kwargs):
        raise OSError('publication failure')
    monkeypatch.setattr(ssurgo, 'write_artifact_provenance', fail)
    with pytest.raises(OSError, match='publication failure'):
        c.writeWeppSoils(str(tmp_path))
    assert path.read_text() == 'identical model bytes'
    assert not Path(str(path) + '.provenance.json').exists()
    c._disconnect()


def test_real_resolver_process_is_killed_at_deadline(monkeypatch):
    monkeypatch.setattr(source, '_RESOLVER_SCRIPT', 'import time; time.sleep(30)')
    started = time.monotonic()
    with pytest.raises(source.SoilServiceUnavailable, match='deadline_exceeded'):
        source._resolve_addresses('localhost', 80, started + 0.1)
    assert time.monotonic() - started < 1


def test_deep_json_is_source_error_not_runtime_fallback():
    def responder(handler):
        payload = b'{"nested":' + b'[' * 2000 + b'0' + b']' * 2000 + b'}'
        handler.send_response(200); handler.send_header('Content-Type', 'application/json')
        handler.send_header('Content-Length', str(len(payload))); handler.end_headers()
        handler.wfile.write(payload)
    with soil_server(responder) as endpoint, pytest.raises(source.SoilDataSourceError):
        source._request_json(endpoint)


@pytest.mark.parametrize('damage', ['missing_columns', 'missing_event_fields', 'missing_history'])
def test_malformed_provenance_fails_before_fetch(tmp_path, damage):
    path = str(tmp_path / 'cache.sqlite')
    identity = source.SoilDataSource('http://localhost/Tabular/post.rest', source.JSON_PROFILE, 'r1')
    c = ssurgo.SurgoSoilCollection([], cache_db_path=path, **identity.identity())
    c._disconnect()
    with sqlite3.connect(path) as conn:
        if damage == 'missing_columns':
            binding = conn.execute('SELECT binding FROM soil_data_source').fetchone()[0]
            conn.execute('DROP TABLE soil_data_source')
            conn.execute('CREATE TABLE soil_data_source(binding TEXT)')
            conn.execute('INSERT INTO soil_data_source VALUES(?)', (binding,))
        elif damage == 'missing_event_fields':
            conn.execute('INSERT INTO soil_data_fetch(event) VALUES(?)', (json.dumps({'identity': identity.identity()}),))
        else:
            conn.execute('INSERT INTO bad_component_mukey VALUES(1)')
    with pytest.raises(source.SoilDataSourceError):
        ssurgo.SurgoSoilCollection([1], cache_db_path=path, **identity.identity())


@pytest.mark.parametrize('datasets', [[None], [{}], [{'dataset': 'SSURGO'}]])
def test_incomplete_metadata_is_not_recorded(tmp_path, datasets):
    def responder(handler):
        payload = metadata()
        payload['active_release']['datasets'] = datasets
        reply(handler, payload)
    path = str(tmp_path / 'cache.sqlite')
    with soil_server(responder) as endpoint, pytest.raises(source.SoilDataSourceError, match='metadata'):
        ssurgo.SurgoSoilCollection([1], cache_db_path=path, endpoint=endpoint, profile=source.JSON_PROFILE, release='r1')
    with sqlite3.connect(path) as conn:
        assert conn.execute('SELECT count(*) FROM soil_data_fetch').fetchone()[0] == 0


def test_later_batch_failure_preserves_committed_batch(tmp_path):
    columns = None
    posts = 0
    def responder(handler):
        nonlocal posts
        if handler.command == 'GET':
            reply(handler, metadata())
        else:
            posts += 1
            reply(handler, {'Table': [columns]}, release='r1' if posts == 1 else 'changed')
    with soil_server(responder) as endpoint:
        c = ssurgo.SurgoSoilCollection([], cache_db_path=str(tmp_path / 'cache.sqlite'),
                                      endpoint=endpoint, profile=source.JSON_PROFILE, release='r1')
        columns = [row[1] for row in c.conn.execute('PRAGMA table_info(component)')]
        try:
            with pytest.raises(source.SoilDataSourceError, match='changed'):
                c._sync('component', ssurgo._fetch_components, 'mukey', range(1001))
            assert c.conn.execute('SELECT count(*) FROM bad_component_mukey').fetchone()[0] == 1000
            assert len(source.cache_evidence(c.conn)['fetches']) == 1
            assert not c.conn.execute('SELECT 1 FROM bad_component_mukey WHERE mukey=1000').fetchall()
        finally:
            c._disconnect()


@pytest.mark.parametrize('endpoint', ['', False, 0])
def test_explicit_empty_endpoint_is_not_defaulted(endpoint):
    with pytest.raises(source.SoilDataSourceError):
        ssurgo.SurgoSoilCollection([], endpoint=endpoint)


def test_metadata_has_its_own_smaller_size_limit(monkeypatch):
    monkeypatch.setattr(source, 'MAX_METADATA_BYTES', 64)
    with soil_server(lambda handler: reply(handler, {'data': 'x' * 100})) as endpoint:
        with pytest.raises(source.SoilDataSourceError):
            source._request_json(endpoint)


def test_resolver_spawn_failure_is_source_failure(monkeypatch):
    def fail(*args, **kwargs):
        raise OSError('resource exhaustion')
    monkeypatch.setattr(source.subprocess, 'run', fail)
    with pytest.raises(source.SoilDataSourceError):
        source._resolve_addresses('localhost', 80, time.monotonic() + 1)


def test_deep_cache_metadata_is_source_failure(monkeypatch):
    c = ssurgo.SurgoSoilCollection([])
    def fail(*args, **kwargs):
        raise RecursionError('malformed metadata')
    monkeypatch.setattr(source.json, 'loads', fail)
    try:
        with pytest.raises(source.SoilDataSourceError):
            source.bind_cache(c.conn, c.data_source)
    finally:
        c._disconnect()
