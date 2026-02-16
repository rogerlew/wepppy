"""NoDir filesystem-like operations (resolve/list/stat/open_read)."""

from __future__ import annotations

import io
import os
import stat as statmod
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import BinaryIO, Literal

from .errors import (
    NoDirError,
    nodir_invalid_archive,
    nodir_limit_exceeded,
    nodir_locked,
    nodir_mixed_state,
)
from .parquet_sidecars import logical_parquet_to_sidecar_relpath, pick_existing_parquet_path
from .paths import NoDirRoot, NoDirView, normalize_relpath, split_nodir_root
from .symlinks import _derive_allowed_symlink_roots, _is_within_any_root, _resolve_path_safely
from .state import is_transitioning_locked

__all__ = [
    "NoDirForm",
    "ResolvedNoDirPath",
    "NoDirDirEntry",
    "resolve",
    "listdir",
    "stat",
    "open_read",
]

_DEFAULT_MAX_OPEN_READ_BYTES = 1_073_741_824  # 1 GiB
_MAX_OPEN_READ_BYTES_ENV = "NODIR_MAX_OPEN_READ_BYTES"


def _get_max_open_read_bytes() -> int | None:
    raw = os.environ.get(_MAX_OPEN_READ_BYTES_ENV)
    if raw is None:
        return _DEFAULT_MAX_OPEN_READ_BYTES
    raw = raw.strip()
    if raw == "":
        return _DEFAULT_MAX_OPEN_READ_BYTES
    try:
        val = int(raw)
    except ValueError:
        # Keep the public surface stable (NoDirError + filesystem errors only).
        # Callers that want strict config validation should check env at startup.
        return _DEFAULT_MAX_OPEN_READ_BYTES
    if val <= 0:
        return None
    return val

def _stat_regular_file(path: Path) -> os.stat_result | None:
    try:
        st = path.stat()
    except FileNotFoundError:
        return None
    if not statmod.S_ISREG(st.st_mode):
        return None
    return st


def _stat_mtime_ns(st: os.stat_result) -> int:
    mtime_ns = getattr(st, "st_mtime_ns", None)
    if mtime_ns is None:
        mtime_ns = int(st.st_mtime * 1_000_000_000)
    return int(mtime_ns)


def _stat_ctime_ns(st: os.stat_result) -> int:
    ctime_ns = getattr(st, "st_ctime_ns", None)
    if ctime_ns is None:
        ctime_ns = int(st.st_ctime * 1_000_000_000)
    return int(ctime_ns)


def _lstat(path: Path) -> os.stat_result | None:
    try:
        return path.stat(follow_symlinks=False)
    except FileNotFoundError:
        return None


def _archive_real_path_and_stat(
    wd_path: Path,
    archive_path: Path,
    archive_lstat: os.stat_result,
) -> tuple[Path, os.stat_result]:
    """Return the archive file path to read + its stat, validating symlinks first."""
    if statmod.S_ISLNK(archive_lstat.st_mode):
        allowed_roots = _derive_allowed_symlink_roots(wd_path)
        resolved_archive = _resolve_path_safely(archive_path)
        if resolved_archive is None or not _is_within_any_root(resolved_archive, allowed_roots):
            raise nodir_invalid_archive("archive resolves outside allowed roots")
        st = _stat_regular_file(resolved_archive)
        if st is None:
            raise nodir_invalid_archive("archive is not a regular file")
        return resolved_archive, st

    if statmod.S_ISREG(archive_lstat.st_mode):
        return archive_path, archive_lstat

    raise nodir_invalid_archive("archive is not a regular file")


NoDirForm = Literal["dir", "archive"]


@dataclass(frozen=True, slots=True)
class ResolvedNoDirPath:
    wd: str
    root: NoDirRoot
    inner_path: str  # posix rel within the logical root; "" means root
    form: NoDirForm
    dir_path: str
    archive_path: str
    archive_fp: tuple[int, int] | None  # (mtime_ns, size_bytes)


