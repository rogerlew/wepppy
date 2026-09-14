"""Stable, read-only raw soil snapshots; no builders or source acquisition."""
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import sqlite3
import stat

from .soil_policy import POLICY, derive_recorded_mapunits
from .soil_thickness import _key, _read_tables
from .rainfall_io import open_local

__all__ = ['snapshot_cache', 'prepare_soil_tables', 'verify_snapshot', 'source_state']
MAX_BYTES = 512 * 1024 * 1024
MAX_TABLE_BYTES = 64 * 1024 * 1024


def source_state(path):
    path = Path(path).absolute()
    if '..' in path.parts or any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('Unsafe soil source path')
    journal = Path(str(path)+'-journal')
    if journal.exists() or journal.is_symlink():
        # Main-file bytes can contain uncommitted spilled pages. Replaying or
        # deleting a rollback journal would mutate upstream state; reject it.
        raise ValueError('Rollback journal present; soil source snapshot is unavailable')
    result = {}
    for suffix in ('', '-wal', '-shm'):
        candidate = Path(str(path)+suffix)
        try:
            info = candidate.lstat()
        except FileNotFoundError:
            if not suffix:
                raise
            result[suffix or 'main'] = None
            continue
        if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_BYTES:
            raise ValueError('Soil source must be a bounded regular file')
        result[suffix or 'main'] = [info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns]
    return result


def _logical(rows):
    return hashlib.sha256(json.dumps(_hashable(rows), sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode('utf-8')).hexdigest()


def _hashable(value):
    if isinstance(value, float) and not math.isfinite(value):
        return {'nonfinite_number': str(value)}
    if isinstance(value, dict):
        return {key: _hashable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_hashable(item) for item in value]
    return value


def _copy_source(source, target, expected):
    # O_NOFOLLOW closes the final-component symlink race. Original identities
    # bracket copying and reading; never open the shared source with SQLite.
    with open_local(source, MAX_BYTES) as incoming, target.open('xb') as outgoing:
        info = os.fstat(incoming.fileno())
        if [info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns] != expected:
            raise ValueError('Soil source changed before copy')
        size = 0
        for block in iter(lambda: incoming.read(1024*1024), b''):
            size += len(block)
            if size > MAX_BYTES:
                raise ValueError('Soil source exceeds copy byte limit')
            outgoing.write(block)


def snapshot_cache(path, output):
    """Bracket one committed-WAL read transaction with file identities."""
    path = Path(path).absolute()
    before = source_state(path)
    output = Path(output).absolute()
    if '..' in output.parts or any(p.is_symlink() for p in (output, *output.parents)):
        raise ValueError('Unsafe soil snapshot output path')
    output.mkdir()
    _write_json(output/'incomplete.json', {'status': 'incomplete', 'source_state': before})
    copied = output/'cache.sqlite'
    for suffix in ('', '-wal'):
        expected = before[suffix or 'main']
        if expected is not None:
            _copy_source(Path(str(path)+suffix), Path(str(copied)+suffix), expected)
    schema = {}
    connection = sqlite3.connect(copied.as_uri()+'?mode=ro', uri=True, timeout=5)
    try:
        connection.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, MAX_TABLE_BYTES)
        connection.execute('PRAGMA query_only=ON')
        connection.execute('PRAGMA trusted_schema=OFF')
        connection.enable_load_extension(False)
        connection.execute('BEGIN')
        components, horizons = _read_tables(connection, allow_empty=True,
                                            max_table_bytes=MAX_TABLE_BYTES, source_schema=schema)
        connection.rollback()
    finally:
        connection.close()
    after = source_state(path)
    if after != before:
        raise ValueError('Soil source changed during snapshot')
    # Sort without normalizing source values; preserve their original types.
    components.sort(key=lambda r: (str(r['cokey']), _logical(r)))
    horizons.sort(key=lambda r: (str(r['chkey']), _logical(r)))
    result = dict(components=components, horizons=horizons, source_schema=schema,
                source_state=after, logical_sha256={'component': _logical(components),
                                                   'chorizon': _logical(horizons)})
    _write_json(output/'manifest.json', {key: value for key, value in result.items()
                                       if key not in ('components', 'horizons')})
    (output/'incomplete.json').unlink()
    return result


def verify_snapshot(path, snapshot, output):
    """Reject drift; callers must also compare source_state at final acceptance."""
    current = snapshot_cache(path, output)
    if any(current[key] != snapshot[key] for key in ('source_schema', 'source_state', 'logical_sha256')):
        raise ValueError('Soil source changed after snapshot')


def _write_csv(path, rows, columns):
    with path.open('x', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: json.dumps(value, sort_keys=True, allow_nan=False)
                             if isinstance(value, (dict, list)) else value for key, value in row.items()})


def _write_json(path, data):
    with path.open('x') as stream:
        json.dump(data, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


def prepare_soil_tables(path, output, *, finalize=True):
    """Retain raw and derived tables in a fresh visible attempt directory."""
    output = Path(output).absolute()
    if '..' in output.parts or any(p.is_symlink() for p in (output, *output.parents)):
        raise ValueError('Unsafe soil output path')
    output.mkdir()
    _write_json(output/'incomplete.json', {'status': 'incomplete', 'policy': POLICY})
    snapshots = output/'snapshots'
    snapshots.mkdir()
    snapshot = snapshot_cache(path, snapshots/'initial')
    for table, filename in (('components', 'components_source.csv'), ('horizons', 'horizons_source.csv')):
        columns = (('mukey', 'cokey', 'compname', 'comppct_r') if table == 'components' else
                   ('cokey', 'chkey', 'hzname', 'hzdept_r', 'hzdepb_r', 'hzthk_r', 'desgnmaster'))
        rows = [{key: _key(value) if key in ('mukey', 'cokey', 'chkey') else value
                 for key, value in row.items()} for row in snapshot[table]]
        rows.sort(key=lambda row: (row['cokey'], row.get('chkey', '')))
        _write_csv(output/filename, rows, columns)
    components, mapunits = derive_recorded_mapunits(snapshot['components'], snapshot['horizons'])
    component_columns = ('mukey', 'cokey', 'compname', 'comppct_r', 'thickness_cm', 'status',
                         'reason_codes', 'horizon_count', 'source_row_count', 'interval_sum_cm',
                         'interval_union_cm', 'deepest_bottom_cm', 'reported_thickness_conflicts', 'pair_reductions')
    mapunit_columns = ('mukey', 'mean_cm', 'known_percentage', 'valid_percentage', 'nonsoil_percentage',
                       'rejected_percentage', 'unreported_percentage', 'status', 'reason_codes')
    _write_csv(output/'components.csv', components, component_columns)
    _write_csv(output/'mapunits.csv', mapunits, mapunit_columns)
    verify_snapshot(path, snapshot, snapshots/'recheck')
    hashes = {}
    for name in ('components_source.csv', 'horizons_source.csv', 'components.csv', 'mapunits.csv'):
        with (output/name).open('rb') as stream:
            hashes[name] = hashlib.file_digest(stream, 'sha256').hexdigest()
    manifest = dict(schema_version=1, status='complete', policy=POLICY, units='cm',
                    source_schema=snapshot['source_schema'], source_state=snapshot['source_state'],
                    logical_sha256=snapshot['logical_sha256'], artifacts_sha256=hashes,
                    counts={'components': len(components), 'horizons': len(snapshot['horizons']),
                            'mapunits': len(mapunits)})
    if finalize:
        _write_json(output/'manifest.json', manifest)
        (output/'incomplete.json').unlink()
    return manifest
