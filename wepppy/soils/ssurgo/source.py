"""Explicit soil transport identity and durable cache/artifact provenance."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import http.client
import io
import json
import math
import os
from pathlib import Path
import re
import socket
import sqlite3
import ssl
import subprocess
import sys
import tempfile
import time
from urllib.parse import urlencode, urlsplit, urlunsplit

from wepppy.all_your_base import try_parse

XML_ENDPOINT = "https://sdmdataaccess.nrcs.usda.gov/Tabular/post.rest"
JSON_PROFILE = "wepppy-json-v1"
MAX_RESPONSE_BYTES = 16 * 1024 * 1024
MAX_METADATA_BYTES = 64 * 1024
_RESOLVER_SCRIPT = "import json,socket,sys; host,port=json.load(sys.stdin); print(json.dumps(socket.getaddrinfo(host,port,type=socket.SOCK_STREAM)))"
REQUEST_DEADLINE_SECONDS = 30.0


class SoilDataSourceError(Exception):
    """Source identity/transport failure; must not become a soil fallback."""


def canonical_endpoint(endpoint: str) -> str:
    if not isinstance(endpoint, str) or any(c.isspace() or c in '`|<>\\' or ord(c) < 32 for c in endpoint):
        raise SoilDataSourceError("Invalid soil endpoint")
    try:
        parts = urlsplit(endpoint)
        port = parts.port
    except ValueError as exc:
        raise SoilDataSourceError("Invalid soil endpoint") from exc
    if (parts.scheme.lower() not in ('http', 'https') or not parts.hostname or
            parts.username is not None or parts.password is not None or parts.query or parts.fragment or
            not parts.path.endswith('/Tabular/post.rest') or '..' in parts.path.split('/')):
        raise SoilDataSourceError("Expected an HTTP(S) soil tabular endpoint without credentials or query")
    host = parts.hostname.lower()
    if ':' in host:
        host = '[' + host + ']'
    if port is not None:
        if port == 0:
            raise SoilDataSourceError("Invalid soil endpoint port")
        if (parts.scheme.lower(), port) not in (('http', 80), ('https', 443)):
            host += ':' + str(port)
    return urlunsplit((parts.scheme.lower(), host, parts.path, '', ''))


@dataclass(frozen=True)
class SoilDataSource:
    endpoint: str = XML_ENDPOINT
    profile: str = 'legacy-xml'
    release: str | None = None

    def __post_init__(self):
        object.__setattr__(self, 'endpoint', canonical_endpoint(self.endpoint))
        if self.profile == 'legacy-xml':
            if self.endpoint != XML_ENDPOINT or self.release is not None:
                raise SoilDataSourceError("Legacy XML requires the USDA endpoint and unknown release")
        elif self.profile == JSON_PROFILE:
            if not isinstance(self.release, str) or not re.fullmatch(r'[A-Za-z0-9._-]{1,128}', self.release):
                raise SoilDataSourceError("JSON soil source requires an explicit immutable release ID")
        else:
            raise SoilDataSourceError("Unsupported soil data profile")

    def identity(self) -> dict:
        return {'endpoint': self.endpoint, 'profile': self.profile, 'release': self.release}

    def cache_path(self, path: str) -> str:
        if self.profile == 'legacy-xml':
            return path
        suffix = hashlib.sha256(json.dumps(self.identity(), sort_keys=True).encode()).hexdigest()
        stem, extension = os.path.splitext(path)
        return stem + '.' + suffix + extension


class _DeadlineReader(io.RawIOBase):
    def __init__(self, owner):
        self.owner = owner
        self.sock, self.deadline = owner.sock, owner.deadline

    def close(self):
        if not self.closed:
            super().close()
            self.owner.reader_closed()

    def readable(self):
        return True

    def readinto(self, buffer):
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError('Soil request deadline exceeded')
        self.sock.settimeout(min(5.0, remaining))
        return self.sock.recv_into(buffer)


class _DeadlineSocket:
    """Apply one absolute deadline to status/header/body socket reads as well as writes."""
    def __init__(self, sock, deadline):
        self.sock, self.deadline = sock, deadline
        self.readers = 0
        self.closing = False

    def makefile(self, mode):
        if mode != 'rb':
            raise SoilDataSourceError('Unexpected HTTP socket mode')
        self.readers += 1
        return io.BufferedReader(_DeadlineReader(self))

    def sendall(self, data):
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError('Soil request deadline exceeded')
        self.sock.settimeout(min(5.0, remaining))
        self.sock.sendall(data)

    def reader_closed(self):
        self.readers -= 1
        if self.closing and self.readers == 0:
            self.sock.close()

    def close(self):
        self.closing = True
        if self.readers == 0:
            self.sock.close()


def _resolve_addresses(host, port, deadline):
    # getaddrinfo has no Python deadline; a killable child bounds resolver stalls.
    remaining = min(5.0, deadline - time.monotonic())
    if remaining <= 0:
        raise SoilDataSourceError('Soil request deadline exceeded')
    try:
        result = subprocess.run([sys.executable, '-I', '-c', _RESOLVER_SCRIPT],
                                input=json.dumps([host, port]), text=True, capture_output=True,
                                timeout=remaining, check=True)
        return json.loads(result.stdout)
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, OSError, ValueError) as exc:
        raise SoilDataSourceError('Soil endpoint resolution failed or exceeded deadline') from exc


def _request_json(url: str, form: dict | None = None, *, address_cache=None) -> tuple[dict, dict, str]:
    parts = urlsplit(url)
    deadline = time.monotonic() + REQUEST_DEADLINE_SECONDS
    port = parts.port or (443 if parts.scheme == 'https' else 80)
    cache = address_cache if address_cache is not None else {}
    key = (parts.hostname, port)
    if key not in cache:
        cache[key] = _resolve_addresses(parts.hostname, port, deadline)

    def connect_address(address, timeout=None, source_address=None):
        last_error = None
        for family, kind, protocol, _, sockaddr in cache[key]:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError('Soil request deadline exceeded')
            sock = socket.socket(family, kind, protocol)
            try:
                sock.settimeout(min(5.0, remaining))
                sock.connect(tuple(sockaddr))
                return sock
            except OSError as exc:
                sock.close()
                last_error = exc
        raise OSError('No soil endpoint address connected') from last_error

    connection = http.client.HTTPConnection(parts.hostname, port)
    connection._create_connection = connect_address
    response = None
    try:
        connection.connect()
        if parts.scheme == 'https':
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError('Soil request deadline exceeded')
            connection.sock.settimeout(min(5.0, remaining))
            connection.sock = ssl.create_default_context().wrap_socket(connection.sock, server_hostname=parts.hostname)
        connection.sock = _DeadlineSocket(connection.sock, deadline)
        body = None if form is None else urlencode(form).encode('ascii')
        headers = {'Accept': 'application/json', 'Accept-Encoding': 'identity'}
        if form is not None:
            headers['Content-Type'] = 'application/x-www-form-urlencoded'
        connection.request('GET' if form is None else 'POST', parts.path, body=body, headers=headers)
        response = connection.getresponse()
        if response.status != 200:
            raise SoilDataSourceError(f'Soil service returned HTTP {response.status}')
        if response.getheader('Content-Encoding', 'identity').lower() not in ('identity', ''):
            raise SoilDataSourceError('Compressed soil responses are outside this profile')
        if response.getheader('Content-Type', '').split(';')[0].strip().lower() != 'application/json':
            raise SoilDataSourceError('Soil service did not return JSON')
        payload = bytearray()
        while True:
            if time.monotonic() >= deadline:
                raise SoilDataSourceError('Soil request deadline exceeded')
            chunk = response.read1(65536)
            if not chunk:
                break
            payload.extend(chunk)
            if len(payload) > min(MAX_RESPONSE_BYTES, MAX_METADATA_BYTES if form is None else MAX_RESPONSE_BYTES):
                raise SoilDataSourceError('Soil response exceeds byte limit')
        depth, quoted, escaped = 0, False, False
        for byte in payload:
            if quoted:
                if escaped:
                    escaped = False
                elif byte == 92:
                    escaped = True
                elif byte == 34:
                    quoted = False
            elif byte == 34:
                quoted = True
            elif byte in (91, 123):
                depth += 1
                if depth > 64:
                    raise SoilDataSourceError('Soil JSON nesting exceeds profile limit')
            elif byte in (93, 125):
                depth -= 1
        parsed = json.loads(payload)
        if not isinstance(parsed, dict):
            raise SoilDataSourceError('Expected a JSON soil object')
        return parsed, {name.lower(): value for name, value in response.getheaders()}, hashlib.sha256(payload).hexdigest()
    except (OSError, http.client.HTTPException, ValueError, UnicodeError, RecursionError) as exc:
        raise SoilDataSourceError('Soil service transport or JSON decoding failed') from exc
    finally:
        if response is not None:
            response.close()
        connection.close()


def parse_table(body: dict, columns: list[str], keys) -> list[tuple]:
    if not isinstance(body, dict) or set(body) != {'Table'} or not isinstance(body['Table'], list) or not body['Table'] or body['Table'][0] != columns:
        raise SoilDataSourceError('Soil response column header differs')
    keys = set(keys)
    result, seen = [], set()
    for row in body['Table'][1:]:
        if not isinstance(row, list) or len(row) != len(columns) or any(v is not None and not isinstance(v, str) for v in row):
            raise SoilDataSourceError('Invalid soil response row shape/types')
        values = []
        for column, value in zip(columns, row):
            if column in ('mukey', 'cokey', 'chkey'):
                if not isinstance(value, str) or not re.fullmatch(r'[0-9]+', value):
                    raise SoilDataSourceError('Invalid exact soil identifier')
                normalized = value.lstrip('0') or '0'
                if len(normalized) > 19 or int(normalized) > 9223372036854775807:
                    raise SoilDataSourceError('Invalid exact soil identifier')
                values.append(int(normalized))
            else:
                values.append(try_parse(None if value == '' else value))
        values = tuple(values)
        if any(isinstance(value, float) and not math.isfinite(value) for value in values):
            raise SoilDataSourceError('Non-finite soil value')
        if values[0] not in keys:
            raise SoilDataSourceError('Soil response contains an unrequested key')
        identity = values[:2] if columns[:2] in (['mukey', 'cokey'], ['cokey', 'chkey']) else values[:1]
        if identity not in seen:
            seen.add(identity)
            result.append(values)
    return result


def valid_manifest(manifest, release):
    if not isinstance(manifest, dict) or set(manifest) != {'id', 'datasets'} or manifest['id'] != release:
        return False
    datasets = manifest['datasets']
    if not isinstance(datasets, list) or not datasets:
        return False
    required = {'dataset', 'release_id', 'scope', 'source_url', 'sha256'}
    for dataset in datasets:
        if not isinstance(dataset, dict) or set(dataset) != required:
            return False
        if any(not isinstance(value, str) or not value for value in dataset.values()):
            return False
        if dataset['dataset'] not in ('SSURGO', 'STATSGO2', 'WEPPPY_CACHE_REPLAY') or not re.fullmatch('[a-f0-9]{64}', dataset['sha256']):
            return False
        try:
            url = urlsplit(dataset['source_url'])
            if not url.scheme or url.username or url.password or any(c.isspace() for c in dataset['source_url']):
                return False
        except ValueError:
            return False
    return True


def _valid_timestamp(value):
    try:
        return isinstance(value, str) and datetime.fromisoformat(value).utcoffset() is not None
    except ValueError:
        return False


def valid_event(event, source):
    if not isinstance(event, dict) or event.get('identity') != source.identity() or not _valid_timestamp(event.get('observed_at')):
        return False
    if event.get('table') not in ('component', 'chorizon', 'chfrags', 'chtexturegrp', 'corestrictions'):
        return False
    if any(type(event.get(key)) is not int or event[key] < 0 for key in ('key_count', 'row_count')):
        return False
    if not isinstance(event.get('processed_records_sha256'), str) or not re.fullmatch('[a-f0-9]{64}', event['processed_records_sha256']):
        return False
    if source.profile == JSON_PROFILE:
        metadata = event.get('metadata')
        if not isinstance(event.get('response_sha256'), str) or not re.fullmatch('[a-f0-9]{64}', event['response_sha256']):
            return False
        if event.get('response_origin') != response_origin(source.endpoint) or not isinstance(metadata, dict):
            return False
        revision = metadata.get('server_code_revision_observed')
        if not isinstance(revision, str) or not re.fullmatch('[a-f0-9]{40}', revision):
            return False
        if not _valid_timestamp(metadata.get('observed_at')) or not valid_manifest(metadata.get('release_manifest'), source.release):
            return False
    return True


class JsonSoilClient:
    def __init__(self, source: SoilDataSource, columns: dict[str, list[str]]):
        self.source, self.columns = source, columns
        self.address_cache = {}
        self.metadata = None
        self.last_event = None

    def query(self, query: str, table: str, keys) -> list[tuple]:
        if self.metadata is None:
            url = self.source.endpoint.removesuffix('/Tabular/post.rest') + '/v1/metadata'
            metadata, _, _ = _request_json(url, address_cache=self.address_cache)
            release = metadata.get('active_release')
            revision = metadata.get('code_revision')
            if (metadata.get('service') != 'soil-data-access' or metadata.get('official') is not False or metadata.get('ready') is not True or metadata.get('contract_version') != JSON_PROFILE or
                    not isinstance(release, dict) or release.get('id') != self.source.release or
                    not valid_manifest(release, self.source.release) or
                    not isinstance(revision, str) or not re.fullmatch('[a-f0-9]{40}', revision)):
                raise SoilDataSourceError('Soil metadata does not match the selected ready release/profile')
            self.metadata = {'observed_at': utc_now(), 'server_code_revision_observed': revision,
                             'release_manifest': release}
        body, headers, response_hash = _request_json(self.source.endpoint, {'query': query, 'format': 'JSON+COLUMNNAME'}, address_cache=self.address_cache)
        if headers.get('x-soil-profile') != self.source.profile or headers.get('x-soil-release') != self.source.release:
            raise SoilDataSourceError('Soil response source profile/release changed')
        records = parse_table(body, self.columns[table], keys)
        self.last_event = {'observed_at': utc_now(), 'response_sha256': response_hash,
                           'response_origin': response_origin(self.source.endpoint), 'metadata': self.metadata}
        return records


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def response_origin(url) -> str | None:
    if not isinstance(url, str):
        return None
    try:
        parts = urlsplit(url)
        if parts.scheme.lower() not in ('http', 'https') or not parts.hostname:
            return None
        host = parts.hostname.lower()
        host = '[' + host + ']' if ':' in host else host
        if parts.port is not None:
            host += ':' + str(parts.port)
        return urlunsplit((parts.scheme.lower(), host, '', '', ''))
    except ValueError:
        return None


def bind_cache(conn: sqlite3.Connection, source: SoilDataSource) -> None:
    with conn:
        conn.execute('BEGIN IMMEDIATE')
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        provenance_tables = tables & {'soil_data_source', 'soil_data_fetch'}
        if provenance_tables:
            if len(provenance_tables) != 2:
                raise SoilDataSourceError('Partial soil cache provenance schema')
            try:
                for table, expected in (('soil_data_source', ['singleton', 'binding']), ('soil_data_fetch', ['id', 'event'])):
                    columns = conn.execute(f'PRAGMA table_info({table})').fetchall()
                    if [row[1] for row in columns] != expected or columns[0][5] != 1:
                        raise SoilDataSourceError('Malformed soil provenance table schema')
                rows = conn.execute('SELECT binding FROM soil_data_source WHERE singleton=1').fetchall()
                if conn.execute('SELECT count(*) FROM soil_data_source').fetchone()[0] != 1:
                    raise SoilDataSourceError('Malformed soil source singleton')
                binding = json.loads(rows[0][0]) if len(rows) == 1 else None
                if (not isinstance(binding, dict) or binding.get('schema_version') != 1 or
                        not isinstance(binding.get('historical_rows_unknown'), bool) or
                        binding.get('identity') != source.identity()):
                    raise SoilDataSourceError('Soil cache source identity mismatch or malformed provenance')
                events = [json.loads(row[0]) for row in conn.execute('SELECT event FROM soil_data_fetch')]
                if any(not valid_event(event, source) for event in events):
                    raise SoilDataSourceError('Malformed or mixed soil fetch provenance')
            except (sqlite3.Error, ValueError, TypeError, RecursionError) as exc:
                raise SoilDataSourceError('Malformed soil cache provenance') from exc
            if source.profile == JSON_PROFILE:
                if binding['historical_rows_unknown'] or (not events and any(conn.execute(f'SELECT 1 FROM "{table}" LIMIT 1').fetchone() is not None for table in tables if table in ('component', 'chorizon', 'chfrags', 'chtexturegrp', 'corestrictions') or table in ('bad_component_mukey', 'bad_chorizon_cokey', 'bad_chfrags_chkey', 'bad_chtexturegrp_chkey', 'bad_corestrictions_cokey'))):
                    raise SoilDataSourceError('Populated JSON cache has no verified retrieval history')
            return
        known = {'component', 'chorizon', 'chfrags', 'chtexturegrp', 'corestrictions',
                 'bad_component_mukey', 'bad_chorizon_cokey', 'bad_chfrags_chkey',
                 'bad_chtexturegrp_chkey', 'bad_corestrictions_cokey'}
        populated = any(conn.execute(f'SELECT 1 FROM "{table}" LIMIT 1').fetchone() is not None for table in tables & known)
        if populated and source.profile != 'legacy-xml':
            raise SoilDataSourceError('Cannot bind an unknown populated cache to a JSON source')
        binding = {'schema_version': 1, 'identity': source.identity(), 'historical_rows_unknown': populated}
        conn.execute('CREATE TABLE soil_data_source (singleton INTEGER PRIMARY KEY CHECK(singleton=1), binding TEXT NOT NULL)')
        conn.execute('CREATE TABLE soil_data_fetch (id INTEGER PRIMARY KEY, event TEXT NOT NULL)')
        conn.execute('INSERT INTO soil_data_source VALUES(1,?)', (json.dumps(binding, sort_keys=True),))


def record_fetch(conn, source, table, keys, records, observation=None):
    event = {'identity': source.identity(), 'observed_at': utc_now(), 'table': table,
             'key_count': len(keys), 'row_count': len(records),
             'processed_records_sha256': hashlib.sha256(json.dumps(records, sort_keys=True).encode()).hexdigest(),
             'response_origin': None}
    if observation:
        event.update(observation)
    conn.execute('INSERT INTO soil_data_fetch(event) VALUES(?)', (json.dumps(event, sort_keys=True),))


def cache_evidence(conn) -> dict:
    binding = json.loads(conn.execute('SELECT binding FROM soil_data_source WHERE singleton=1').fetchone()[0])
    events = [json.loads(row[0]) for row in conn.execute('SELECT event FROM soil_data_fetch ORDER BY id')]
    return {'binding': binding, 'fetches': events}


def write_artifact_provenance(path: str, evidence: dict) -> None:
    target = Path(path + '.provenance.json')
    evidence = dict(evidence, soil_sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest())
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', dir=target.parent, prefix='.soil-provenance-', delete=False) as stream:
            temporary = stream.name
            json.dump(evidence, stream, indent=2, sort_keys=True)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    finally:
        if temporary is not None and os.path.exists(temporary):
            os.unlink(temporary)


def read_artifact_provenance(path: str) -> dict:
    data = json.loads(Path(path + '.provenance.json').read_text())
    if data.get('soil_sha256') != hashlib.sha256(Path(path).read_bytes()).hexdigest():
        raise SoilDataSourceError('Soil provenance hash does not match the artifact')
    return data
