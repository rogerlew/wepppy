"""Real HTTP/TLS/SQLite selection boundaries; SDA is a controlled local TLS peer."""
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import socket
import sqlite3
import ssl
import subprocess
import threading
from urllib.parse import parse_qs
from xml.etree import ElementTree

import pytest

from wepppy.soils.ssurgo import selection, source, ssurgo

pytestmark = pytest.mark.unit


@pytest.fixture
def schema():
    c = ssurgo.SurgoSoilCollection([])
    columns = {name: [row[1] for row in c.conn.execute(f'PRAGMA table_info({name})')]
               for name in ('component', 'chorizon', 'chfrags', 'chtexturegrp', 'corestrictions')}
    c._disconnect()
    return columns


def metadata():
    return {'service': 'soil-data-access', 'official': False, 'ready': True,
            'contract_version': source.JSON_PROFILE, 'code_revision': 'a' * 40,
            'active_release': {'id': 'r1', 'datasets': [{'dataset': 'SSURGO', 'release_id': 'r1',
                'scope': 'authored test data', 'source_url': 'https://example.com/source', 'sha256': 'b' * 64}]}}


def row_for(table, columns, label):
    values = ({'mukey': '1', 'cokey': '11', 'compname': label, 'comppct_r': '100', 'hydgrpdcd': 'B'}
              if table == 'component' else
              {'cokey': '11', 'chkey': '111', 'hzname': 'A', 'hzdept_r': '0', 'hzdepb_r': '50',
               'hzthk_r': '50', 'sandtotal_r': '40', 'claytotal_r': '20', 'om_r': '2',
               'dbthirdbar_r': '1.2', 'ksat_r': '5', 'cec7_r': '12', 'sandvf_r': '10'})
    return [values.get(column) for column in columns]


@contextmanager
def server(schema, *, mode='success', label='mirror', tls=None):
    calls = []
    release_stalled_response = threading.Event()
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass
        def do_GET(self):
            calls.append(('metadata', None))
            self.respond('metadata', None)
        def do_POST(self):
            form = parse_qs(self.rfile.read(int(self.headers['Content-Length'])).decode())
            query = form['query'][0].lower()
            table = next(name for name in schema if 'from ' + name in query)
            calls.append((table, form['format'][0]))
            self.respond(table, form['format'][0])
        def respond(self, table, fmt):
            try:
                if mode == 'xml_error':
                    payload = b'<Error>query failed</Error>'
                    self.send_response(200); self.send_header('Content-Type', 'text/xml')
                    self.send_header('Content-Length', str(len(payload))); self.end_headers()
                    self.wfile.write(payload); return
                if mode == 'unavailable' or (mode == 'partial' and table == 'chorizon'):
                    self.send_response(503); self.end_headers(); return
                if mode == 'slow_headers':
                    self.wfile.write(b'HTTP/1.1 200 OK\r\n'); self.wfile.flush()
                    release_stalled_response.wait(timeout=5)
                    return
                if mode == 'slow_body':
                    self.send_response(200); self.send_header('Content-Type', 'application/json')
                    self.send_header('Content-Length', '100'); self.end_headers()
                    self.wfile.write(b'{'); self.wfile.flush()
                    release_stalled_response.wait(timeout=5)
                    return
                if table == 'metadata':
                    data = metadata()
                    if mode == 'not_ready':
                        data.update(ready=False, active_release=None)
                    payload = json.dumps(data).encode(); content_type = 'application/json'
                else:
                    rows = [] if table not in ('component', 'chorizon') or mode == 'missing' else [row_for(table, schema[table], label)]
                    if fmt == 'xml':
                        root = ElementTree.Element('NewDataSet')
                        for row in rows:
                            element = ElementTree.SubElement(root, 'Table')
                            for name, value in zip(schema[table], row):
                                ElementTree.SubElement(element, name).text = value
                        payload = ElementTree.tostring(root); content_type = 'text/xml'
                    else:
                        payload = json.dumps({'Table': [schema[table]] + rows}).encode(); content_type = 'application/json'
                self.send_response(200)
                self.send_header('Content-Type', content_type)
                self.send_header('X-Soil-Profile', source.JSON_PROFILE)
                self.send_header('X-Soil-Release', 'wrong' if mode == 'wrong_release' else 'r1')
                self.send_header('Content-Length', str(len(payload)))
                self.end_headers(); self.wfile.write(payload)
            except (BrokenPipeError, ConnectionResetError):
                pass
    srv = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    if tls is not None:
        srv.socket = tls.wrap_socket(srv.socket, server_side=True)
    thread = threading.Thread(target=srv.serve_forever, daemon=True); thread.start()
    try:
        yield srv, calls
    finally:
        release_stalled_response.set()
        srv.shutdown(); srv.server_close(); thread.join()