@dataclass(frozen=True, slots=True)
class NoDirDirEntry:
    name: str
    is_dir: bool
    size_bytes: int | None
    mtime_ns: int | None



def _zip_mtime_ns(info: zipfile.ZipInfo) -> int | None:
    try:
        dt = datetime(*info.date_time, tzinfo=timezone.utc)
        return int(dt.timestamp() * 1_000_000_000)
    except Exception:
        return None


def _validate_zip_entry_name(raw_name: str) -> tuple[str, bool]:
    """Return (normalized_name_without_trailing_slash, is_dir) or raise NoDirError."""
    if "\x00" in raw_name:
        raise nodir_invalid_archive("zip entry name contains null byte")
    if raw_name.startswith("/"):
        raise nodir_invalid_archive("zip entry name must be relative (no leading '/')")
    if "\\" in raw_name:
        raise nodir_invalid_archive("zip entry name must use '/' separators (no backslashes)")
    # Windows drive letters are not allowed (even on Linux).
    if len(raw_name) >= 2 and raw_name[1] == ":" and raw_name[0].isalpha():
        raise nodir_invalid_archive("zip entry name must not contain a drive letter")
    if raw_name.endswith("//"):
        raise nodir_invalid_archive("zip entry name is not normalized")

    is_dir = raw_name.endswith("/")
    name = raw_name.rstrip("/") if is_dir else raw_name
    if name == "":
        raise nodir_invalid_archive("zip entry name is empty")

    parts = name.split("/")
    for part in parts:
        if part in ("", ".", ".."):
            raise nodir_invalid_archive("zip entry name is not normalized")
    normalized = "/".join(parts)
    return normalized, is_dir


def _validate_zip_info(info: zipfile.ZipInfo) -> tuple[str, bool]:
    if info.flag_bits & 0x1:
        raise nodir_invalid_archive("encrypted zip entries are not supported")
    if info.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
        raise nodir_invalid_archive("unsupported zip compression method")

    name, is_dir = _validate_zip_entry_name(info.filename)
    if name.casefold().endswith(".parquet"):
        raise nodir_invalid_archive("parquet sidecars must not be stored inside NoDir archives")

    # Reject symlinks and special file types when UNIX mode bits are present.
    mode = (info.external_attr >> 16) & 0xFFFF
    if mode:
        ftype = statmod.S_IFMT(mode)
        if ftype in (
            statmod.S_IFLNK,
            statmod.S_IFCHR,
            statmod.S_IFBLK,
            statmod.S_IFIFO,
            statmod.S_IFSOCK,
        ):
            raise nodir_invalid_archive("zip entry type is not a regular file/directory")
        if ftype == statmod.S_IFDIR and not is_dir:
            raise nodir_invalid_archive("zip directory entries must end with '/'")
        if ftype and ftype != statmod.S_IFDIR and is_dir:
            raise nodir_invalid_archive("zip directory entries must be marked as directories")

    return name, is_dir


@dataclass(frozen=True, slots=True)
class _ZipIndex:
    files: dict[str, zipfile.ZipInfo]  # normalized name -> ZipInfo
    dirs: dict[str, zipfile.ZipInfo]  # normalized name -> ZipInfo (explicit only)


