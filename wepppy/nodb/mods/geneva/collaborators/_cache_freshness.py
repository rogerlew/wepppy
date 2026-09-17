"""Bounded provenance and retained publication for Geneva geometry/alignment."""
from dataclasses import dataclass
import errno
import json
import logging
import os
from pathlib import Path
import stat
from uuid import uuid4

from osgeo import gdal

from wepppy.all_your_base.file_digest import sha256_file
from wepppy.all_your_base.raster_freshness import _companions, observe_raster_dependencies
from wepppy.nodb.mods.geneva.errors import GenevaKernelError

_LOG = logging.getLogger(__name__)
GEOJSON_PROOF = '_wepppy_freshness'
TIFF_PROOF = 'WEPPPY_GENEVA_FRESHNESS'


def changed_source():
    return GenevaKernelError('Geneva dependencies changed during derivation.',
                             code='changed_source', status_code=409)


def _version(path):
    info = Path(path).stat()
    return (str(Path(path).resolve()), info.st_dev, info.st_ino, info.st_size,
            info.st_mtime_ns, info.st_ctime_ns)


def _json_value(value):
    return json.loads(json.dumps(value, sort_keys=True, default=str))


@dataclass(frozen=True)
class _Inputs:
    identity: object
    guard: object
    observations: tuple = ()

    def check_unchanged(self):
        try:
            for observation in self.observations:
                observation.check_unchanged()
            # Reuse the proven graph only within this call. Recent equal-stat
            # rewrites still need the digest helper's uncached admission check.
            for observation in self.observations:
                for path, resolved, digest in observation.signature[3]:
                    if str(Path(path).resolve()) != resolved or sha256_file(path) != digest:
                        raise changed_source()
                for path, (_, companions) in observation.signature[2]:
                    if _companions(path) != companions:
                        raise changed_source()
            for observation in self.observations:
                observation.check_unchanged()
        except OSError as exc:
            if exc.errno in (errno.ENOENT, errno.ENOTDIR, errno.EACCES, errno.EPERM, errno.ESTALE):
                raise changed_source() from exc
            raise

    def validate(self, after):
        if self.identity is not None and (self.identity != after.identity or self.guard != after.guard):
            raise changed_source()


def validate_inputs(before, acquire):
    try:
        after = acquire()
    except OSError as exc:
        if before.identity is not None and exc.errno in (
                errno.ENOENT, errno.ENOTDIR, errno.EACCES, errno.EPERM, errno.ESTALE):
            raise changed_source() from exc
        raise
    before.validate(after)


def geometry_inputs(source, legend):
    before = _version(legend)
    digest = sha256_file(legend)
    raster = observe_raster_dependencies((source,))
    if _version(legend) != before:
        raise changed_source()
    if raster is None:
        return _Inputs(None, None)
    return _Inputs(_json_value({'raster': raster.signature, 'legend': (str(legend), before[0], digest)}),
                   (raster.read_guard, before))


def alignment_inputs(source, bound):
    source_observation = observe_raster_dependencies((source,))
    if source_observation is None:
        return _Inputs(None, None)
    bound_observation = observe_raster_dependencies((bound,))
    if bound_observation is None:
        return _Inputs(None, None)
    import rasterio
    with rasterio.open(bound) as dataset:
        profile = dict(dataset.profile)
    for key in ('driver', 'count', 'compress', 'nodata', 'dtype'):
        profile.pop(key, None)
    source_observation.check_unchanged()
    bound_observation.check_unchanged()
    return _Inputs(_json_value({'source': source_observation.signature,
                               'bound': (str(bound), str(Path(bound).resolve()), profile)}),
                   (source_observation.read_guard, bound_observation.read_guard),
                   (source_observation, bound_observation))


def matches(proof, kind, inputs):
    return (inputs.identity is not None and isinstance(proof, dict)
            and set(proof) == {'version', 'kind', 'attempt_id', 'dependencies'}
            and type(proof['version']) is int and proof['version'] == 1
            and proof['kind'] == kind and isinstance(proof['attempt_id'], str)
            and len(proof['attempt_id']) == 32
            and proof['dependencies'] == inputs.identity)


