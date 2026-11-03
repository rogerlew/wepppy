"""Declare/acquire seven development materials with the owned SSURGO collection.

No source soil build, controller, or native execution is part of this helper.
Run `declare` first; `acquire` requires the immutable declaration and review receipt.
"""
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
import argparse
import hashlib
import json
import math
import os
import re
import signal
import sqlite3
import sys
import time
import xml.etree.ElementTree as ET

import requests
import wepppy.soils.ssurgo.ssurgo as ssurgo

ART = Path(__file__).resolve().parent
ROOT = Path('/wc1/runs/ro/roads-parameterization-program-20261103/retention-source-v1')
PROTOCOL = ART / 'resumption-r7-retention-acquisition-protocol.md'
DESIGN = ART / 'design-v2.json'
MUKEYS = (1718465, 1718494, 1718510, 1856573, 2711184, 2711250, 53949)
TABLES = ('component', 'chorizon', 'corestrictions', 'chfrags', 'chtexturegrp')
PARENT = dict(component='mukey', chorizon='cokey', corestrictions='cokey', chfrags='chkey', chtexturegrp='chkey')
FETCH = {table: getattr(ssurgo, '_fetch_components' if table == 'component' else '_fetch_' + table) for table in TABLES}
MAX_BYTES = 10_000_000
MAX_ROWS = dict(component=200, chorizon=2000, corestrictions=10000, chfrags=10000, chtexturegrp=10000)


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def read(path):
    return json.loads(path.read_text())


def now():
    return datetime.now(timezone.utc).isoformat()


def owned_query(table, keys):
    """Exercise the unchanged owned query constructor, without transport."""
    captured = []
    def capture(query):
        captured.append(query)
        return b'<NewDataSet/>'
    with patch.object(ssurgo, '_make_sda_post_request', capture):
        FETCH[table](keys)
    if len(captured) != 1:
        raise ValueError('Unexpected owned query construction')
    return captured[0]


def dependencies():
    paths = {Path(__file__).resolve(), PROTOCOL, DESIGN, Path(ssurgo.__file__).resolve()}
    prefixes = ('wepppy', 'requests', 'urllib3', 'sqlite3', '_sqlite3', 'xml', 'ssl', '_ssl', 'http', 'urllib')
    for name, module in tuple(sys.modules.items()):
        location = getattr(module, '__file__', None)
        if location and any(name == prefix or name.startswith(prefix + '.') for prefix in prefixes):
            path = Path(location).resolve()
            if path.is_file():
                paths.add(path)
    return {str(path): sha(path) for path in sorted(paths)}


def verify_dependencies(bindings):
    for name, value in bindings.items():
        if sha(name) != value:
            raise ValueError('Acquisition dependency drift: ' + name)


def declare(root=ROOT):
    withheld = {int(row['mukey']) for row in read(DESIGN)['withheld_validation']}
    if set(MUKEYS) & withheld:
        raise ValueError('Withheld material overlap')
    empty = ssurgo.SurgoSoilCollection([])
    try:
        schemas = {table: empty.conn.execute('SELECT sql FROM sqlite_master WHERE name=?', (table,)).fetchone()[0]
                   for table in TABLES}
    finally:
        empty._disconnect()
    root.mkdir(parents=True, exist_ok=False)
    save(root / 'declaration.json', dict(schema='roads-retention-acquisition-declaration-v1',
        created_utc=now(), root=str(root.resolve()), requested_mukeys=list(MUKEYS), excluded_mukeys=sorted(withheld),
        endpoint=ssurgo._ssurgo_url, tables=list(TABLES), query_templates={table: owned_query(table, [0]) for table in TABLES},
        owned_table_schemas=schemas, dependencies=dependencies(), uid=os.getuid(), gid=os.getgid(),
        max_response_bytes=MAX_BYTES, max_rows=MAX_ROWS, total_deadline_seconds=600,
        owned_timeout_seconds=30, owned_max_attempts=ssurgo._SSURGO_MAX_RETRIES,
        safe_response_headers=['Date', 'Content-Type'], source_builds=0, native_calls=0,
        scope='One sequential seven-material cohort; not an atomic SDA snapshot or retention efficacy result'))
    print(json.dumps(dict(declared=str(root), declaration_sha256=sha(root / 'declaration.json'), network_requests=0)))


def number_or_text(value):
    """Independently reproduce owned scalar conversion; never zero-fill nulls."""
    if value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError, OverflowError):
        return value
    if not math.isfinite(numeric):
        raise ValueError('Nonfinite source token')
    try:
        return int(value)
    except (TypeError, ValueError, OverflowError):
        return numeric


