"""Bounded local raster read-set proof for numerical cache reuse.

Unproven layouts retain their original native operation, uncached. See
``docs/schemas/raster-dependency-freshness-contract.md`` for coverage/authority.
"""
from dataclasses import dataclass, field
import errno
import logging
import os
from pathlib import Path
import stat

from osgeo import gdal

from .file_digest import sha256_file

__all__ = ["RasterDependencyObservation", "observe_raster_dependencies",
           "raster_dependency_signature", "raster_dependency_signatures"]


@dataclass(frozen=True)
class RasterDependencyObservation:
    """Content equality for reuse, with separate whole-operation read guards."""
    signature: tuple
    read_guard: tuple = field(compare=False, hash=False)

    def check_unchanged(self) -> None:
        """Guard additional dependency reads within this acquisition, without rehashing."""
        configuration, files, directories = self.read_guard
        try:
            for path, expected in files:
                if (os.path.realpath(path), _version(path)) != expected:
                    raise OSError(errno.ESTALE, "Raster dependency changed", path)
            for parent, expected in directories:
                if _directory_version(parent) != expected:
                    raise OSError(errno.ESTALE, "Raster companion directory changed", parent)
        except (OSError, _Unverified) as exc:
            raise OSError(errno.ESTALE, "Raster read generation changed") from exc
        if tuple(gdal.GetConfigOption(key) for key in _DEFAULTS) != configuration:
            raise OSError(errno.ESTALE, "GDAL configuration changed during raster read")


_LOG = logging.getLogger(__name__)
_DRIVERS = ["GTiff", "AAIGrid"]
_DEFAULTS = {
    "GDAL_PAM_PROXY_DIR": None,
    "GDAL_PAM_ENABLED": "YES",
    "GDAL_DISABLE_READDIR_ON_OPEN": "FALSE",
    "GDAL_READDIR_LIMIT_ON_OPEN": "1000",
    "GDAL_GEOREF_SOURCES": None,
    "USE_RRD": "NO",
    "TIFF_USE_OVR": "FALSE",
}
# Unknown companion mechanisms are not inferred from GDAL's final file list.
_ORDINARY = (".prj", ".wld", ".tfw", ".tifw", ".tab", ".hdr")
_OPAQUE = (".aux", ".aux.xml", ".xml", ".rpb", "_rpc.txt", ".rpc.txt", ".imd", ".rrd")
_RASTERS = (".msk", ".ovr")


class _Unverified(ValueError):
    pass


def _configuration():
    values = tuple(gdal.GetConfigOption(key) for key in _DEFAULTS)
    for (key, default), value in zip(_DEFAULTS.items(), values):
        if value is not None and (default is None or value.upper() != default):
            raise _Unverified(f"nondefault GDAL configuration: {key}")
    return values


def _version(path):
    info = os.stat(path)
    if not stat.S_ISREG(info.st_mode):
        raise _Unverified(f"not an ordinary file: {path}")
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)



def _directory_version(path):
    info = os.stat(path)
    if not stat.S_ISDIR(info.st_mode):
        raise OSError(errno.ESTALE, "Raster companion parent is not a directory", path)
    return (info.st_dev, info.st_ino, info.st_mtime_ns, info.st_ctime_ns)


def _companions(path):
    """Find case variants in both lexical and resolved filename contexts."""
    found = {}
    for source in {path, os.path.realpath(path)}:
        parent, name = os.path.split(source)
        bases = {name.lower(), os.path.splitext(name)[0].lower()}
        candidates = {base + suffix: suffix for base in bases
                      for suffix in _ORDINARY + _OPAQUE + _RASTERS}
        extension = os.path.splitext(name)[1].lower().lstrip(".")
        if extension:
            for suffix in ("." + extension + "w", "." + extension[0] + extension[-1] + "w"):
                for base in bases:
                    candidates[base + suffix] = ".wld"
        with os.scandir(parent) as entries:
            for entry in entries:
                suffix = candidates.get(entry.name.lower())
                if suffix and entry.path != path:
                    found[entry.path] = suffix
    return tuple(sorted(found.items()))