@lru_cache(maxsize=64)
def _load_zip_index(
    archive_path: str,
    mtime_ns: int,
    size_bytes: int,
    inode: int,
    ctime_ns: int,
    dev: int,
) -> _ZipIndex:
    try:
        with zipfile.ZipFile(archive_path, "r") as zf:
            files: dict[str, zipfile.ZipInfo] = {}
            dirs: dict[str, zipfile.ZipInfo] = {}
            implied_dirs: set[str] = set()

            def _iter_parent_prefixes(path: str) -> list[str]:
                parts = path.split("/")
                out: list[str] = []
                prefix = ""
                for part in parts[:-1]:
                    prefix = part if not prefix else f"{prefix}/{part}"
                    out.append(prefix)
                return out

            for info in zf.infolist():
                name, is_dir = _validate_zip_info(info)
                if is_dir:
                    if name in files:
                        raise nodir_invalid_archive("zip contains both file and directory entries for the same path")
                    for parent in _iter_parent_prefixes(name):
                        if parent in files:
                            raise nodir_invalid_archive("zip contains a file that is also a directory prefix")
                    if name in dirs:
                        continue
                    dirs[name] = info
                    implied_dirs.add(name)
                    implied_dirs.update(_iter_parent_prefixes(name))
                    continue
                if name in dirs or name in implied_dirs:
                    raise nodir_invalid_archive("zip contains both file and directory entries for the same path")
                for parent in _iter_parent_prefixes(name):
                    if parent in files:
                        raise nodir_invalid_archive("zip contains a file that is also a directory prefix")
                if name in files:
                    raise nodir_invalid_archive("zip contains duplicate file entries")
                files[name] = info
                implied_dirs.update(_iter_parent_prefixes(name))
            return _ZipIndex(files=files, dirs=dirs)
    except NoDirError:
        raise
    except zipfile.BadZipFile as e:
        raise nodir_invalid_archive(f"invalid zip archive: {e}") from e
    except OSError as e:
        raise nodir_invalid_archive(f"unable to read archive: {e}") from e


def _get_zip_index(target: ResolvedNoDirPath) -> tuple[Path, _ZipIndex]:
    wd_path = Path(target.wd)
    archive_path = Path(target.archive_path)
    archive_lstat = _lstat(archive_path)
    if archive_lstat is None:
        raise nodir_invalid_archive("archive is not a regular file")

    real_path, st = _archive_real_path_and_stat(wd_path, archive_path, archive_lstat)
    index = _load_zip_index(
        str(real_path),
        _stat_mtime_ns(st),
        int(st.st_size),
        int(st.st_ino),
        _stat_ctime_ns(st),
        int(st.st_dev),
    )
    return real_path, index


def _logical_parquet_sidecar_path(wd: Path, logical_rel: str) -> Path | None:
    sidecar_rel = logical_parquet_to_sidecar_relpath(logical_rel)
    if sidecar_rel is None:
        return None
    candidate = wd / sidecar_rel
    st = _lstat(candidate)
    if st is None:
        return None
    if statmod.S_ISREG(st.st_mode):
        return candidate
    if statmod.S_ISLNK(st.st_mode):
        allowed_roots = _derive_allowed_symlink_roots(wd)
        if not _is_within_any_root(candidate, allowed_roots):
            return None
        try:
            target_st = candidate.stat()
        except OSError:
            return None
        if statmod.S_ISREG(target_st.st_mode):
            return candidate
    return None