def clean_tiff_proof(path):
    """Return (clean target layout, proof, read observation), without opening unproven native sources."""
    try:
        with Path(path).open('rb'):
            pass
    except FileNotFoundError:
        # The same bounded filename inventory applies before the first main file.
        try:
            companions = _companions(str(Path(path).absolute()))
        except FileNotFoundError:
            companions = ()
        return not companions, None, None
    observation = observe_raster_dependencies((path,))
    if observation is None:
        return False, None, None
    if any(companions for _, (_, companions) in observation.signature[2]):
        return False, None, None
    driver = gdal.IdentifyDriver(str(path))
    if driver is None or driver.ShortName != 'GTiff':
        return False, None, None
    dataset = gdal.OpenEx(str(path), gdal.OF_RASTER | gdal.OF_READONLY,
                          allowed_drivers=['GTiff'], sibling_files=[Path(path).name])
    if dataset is None:
        raise changed_source()
    try:
        raw = dataset.GetMetadataItem(TIFF_PROOF)
    finally:
        dataset = None
    observation.check_unchanged()
    if raw is None:
        return True, None, observation
    try:
        return True, json.loads(raw), observation
    except (ValueError, TypeError):
        return True, None, observation


class _Attempt:
    def __init__(self, geneva, relpath, kind):
        self.geneva = geneva
        self.relpath = relpath
        self.kind = kind
        self.target = geneva.artifact_io.resolve_path(geneva.wd, relpath)
        self.target.parent.mkdir(parents=True, exist_ok=True)
        self.attempt_id = uuid4().hex
        self.relative_root = f'cache_attempts/{self.attempt_id}'
        self.root = geneva.artifact_io.resolve_path(geneva.wd, self.relative_root)
        self.root.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.root.mkdir(mode=0o700)
        self.committed = False
        self.compatibility = False
        self.inputs = None
        self.input_validator = None

    def candidate(self, name):
        # This unique directory was resolved and created inside ArtifactIO's root.
        # Recheck member containment, without repeating unrelated root creation.
        if Path(name).name != name:
            raise ValueError('Geneva attempt member must be a basename')
        candidate = (self.root / name).resolve()
        if not candidate.is_relative_to(self.root):
            raise ValueError('Geneva attempt member escapes its private directory')
        return candidate

    def proof(self, inputs):
        return {'version': 1, 'kind': self.kind, 'attempt_id': self.attempt_id,
                'dependencies': inputs.identity}

    def _status(self, status, error=None):
        payload = {'status': status, 'attempt_id': self.attempt_id, 'kind': self.kind,
                   'target': self.relpath, 'compatibility_native_overwrite': self.compatibility,
                   'dependencies': self.inputs, 'error': error}
        temporary = self.candidate(f'status.{uuid4().hex}.json')
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w') as outgoing:
            json.dump(payload, outgoing, indent=2, sort_keys=True)
            outgoing.write('\n')
        os.replace(temporary, self.candidate('status.json'))

    def __enter__(self):
        self._status('working')
        return self

    def __exit__(self, exc_type, exc, traceback):
        validation_error = None
        if exc is not None and not self.committed and self.input_validator is not None:
            try:
                self.input_validator()
            except (GenevaKernelError, OSError) as error:
                validation_error = error
                exc = error
        # Diagnostic boundary: do not mask original failures or reverse a commit.
        try:
            self._status('complete' if self.committed else 'failed', None if exc is None else str(exc))
        except (OSError, ValueError):
            _LOG.exception('Unable to record Geneva derivation status at %s', self.root)
        if validation_error is not None:
            raise validation_error
        return False

    def publish(self, candidate, *, clean_tiff=False, validate=None):
        if self.geneva.artifact_io.resolve_path(self.geneva.wd, self.relpath) != self.target:
            raise changed_source()
        if clean_tiff and not clean_tiff_proof(self.target)[0]:
            raise changed_source()
        try:
            existing = self.target.stat()
        except FileNotFoundError:
            existing = None
        if existing is not None:
            # JSON previously wrote the inode; raster_stacker replaced its path.
            if not clean_tiff:
                os.close(os.open(self.target, os.O_WRONLY))
            info = candidate.stat()
            if (info.st_uid, info.st_gid) != (existing.st_uid, existing.st_gid):
                os.chown(candidate, existing.st_uid, existing.st_gid)
            candidate.chmod(stat.S_IMODE(existing.st_mode))
        if validate is not None:
            validate()
        if self.geneva.artifact_io.resolve_path(self.geneva.wd, self.relpath) != self.target:
            raise changed_source()
        if clean_tiff and not clean_tiff_proof(self.target)[0]:
            raise changed_source()
        os.replace(candidate, self.target)
        self.committed = True


__all__ = ['GEOJSON_PROOF', 'TIFF_PROOF', 'changed_source', 'geometry_inputs',
           'alignment_inputs', 'matches', 'clean_tiff_proof', 'validate_inputs']