class _Observation:
    def __init__(self):
        self.versions = {}
        self.directories = {}
        self.companions = {}
        self.graph = {}
        self.visiting = set()

    def remember(self, path):
        identity = (os.path.realpath(path), _version(path))
        previous = self.versions.setdefault(path, identity)
        if previous != identity:
            raise OSError(errno.ESTALE, "Raster dependency changed", path)

    def discover(self, path):
        self.remember(path)
        resolved = os.path.realpath(path)
        if resolved in self.visiting:
            raise _Unverified(f"cyclic raster companions: {path}")
        if path in self.graph:
            return
        self.visiting.add(resolved)
        for parent in {os.path.dirname(path), os.path.dirname(resolved)}:
            version = _directory_version(parent)
            if self.directories.setdefault(parent, version) != version:
                raise OSError(errno.ESTALE, "Raster companion directory changed", parent)
        companions = self.companions[path] = _companions(path)
        for member, suffix in companions:
            if suffix in _OPAQUE:
                raise _Unverified(f"opaque raster companion: {member}")
            self.remember(member)
            if suffix in _RASTERS:
                self.discover(member)
        driver = gdal.IdentifyDriver(path)
        if driver is None or driver.ShortName not in _DRIVERS:
            raise _Unverified(f"unproven raster driver: {path}")
        # A replacement between identification and open cannot invoke a VRT reader.
        siblings = [os.path.basename(path), *[
            os.path.basename(member) for member, suffix in companions
            if suffix in _ORDINARY and os.path.dirname(member) == os.path.dirname(path)
        ]]
        dataset = gdal.OpenEx(path, gdal.OF_RASTER | gdal.OF_READONLY,
                              allowed_drivers=_DRIVERS, sibling_files=siblings)
        if dataset is None:
            raise _Unverified(f"raster unavailable for inspection: {path}")
        try:
            if dataset.GetMetadata("OVERVIEWS") or dataset.GetMetadata("GEOLOCATION"):
                raise _Unverified(f"external raster metadata relationship: {path}")
            members = tuple(sorted(str(Path(item).absolute()) for item in dataset.GetFileList() or ()))
        finally:
            dataset = None
        allowed = {path, resolved}
        for member, _ in companions:
            allowed.update((member, os.path.realpath(member)))
        # Nested proven companions can also be included by the parent driver.
        for member in self.versions:
            allowed.update((member, os.path.realpath(member)))
        if not members or any(member not in allowed for member in members):
            raise _Unverified(f"unproven native dependency membership: {path}")
        for member in members:
            self.remember(member)
        # Restricted GDAL inventory does not reopen masks/overviews; their
        # independently verified companion edges still belong to this read set.
        self.graph[path] = (members, companions)
        self.visiting.remove(resolved)

    def validate(self):
        for parent, version in self.directories.items():
            try:
                current = _directory_version(parent)
            except OSError as exc:
                raise OSError(errno.ESTALE, "Raster companion directory became unavailable", parent) from exc
            if current != version:
                raise OSError(errno.ESTALE, "Raster companion directory changed", parent)
        for path, expected in self.companions.items():
            try:
                current = _companions(path)
            except OSError as exc:
                raise OSError(errno.ESTALE, "Raster companion directory became unavailable", path) from exc
            if current != expected:
                raise OSError(errno.ESTALE, "Raster companions changed", path)
        for path, identity in self.versions.items():
            try:
                current = (os.path.realpath(path), _version(path))
            except (OSError, _Unverified) as exc:
                raise OSError(errno.ESTALE, "Raster dependency became unavailable", path) from exc
            if current != identity:
                raise OSError(errno.ESTALE, "Raster dependency changed", path)


def observe_raster_dependencies(paths):
    """Return joint content proof, or None with a diagnostic for unproven inputs.

    All members are guarded across the complete multi-raster observation. ESTALE
    is a source-change failure, never an unverified cache key.
    """
    selected = tuple(str(Path(path).absolute()) for path in paths)
    observation = None
    configuration = None
    try:
        configuration = _configuration()
        observation = _Observation()
        for path in selected:
            observation.discover(path)
        digests = tuple((path, observation.versions[path][0], sha256_file(path))
                        for path in sorted(observation.versions))
        observation.validate()
        if tuple(gdal.GetConfigOption(key) for key in _DEFAULTS) != configuration:
            raise OSError(errno.ESTALE, "GDAL configuration changed during raster observation")
        signature = ("local-raster-v1", selected, tuple(sorted(observation.graph.items())), digests)
        guard = (configuration, tuple(sorted(observation.versions.items())),
                 tuple(sorted(observation.directories.items())))
        return RasterDependencyObservation(signature, guard)
    except (_Unverified, RuntimeError, OSError) as exc:
        # GDAL's Python boundary reports inspection errors as RuntimeError. The
        # original native operation owns format/access errors for uncached inputs.
        if isinstance(exc, OSError) and exc.errno == errno.ESTALE:
            raise
        # An inspection failure cannot conceal an already observed source change.
        if observation is not None:
            observation.validate()
            if tuple(gdal.GetConfigOption(key) for key in _DEFAULTS) != configuration:
                raise OSError(errno.ESTALE, "GDAL configuration changed during raster observation") from exc
        _LOG.debug("Raster cache coverage unverified for %s: %s", selected, exc)
        return None



def raster_dependency_signatures(paths):
    """Return only content identity; materializers must retain the observation guard."""
    observation = observe_raster_dependencies(paths)
    return None if observation is None else observation.signature


def raster_dependency_signature(path):
    """Observe one raster using the same joint guard as multi-raster consumers."""
    return raster_dependency_signatures((path,))