def resolve(wd: str, rel: str, *, view: NoDirView = "effective") -> ResolvedNoDirPath | None:
    rel_norm = normalize_relpath(rel)
    root, inner = split_nodir_root(rel_norm)
    if root is None:
        return None

    wd_path = Path(os.path.abspath(wd))
    dir_path = wd_path / root
    archive_path = wd_path / f"{root}.nodir"

    dir_lstat = _lstat(dir_path)
    dir_exists = False
    if dir_lstat is not None:
        if statmod.S_ISDIR(dir_lstat.st_mode):
            dir_exists = True
        elif statmod.S_ISLNK(dir_lstat.st_mode):
            allowed_roots = _derive_allowed_symlink_roots(wd_path)
            resolved_dir = _resolve_path_safely(dir_path)
            if resolved_dir is not None and _is_within_any_root(resolved_dir, allowed_roots):
                try:
                    if resolved_dir.is_dir():
                        dir_exists = True
                except OSError:
                    dir_exists = False
    archive_lstat = _lstat(archive_path)
    archive_present = archive_lstat is not None

    if view in ("effective", "archive") and is_transitioning_locked(wd_path, root):
        raise nodir_locked(f"{root} is transitioning (thaw/freeze in progress)")

    if view == "effective":
        if dir_exists and archive_present:
            raise nodir_mixed_state(f"{root} is in mixed state (dir + .nodir present)")
        if archive_present and not dir_exists:
            real_path, st = _archive_real_path_and_stat(wd_path, archive_path, archive_lstat)
            archive_fp = (_stat_mtime_ns(st), int(st.st_size))
            _load_zip_index(
                str(real_path),
                archive_fp[0],
                archive_fp[1],
                int(st.st_ino),
                _stat_ctime_ns(st),
                int(st.st_dev),
            )
            form: NoDirForm = "archive"
        else:
            archive_fp = None
            form = "dir"

        return ResolvedNoDirPath(
            wd=str(wd_path),
            root=root,
            inner_path=inner,
            form=form,
            dir_path=str(dir_path),
            archive_path=str(archive_path),
            archive_fp=archive_fp,
        )

    if view == "dir":
        if not dir_exists:
            return None
        archive_fp: tuple[int, int] | None = None
        if archive_present:
            try:
                _, archive_st = _archive_real_path_and_stat(wd_path, archive_path, archive_lstat)
            except NoDirError:
                archive_fp = None
            else:
                archive_fp = (_stat_mtime_ns(archive_st), int(archive_st.st_size))
        return ResolvedNoDirPath(
            wd=str(wd_path),
            root=root,
            inner_path=inner,
            form="dir",
            dir_path=str(dir_path),
            archive_path=str(archive_path),
            archive_fp=archive_fp,
        )

    if view == "archive":
        if not archive_present:
            return None
        real_path, st = _archive_real_path_and_stat(wd_path, archive_path, archive_lstat)
        archive_fp = (_stat_mtime_ns(st), int(st.st_size))
        _load_zip_index(
            str(real_path),
            archive_fp[0],
            archive_fp[1],
            int(st.st_ino),
            _stat_ctime_ns(st),
            int(st.st_dev),
        )
        return ResolvedNoDirPath(
            wd=str(wd_path),
            root=root,
            inner_path=inner,
            form="archive",
            dir_path=str(dir_path),
            archive_path=str(archive_path),
            archive_fp=archive_fp,
        )

    raise ValueError(f"unknown NoDir view: {view}")


