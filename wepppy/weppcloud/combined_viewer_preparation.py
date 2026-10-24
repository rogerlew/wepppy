"""Explicit offline PCV-01 preparation; never invoked by a web request.

READONLY and source files remain unchanged. Inspect the run-local
combined-viewer-preparation directory for working/failed/complete evidence.
"""
from __future__ import annotations

from wepppy.query_engine.catalog_refresh import catalog_lifecycle_guard

import argparse
import hashlib
import json
import math
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

import pyarrow.parquet as pq

from wepppy.query_engine.activate import _build_catalog
from wepppy.wepp.interchange.watershed_loss_interchange import (
    run_wepp_watershed_loss_interchange, AVERAGE_FILENAMES, ALL_YEARS_FILENAMES,
)

STATE_DIR = 'combined-viewer-preparation'
COLUMNS = ('Runoff Volume', 'Subrunoff Volume', 'Baseflow Volume', 'Soil Loss',
           'Sediment Deposition', 'Sediment Yield', 'Hillslope Area',
           'Solub. React. Pollutant', 'Particulate Pollutant', 'Total Pollutant')


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


ALLOWED_OUTPUTS = frozenset(
    ['_query_engine/catalog.json'] + [f'wepp/output/interchange/{name}'
    for name in (*AVERAGE_FILENAMES.values(), *ALL_YEARS_FILENAMES.values())]
)


def writer_identity():
    """Content-address the actual Python writer and loaded native binary."""
    from wepppy.wepp.interchange import watershed_loss_interchange
    import wepppyo3
    root = Path(wepppyo3.__file__).parent
    binaries = sorted(root.rglob('*.so'))
    if not binaries:
        raise RuntimeError('Cannot identify the required native writer binary')
    return {'python_writer_sha256': digest(watershed_loss_interchange.__file__),
            'preparation_sha256': digest(__file__),
            'native_sha256': {str(p.relative_to(root)): digest(p) for p in binaries}}


def _validate_manifest(manifest):
    outputs = set(manifest['outputs'])
    if not outputs <= ALLOWED_OUTPUTS or outputs.intersection(manifest['sources']):
        raise ValueError('Manifest contains unowned output paths')