def projection(raw, query):
    """Validate the SDA envelope and retain ordered original tokens and nulls."""
    if b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():
        raise ValueError('XML declarations outside the expected SDA format')
    root = ET.fromstring(raw)
    schema_tag = '{http://www.w3.org/2001/XMLSchema}schema'
    if root.tag != 'NewDataSet' or any(child.tag not in (schema_tag, 'Table') for child in root):
        raise ValueError('Unexpected SDA response envelope')
    schemas = root.findall(schema_tag)
    if len(schemas) != 1:
        raise ValueError('Missing or duplicate SDA schema')
    fields = [field.strip().split('.')[-1] for field in query.split('FROM', 1)[0].removeprefix('SELECT ').split(',')]
    namespace = {'xs': 'http://www.w3.org/2001/XMLSchema'}
    sequence = schemas[0].find('.//xs:element[@name="Table"]/xs:complexType/xs:sequence', namespace)
    if sequence is None or [element.get('name') for element in sequence] != fields:
        raise ValueError('SDA projection schema differs from the owned query')
    tokens = []
    for row in root.findall('Table'):
        if [child.tag for child in row] != fields or any(child.attrib or len(child) for child in row):
            raise ValueError('Omitted/reordered/structured source column cannot satisfy the owned positional extractor')
        tokens.append([child.text for child in row])
    return fields, tokens, [[number_or_text(value) for value in row] for row in tokens]


def reduce_rows(table, rows):
    seen, reduced = set(), []
    for row in rows:
        identity = tuple(row[:2]) if table in ('component', 'chorizon') else row[0]
        if identity not in seen:
            seen.add(identity)
            reduced.append(row)
    return reduced


class Recorder:
    """Single-process transport recorder; owned query/extraction/retry code runs."""
    def __init__(self, root, declaration, transport):
        self.root, self.declaration, self.transport = root, declaration, transport
        self.accepted = {}
        self.attempts = defaultdict(int)
        self.records = []
        (root / 'requests').mkdir()
        (root / 'normalized').mkdir()

    def keys_for(self, table):
        if table == 'component':
            return set(MUKEYS)
        source = self.accepted['component' if table in ('chorizon', 'corestrictions') else 'chorizon']['rows']
        return {row[1] for row in source}

    def __call__(self, url, *, data, headers, timeout):
        query = data['query']
        match = re.search(r'\bFROM\s+(\w+).*\bWHERE\s+(?:component\.)?(\w+)\s+IN\s*\(\s*([\d,\s]+)\)', query)
        if not match or match[1] not in TABLES:
            raise ValueError('Unexpected source query')
        table = match[1]
        keys = [int(token.strip()) for token in match[3].split(',')]
        expected_table = TABLES[len(self.accepted)] if len(self.accepted) < len(TABLES) else None
        if (table != expected_table or match[2] != PARENT[table] or len(keys) != len(set(keys))
                or set(keys) != self.keys_for(table) or query != owned_query(table, keys)):
            raise ValueError('Query order/projection/parent boundary differs from owned collection')
        if (url != self.declaration['endpoint'] or data != {'query': query, 'format': 'xml'}
                or timeout != 30 or headers != {'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8'}):
            raise ValueError('Owned transport contract drift')
        self.attempts[table] += 1
        if self.attempts[table] > self.declaration['owned_max_attempts']:
            raise ValueError('Owned retry bound exceeded')
        stem = f'{len(self.records)+1:02d}-{table}-attempt-{self.attempts[table]}'
        query_path = self.root / 'requests' / (stem + '.sql')
        query_path.write_text(query)
        record = dict(table=table, attempt=self.attempts[table], query_path=str(query_path.relative_to(self.root)),
            query_sha256=sha(query_path), requested_parent_keys=keys, requested_utc=now(), endpoint=url,
            status=None, safe_response_headers={}, error_class=None, response_valid=False)
        started = time.monotonic()
        try:
            response = self.transport(url, data=data, headers=headers, timeout=timeout)
            raw = response.content
            record.update(status=response.status_code, received_utc=now(),
                safe_response_headers={name: response.headers[name] for name in ('Date', 'Content-Type') if name in response.headers},
                response_bytes=len(raw), response_sha256=hashlib.sha256(raw).hexdigest(),
                body_complete=len(raw) <= MAX_BYTES)
            raw_path = self.root / 'requests' / (stem + '.xml')
            raw_path.write_bytes(raw[:MAX_BYTES])
            record.update(raw_path=str(raw_path.relative_to(self.root)), raw_sha256=sha(raw_path))
            if len(raw) > MAX_BYTES:
                raise ValueError('Response exceeds declared post-read retention bound')
            if response.status_code != 200:
                return response  # The unchanged owned request code raises its normal error.
            fields, tokens, rows = projection(raw, query)
            if len(rows) > MAX_ROWS[table] or any(row[0] not in set(keys) for row in rows):
                raise ValueError('Source cardinality/parent identity violation')
            if table == 'component' and {row[0] for row in rows} != set(MUKEYS):
                raise ValueError('Incomplete requested material coverage')
            if table == 'chorizon':
                owners = {row[1]: row[0] for row in self.accepted['component']['rows']}
                if {owners[row[0]] for row in rows} != set(MUKEYS):
                    raise ValueError('A requested material lacks horizon support')
            reduced = reduce_rows(table, rows)
            normalized = dict(fields=fields, raw_tokens=tokens, rows=rows, reduced_rows=reduced,
                requested_parent_keys=keys, missing_parent_keys=sorted(set(keys) - {row[0] for row in rows}))
            normalized_path = self.root / 'normalized' / (table + '.json')
            save(normalized_path, normalized)
            record.update(response_valid=True, raw_rows=len(rows), reduced_rows=len(reduced),
                normalized_path=str(normalized_path.relative_to(self.root)), normalized_sha256=sha(normalized_path))
            self.accepted[table] = normalized
            return response
        except Exception as exc:
            # Deliberate HTTP-observation boundary: retain class/status, never
            # stringify a request/response exception that may embed headers/body.
            record['error_class'] = type(exc).__name__
            raise
        finally:
            record.update(finished_utc=now(), elapsed_seconds=time.monotonic()-started)
            save(self.root / 'requests' / (stem + '.json'), record)
            self.records.append(record)