def listdir(target: ResolvedNoDirPath) -> list[NoDirDirEntry]:
    wd_path = Path(target.wd)

    if target.form == "dir":
        base = Path(target.dir_path)
        abs_dir = base if not target.inner_path else base / target.inner_path
        allowed_roots = _derive_allowed_symlink_roots(wd_path)
        if not _is_within_any_root(abs_dir, allowed_roots):
            raise FileNotFoundError(target.inner_path or target.root)
        entries: list[NoDirDirEntry] = []
        with os.scandir(abs_dir) as it:
            for entry in it:
                follow = False
                if entry.is_symlink():
                    candidate = Path(entry.path)
                    follow = _is_within_any_root(candidate, allowed_roots)
                try:
                    st = entry.stat(follow_symlinks=follow)
                except OSError:
                    st = None
                try:
                    is_dir = entry.is_dir(follow_symlinks=follow)
                except OSError:
                    is_dir = False
                size_bytes: int | None
                if is_dir:
                    size_bytes = None
                else:
                    size_bytes = int(st.st_size) if st is not None else None
                mtime_ns: int | None
                if st is None:
                    mtime_ns = None
                else:
                    mtime_ns = getattr(st, "st_mtime_ns", None)
                    if mtime_ns is None:
                        mtime_ns = int(st.st_mtime * 1_000_000_000)
                entries.append(
                    NoDirDirEntry(
                        name=entry.name,
                        is_dir=bool(is_dir),
                        size_bytes=size_bytes,
                        mtime_ns=int(mtime_ns) if mtime_ns is not None else None,
                    )
                )
        entries.sort(key=lambda e: (0 if e.is_dir else 1, e.name.lower(), e.name))
        return entries

    # Archive form
    _, index = _get_zip_index(target)
    prefix = target.inner_path.strip("/")
    if prefix and prefix in index.files:
        raise NotADirectoryError(prefix)
    prefix_with = f"{prefix}/" if prefix else ""

    if prefix:
        has_explicit = prefix in index.dirs
        has_any = any(n.startswith(prefix_with) for n in index.files) or any(
            n.startswith(prefix_with) for n in index.dirs
        )
        if not has_explicit and not has_any:
            raise FileNotFoundError(prefix)

    children: dict[str, NoDirDirEntry] = {}

    def _add_dir(name: str, mtime_ns: int | None = None) -> None:
        existing = children.get(name)
        if existing is None or not existing.is_dir:
            children[name] = NoDirDirEntry(name=name, is_dir=True, size_bytes=None, mtime_ns=mtime_ns)

    def _add_file(name: str, info: zipfile.ZipInfo) -> None:
        children[name] = NoDirDirEntry(
            name=name,
            is_dir=False,
            size_bytes=int(info.file_size),
            mtime_ns=_zip_mtime_ns(info),
        )

    # Explicit directory entries first (may carry best-effort mtime).
    for dir_name, info in index.dirs.items():
        if not dir_name.startswith(prefix_with):
            continue
        rest = dir_name[len(prefix_with) :]
        if not rest:
            continue
        child, sep, _ = rest.partition("/")
        if sep:
            _add_dir(child)
        else:
            _add_dir(child, _zip_mtime_ns(info))

    # File entries imply parent directories.
    for file_name, info in index.files.items():
        if not file_name.startswith(prefix_with):
            continue
        rest = file_name[len(prefix_with) :]
        if not rest:
            continue
        child, sep, _ = rest.partition("/")
        if sep:
            _add_dir(child)
        else:
            _add_file(child, info)

    entries = list(children.values())
    entries.sort(key=lambda e: (0 if e.is_dir else 1, e.name.lower(), e.name))
    return entries


def stat(target: ResolvedNoDirPath) -> NoDirDirEntry:
    wd_path = Path(target.wd)
    logical_rel = f"{target.root}/{target.inner_path}" if target.inner_path else target.root

    if logical_rel.endswith(".parquet"):
        sidecar = _logical_parquet_sidecar_path(wd_path, logical_rel)
        if sidecar is not None:
            allowed_roots = _derive_allowed_symlink_roots(wd_path)
            if not _is_within_any_root(sidecar, allowed_roots):
                raise FileNotFoundError(logical_rel)
            st = sidecar.stat()
            mtime_ns = getattr(st, "st_mtime_ns", None)
            if mtime_ns is None:
                mtime_ns = int(st.st_mtime * 1_000_000_000)
            name = target.root if not target.inner_path else target.inner_path.split("/")[-1]
            return NoDirDirEntry(
                name=name,
                is_dir=False,
                size_bytes=int(st.st_size),
                mtime_ns=int(mtime_ns),
            )
        if target.form == "archive":
            raise FileNotFoundError(logical_rel)

    if target.form == "dir":
        base = Path(target.dir_path)
        abs_path = base if not target.inner_path else base / target.inner_path
        allowed_roots = _derive_allowed_symlink_roots(wd_path)
        if not _is_within_any_root(abs_path, allowed_roots):
            raise FileNotFoundError(logical_rel)
        st = abs_path.stat()
        is_dir = statmod.S_ISDIR(st.st_mode)
        name = target.root if not target.inner_path else target.inner_path.split("/")[-1]
        mtime_ns = getattr(st, "st_mtime_ns", None)
        if mtime_ns is None:
            mtime_ns = int(st.st_mtime * 1_000_000_000)
        size_bytes = None if is_dir else int(st.st_size)
        return NoDirDirEntry(name=name, is_dir=bool(is_dir), size_bytes=size_bytes, mtime_ns=int(mtime_ns))

    _, index = _get_zip_index(target)
    inner = target.inner_path.strip("/")
    name = target.root if not inner else inner.split("/")[-1]

    if inner == "":
        return NoDirDirEntry(name=name, is_dir=True, size_bytes=None, mtime_ns=None)

    info = index.files.get(inner)
    if info is not None:
        return NoDirDirEntry(name=name, is_dir=False, size_bytes=int(info.file_size), mtime_ns=_zip_mtime_ns(info))

    if inner in index.dirs:
        return NoDirDirEntry(name=name, is_dir=True, size_bytes=None, mtime_ns=_zip_mtime_ns(index.dirs[inner]))

    prefix = f"{inner}/"
    if any(n.startswith(prefix) for n in index.files) or any(n.startswith(prefix) for n in index.dirs):
        return NoDirDirEntry(name=name, is_dir=True, size_bytes=None, mtime_ns=None)

    raise FileNotFoundError(inner)