@pytest.fixture
def sda_tls(tmp_path, monkeypatch):
    cert, key = tmp_path / 'cert.pem', tmp_path / 'key.pem'
    subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '1',
        '-keyout', str(key), '-out', str(cert), '-subj', '/CN=sdmdataaccess.nrcs.usda.gov',
        '-addext', 'subjectAltName=DNS:sdmdataaccess.nrcs.usda.gov'], check=True, capture_output=True)
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER); ctx.load_cert_chain(cert, key)
    trusted = ssl.create_default_context(cafile=str(cert))
    monkeypatch.setattr(source.ssl, 'create_default_context', lambda: trusted)
    return ctx


def route_sda(monkeypatch, srv):
    original = source._resolve_addresses
    def resolve(host, port, deadline):
        if host == 'sdmdataaccess.nrcs.usda.gov':
            return socket.getaddrinfo('127.0.0.1', srv.server_port, type=socket.SOCK_STREAM)
        return original(host, port, deadline)
    monkeypatch.setattr(source, '_resolve_addresses', resolve)


def build(primary, tmp_path, keys=(1,)):
    endpoint = f'http://127.0.0.1:{primary.server_port}/Tabular/post.rest'
    return selection.soil_collection(keys, cache_db_path=str(tmp_path / 'mirror.sqlite'),
        endpoint=endpoint, profile=source.JSON_PROFILE, release='r1', fallback_to_sda=True,
        fallback_cache_db_path=str(tmp_path / 'sda.sqlite'))


def test_primary_success_and_warm_reuse_preserve_retrievals(schema, tmp_path):
    with server(schema) as (primary, calls):
        c = build(primary, tmp_path)
        assert c.selection_event['actual_supplier'] == c.data_source.identity()
        assert len(c.selection_event['attempts']) == 1
        before = source.cache_evidence(c.conn)
        c._disconnect()
        count = len(calls)
        c = build(primary, tmp_path)
        assert c.selection_event['attempts'][0]['reason'] == 'cache_reused'
        assert source.cache_evidence(c.conn) == before
        assert len(calls) == count
        assert c.conn.execute('SELECT count(*) FROM soil_data_selection').fetchone()[0] == 2
        c._disconnect()
    assert not (tmp_path / 'sda.sqlite').exists()


@pytest.mark.parametrize('mode', ['unavailable', 'partial', 'missing', 'not_ready', 'slow_headers', 'slow_body'])
def test_fallback_rebuilds_whole_collection_with_real_xml_tls(schema, tmp_path, monkeypatch, sda_tls, mode):
    if mode.startswith('slow'):
        # Stall the real mirror request while leaving the XML/TLS fallback its full budget.
        request_json = source._request_json

        def short_mirror_request(*args, **kwargs):
            with monkeypatch.context() as mirror:
                mirror.setattr(source, 'REQUEST_DEADLINE_SECONDS', 0.2)
                return request_json(*args, **kwargs)

        monkeypatch.setattr(source, '_request_json', short_mirror_request)
    with server(schema, mode=mode) as (primary, _), server(schema, label='SDA', tls=sda_tls) as (sda, calls):
        route_sda(monkeypatch, sda)
        c = build(primary, tmp_path)
        if mode.startswith('slow'):
            assert c.selection_event['attempts'][0]['reason'] == 'deadline_exceeded'
        assert c.conn.execute('SELECT compname FROM component').fetchone()[0] == 'SDA'
        assert c.data_source.profile == 'legacy-xml'
        assert c.selection_event['actual_supplier'] == source.SoilDataSource().identity()
        assert len(c.selection_event['attempts']) == 2
        assert all(fmt == 'xml' for _, fmt in calls)
        assert c.selection_event['historical_rows_unknown'] is False
        c._disconnect()
    if mode == 'partial':
        with sqlite3.connect(tmp_path / 'mirror.sqlite') as conn:
            assert conn.execute('SELECT compname FROM component').fetchone()[0] == 'mirror'