def compare_cache(root, declaration, records):
    """Reparse raw receipts independently of owned extractors and recorder rows."""
    cache = root / 'collection.sqlite'
    if any(Path(str(cache) + suffix).exists() for suffix in ('-wal', '-shm')):
        raise ValueError('Cache not finalized without WAL/SHM')
    actual = sqlite3.connect(f'file:{cache.resolve()}?mode=ro&immutable=1', uri=True)
    expected = sqlite3.connect(':memory:')
    tables, represented = {}, set()
    try:
        if actual.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('Finalized SQLite integrity failure')
        for table in TABLES:
            matches = [record for record in records if record['table'] == table and record['response_valid']]
            if len(matches) != 1:
                raise ValueError('Missing or repeated accepted source table')
            record = matches[0]
            query_path, raw_path = root / record['query_path'], root / record['raw_path']
            if sha(query_path) != record['query_sha256'] or sha(raw_path) != record['raw_sha256']:
                raise ValueError('Raw source receipt drift')
            fields, tokens, rows = projection(raw_path.read_bytes(), query_path.read_text())
            reduced = reduce_rows(table, rows)
            normalized = read(root / record['normalized_path'])
            if (sha(root / record['normalized_path']) != record['normalized_sha256']
                    or normalized['fields'] != fields or normalized['raw_tokens'] != tokens
                    or normalized['rows'] != rows or normalized['reduced_rows'] != reduced):
                raise ValueError('Raw-to-normalized source mismatch')
            sql = declaration['owned_table_schemas'][table]
            if actual.execute('SELECT sql FROM sqlite_master WHERE name=?', (table,)).fetchone()[0] != sql:
                raise ValueError('Owned cache schema drift')
            expected.execute(sql)
            if reduced:
                expected.executemany(f'INSERT INTO {table} VALUES ({",".join("?" for _ in fields)})', reduced)
            # Scratch SQLite applies the frozen schema's real type affinity;
            # numeric-looking TEXT and nonnumeric REAL values are preserved.
            wanted = expected.execute(f'SELECT * FROM {table} ORDER BY rowid').fetchall()
            got = actual.execute(f'SELECT * FROM {table} ORDER BY rowid').fetchall()
            typed = lambda values: [[(type(value).__name__, value) for value in row] for row in values]
            if typed(wanted) != typed(got):
                raise ValueError('Normalized source rows differ from finalized cache: ' + table)
            missing = sorted(set(record['requested_parent_keys']) - {row[0] for row in reduced})
            bad = [row[0] for row in actual.execute(f'SELECT {PARENT[table]} FROM bad_{table}_{PARENT[table]} ORDER BY {PARENT[table]}')]
            # Owned _sync returns early for an entirely empty response; no bad
            # rows are inserted in that case. Report the gap without filling it.
            if bad != (missing if reduced else []):
                raise ValueError('Missing-parent cache records disagree: ' + table)
            tables[table] = dict(raw_rows=len(rows), cached_rows=len(got), reduced_rows=len(reduced),
                missing_parent_keys=missing, cached_bad_parent_keys=bad,
                empty_response_early_return=not reduced,
                ordered_cache_rows_sha256=hashlib.sha256(json.dumps(typed(got), separators=(',', ':')).encode()).hexdigest())
            if table == 'component':
                represented = {row[0] for row in got}
        if represented != set(MUKEYS):
            raise ValueError('Finalized cohort differs from all seven requested materials')
        return dict(passed=True, cache=dict(path='collection.sqlite', sha256=sha(cache), integrity='ok',
                    journal_mode=actual.execute('PRAGMA journal_mode').fetchone()[0]),
                    represented_mukeys=sorted(represented), tables=tables)
    finally:
        actual.close()
        expected.close()


