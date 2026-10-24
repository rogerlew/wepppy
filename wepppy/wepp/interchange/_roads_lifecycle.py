"""Current Roads publication and replacement; roads-preparation-lifecycle-contract.md."""
from __future__ import annotations

from contextlib import ExitStack, contextmanager
from contextvars import ContextVar
import fcntl
from functools import wraps
import inspect
import json
import os
from pathlib import Path
import shutil
import stat
from uuid import uuid4

POLICY = 'roads_current_v1'
LOCK = 'roads.lifecycle.lock'
OUTPUT = Path('wepp/roads/output')
SEGMENTS = Path('wepp/roads/segments')
RUNS = Path('wepp/roads/runs')
HISTORY = Path('wepp/roads/history')
RECEIPT = OUTPUT / 'roads.current.json'
CACHE = Path('wepp/reports/cache')
CACHE_KEY = 'hillslope_watbal_summary_roads'
COMMON = ('H.pass.parquet', 'ebe_pw0.parquet', 'README.md')
CONTINUOUS = ('H.wat.parquet', 'loss_pw0.out.parquet', 'loss_pw0.hill.parquet',
              'loss_pw0.chn.parquet', 'totalwatsed3.parquet', 'roads_segment_loss_summary.parquet')
_INVALIDATED = ContextVar('roads_lifecycle_invalidated', default=frozenset())
_WRITERS = ContextVar('roads_lifecycle_writers', default=frozenset())


class RoadsResultsUnavailable(RuntimeError):
    code = 'roads_results_unavailable'

    def __init__(self, message='Run Roads to generate current results.'):
        super().__init__(message)


class RoadsOperationBusy(RuntimeError):
    code = 'roads_operation_busy'


def _path(root: Path, relative: str | Path) -> Path:
    relative = Path(relative)
    if relative.is_absolute() or '..' in relative.parts:
        raise ValueError(f'Invalid Roads lifecycle path: {relative}')
    path = root / relative
    if path.resolve() != root.resolve() / relative:
        raise ValueError(f'Roads lifecycle path alias: {relative}')
    return path


def current_path(relative: str | Path) -> bool:
    parts = Path(relative).parts
    if '..' in parts:
        raise ValueError('Invalid Roads path traversal')
    if parts[:3] == ('wepp', 'roads', 'history'):
        return False
    return (parts[:3] == ('wepp', 'roads', 'output') or
            (parts[:3] == ('wepp', 'reports', 'cache') and len(parts) > 3 and
             (parts[3] in (CACHE_KEY+'.parquet', CACHE_KEY+'.meta.json', CACHE_KEY+'.attempts'))))


def path_owner(path: str | Path) -> Path | None:
    """Find the project owning a physical current-result path, excluding history."""
    path = Path(path).absolute()
    parts = path.parts
    if '..' in parts:
        # External boundaries reject traversal; physical classification still
        # runs on resolved sources without replacing their existing 400/403.
        return None
    # Stop at the outer Roads history namespace; its nested layout is diagnostic.
    for i in range(len(parts)-2):
        if parts[i:i+3] == ('wepp', 'roads', 'history'):
            return None
        if current_path(Path(*parts[i:])):
            return Path(*parts[:i])
    return None


