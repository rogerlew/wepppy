"""Basin-derived preparation from retained local source assets; no network IO.

The same path produces project manifests for any eligible grid/key set. Network
delivery may supply these assets later without changing the local soil reader.
"""
from datetime import datetime, timezone
from contextlib import contextmanager
import json
import logging
import math
import os
from pathlib import Path
import uuid

import numpy as np
import rasterio
from redis.exceptions import LockError, RedisError
from rasterio.warp import transform_bounds
from rasterio.windows import Window, from_bounds

from . import rainfall_io as io
from .m1_inputs import companions, read_raster
from .soil_inputs import META, SOURCE_ID, _copy, _json_snapshot, dependency_state, prepared_sources
from .soil_snapshot import snapshot_cache, source_state, verify_snapshot

__all__ = ['prepare_local_sources', 'promote_local_sources']


@contextmanager
def _directory(path):
    """Pin a directory without following any symlink component."""
    path = Path(path).absolute()
    descriptor = os.open(path.anchor, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for component in path.parts[1:]:
            child = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        yield descriptor
    finally:
        os.close(descriptor)


def _inside(root, path):
    path = Path(path).absolute()
    if not path.is_relative_to(root) or '..' in path.parts or any(p.is_symlink() for p in (path, *path.parents)):
        io.fail('invalid_input', 'Source preparation paths must remain in this project')
    return path


def _keys(values, valid, domain):
    if np.any(values[valid] <= 0) or np.any(values[valid] != np.floor(values[valid])):
        io.fail('invalid_input', 'Original soil labels must be aligned positive integer MUKEYs')
    result, size = set(), 2
    # Bound incremental uniqueness instead of materializing all unique raster
    # labels first. Existing raster admission bounds the input array itself.
    for start in range(0, values.shape[0], 128):
        selected = values[start:start+128][valid[start:start+128] & domain[start:start+128]]
        for value in np.unique(selected):
            if value <= 0:
                continue
            if value != math.floor(value):
                io.fail('invalid_input', 'Original MUKEYs must be integer labels')
            key = str(int(value))
            if key not in result:
                size += len(json.dumps(key).encode())+1
                if size > io.MAX_TEXT:
                    io.fail('resource_limit', 'Encoded basin key list exceeds 1 MiB')
                result.add(key)
    return sorted(result, key=int)


def _retain(path, output, name, hashes, limit=512*1024*1024):
    if path is None:
        return None
    path = Path(path).absolute()
    expected = io.digest(path, limit)
    target = output/name
    _copy(path, target, expected, limit)
    hashes[str(path)] = expected
    if path.suffix.lower() in ('.tif', '.tiff'):
        for extra in companions(path):
            expected = io.digest(extra, 512*1024*1024)
            _copy(extra, Path(str(target)+'.msk'), expected, 512*1024*1024)
            hashes[str(extra)] = expected
    return target


def _thick_window(native, evidence, grid, output):
    # Enforce the existing self-contained native raster boundary before a
    # windowed GDAL read. The crop retains original native cells and encoding.
    _, _, native_grid = read_raster(native, continuous_missing=True,
                                    allowed_units=(None, '', 'inch', 'inches', 'in'))
    with rasterio.open(native) as ds:
        if evidence.get('grid') != native_grid or evidence.get('bounds') != list(ds.bounds):
            io.fail('provenance_mismatch', 'Native THICK asset differs from its preparation evidence')
        rows, cols = grid['shape']
        transform = rasterio.Affine(*grid['transform'])
        left, top = transform*(0,0)
        right, bottom = transform*(cols,rows)
        bounds = transform_bounds(grid['crs'], ds.crs, left, bottom, right, top)
        floating = from_bounds(*bounds, transform=ds.transform)
        col, row = math.floor(floating.col_off), math.floor(floating.row_off)
        end_col = math.ceil(floating.col_off+floating.width)
        end_row = math.ceil(floating.row_off+floating.height)
        if col < 0 or row < 0 or end_col > ds.width or end_row > ds.height:
            io.fail('missing_input', 'Retained native THICK asset does not cover this basin DEM extent')
        window = Window(col,row,end_col-col,end_row-row)
        values = ds.read(1, window=window, masked=True)
        profile = ds.profile.copy()
        profile.update(width=int(window.width), height=int(window.height), transform=ds.window_transform(window),
                       driver='GTiff', compress='deflate')
        with rasterio.Env(GDAL_TIFF_INTERNAL_MASK=True):
            with rasterio.open(output, 'w', **profile) as target:
                target.write(values.filled(ds.nodata if ds.nodata is not None else 0),1)
                target.write_mask((~np.ma.getmaskarray(values)).astype('uint8')*255)
                target.set_band_unit(1,'inch')
    with rasterio.open(output) as ds:
        result_grid = {'shape':list(ds.shape), 'crs':str(ds.crs), 'transform':list(ds.transform)[:6]}
        return result_grid, list(ds.bounds)


def prepare_local_sources(wd, dem, mask, *, collection_catalog=None, thick=None, thick_evidence=None):
    """Create a fresh verified candidate; do not replace the active input manifest.

    Catalog and native THICK evidence are existing project-contained raw source
    assets, not hand-authored per-basin key/window manifests. Keys and the crop
    are derived here. The returned receipt is not an activation authorization.
    """
    root = Path(wd).absolute()
    inputs = [_inside(root,p) for p in (dem,mask)]
    optional = [None if p is None else _inside(root,p) for p in (collection_catalog,thick,thick_evidence)]
    collection_catalog, thick, thick_evidence = optional
    if (thick is None) != (thick_evidence is None):
        io.fail('invalid_input', 'Native THICK and its evidence must be supplied together')
    labels, cache = root/'soils/ssurgo.tif', root/'soils/ssurgo_tabular_cache.sqlite'
    known = [*inputs, *[p for p in optional if p is not None], labels, cache, root/META]
    for p in tuple(known):
        if p.suffix.lower() in ('.tif', '.tiff'):
            known.append(Path(str(p)+'.msk'))
    state = dependency_state(known)
    parent = _inside(root, root/'postfire_debris_flow/source_preparation')
    parent.mkdir(parents=True, exist_ok=True)
    output = parent/uuid.uuid4().hex; output.mkdir()
    io.write_json(output/'incomplete.json', {'status':'incomplete'})
    retained = output/'sources'; retained.mkdir()
    hashes = {}
    dem_copy = _retain(inputs[0], retained, 'dem.tif', hashes)
    mask_copy = _retain(inputs[1], retained, 'mask.tif', hashes)
    _, _, grid = read_raster(dem_copy, target_grid=True)
    values, valid, mask_grid = read_raster(mask_copy, target_grid=True)
    domain = valid & (values > 0)
    if grid != mask_grid or grid['transform'][0] != 10 or not domain.any():
        io.fail('invalid_input', 'Source preparation requires a nonempty aligned 10 m basin')
    keys, primary_reason, snapshot = [], 'missing_primary_mapping', None
    if state[str(cache)] is not None:
        snapshot = snapshot_cache(cache, output/'cache_snapshot')
    if state[str(labels)] is not None:
        copied = _retain(labels, retained, 'original_mukey.tif', hashes)
        label_values, label_valid, label_grid = read_raster(copied, categorical=True)
        if label_grid != grid:
            io.fail('invalid_input', 'Original MUKEY grid differs from this basin')
        mapped = _keys(label_values, label_valid, domain)
        if snapshot is not None:
            keys = mapped
            primary_reason = 'unverified_collection' if keys else 'no_original_keys'
        else:
            primary_reason = 'missing_primary_cache'
    candidate = {'schema_version':1}
    catalog = _retain(collection_catalog, retained, 'collection_catalog.json', hashes, io.MAX_TEXT)
    if catalog is not None:
        record, catalog_hash = _json_snapshot(catalog)
        associations = record.get('collection_by_mukey')
        if (type(record.get('schema_version')) is not int or record['schema_version'] != 1 or not isinstance(associations,dict)
                or any(not isinstance(record.get(k),str) or not record[k].strip() for k in ('source','retrieved_at'))):
            io.fail('invalid_input', 'Malformed collection source catalog')
        if any(not isinstance(k,str) or not k.isascii() or not k.isdecimal() or int(k) <= 0
               or str(int(k)) != k or v not in ('SSURGO', 'STATSGO', 'STATSGO2')
               for k,v in associations.items()):
            io.fail('invalid_input', 'Malformed collection source catalog associations')
        verified = [key for key in keys if associations.get(key) == 'SSURGO']
        if verified:
            evidence = output/'primary_evidence.json'
            io.write_json(evidence, dict(schema_version=1, collection_by_mukey={k:'SSURGO' for k in verified},
                                        source=record['source'], retrieved_at=record['retrieved_at'], catalog_sha256=catalog_hash))
            candidate['primary'] = dict(collection='SSURGO', mukeys=verified,
                evidence=str(evidence.relative_to(root)), evidence_sha256=io.digest(evidence,io.MAX_TEXT))
            primary_reason = None
    native = _retain(thick, retained, 'native_asset.tif', hashes)
    native_evidence = _retain(thick_evidence, retained, 'native_evidence.json', hashes, io.MAX_TEXT)
    if native is not None:
        record, _ = _json_snapshot(native_evidence)
        if (type(record.get('schema_version')) is not int or record['schema_version'] != 1 or record.get('source_id') != SOURCE_ID
                or record.get('sha256') != hashes[str(thick)] or not isinstance(record.get('source'),str) or not record['source'].strip()):
            io.fail('provenance_mismatch', 'Native THICK source identity is unverified')
        window = output/'fallback_native.tif'
        window_grid, bounds = _thick_window(native, record, grid, window)
        window_hash = io.digest(window, io.MAX_PREDICTOR_BYTES)
        evidence = output/'fallback_evidence.json'
        io.write_json(evidence, dict(schema_version=1, source_id=SOURCE_ID, source=record['source'],
            sha256=window_hash, grid=window_grid, bounds=bounds, parent_sha256=record['sha256']))
        candidate['fallback'] = dict(path=str(window.relative_to(root)), sha256=window_hash,
            source_id=SOURCE_ID, units='inch', evidence=str(evidence.relative_to(root)),
            evidence_sha256=io.digest(evidence,io.MAX_TEXT))
    text_sources = {str(p) for p in (collection_catalog, thick_evidence) if p is not None}
    source_limits = {p:io.MAX_TEXT if p in text_sources else 512*1024*1024 for p in hashes}
    io.recheck(hashes, limits=source_limits)
    if dependency_state(state) != state:
        io.fail('source_changed', 'Basin source identity changed during preparation')
    if snapshot is not None and source_state(cache) != snapshot['source_state']:
        io.fail('source_changed', 'Basin cache changed during source preparation')
    io.write_json(output/'soil_sources.json', candidate)
    prepared_sources(root, metadata_path=output/'soil_sources.json')
    receipt = dict(schema_version=1, status='complete', project=str(root), grid=grid, mukeys=keys,
        primary_reason=primary_reason, fallback_reason=None if native is not None else 'missing_prepared_thick',
        dependency_state=state, sources_sha256=hashes, source_limits=source_limits,
        cache_identity=None if snapshot is None else {k:snapshot[k] for k in ('source_schema','source_state','logical_sha256')},
        candidate_sha256=io.digest(output/'soil_sources.json',io.MAX_TEXT),
        prepared_at=datetime.now(timezone.utc).isoformat())
    io.write_json(output/'receipt.json',receipt)
    (output/'incomplete.json').unlink()
    return output/'receipt.json'


def promote_local_sources(controller, receipt_path, *, expected_sha256, verify_project=None):
    """Verify outside the lock, then atomically install under the module lock."""
    root = Path(controller.wd).absolute()
    receipt_path = _inside(root, receipt_path)
    if receipt_path.name != 'receipt.json' or receipt_path.parent.parent != root/'postfire_debris_flow/source_preparation':
        io.fail('invalid_input', 'Expected this project source-preparation receipt')
    receipt_state = dependency_state([receipt_path])
    receipt, receipt_hash = _json_snapshot(receipt_path)
    if receipt_hash != expected_sha256:
        io.fail('provenance_mismatch', 'Source-preparation receipt changed')
    if type(receipt.get('schema_version')) is not int or receipt['schema_version'] != 1 or receipt.get('status') != 'complete' or receipt.get('project') != str(root):
        io.fail('invalid_input', 'Source-preparation receipt belongs to another project or is incomplete')
    state, hashes = receipt.get('dependency_state'), receipt.get('sources_sha256')
    if not isinstance(state,dict) or not state or not isinstance(hashes,dict) or not hashes:
        io.fail('invalid_input', 'Missing source-preparation identities')
    for path in set(state)|set(hashes):
        _inside(root,path)
    if str(root/META) not in state:
        io.fail('invalid_input', 'Missing previous input manifest identity')
    limits = receipt.get('source_limits')
    if (not isinstance(limits,dict) or set(limits) != set(hashes)
            or any(type(v) is not int or v not in (io.MAX_TEXT,512*1024*1024) for v in limits.values())):
        io.fail('invalid_input', 'Invalid source-preparation byte limits')
    io.recheck(hashes, limits=limits)
    if dependency_state(state) != state:
        io.fail('source_changed', 'Basin dependencies changed before source promotion')
    folder = receipt_path.parent
    candidate = folder/'soil_sources.json'
    candidate_state = dependency_state([candidate])
    if io.digest(candidate,io.MAX_TEXT) != receipt.get('candidate_sha256'):
        io.fail('provenance_mismatch', 'Prepared candidate changed')
    inventory = prepared_sources(root, metadata_path=candidate)
    artifact_state = dependency_state(inventory['files'])
    artifact_state.update(receipt_state)
    artifact_state.update(candidate_state)
    native_path = None if inventory['fallback'] is None else str(root/inventory['fallback']['path'])
    for path, expected in inventory['files'].items():
        if io.digest(path,io.MAX_PREDICTOR_BYTES if path == native_path else io.MAX_TEXT) != expected:
            io.fail('provenance_mismatch', 'Prepared source evidence or raster changed')
    if dependency_state(artifact_state) != artifact_state:
        io.fail('source_changed', 'Prepared artifacts changed during verification')
    cache = root/'soils/ssurgo_tabular_cache.sqlite'
    cache_identity = receipt.get('cache_identity')
    if cache_identity is not None:
        verify_snapshot(cache,cache_identity,folder/('recheck-'+uuid.uuid4().hex))
    staged = folder/('promotion-'+uuid.uuid4().hex+'.json')
    _copy(candidate,staged,receipt['candidate_sha256'])
    staged_state = dependency_state([staged])
    def install():
        nonlocal committed
        if verify_project is not None:
            verify_project()
        if dependency_state(state) != state or dependency_state(artifact_state) != artifact_state or dependency_state(staged_state) != staged_state:
            io.fail('source_changed', 'Source preparation changed before locked promotion')
        if cache_identity is not None and source_state(cache) != cache_identity['source_state']:
            io.fail('source_changed', 'Soil cache changed before locked promotion')
        destination = _inside(root,root/META)
        destination.parent.mkdir(parents=True,exist_ok=True)
        with _directory(staged.parent) as source_fd, _directory(destination.parent) as destination_fd:
            # A renamed/replaced pathname cannot redirect this write outside
            # the directory admitted above. Both sides use pinned descriptors.
            if dependency_state(staged_state) != staged_state:
                io.fail('source_changed', 'Staged source changed before atomic install')
            if not gate.owned():
                raise LockError('Source promotion mutation lease expired')
            controller._assert_lock_owned_for_dump()
            os.replace(staged.name,destination.name,src_dir_fd=source_fd,dst_dir_fd=destination_fd)
            committed = True
    # This transaction changes a file, not NoDb state. Like publication, take
    # the existing locks explicitly; change()/locked() would dump after commit.
    result = {'status':'committed', 'receipt':str(receipt_path), 'warnings':[]}
    committed = False
    def release(callback, name):
        try:
            callback()
        except (RedisError, RuntimeError) as exc:
            # Cleanup boundary: after rename, reporting failure invites an
            # unsafe retry. Preserve the committed outcome and surface cleanup.
            if not committed:
                raise
            warning = f'{name}_release_failed:{type(exc).__name__}'
            result['warnings'].append(warning)
            logging.getLogger(__name__).warning('Source promotion committed with cleanup warning: %s; receipt=%s',
                                                warning, receipt_path)
    gate = controller._mutation_gate()
    if not gate.acquire():
        raise LockError('Could not acquire source promotion mutation gate')
    try:
        controller = type(controller).getInstance(controller.wd)
        controller.lock()
        try:
            try:
                install()
            except OSError as exc:
                # Descriptor cleanup occurs after rename; preserve its commit
                # just as for lock cleanup, with an explicit warning outcome.
                if not committed:
                    raise
                warning = f'directory_release_failed:{type(exc).__name__}'
                result['warnings'].append(warning)
                logging.getLogger(__name__).warning('Source promotion committed with cleanup warning: %s; receipt=%s',
                                                    warning, receipt_path)
        finally:
            release(controller.unlock, 'nodb')
    finally:
        release(gate.release, 'mutation_gate')
    return result
