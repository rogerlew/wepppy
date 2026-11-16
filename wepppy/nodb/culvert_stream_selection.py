"""Versioned culvert stream candidates and auditable per-run selection (ADR-0144)."""
from __future__ import annotations

from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import tempfile

import numpy as np
import rasterio
from rasterio.warp import transform
from rasterio.windows import Window
from whitebox_tools import WhiteboxTools

POLICY = 'stream_selection_policy.json'
MANIFEST = 'stream_candidates.json'
RECEIPT = 'stream_selection.json'


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, 'w') as handle:
            json.dump(value, handle, indent=2, allow_nan=False)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def read_json(path: Path) -> dict:
    value = json.loads(path.read_text())
    if not isinstance(value, dict) or value.get('version') != 1:
        raise ValueError(f'Invalid stream selection metadata: {path}')
    return value


def has_policy(root: Path) -> bool:
    if (root / POLICY).exists():
        read_json(root / POLICY)
        return True
    if (root / MANIFEST).exists() or any((root / 'runs').glob(f'*/{RECEIPT}')):
        raise ValueError('Stream selection metadata exists without policy intent')
    return False


def digest(path: Path) -> str:
    with path.open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def artifact(root: Path, path: Path) -> dict:
    return {'path': str(path.relative_to(root)), 'sha256': digest(path)}


def resolve(root: Path, entry: dict, *, verify: bool = False) -> Path:
    relative = Path(entry['path'])
    path = (root / relative).resolve()
    if relative.is_absolute() or not path.is_relative_to(root.resolve()):
        raise ValueError('Stream artifact path escapes batch')
    if not path.is_file():
        raise FileNotFoundError(path)
    if verify and digest(path) != entry['sha256']:
        raise ValueError(f'Stream artifact identity changed: {relative}')
    return path


def grid(path: Path) -> tuple:
    with rasterio.open(path) as ds:
        return ds.width, ds.height, ds.transform, ds.crs


def grid_record(path: Path) -> dict:
    with rasterio.open(path) as ds:
        return {'width': ds.width, 'height': ds.height,
                'transform': list(ds.transform)[:6], 'crs': str(ds.crs)}


def ready_manifest(root: Path) -> dict:
    manifest = read_json(root / MANIFEST)
    if manifest.get('state') != 'ready':
        raise ValueError('Stream candidates are not ready')
    count = manifest.get('starting_passes')
    candidates = manifest.get('candidates')
    if type(count) is not int or count < 0 or not isinstance(candidates, list):
        raise ValueError('Invalid stream candidate list')
    if [c.get('passes') for c in candidates] != list(range(count, -1, -1)):
        raise ValueError('Incomplete stream candidate ladder')
    reference = None
    for candidate in candidates:
        for key in ('streams', 'junctions'):
            value = grid(resolve(root, candidate[key]))
            if reference is not None and value != reference:
                raise ValueError('Stream candidate grid mismatch')
            reference = value
    if manifest.get('grid') != grid_record(resolve(root, candidates[0]['streams'])):
        raise ValueError('Stream manifest grid metadata mismatch')
    if manifest.get('generation_policy') != 'strahler-v1-short-length-2cells-zero-original':
        raise ValueError('Unknown stream candidate generation policy')
    return manifest


def _prepare(root: Path, pointer: Path, short_streams: Path, original: Path, count: int, *, dem: Path | None = None) -> None:
    """Generate all candidates before child admission; ready candidates are immutable."""
    if not has_policy(root):
        raise ValueError('Missing stream policy intent')
    inputs = {key: artifact(root, path) for key, path in
              [('pointer', pointer), ('original', original)]}
    if dem is not None:
        inputs['dem'] = artifact(root, dem)
    if (root / MANIFEST).exists() and read_json(root / MANIFEST).get('state') == 'ready':
        manifest = ready_manifest(root)
        if manifest['starting_passes'] != count or manifest.get('inputs') != inputs:
            raise ValueError('Cannot change prepared stream policy on retry')
        for c in manifest['candidates']:
            for key in ('streams', 'junctions'):
                resolve(root, c[key], verify=True)
        return
    if any((root / 'runs').glob(f'*/{RECEIPT}')):
        raise ValueError('Cannot rebuild candidates referenced by run receipts')
    manifest = {'version': 1, 'state': 'preparing', 'starting_passes': count, 'inputs': inputs,
                'grid': grid_record(original),
                'generation_policy': 'strahler-v1-short-length-2cells-zero-original'}
    write_json(root / MANIFEST, manifest)
    work = root / 'topo/stream_candidates'
    work.mkdir(parents=True, exist_ok=True)
    wbt = WhiteboxTools(verbose=False, raise_on_error=True)
    wbt.set_working_dir(str(work))
    # This boundary retains the preparation state; exceptions still propagate.
    try:
        order = work / 'order.tif'
        if count:
            wbt.strahler_stream_order(str(pointer), str(short_streams), str(order))
        candidates = []
        for passes in range(count + 1):
            directory = work / f'pass_{passes}'
            directory.mkdir(exist_ok=True)
            streams = original if passes == 0 else directory / 'streams.tif'
            if passes:
                with rasterio.open(order) as src:
                    profile = src.profile.copy()
                    profile.update(dtype='uint8', nodata=0)
                    with rasterio.open(streams, 'w', **profile) as dst:
                        for _, window in src.block_windows(1):
                            values = src.read(1, window=window, masked=True)
                            dst.write(np.ma.filled(values > passes, False).astype('uint8'), 1, window=window)
            junctions = directory / 'junctions.tif'
            wbt.stream_junction_identifier(str(pointer), str(streams), str(junctions))
            if grid(streams) != grid(junctions) or grid(streams) != grid(original):
                raise ValueError('Generated candidate grid mismatch')
            candidates.append({'passes': passes, 'streams': artifact(root, streams),
                               'junctions': artifact(root, junctions)})
        manifest.update(state='ready', candidates=list(reversed(candidates)))
        write_json(root / MANIFEST, manifest)
    except Exception as exc:  # broad-except: persist preparation failure and re-raise
        # Preparation boundary: never publish partial candidates as usable.
        write_json(root / MANIFEST, dict(manifest, state='failed', error=type(exc).__name__))
        raise