@contextmanager
def operation(root: str | Path, *, shared=False, create=False):
    root = Path(root).resolve()
    if root in _WRITERS.get():
        yield
        return
    # Writers acquire catalog before Roads. Readers retain concurrent SH admission
    # and take only short catalog barriers: writer EX is nonblocking, so a reader
    # holding Roads cannot deadlock behind a writer holding catalog ownership.
    from wepppy.query_engine.catalog_refresh import catalog_lifecycle_guard
    with ExitStack() as guards:
        if not shared:
            try:
                guards.enter_context(catalog_lifecycle_guard(root, blocking=False))
            except BlockingIOError as exc:
                raise RoadsOperationBusy('Roads is busy; wait for the active operation to finish.') from exc
        lock_path = _path(root, LOCK)
        try:
            fd = os.open(lock_path, (os.O_RDONLY if shared and not create else os.O_RDWR | os.O_CREAT) | os.O_NOFOLLOW, 0o666)
        except FileNotFoundError as exc:
            if shared:
                raise RoadsResultsUnavailable() from exc
            raise
        token = None
        try:
            if not stat.S_ISREG(os.fstat(fd).st_mode) or os.fstat(fd).st_nlink != 1:
                raise ValueError('Invalid Roads coordination file')
            try:
                fcntl.flock(fd, (fcntl.LOCK_SH if shared else fcntl.LOCK_EX) | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                error = RoadsResultsUnavailable if shared else RoadsOperationBusy
                raise error('Roads is busy; wait for the active operation to finish.') from exc
            if not shared:
                token = _WRITERS.set(_WRITERS.get() | {root})
            yield
        finally:
            if token is not None:
                _WRITERS.reset(token)
            os.close(fd)


def mandatory_paths(single_storm: bool) -> set[str]:
    return {str(OUTPUT/'interchange'/name) for name in COMMON + (() if single_storm else CONTINUOUS)}


def _validate_receipt(root: Path, payload: dict) -> list[str]:
    if not isinstance(payload, dict) or set(payload) != {'policy', 'is_single_storm', 'required_relpaths'} or payload.get('policy') != POLICY or type(payload.get('is_single_storm')) is not bool:
        raise RoadsResultsUnavailable('Prepare and run Roads again; current result receipt is invalid.')
    paths = payload.get('required_relpaths')
    if (not isinstance(paths, list) or not paths or any(not isinstance(p, str) for p in paths)
            or len(set(paths)) != len(paths) or not mandatory_paths(payload['is_single_storm']).issubset(paths)):
        raise RoadsResultsUnavailable('Roads result receipt has incomplete required resources.')
    optional = [OUTPUT/'interchange/chnwb.parquet']
    ledger = SEGMENTS/'roads.accounting.json'
    if (root/ledger).exists():
        optional.append(ledger)
        if not payload['is_single_storm']:
            optional.append(OUTPUT/'interchange/H.accounting.wat.parquet')
    if any(str(p) not in paths for p in optional if p != OUTPUT/'interchange/chnwb.parquet' or (root/p).exists()):
        raise RoadsResultsUnavailable('Roads receipt omits produced report resources.')
    for relative in paths:
        if not _path(root, relative).is_file():
            raise RoadsResultsUnavailable(f'Roads result resource is missing: {relative}')
        with _path(root, relative).open('rb') as stream:
            stream.read(1)
    return paths


def require_current(root: str | Path) -> dict:
    root = Path(root).resolve()
    try:
        payload = json.loads(_path(root, RECEIPT).read_text())
        _validate_receipt(root, payload)
    except (OSError, ValueError, TypeError) as exc:
        raise RoadsResultsUnavailable('Prepare and run Roads again; current results are unavailable.') from exc
    return payload


@contextmanager
def current_read(root: str | Path):
    root = Path(root).resolve()
    if root in _WRITERS.get():
        yield
        return
    with operation(root, shared=True):
        require_current(root)
        yield


def available(root: str | Path) -> bool:
    try:
        with current_read(root):
            return True
    except RoadsResultsUnavailable:
        return False


@contextmanager
def read_paths(paths):
    owners = set()
    for path in paths:
        lexical = Path(path).absolute()
        resolved = lexical.resolve()
        owner = path_owner(lexical)
        if owner is not None and owner.resolve() / lexical.relative_to(owner) != resolved:
            raise RoadsResultsUnavailable('Current Roads source cannot alias another resource.')
        owners.update(root.resolve() for root in (owner, path_owner(resolved)) if root is not None)
    with ExitStack() as stack:
        for owner in sorted(owners):
            stack.enter_context(current_read(owner))
        yield


def _copy_parents(root: Path, snapshot: Path, relative: Path):
    for parent in reversed(relative.parents):
        if parent == Path('.'):
            continue
        target = snapshot / parent
        if not target.exists():
            target.mkdir()
            source = _path(root, parent)
            if source.exists():
                shutil.copystat(source, target)


def retain(root: str | Path, *, replace_segments=False) -> Path | None:
    """Move current outputs out of admission before any replacement writes."""
    root = Path(root).resolve()
    if root not in _WRITERS.get():
        raise RuntimeError('Roads retention requires the operation guard')
    relatives = [OUTPUT, RUNS, SEGMENTS]
    relatives += [CACHE/(CACHE_KEY+suffix) for suffix in ('.parquet', '.meta.json', '.attempts')]
    existing = [p for p in relatives if _path(root, p).exists()]
    if not existing:
        _INVALIDATED.set(_INVALIDATED.get() | {root})
        return None
    linked_files = []
    snapshot_mode = stat.S_IMODE((root / 'wepp/roads').stat().st_mode)
    for relative in existing:
        source = _path(root, relative)
        if source.is_dir():
            for item in source.rglob('*'):
                if item.is_symlink():
                    target = item.resolve(strict=True)
                    if not target.is_file() or not target.is_relative_to(root):
                        raise ValueError(f'Unowned Roads retention link: {item}')
                    linked_files.append((item.relative_to(root), target))
                    # A copied link must not bypass restricted target ancestry.
                    for parent in target.parents:
                        if parent == root:
                            break
                        snapshot_mode &= stat.S_IMODE(parent.stat().st_mode)
    history = _path(root, HISTORY)
    history.mkdir(parents=True, exist_ok=True)
    snapshot = history / uuid4().hex
    snapshot.mkdir(mode=0o700)
    retained_links = []
    for relative, target in linked_files:
        candidate = snapshot / ('.retained-link-' + uuid4().hex)
        shutil.copy2(target, candidate)
        retained_links.append((relative, candidate))
    # Copy preparation context first. A failed copy aborts before output admission changes.
    if SEGMENTS in existing:
        _copy_parents(root, snapshot, SEGMENTS)
        shutil.copytree(root/SEGMENTS, snapshot/SEGMENTS, symlinks=True)
    for relative in existing:
        if relative == SEGMENTS:
            continue
        _copy_parents(root, snapshot, relative)
        os.rename(_path(root, relative), snapshot/relative)
        _INVALIDATED.set(_INVALIDATED.get() | {root})
    _INVALIDATED.set(_INVALIDATED.get() | {root})
    if replace_segments and SEGMENTS in existing:
        # The retained copy has the original permissions/content; remove only after retention.
        shutil.rmtree(_path(root, SEGMENTS))
    elif SEGMENTS in existing:
        for name in ('roads.segment.pass.manifest.json', 'roads.accounting.json'):
            _path(root, SEGMENTS/name).unlink(missing_ok=True)
    for relative, candidate in retained_links:
        os.replace(candidate, snapshot / relative)
    snapshot.chmod(snapshot_mode)
    return snapshot


def segment_ids(features):
    if not isinstance(features, list):
        raise ValueError('Prepared Roads features must be a list')
    ids = []
    for feature in features:
        properties = feature.get('properties') if isinstance(feature, dict) else None
        value = properties.get('segment_id') if isinstance(properties, dict) else None
        if not isinstance(value, str) or not value.strip():
            raise ValueError('Prepared Roads segment IDs must be nonempty strings')
        ids.append(value)
    if len(set(ids)) != len(ids):
        raise ValueError('Duplicate prepared Roads segment ID')
    return ids


def _validate_generated_set(root, payload):
    paths = _validate_receipt(root, payload)
    import pyarrow.parquet as pq
    for relative in paths:
        if relative.endswith('.parquet'):
            for batch in pq.ParquetFile(_path(root, relative)).iter_batches():
                batch.validate(full=True)
    manifest_path = _path(root, SEGMENTS/'roads.segment.pass.manifest.json')
    records = json.loads(manifest_path.read_text())
    geometry = json.loads(_path(root, SEGMENTS/'roads.inslope.monotonic.geojson').read_text())
    ids = segment_ids(geometry['features'])
    profile_ids = set()
    for record in records:
        if record.get('status', 'completed') != 'completed':
            continue
        profile = record['segment_run_id']
        if not isinstance(profile, (int, str)) or isinstance(profile, bool) or not str(profile).strip():
            raise ValueError('Modeled Roads profile ID is invalid')
        if profile in profile_ids:
            raise ValueError('Duplicate modeled Roads profile ID')
        profile_ids.add(profile)
        if record.get('design') != 'outslope_unrutted_remainder' and record['segment_id'] not in ids:
            raise ValueError('Roads profile has no prepared geometry')
    if (root / SEGMENTS / 'roads.accounting.json').exists():
        from wepppy.wepp.interchange.roads_accounting import accounting_source, load
        if payload['is_single_storm']:
            load(root)
        else:
            accounting_source(root)


def publish(root: str | Path, resources: dict, *, single_storm: bool):
    root = Path(root).resolve()
    if root not in _WRITERS.get():
        raise RuntimeError('Only the full Roads operation may publish current results')
    payload = {'policy': POLICY, 'is_single_storm': single_storm,
               'required_relpaths': resources['required_relpaths']}
    _validate_generated_set(root, payload)
    destination = _path(root, RECEIPT)
    candidate = destination.with_name(f'roads.current.pending-{uuid4().hex}.json')
    with candidate.open('x') as stream:
        json.dump(payload, stream, sort_keys=True)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(candidate, destination)


def mutation(function):
    @wraps(function)
    def wrapped(self, *args, **kwargs):
        with operation(self.wd):
            if (Path(self.wd) / 'READONLY').exists():
                raise PermissionError('Cannot modify Roads in a readonly project.')
            # Reject a stale controller before touching any artifacts. Dump retains
            # the authoritative check under its own persistence lock as well.
            from wepppy.nodb.base import NoDbStaleWriteError
            expected = (getattr(self, '_nodb_mtime', None), getattr(self, '_nodb_size', None))
            if expected != (None, None):
                observed = os.stat(self._nodb)
                if expected != (observed.st_mtime, observed.st_size):
                    raise NoDbStaleWriteError('Reload Roads before modifying a changed project.')
            token = _INVALIDATED.set(frozenset())
            succeeded = False
            try:
                result = function(self, *args, **kwargs)
                succeeded = True
                return result
            finally:
                try:
                    if not succeeded and Path(self.wd).resolve() in _INVALIDATED.get():
                        retain(self.wd)
                finally:
                    _INVALIDATED.reset(token)
    return wrapped


def report_read(root_argument='wd'):
    """Protect direct report builders, including their cached-result reads."""
    def decorate(function):
        signature = inspect.signature(function)
        @wraps(function)
        def wrapped(*args, **kwargs):
            values = signature.bind(*args, **kwargs).arguments
            if str(values.get('output_scope') or 'baseline').strip().lower() != 'roads':
                return function(*args, **kwargs)
            root = values[root_argument]
            if not isinstance(root, (str, Path)):
                root = values['self']._infer_wd_from_loss(root)
            with current_read(root):
                return function(*args, **kwargs)
        return wrapped
    return decorate


@contextmanager
def restore_operation(root):
    """Never release an interrupted restore with an extracted current receipt."""
    with operation(root):
        completed = False
        try:
            yield
            if (Path(root) / RECEIPT).exists():
                payload = require_current(root)
                _validate_generated_set(Path(root).resolve(), payload)
            completed = True
        finally:
            if not completed:
                _revoke_receipt(Path(root).resolve())


def inspection(function):
    @wraps(function)
    def wrapped(self, *args, **kwargs):
        with operation(self.wd, shared=True, create=True):
            expected = (getattr(self, '_nodb_mtime', None), getattr(self, '_nodb_size', None))
            if expected != (None, None):
                observed = os.stat(self._nodb)
                if expected != (observed.st_mtime, observed.st_size):
                    raise RoadsResultsUnavailable('Reload Roads to read the updated project.')
            return function(self, *args, **kwargs)
    return wrapped


def invalidated(root):
    return Path(root).resolve() in _INVALIDATED.get()


def _revoke_receipt(root):
    # Restores may already have applied read-only archived directory modes.
    # Temporarily restore owner access to remove admission, then restore modes.
    modes = []
    try:
        for relative in (Path('.'), Path('wepp'), Path('wepp/roads'), OUTPUT):
            path = _path(root, relative)
            if not path.exists():
                return
            mode = stat.S_IMODE(path.stat().st_mode)
            if mode & 0o700 != 0o700:
                path.chmod(mode | 0o700)
                modes.append((path, mode))
        (root / RECEIPT).unlink(missing_ok=True)
    finally:
        for path, mode in reversed(modes):
            path.chmod(mode)


def protect_flask_response(root):
    """Post-authorization admission through WSGI consumption/close."""
    from flask import after_this_request, abort, g, jsonify, make_response
    from werkzeug.wsgi import ClosingIterator
    root = Path(root).resolve()
    guards = getattr(g, '_roads_read_guards', None)
    if guards is None:
        guards = g._roads_read_guards = {}
    if root in guards:
        return
    guard = current_read(root)
    try:
        guard.__enter__()
    except RoadsResultsUnavailable as exc:
        response = make_response(jsonify(error=str(exc), code=exc.code), 409)
        response.headers['Cache-Control'] = 'no-store'
        abort(response)
    guards[root] = guard

    @after_this_request
    def finish(response):
        response.headers['Cache-Control'] = 'no-store'
        response.response = ClosingIterator(response.response, lambda: guard.__exit__(None, None, None))
        response.direct_passthrough = False
        return response