def _save(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')
    temporary.replace(path)


def _contained(base, relative):
    candidate = base / relative
    if candidate.is_symlink() or not candidate.resolve().is_relative_to(base):
        raise ValueError(f'Unsafe preparation path: {relative}')
    return candidate


def validate_average(source, parquet):
    """Independent readback of the last average Hill block, not annual rows."""
    text = source.read_text()
    marker = 'YEAR AVERAGE ANNUAL VALUES FOR WATERSHED'
    if marker not in text:
        raise ValueError('Expected legacy average annual LOSS section is absent')
    rows = {}
    for line in text.rsplit(marker, 1)[1].splitlines():
        values = line.split()
        if not values or values[0] != 'Hill':
            continue
        if len(values) != 12:
            raise ValueError('Unsupported average Hill columns; inspect source before conversion')
        row = [float(value.replace('D', 'E')) for value in values[2:]]
        if int(values[1]) in rows:
            raise ValueError('Duplicate average hillslope ID')
        rows[int(values[1])] = row
    table = pq.read_table(parquet)
    actual = table.to_pylist()
    if not rows or len(rows) != len(actual):
        raise ValueError('Average native/source row count differs')
    seen = set()
    for row in actual:
        identifier = row['wepp_id']
        if identifier in seen or identifier not in rows:
            raise ValueError('Native/source identifier mismatch')
        seen.add(identifier)
        for column, expected in zip(COLUMNS, rows[identifier]):
            value = row[column]
            if value is None or not math.isfinite(value) or value != expected:
                raise ValueError(f'Native/source value mismatch at {identifier}/{column}')
        if row['Hillslope Area'] <= 0:
            raise ValueError(f'Invalid area at {identifier}')
    return dict(rows=len(actual), min_area_ha=min(row['Hillslope Area'] for row in actual),
                max_area_ha=max(row['Hillslope Area'] for row in actual), comparison='exact source-decimal equality')


def _verify(base, entries):
    for relative, expected in entries.items():
        path = _contained(base, relative)
        if not path.is_file() or digest(path) != expected:
            raise ValueError(f'Changed or missing manifest file: {relative}')


def prepare(wd):
    with catalog_lifecycle_guard(wd):
        return _prepare_guarded(wd)


def _prepare_guarded(wd):
    base = Path(wd).resolve(strict=True)
    state = _contained(base, STATE_DIR)
    manifest_path = state / 'manifest.json'
    if state.exists():
        manifest = json.loads(manifest_path.read_text())
        _validate_manifest(manifest)
        if manifest['status'] != 'complete':
            raise RuntimeError('Previous preparation incomplete. Inspect evidence and use --rollback before retry.')
        _verify(base, manifest['sources'])
        _verify(base, manifest['outputs'])
        return manifest
    output_dir = _contained(base, 'wepp/output/interchange')
    catalog_path = _contained(base, '_query_engine/catalog.json')
    if catalog_path.exists() or output_dir.exists():
        raise FileExistsError('Refusing unknown existing interchange/catalog; inspect before preparation')
    source = _contained(base, 'wepp/output/loss_pw0.txt')
    geometry = _contained(base, 'dem/topaz/SUBCATCHMENTS.WGS.JSON')
    sources = list(base.glob('*.nodb')) + [source, geometry]
    for name in ('READONLY', 'PUBLIC'):
        if (base / name).exists():
            sources.append(base / name)
    hashes = {str(path.relative_to(base)): digest(_contained(base, path.relative_to(base))) for path in sources}
    state.mkdir()
    manifest = dict(version=1, status='working', created_at=datetime.now(timezone.utc).isoformat(),
                    sources=hashes, outputs={}, validation=None, writer=writer_identity())
    _save(manifest_path, manifest)
    try:
        stage = state / 'staging'
        stage.mkdir()
        shutil.copy2(source, stage / 'loss_pw0.txt')
        products = run_wepp_watershed_loss_interchange(stage)
        manifest['validation'] = validate_average(source, products['average_hill'])
        # Validate the actual retained geometry and legacy identifier mapping without mutating NoDb.
        watershed = json.loads((base / 'watershed.nodb').read_text())['_subs_summary']
        mapping = {int(top): int(row['wepp_id']) for top, row in watershed.items()}
        geometry_ids = [int(feature['properties']['TopazID']) for feature in json.loads(geometry.read_text())['features']]
        native_ids = pq.read_table(products['average_hill'], columns=['wepp_id']).column(0).to_pylist()
        if (set(geometry_ids) != set(mapping)
                or len(set(mapping.values())) != len(mapping) or set(mapping.values()) != set(native_ids)):
            raise ValueError('Geometry/NoDb/native hillslope join is incomplete')
        manifest['validation']['geometry_join'] = 'complete one-to-one'
        output_dir.mkdir(parents=True)
        for staged in products.values():
            target = output_dir / staged.name
            relative = str(target.relative_to(base))
            # Journal before atomic, exclusive publication; interruption leaves a whole file or none.
            manifest['outputs'][relative] = digest(staged)
            _save(manifest_path, manifest)
            os.link(staged, target)
        catalog = dict(version=1, generated_at=datetime.now(timezone.utc).isoformat(),
                       root=str(base), files=_build_catalog(base))
        catalog_path.parent.mkdir(exist_ok=True)
        staged_catalog = state / 'catalog.json'
        staged_catalog.write_text(json.dumps(catalog, indent=2) + '\n')
        manifest['outputs'][str(catalog_path.relative_to(base))] = digest(staged_catalog)
        _save(manifest_path, manifest)
        os.link(staged_catalog, catalog_path)
        _verify(base, hashes)
        _verify(base, manifest['outputs'])
        manifest['status'] = 'complete'
        _save(manifest_path, manifest)
        return manifest
    except Exception as exc:  # broad-except: Offline boundary records failure evidence and re-raises.
        # Offline operation boundary: retain failure evidence, then propagate the original failure.
        manifest['status'] = 'failed'
        manifest['error'] = f'{type(exc).__name__}: {exc}'
        _save(manifest_path, manifest)
        raise


def rollback(wd):
    with catalog_lifecycle_guard(wd):
        return _rollback_guarded(wd)


def _rollback_guarded(wd):
    base = Path(wd).resolve(strict=True)
    state = _contained(base, STATE_DIR)
    manifest = json.loads((state / 'manifest.json').read_text())
    _validate_manifest(manifest)
    _verify(base, manifest['sources'])
    present = {name: checksum for name, checksum in manifest['outputs'].items() if (base / name).exists()}
    _verify(base, present)
    for name in present:
        _contained(base, name).unlink()
    for relative in ('wepp/output/interchange', '_query_engine'):
        directory = _contained(base, relative)
        if directory.is_dir() and not any(directory.iterdir()):
            directory.rmdir()
    manifest['status'] = 'rolled_back'
    _save(state / 'manifest.json', manifest)
    # Keep provenance and failed staging; a new attempt starts only after an explicit evidence rename.
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_directory', nargs='+')
    parser.add_argument('--rollback', action='store_true')
    args = parser.parse_args()
    for wd in args.run_directory:
        result = rollback(wd) if args.rollback else prepare(wd)
        print(json.dumps(dict(run=Path(wd).name, status=result['status'], validation=result['validation'])), flush=True)


if __name__ == '__main__':
    main()
