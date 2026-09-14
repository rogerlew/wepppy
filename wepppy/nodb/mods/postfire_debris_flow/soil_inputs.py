"""Prepared-local M3 soil provenance and cellwise recorded-depth composition.

No acquisition, soil builders, substitutions or shared cache writes.
"""
import csv
import hashlib
import json
import os
from pathlib import Path

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.warp import reproject

from . import rainfall_io as io
from .m1_inputs import companions, read_raster, prepare
from .soil_policy import POLICY
from .soil_snapshot import prepare_soil_tables, source_state

__all__ = ['prepared_sources', 'prepare_soil', 'dependency_state']
SOURCE_ID = 'USGS-675721b9d34e5c5dfd05c575-THICK'
META = 'postfire_debris_flow/inputs/soil_sources.json'


def _path(root, relative):
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute() or '..' in Path(relative).parts:
        io.fail('invalid_input', 'Expected project-relative soil source path')
    return io.regular(root/relative, 512*1024*1024)


def _key(value):
    return isinstance(value, str) and value.isascii() and value.isdecimal() and int(value) > 0 and str(int(value)) == value


def _json_snapshot(path):
    with io.open_local(path, io.MAX_TEXT) as stream:
        raw = stream.read(io.MAX_TEXT+1)
    if len(raw) > io.MAX_TEXT:
        io.fail('resource_limit', 'Soil metadata exceeds byte limit')
    try:
        value = json.loads(raw, object_pairs_hook=io._pairs, parse_float=io._json_float,
                           parse_constant=lambda _: io.fail('invalid_input', 'Nonfinite soil metadata'))
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise io.RainfallError('invalid_input', 'Malformed soil metadata') from exc
    if not isinstance(value, dict):
        io.fail('invalid_input', 'Soil metadata must be an object')
    return value, hashlib.sha256(raw).hexdigest()


def prepared_sources(wd, *, metadata_path=None):
    """Validate only bounded local metadata; never decode rasters in preflight."""
    root = Path(wd).absolute()
    path = root/META if metadata_path is None else Path(metadata_path).absolute()
    if not path.is_relative_to(root):
        io.fail('invalid_input', 'Soil metadata must remain inside this project')
    if not path.exists() and not path.is_symlink():
        return {'primary': None, 'fallback': None, 'files': {}, 'metadata': None}
    m, metadata_hash = _json_snapshot(path)
    if set(m)-{'schema_version', 'primary', 'fallback'} or (m and (type(m.get('schema_version')) is not int or m['schema_version'] != 1)):
        io.fail('invalid_input', 'Invalid soil source metadata schema')
    result = {'primary': None, 'fallback': None, 'metadata': m, 'files': {str(path): metadata_hash}}
    for kind in ('primary', 'fallback'):
        entry = m.get(kind)
        if entry is None:
            continue
        fields = {'collection', 'mukeys', 'evidence', 'evidence_sha256'} if kind == 'primary' else {'path', 'sha256', 'source_id', 'units', 'evidence', 'evidence_sha256'}
        if not isinstance(entry, dict) or not fields <= entry.keys() or not io.hash_value(entry['evidence_sha256']):
            io.fail('invalid_input', 'Malformed populated soil source')
        evidence_path = _path(root, entry['evidence'])
        evidence, evidence_hash = _json_snapshot(evidence_path)
        if evidence_hash != entry['evidence_sha256']:
            io.fail('provenance_mismatch', 'Soil evidence hash mismatch')
        if type(evidence.get('schema_version')) is not int or evidence['schema_version'] != 1:
            io.fail('invalid_input', 'Invalid soil evidence schema')
        result['files'][str(evidence_path)] = entry['evidence_sha256']
        if kind == 'primary':
            keys, associations = entry['mukeys'], evidence.get('collection_by_mukey')
            if (entry['collection'] != 'SSURGO' or not isinstance(keys, list) or not keys
                    or not all(_key(k) for k in keys) or len(set(keys)) != len(keys)
                    or not isinstance(associations, dict) or any(not _key(k) or v != 'SSURGO' for k,v in associations.items())
                    or any(associations.get(k) != 'SSURGO' for k in keys)
                    or any(not isinstance(evidence.get(k), str) or not evidence[k].strip() for k in ('source', 'retrieved_at'))):
                io.fail('missing_provenance', 'Primary keys require explicit SSURGO collection evidence')
        else:
            if entry['source_id'] != SOURCE_ID or entry['units'] != 'inch' or not io.hash_value(entry['sha256']):
                io.fail('missing_provenance', 'Expected original USGS THICK in inches')
            native = _path(root, entry['path'])
            if native.suffix.lower() not in ('.tif', '.tiff'):
                io.fail('invalid_input', 'THICK must be a local GeoTIFF')
            if (evidence.get('source_id') != SOURCE_ID or evidence.get('sha256') != entry['sha256']
                    or not isinstance(evidence.get('grid'), dict) or not isinstance(evidence.get('bounds'), list)
                    or not isinstance(evidence.get('source'), str) or not evidence['source'].strip()):
                io.fail('missing_provenance', 'THICK preparation evidence must bind source, hash, grid and bounds')
            result['files'][str(native)] = entry['sha256']
        result[kind] = {**entry, 'evidence_record': evidence}
    return result