class _ZipStream(io.RawIOBase):
    def __init__(self, zf: zipfile.ZipFile, zef: zipfile.ZipExtFile) -> None:
        super().__init__()
        self._zf = zf
        self._zef = zef

    def readable(self) -> bool:  # pragma: no cover (trivial)
        return True

    def read(self, size: int = -1) -> bytes:
        return self._zef.read(size)

    def readinto(self, b) -> int:
        data = self._zef.read(len(b))
        if not data:
            return 0
        n = len(data)
        b[:n] = data
        return n

    def close(self) -> None:
        try:
            self._zef.close()
        finally:
            self._zf.close()
        super().close()


def open_read(target: ResolvedNoDirPath) -> BinaryIO:
    wd_path = Path(target.wd)
    logical_rel = f"{target.root}/{target.inner_path}" if target.inner_path else target.root

    if logical_rel.endswith(".parquet"):
        sidecar = _logical_parquet_sidecar_path(wd_path, logical_rel)
        if sidecar is not None:
            allowed_roots = _derive_allowed_symlink_roots(wd_path)
            if not _is_within_any_root(sidecar, allowed_roots):
                raise FileNotFoundError(logical_rel)
            return sidecar.open("rb")
        if target.form == "dir":
            legacy = pick_existing_parquet_path(wd_path, logical_rel)
            if legacy is not None:
                allowed_roots = _derive_allowed_symlink_roots(wd_path)
                if not _is_within_any_root(legacy, allowed_roots):
                    raise FileNotFoundError(logical_rel)
                return legacy.open("rb")
        raise FileNotFoundError(logical_rel)

    if target.form == "dir":
        base = Path(target.dir_path)
        abs_path = base if not target.inner_path else base / target.inner_path
        allowed_roots = _derive_allowed_symlink_roots(wd_path)
        if not _is_within_any_root(abs_path, allowed_roots):
            raise FileNotFoundError(logical_rel)
        return abs_path.open("rb")

    archive_real_path, index = _get_zip_index(target)
    inner = target.inner_path.strip("/")
    info = index.files.get(inner)
    if info is None:
        raise FileNotFoundError(inner)

    max_bytes = _get_max_open_read_bytes()
    if max_bytes is not None and int(info.file_size) > max_bytes:
        raise nodir_limit_exceeded(
            f"archive entry exceeds max uncompressed size ({int(info.file_size)} > {max_bytes})"
        )

    zf = zipfile.ZipFile(str(archive_real_path), "r")
    try:
        zef = zf.open(info, "r")
    except Exception:
        zf.close()
        raise
    return io.BufferedReader(_ZipStream(zf, zef))