def deadline(*_):
    raise TimeoutError('Declared acquisition deadline')


def acquire(root=ROOT):
    declaration_path = root / 'declaration.json'
    declaration = read(declaration_path)
    review = read(root / 'execution-review.json')
    if (declaration['root'] != str(root.resolve()) or declaration['requested_mukeys'] != list(MUKEYS)
            or review['declaration_sha256'] != sha(declaration_path)
            or review['implementation_review_pass'] is not True or review['scientific_review_pass'] is not True):
        raise ValueError('Declared cohort/review identity mismatch')
    verify_dependencies(declaration['dependencies'])
    verify_dependencies(review['files'])
    if (os.getuid(), os.getgid()) != (declaration['uid'], declaration['gid']):
        raise ValueError('Declared service identity mismatch')
    cache = root / 'collection.sqlite'
    if cache.exists():
        raise ValueError('Acquisition requires a fresh cache')
    save(root / 'acquisition-start.json', dict(started_utc=now(), declaration_sha256=sha(declaration_path),
         execution_review_sha256=sha(root / 'execution-review.json')))
    recorder = Recorder(root, declaration, requests.post)
    collection = ssurgo.SurgoSoilCollection.__new__(ssurgo.SurgoSoilCollection)
    collection.conn = collection.cur = None
    error_class, association = None, None
    old_handler = signal.signal(signal.SIGALRM, deadline)
    signal.setitimer(signal.ITIMER_REAL, declaration['total_deadline_seconds'])
    try:
        with patch.object(ssurgo.requests, 'post', recorder):
            collection.__init__(MUKEYS, cache_db_path=str(cache))
        collection.conn.commit()
        checkpoint = collection.conn.execute('PRAGMA wal_checkpoint(TRUNCATE)').fetchone()
        if checkpoint[0] != 0:
            raise ValueError('SQLite checkpoint blocked')
        if collection.conn.execute('PRAGMA journal_mode=DELETE').fetchone()[0] != 'delete':
            raise ValueError('Could not finalize SQLite journal')
        collection._disconnect()
        association = compare_cache(root, declaration, recorder.records)
        verify_dependencies(declaration['dependencies'])
        save(root / 'cache-association.json', association)
    except Exception as exc:
        # Deliberate acquisition-receipt boundary; preserve failures and never
        # promote partial source acquisition or expose exception response text.
        error_class = type(exc).__name__
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old_handler)
        collection._disconnect()
    # The final receipt is written last. Bind every earlier cohort artifact,
    # including cache metadata, review/start receipts and any failed WAL files.
    artifacts = {str(path.relative_to(root)): sha(path)
                 for path in sorted(root.rglob('*')) if path.is_file()}
    success = error_class is None and association is not None and association['passed']
    result = dict(schema='roads-retention-acquisition-v1', passed=success, source_association_valid=success,
        finished_utc=now(), error_class=error_class, declaration_sha256=sha(declaration_path),
        requested_mukeys=list(MUKEYS), represented_mukeys=association['represented_mukeys'] if success else [],
        cache_sha256=sha(cache) if cache.exists() else None,
        association_sha256=sha(root / 'cache-association.json') if success else None,
        requests=recorder.records, artifacts=artifacts, source_builds=0, native_calls=0,
        cohort_scope='Sequential source cohort, not atomic SDA snapshot; source vintage is separate from policy effect')
    save(root / 'acquisition.json', result)
    print(json.dumps(dict(passed=success, receipt=str(root / 'acquisition.json'), receipt_sha256=sha(root / 'acquisition.json'))))
    if not success:
        raise SystemExit('Acquisition failed; retain receipt and partial files for review')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('declare', 'acquire'))
    args = parser.parse_args()
    {'declare': declare, 'acquire': acquire}[args.action]()