def _copy(source, target, expected, limit=io.MAX_TEXT):
    before = io.regular(source, limit).stat()
    if io.digest(source, limit) != expected:
        io.fail('provenance_mismatch', 'Prepared soil source hash mismatch')
    with io.open_local(source, limit) as incoming, target.open('xb') as outgoing:
        opened = os.fstat(incoming.fileno())
        fields = ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
        if any(getattr(before, key) != getattr(opened, key) for key in fields):
            io.fail('source_changed', 'Soil source descriptor identity changed before copy')
        size = 0
        for block in iter(lambda: incoming.read(1024*1024), b''):
            size += len(block)
            if size > limit:
                io.fail('resource_limit', 'Soil source grew beyond copy byte limit')
            outgoing.write(block)
    if io.digest(target, limit) != expected or io.digest(source, limit) != expected:
        io.fail('source_changed', 'Prepared soil source changed while copying')


def dependency_state(paths):
    result = {}
    for value in paths:
        path = Path(value).absolute()
        if '..' in path.parts or any(p.is_symlink() for p in (path, *path.parents)):
            io.fail('invalid_input', 'Unsafe soil dependency path')
        try:
            info = path.stat()
        except FileNotFoundError:
            result[str(path)] = None
            continue
        io.regular(path, 512*1024*1024)
        result[str(path)] = [info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns]
    return result