def test_both_unavailable_record_both_attempts(schema, tmp_path, monkeypatch, sda_tls):
    with server(schema, mode='unavailable') as (primary, _), server(schema, mode='unavailable', tls=sda_tls) as (sda, _):
        route_sda(monkeypatch, sda)
        with pytest.raises(selection.SoilSourceSelectionError) as error:
            build(primary, tmp_path)
        event = json.loads((tmp_path / 'mirror.sqlite.selection.json').read_text())
        assert event == error.value.selection
        assert event['actual_supplier'] is None
        assert [a['reason'] for a in event['attempts']] == ['http_5xx', 'http_5xx']


def test_wrong_release_never_falls_back(schema, tmp_path, monkeypatch, sda_tls):
    with server(schema, mode='wrong_release') as (primary, _), server(schema, tls=sda_tls) as (sda, calls):
        route_sda(monkeypatch, sda)
        with pytest.raises(selection.SoilSourceSelectionError):
            build(primary, tmp_path)
        assert calls == []
        assert not (tmp_path / 'sda.sqlite').exists()


def test_publication_failure_invalidates_old_selection_and_is_source_error(schema, tmp_path, monkeypatch):
    with server(schema) as (primary, _):
        c = build(primary, tmp_path); c._disconnect()
        path = tmp_path / 'mirror.sqlite.selection.json'
        assert path.exists()
        original = selection.os.replace
        def fail(src, dst):
            if str(dst).endswith('.selection.json'):
                raise PermissionError('injected filesystem fault')
            return original(src, dst)
        monkeypatch.setattr(selection.os, 'replace', fail)
        with pytest.raises(source.SoilDataSourceError):
            build(primary, tmp_path)
        assert not path.exists()


def test_selection_sqlite_fault_is_not_numerical_fallback(schema, tmp_path):
    with server(schema) as (primary, _):
        c = build(primary, tmp_path)
        c.conn.execute("CREATE TRIGGER fail_selection BEFORE INSERT ON soil_data_selection BEGIN SELECT RAISE(ABORT,'injected fault'); END")
        c.conn.commit(); c._disconnect()
        with pytest.raises(source.SoilDataSourceError, match='persistence'):
            build(primary, tmp_path)
        assert not (tmp_path / 'mirror.sqlite.selection.json').exists()


@pytest.mark.parametrize('encoding', ['utf-8', 'utf-16'])
def test_xml_entity_declarations_rejected_for_all_encodings(encoding):
    text = '<?xml version="1.0" encoding="' + encoding + '"?><!DOCTYPE x [<!ENTITY a "bad">]><x>&a;</x>'
    parser = ElementTree.XMLParser(target=source._BoundedXmlTreeBuilder())
    with pytest.raises(source.SoilDataSourceError, match='DTD'):
        ElementTree.fromstring(text.encode(encoding), parser=parser)


def test_deployment_default_does_not_override_saved_selection(monkeypatch, tmp_path):
    from wepppy.nodb.core.soils import Soils
    monkeypatch.setenv('SOIL_DATA_MODE', 'mirror-first')
    monkeypatch.setenv('SOIL_DATA_ENDPOINT', 'http://soil-api:8080/Tabular/post.rest')
    monkeypatch.setenv('SOIL_DATA_RELEASE', 'r1')
    s = Soils.__new__(Soils); s.wd = str(tmp_path); s._config = '0.cfg'
    assert s.soil_data_policy == 'mirror-first'
    assert s.soil_data_source['release'] == 'r1'
    assert s._soil_data_source_kwargs(use_statsgo=True)['fallback_cache_db_path'].endswith('statsgo_tabular_cache.sqlite')
    s._soil_data_source = source.SoilDataSource().identity()
    assert s.soil_data_policy == 'explicit'
    assert s.soil_data_source['profile'] == 'legacy-xml'
    s._soil_data_policy = 'invalid'
    with pytest.raises(source.SoilDataSourceError):
        s._soil_data_source_kwargs()


def test_corrupt_selection_history_fails_before_network(schema, tmp_path):
    with server(schema) as (primary, calls):
        c = build(primary, tmp_path)
        c.conn.execute("UPDATE soil_data_selection SET event='{}'")
        c.conn.commit(); c._disconnect()
        count = len(calls)
        with pytest.raises(source.SoilDataSourceError):
            build(primary, tmp_path)
        assert len(calls) == count
        assert not (tmp_path / 'sda.sqlite').exists()