def _select(root: Path, run: Path, point_id: str, xy: tuple, point_crs: str, mask: Path) -> tuple[str, str]:
    if not has_policy(root):
        raise ValueError('Missing stream selection policy')
    manifest = ready_manifest(root)
    receipt_path = run / RECEIPT
    if receipt_path.exists():
        receipt = read_json(receipt_path)
        if (receipt.get('state') != 'selected' or receipt.get('point_id') != point_id
                or receipt.get('point') != list(xy) or receipt.get('point_crs') != point_crs):
            raise ValueError('Invalid or failed stream selection receipt')
        candidate = next((c for c in manifest['candidates'] if c['passes'] == receipt.get('selected_passes')), None)
        if candidate is None or candidate != receipt.get('candidate'):
            raise ValueError('Stream selection receipt does not match manifest')
        return tuple(str(resolve(root, candidate[k], verify=True)) for k in ('streams', 'junctions'))
    attempted = []
    for candidate in manifest['candidates']:
        streams = resolve(root, candidate['streams'], verify=True)
        resolve(root, candidate['junctions'], verify=True)
        coverage = False
        with rasterio.open(streams) as src, rasterio.open(mask) as target:
            if grid(streams) != grid(mask):
                raise ValueError('Selection mask grid mismatch')
            xs, ys = transform(point_crs, src.crs, [xy[0]], [xy[1]])
            row, col = src.index(xs[0], ys[0])
            intersects = False
            if 0 <= row < src.height and 0 <= col < src.width:
                value = src.read(1, window=Window(col, row, 1, 1), masked=True)
                intersects = bool(np.ma.filled(value > 0, False).any())
            if intersects:
                for _, window in target.block_windows(1):
                    inside = np.ma.filled(target.read(1, window=window, masked=True) > 0, False)
                    if inside.any() and np.any(inside & np.ma.filled(src.read(1, window=window, masked=True) > 0, False)):
                        coverage = True
                        break
        reason = 'selected' if intersects and coverage else 'point_off_stream' if not intersects else 'no_watershed_coverage'
        attempted.append({'passes': candidate['passes'], 'reason': reason})
        receipt = {'version': 1, 'point_id': point_id, 'starting_passes': manifest['starting_passes'],
                   'point': list(xy), 'point_crs': point_crs, 'cell': [row, col], 'attempted': attempted}
        if intersects and coverage:
            paths = tuple(str(resolve(root, candidate[k], verify=True)) for k in ('streams', 'junctions'))
            write_json(receipt_path, dict(receipt, state='selected', selected_passes=candidate['passes'], candidate=candidate))
            return paths
    write_json(receipt_path, dict(receipt, state='failed'))
    raise ValueError(f'No stream candidate retains culvert Point_ID {point_id}')


def prepare(root: Path, pointer: Path, short_streams: Path, original: Path, count: int, *, dem: Path | None = None) -> None:
    # Shared batch filesystem lock serializes candidate publication across workers.
    with (root / '.stream_candidates.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        _prepare(root, pointer, short_streams, original, count, dem=dem)


def select(root: Path, run: Path, point_id: str, xy: tuple, point_crs: str, mask: Path) -> tuple[str, str]:
    run.mkdir(parents=True, exist_ok=True)
    with (run / '.stream_selection.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        return _select(root, run, point_id, xy, point_crs, mask)


@contextmanager
def topology_lock(root: Path):
    """Cover shared topology mutation as well as candidate publication."""
    with (root / '.stream_topology.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield


def reuse_ready(root: Path) -> bool:
    if not (root / MANIFEST).exists():
        if any((root / 'runs').glob(f'*/{RECEIPT}')):
            raise ValueError('Run receipts reference missing stream candidates')
        return False
    manifest = read_json(root / MANIFEST)
    if manifest.get('state') != 'ready':
        if any((root / 'runs').glob(f'*/{RECEIPT}')):
            raise ValueError('Run receipts reference incomplete stream candidates')
        return False
    ready_manifest(root)
    for entry in manifest['inputs'].values():
        resolve(root, entry, verify=True)
    return True