def prepare_soil(wd, output, grid, domain):
    """Retain source evidence and choose primary, then THICK, per basin cell."""
    root, output = Path(wd).absolute(), Path(output).absolute()
    cache = root/'soils/ssurgo_tabular_cache.sqlite'
    observed = dependency_state([root/META, cache, root/'soils/ssurgo.tif', root/'soils/ssurgo.tif.msk',
                                 root/'soils/ssurgo.tif.meta', root/'soils/ssurgo_tabular_cache.sqlite.meta.md'])
    if cache.exists() or cache.is_symlink():
        manifest = prepare_soil_tables(cache, output, finalize=False)
    else:
        if '..' in output.parts or any(p.is_symlink() for p in (output, *output.parents)):
            io.fail('invalid_input', 'Unsafe soil output')
        output.mkdir()
        io.write_json(output/'incomplete.json', {'status': 'incomplete', 'policy': POLICY})
        manifest = dict(schema_version=1, status='complete', policy=POLICY, units='cm',
                        source_schema={}, source_state=None, logical_sha256={}, artifacts_sha256={},
                        counts={'components': 0, 'horizons': 0, 'mapunits': 0})
        for name, columns in (
            ('components_source.csv', 'mukey,cokey,compname,comppct_r'),
            ('horizons_source.csv', 'cokey,chkey,hzname,hzdept_r,hzdepb_r,hzthk_r,desgnmaster'),
            ('components.csv', 'mukey,cokey,compname,comppct_r,thickness_cm,status,reason_codes,horizon_count,source_row_count,interval_sum_cm,interval_union_cm,deepest_bottom_cm,reported_thickness_conflicts,pair_reductions'),
            ('mapunits.csv', 'mukey,mean_cm,known_percentage,valid_percentage,nonsoil_percentage,rejected_percentage,unreported_percentage,status,reason_codes')):
            with (output/name).open('x') as stream:
                stream.write(columns+'\n')
            manifest['artifacts_sha256'][name] = io.digest(output/name)
    inventory = prepared_sources(root)
    for path, state in dependency_state(inventory['files']).items():
        observed.setdefault(path, state)
    raster_companions = {}
    copies = output/'sources'; copies.mkdir()
    if inventory['metadata'] is not None:
        _copy(root/META, copies/'soil_sources.json', inventory['files'][str(root/META)])
    thickness = np.full(domain.shape, np.nan, dtype=np.float64)
    source = np.full(domain.shape, 255, dtype=np.uint8); source[domain] = 0
    primary = inventory['primary']
    if primary is not None:
        _copy(root/primary['evidence'], copies/'primary_evidence.json', primary['evidence_sha256'])
    retrieval = root/'soils/ssurgo_tabular_cache.sqlite.meta.md'
    if retrieval.exists() or retrieval.is_symlink():
        expected = io.digest(retrieval, io.MAX_TEXT)
        _copy(retrieval, copies/'cache_retrieval.meta.md', expected)
        inventory['files'][str(retrieval)] = expected
    labels = root/'soils/ssurgo.tif'
    label_metadata = root/'soils/ssurgo.tif.meta'
    if label_metadata.exists() or label_metadata.is_symlink():
        expected = io.digest(label_metadata, io.MAX_TEXT)
        _copy(label_metadata, copies/'soil_raster.meta', expected)
        inventory['files'][str(label_metadata)] = expected
    if labels.exists() or labels.is_symlink():
        io.regular(labels, 512*1024*1024)
        raster_companions[str(labels)] = companions(labels)
        for p in (labels, *raster_companions[str(labels)]):
            expected = io.digest(p, 512*1024*1024)
            inventory['files'][str(p)] = expected
            suffix = '.msk' if p != labels else ''
            _copy(p, copies/('original_mukey.tif'+suffix), expected, 512*1024*1024)
        values, valid, label_grid = read_raster(copies/'original_mukey.tif', categorical=True)
        if label_grid != grid or np.any(valid & ((values <= 0) | (values != np.floor(values)))):
            io.fail('invalid_input', 'Original soil labels must be aligned positive integer MUKEYs')
        if primary is not None and manifest['source_state'] is not None:
            with (output/'mapunits.csv').open() as stream:
                means = {r['mukey']: float(r['mean_cm']) for r in csv.DictReader(stream) if r['mean_cm']}
            for key in primary['mukeys']:
                if key in means:
                    use = domain & valid & (values == int(key))
                    thickness[use] = means[key]; source[use] = 1
    fallback = inventory['fallback']
    if fallback is not None:
        native = root/fallback['path']
        raster_companions[str(native)] = companions(native)
        if raster_companions[str(native)]:
            io.fail('invalid_input', 'Prepared native THICK must be self-contained')
        _copy(native, copies/'fallback_native.tif', fallback['sha256'], 512*1024*1024)
        _copy(root/fallback['evidence'], copies/'fallback_evidence.json', fallback['evidence_sha256'])
        values, valid, native_grid = read_raster(copies/'fallback_native.tif', continuous_missing=True,
                                                allowed_units=(None, '', 'inch', 'inches', 'in'))
        with rasterio.open(copies/'fallback_native.tif') as ds:
            bounds = list(ds.bounds)
        evidence = fallback['evidence_record']
        if evidence['grid'] != native_grid or evidence['bounds'] != bounds:
            io.fail('provenance_mismatch', 'THICK native grid/bounds differ from preparation evidence')
        aligned = np.full(domain.shape, np.nan, dtype=np.float64)
        reproject(np.where(valid & (values >= 0), values, np.nan), aligned,
                  src_transform=rasterio.Affine(*native_grid['transform']), src_crs=native_grid['crs'], src_nodata=np.nan,
                  dst_transform=rasterio.Affine(*grid['transform']), dst_crs=grid['crs'], dst_nodata=np.nan,
                  resampling=Resampling.nearest)
        use = domain & (source == 0) & np.isfinite(aligned) & (aligned >= 0)
        thickness[use] = aligned[use]*2.54; source[use] = 2
    usable = domain & (source != 0)
    prepare(output/'thickness_cm.tif', thickness, usable, grid)
    with rasterio.open(output/'source.tif', 'w', driver='GTiff', height=domain.shape[0], width=domain.shape[1],
                       count=1, dtype='uint8', nodata=255, crs=grid['crs'],
                       transform=rasterio.Affine(*grid['transform']), compress='deflate') as ds:
        ds.write(source, 1)
    for path, expected in inventory['files'].items():
        if io.digest(path, 512*1024*1024) != expected:
            io.fail('source_changed', 'Soil composition input changed')
    if dependency_state(observed) != observed or any(companions(Path(path)) != names for path,names in raster_companions.items()):
        io.fail('source_changed', 'Soil dependency presence or identity changed')
    if manifest['source_state'] is not None and source_state(cache) != manifest['source_state']:
        io.fail('source_changed', 'Soil cache changed during raster composition')
    manifest.update(grid=grid, sources_sha256=inventory['files'], dependency_state=observed,
                    absent_sources=[k for k in ('primary', 'fallback') if inventory[k] is None],
                    source_cells={k: int(np.count_nonzero(source == v)) for k,v in
                                  (('primary',1),('fallback',2),('unavailable',0),('outside',255))})
    for p in (output/'thickness_cm.tif', output/'source.tif', *copies.iterdir()):
        manifest['artifacts_sha256'][str(p.relative_to(output))] = io.digest(p, io.MAX_PREDICTOR_BYTES)
    io.write_json(output/'manifest.json', manifest)
    (output/'incomplete.json').unlink()
    return manifest
