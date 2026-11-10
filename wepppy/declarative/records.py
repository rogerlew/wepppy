"""Visible atomic records and exact-path local Git checkpoints."""

from __future__ import annotations

from contextlib import contextmanager
from configparser import RawConfigParser
from datetime import datetime, timezone
import hashlib
import fcntl
import os
from pathlib import Path
import subprocess
import tempfile

from .schema import AdmissionError, SCHEMA, identities, loads, uuid_text

__all__ = ["utcnow", "read", "write", "marker", "guard", "checkpoint", "digest",
           "protected_manifest", "verify_protected", "ProtectedProjectError"]


class ProtectedProjectError(PermissionError):
    code = "declarative_protected"


def utcnow():
    return datetime.now(timezone.utc).isoformat()


def safe_path(wd, relative):
    base = Path(wd)
    rel = Path(relative)
    if rel.is_absolute() or ".." in rel.parts or not rel.parts:
        raise ProtectedProjectError("Invalid provenance path")
    current = base
    if base.is_symlink():
        raise ProtectedProjectError("Symlinked project root")
    for part in rel.parts:
        current = current / part
        if current.is_symlink():
            raise ProtectedProjectError("Symlinked provenance path")
    return current


def read(wd, relative):
    return loads(safe_path(wd, relative).read_text())


def marker(wd):
    # Ordinary project lookup must not acquire new path/format restrictions.
    candidate = Path(wd) / "provenance/declarative.json"
    if not candidate.exists() and not candidate.is_symlink():
        if not (Path(wd) / "provenance").is_symlink():
            return None
    path = safe_path(wd, "provenance/declarative.json")
    if not path.exists():
        return None
    try:
        value = read(wd, "provenance/declarative.json")
        if not isinstance(value, dict) or value.get("schema") != SCHEMA:
            raise AdmissionError("Invalid marker")
        runid, queue = identities(value["definition"]["submission_id"])
        uuid_text(value["attempt_id"])
        uuid_text(value["finalizer_id"])
        if (value["runid"] != runid or value["queue"] != queue
                or Path(wd).name != runid or type(value["owner_id"]) is not int):
            raise AdmissionError("Invalid marker identity")
        return value
    except (ValueError, TypeError, KeyError) as exc:
        raise ProtectedProjectError("Malformed declarative admission record") from exc


@contextmanager
def guard(wd):
    # This stable guard also serializes archive replacement and catalog publication.
    from wepppy.query_engine.catalog_refresh import catalog_lifecycle_guard
    with catalog_lifecycle_guard(wd):
        safe_path(wd, "provenance").mkdir(exist_ok=True)
        lock = safe_path(wd, "provenance/.publication.lock")
        with lock.open("a") as stream:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def project_identity(wd):
    base = Path(wd)
    stat = base.stat()
    incarnation = base / "_query_engine/refresh/incarnation.json"
    return stat.st_dev, stat.st_ino, incarnation.read_bytes() if incarnation.exists() else None


def write(wd, relative, value, *, exclusive=False):
    import json
    path = safe_path(wd, relative)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()
    fd, temp = tempfile.mkstemp(prefix=".publish-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        if exclusive:
            os.link(temp, path)
        else:
            os.replace(temp, path)
        directory_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        Path(temp).unlink(missing_ok=True)


def digest(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def _git(root, *args):
    # No shell, hooks, inherited Git paths, signing or remote transport.
    git_dir = root / ".git"
    if git_dir.exists():
        if not git_dir.is_dir() or any(path.is_symlink() for path in git_dir.rglob("*")):
            raise ProtectedProjectError("Untrusted provenance repository")
        config = RawConfigParser()
        config.read(git_dir / "config")
        if set(config.sections()) != {"core"} or set(config["core"]) - {
            "repositoryformatversion", "filemode", "bare", "logallrefupdates",
        } or config.get("core", "bare", fallback="true") != "false":
            raise ProtectedProjectError("Unapproved provenance Git configuration")
        if (git_dir / "objects/info/alternates").exists():
            raise ProtectedProjectError("External Git object stores are prohibited")
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL="/dev/null",
               GIT_TERMINAL_PROMPT="0")
    return subprocess.check_output(
        ["git", "-c", "core.hooksPath=/dev/null", "-c", "core.fsmonitor=false", "-c", "commit.gpgSign=false",
         "-c", "user.name=WEPPcloud provenance", "-c", "user.email=provenance@localhost",
         "-C", str(root), *args], env=env, stderr=subprocess.PIPE, text=True,
    ).strip()


def checkpoint(wd, attempt_id, paths):
    uuid_text(attempt_id)
    root = safe_path(wd, "provenance")
    safe_path(wd, "provenance/.git")
    allowed = {"declarative.json", f"attempts/{attempt_id}.json"}
    if not paths or set(paths) - allowed:
        raise ProtectedProjectError("Unapproved checkpoint path")
    for path in paths:
        safe_path(wd, "provenance/" + path)
    if not (root / ".git").exists():
        _git(root, "init", "--quiet")
    elif _git(root, "for-each-ref", "--format=%(refname)"):
        found = _git(root, "log", "--all", "--format=%H", "--fixed-strings",
                     f"--grep=attempt:{attempt_id}")
        if found:
            return found.splitlines()[0]
    _git(root, "add", "--", *paths)
    _git(root, "commit", "--quiet", "--only", "-m", f"attempt:{attempt_id}", "--", *paths)
    return _git(root, "rev-parse", "HEAD")


def verify_checkpoint(wd, commit, attempt_id):
    import re
    uuid_text(attempt_id)
    if not isinstance(commit, str) or re.fullmatch(r"[0-9a-f]{40,64}", commit) is None:
        raise ProtectedProjectError("Invalid checkpoint identity")
    root = safe_path(wd, "provenance")
    message = _git(root, "show", "-s", "--format=%B", commit)
    content = _git(root, "show", f"{commit}:attempts/{attempt_id}.json")
    if message != f"attempt:{attempt_id}" or loads(content) != read(wd, f"provenance/attempts/{attempt_id}.json"):
        raise ProtectedProjectError("Required checkpoint does not match attempt record")


def protected_manifest(wd):
    base = Path(wd)
    files = list(base.glob("*.nodb")) + list((base / "dem").rglob("*"))
    return {str(p.relative_to(base)): digest(safe_path(wd, p.relative_to(base)))
            for p in sorted(files) if p.is_file()}


def verify_protected(wd):
    expected = read(wd, "provenance/protected.json")
    if expected != protected_manifest(wd):
        raise ProtectedProjectError("Protected build artifacts changed")
