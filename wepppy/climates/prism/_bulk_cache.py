"""Immutable PRISM attempt data and atomically published cell references."""
from contextlib import contextmanager
import fcntl
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import re
import time
import uuid

import pandas as pd

from ._bulk_protocol import GRID_ID, SCHEMA, PrismCacheError, validate_frame
from ._bulk_transport import write_json


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    # Failed candidates remain visible; only the final name is a published entry.
    write_json(temporary, value)
    with temporary.open('rb') as fp:
        os.fsync(fp.fileno())
    os.replace(temporary, path)


class BulkCache:
    def __init__(self, root, *, lock_timeout=600):
        self.root = Path(root) / f'v{SCHEMA}' / GRID_ID
        self.lock_timeout = lock_timeout
        if not math.isfinite(lock_timeout) or lock_timeout <= 0:
            raise ValueError('lock_timeout must be positive')
        self.root.mkdir(parents=True, exist_ok=True)
        for folder in ('attempts', 'entries', 'locks'):
            (self.root / folder).mkdir(exist_ok=True)

    @contextmanager
    def lock(self, partition):
        with (self.root / 'locks' / f'{partition}.lock').open('a') as fp:
            deadline = time.monotonic() + self.lock_timeout
            while True:
                try:
                    fcntl.flock(fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.monotonic() >= deadline:
                        raise TimeoutError(f'PRISM cache lock timed out: {partition}')
                    time.sleep(min(.1, max(0, deadline-time.monotonic())))
            try:
                yield
            finally:
                fcntl.flock(fp, fcntl.LOCK_UN)

    def attempt(self):
        directory = self.root / 'attempts' / uuid.uuid4().hex
        directory.mkdir()
        return directory

    def load(self, cell, start, end, manifest, checked):
        partition = f'{start}_{end}'
        entry = self.root / 'entries' / partition / f'{cell.id}.json'
        if not entry.exists():
            return None
        try:
            meta = json.loads(entry.read_text())
            if (meta['schema'] != SCHEMA or meta['grid'] != GRID_ID or meta['cell'] != cell.id
                    or meta['start'] != str(start) or meta['end'] != str(end)
                    or not re.fullmatch('[a-f0-9]{32}', meta['attempt'])):
                raise ValueError('Cache identity mismatch')
            attempt = self.root / 'attempts' / meta['attempt']
            key = (meta['attempt'], meta['manifest_sha256'], meta['raw_sha256'])
            if key not in checked:
                if digest(attempt / 'manifest.json') != meta['manifest_sha256'] or digest(attempt / 'bulk.csv.gz') != meta['raw_sha256']:
                    raise ValueError('Source evidence checksum mismatch')
                checked[key] = json.loads((attempt / 'manifest.json').read_text())
            if checked[key] != manifest:
                return None
            path = attempt / f'{cell.id}.parquet'
            if digest(path) != meta['data_sha256']:
                raise ValueError('Climate checksum mismatch')
            frame = pd.read_parquet(path)
            validate_frame(frame, start, end)
            return frame, meta
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise PrismCacheError(f'Invalid PRISM cache entry {entry}: {exc}') from exc

    def stage(self, attempt, frames, raw, manifest, start, end):
        (attempt / 'bulk.csv.gz').write_bytes(gzip.compress(raw, mtime=0))
        write_json(attempt / 'manifest.json', manifest)
        common = dict(schema=SCHEMA, grid=GRID_ID, start=str(start), end=str(end),
                      attempt=attempt.name, manifest_sha256=digest(attempt / 'manifest.json'),
                      raw_sha256=digest(attempt / 'bulk.csv.gz'),
                      freshness='release_manifest_unchanged', sampling='nearest_native_cell',
                      units=dict(ppt='mm', tmin='degC', tmax='degC', tdmean='degC', soltotal='MJ/m2/day'),
                      provider_day='24 hours ending 12:00 UTC')
        entries = {}
        for cell, frame in frames.items():
            path = attempt / f'{cell}.parquet'
            frame.to_parquet(path)
            pd.testing.assert_frame_equal(pd.read_parquet(path), frame)
            entries[cell] = dict(common, cell=cell, data_sha256=digest(path),
                                 semantic_sha256=hashlib.sha256(frame.to_csv(float_format='%.10g').encode()).hexdigest())
        return entries

    def publish(self, entries, start, end):
        for cell, meta in entries.items():
            atomic_json(self.root / 'entries' / f'{start}_{end}' / f'{cell}.json', meta)