def test_warm_historical_fallback_preserves_unknown_origin(schema, tmp_path, monkeypatch, sda_tls):
    with server(schema, mode='unavailable') as (primary, _), server(schema, tls=sda_tls) as (sda, calls):
        route_sda(monkeypatch, sda)
        c = build(primary, tmp_path)
        for table in ('soil_data_selection', 'soil_data_fetch', 'soil_data_source'):
            c.conn.execute('DROP TABLE ' + table)
        c.conn.commit(); c._disconnect()
        count = len(calls)
        c = build(primary, tmp_path)
        assert c.selection_event['historical_rows_unknown'] is True
        assert c.selection_event['attempts'][-1]['reason'] == 'cache_reused'
        assert len(calls) == count
        c._disconnect()
    with server(schema, mode='unavailable') as (other, _):
        c = selection.soil_collection([1], cache_db_path=str(tmp_path / 'other.sqlite'),
            endpoint=f'http://127.0.0.1:{other.server_port}/Tabular/post.rest',
            profile=source.JSON_PROFILE, release='r1', fallback_to_sda=True,
            fallback_cache_db_path=str(tmp_path / 'sda.sqlite'))
        assert c.selection_event['historical_rows_unknown'] is True
        assert c.conn.execute('SELECT count(*) FROM soil_data_selection').fetchone()[0] == 2
        c._disconnect()


def test_untrusted_tls_is_contract_error_not_availability(schema, tmp_path, monkeypatch, sda_tls):
    with server(schema, tls=sda_tls) as (primary, _):
        # Generated certificate is for USDA, not the loopback primary hostname.
        with pytest.raises(selection.SoilSourceSelectionError) as error:
            selection.soil_collection([1], cache_db_path=str(tmp_path / 'mirror.sqlite'),
                endpoint=f'https://127.0.0.1:{primary.server_port}/Tabular/post.rest',
                profile=source.JSON_PROFILE, release='r1', fallback_to_sda=True,
                fallback_cache_db_path=str(tmp_path / 'sda.sqlite'))
        assert [a['outcome'] for a in error.value.selection['attempts']] == ['contract_error']
        assert not (tmp_path / 'sda.sqlite').exists()


def test_xml_error_envelope_is_not_negative_cached(schema, tmp_path, monkeypatch, sda_tls):
    with server(schema, mode='unavailable') as (primary, _), server(schema, mode='xml_error', tls=sda_tls) as (sda, _):
        route_sda(monkeypatch, sda)
        with pytest.raises(selection.SoilSourceSelectionError) as error:
            build(primary, tmp_path)
        assert error.value.selection['actual_supplier'] is None
        assert error.value.selection['attempts'][-1]['outcome'] == 'contract_error'
        with sqlite3.connect(tmp_path / 'sda.sqlite') as conn:
            assert conn.execute('SELECT count(*) FROM soil_data_fetch').fetchone()[0] == 0


def test_evidence_read_failure_closes_collection_and_records_failure(schema, tmp_path, monkeypatch):
    captured = []
    def fail(conn):
        captured.append(conn)
        raise sqlite3.OperationalError('injected read failure')
    monkeypatch.setattr(selection, 'cache_evidence', fail)
    with server(schema) as (primary, _):
        with pytest.raises(selection.SoilSourceSelectionError) as error:
            build(primary, tmp_path)
    assert error.value.selection['actual_supplier'] is None
    assert error.value.selection['attempts'][0]['outcome'] == 'contract_error'
    assert json.loads((tmp_path / 'mirror.sqlite.selection.json').read_text()) == error.value.selection
    with pytest.raises(sqlite3.ProgrammingError):
        captured[0].execute('SELECT 1')


def test_selection_history_cannot_relabel_unknown_origin(schema, tmp_path):
    with server(schema) as (primary, _):
        c = build(primary, tmp_path)
        event = c.selection_event
        event['historical_rows_unknown'] = True
        c.conn.execute('UPDATE soil_data_selection SET event=?', (json.dumps(event),))
        c.conn.commit(); c._disconnect()
        with pytest.raises(source.SoilDataSourceError):
            build(primary, tmp_path)
