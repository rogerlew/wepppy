"""Pure deployment path mappings and descriptor-bound catalog reads."""

from contextlib import contextmanager
from collections import deque
from dataclasses import dataclass
import errno
import os
from pathlib import Path
import stat

__all__ = ["Roots", "SourceScopeError", "project_directory", "read_source", "signature"]


class SourceScopeError(OSError):
    """A registered source cannot be opened within its trusted boundary."""


@dataclass(frozen=True)
class Roots:
    primary: str = "/wc1/runs"
    legacy: str = "/geodata/weppcloud_runs"
    batch: str = "/wc1/batch"
    culvert: str = "/wc1/culverts"
    profile_runs: str = "/workdir/wepppy-test-engine-data/playback/runs"
    profile_fork: str = "/workdir/wepppy-test-engine-data/playback/fork"
    profile_archive: str = "/workdir/wepppy-test-engine-data/playback/archive"
    playback_clone: bool = False

    @classmethod
    def from_environ(cls):
        base = os.getenv("PROFILE_PLAYBACK_BASE", "/workdir/wepppy-test-engine-data/playback")
        return cls(
            batch=os.getenv("BATCH_RUNNER_ROOT", "/wc1/batch"),
            culvert=os.getenv("CULVERTS_ROOT", "/wc1/culverts"),
            profile_runs=os.getenv("PROFILE_PLAYBACK_RUN_ROOT", base + "/runs"),
            profile_fork=os.getenv("PROFILE_PLAYBACK_FORK_ROOT", base + "/fork"),
            profile_archive=os.getenv("PROFILE_PLAYBACK_ARCHIVE_ROOT", base + "/archive"),
            playback_clone=os.getenv("PROFILE_PLAYBACK_USE_CLONE", "false").lower() in {"1", "true", "yes", "on"},
        )

    def candidates(self, runid):
        if not isinstance(runid, str):
            raise ValueError("Invalid run identifier")
        parts = runid.split(";;")
        if any(part in {"", ".", ".."} or any(char in part for char in ("/", "\\", "\0")) for part in parts):
            raise ValueError("Invalid run identifier")
        if (len(parts) == 5 and parts[0] == "batch" and parts[-2] in {"omni", "omni-contrast"}) or (len(parts) == 3 and parts[0] not in {"batch", "culvert"} and parts[-2] in {"omni", "omni-contrast"}):
            parent = ";;".join(parts[:-2])
            suffix = ("_pups", "omni", "scenarios" if parts[-2] == "omni" else "contrasts", parts[-1])
            parents = self.candidates(parent) if len(parts) == 5 else [(self.primary, (parent[:2], parent)), (self.legacy, (parent,))]
            if any(component in {"", ".", ".."} for _, relative in parents for component in relative):
                raise ValueError("Unsafe generated path component")
            return [(root, relative + suffix) for root, relative in parents]
        if len(parts) == 1:
            if runid[:2] in {".", ".."}:
                raise ValueError("Unsafe generated path component")
            candidates = [(self.primary, (runid[:2], runid)), (self.legacy, (runid,))]
            return ([(self.profile_runs, (runid,))] if self.playback_clone else []) + candidates
        if len(parts) == 3:
            group, name, leaf = parts
            if group == "batch":
                return [(self.batch, (name, leaf) if leaf == "_base" else (name, "runs", leaf))]
            if group == "culvert":
                return [(self.culvert, (name, "runs", leaf))]
            if group == "profile" and name in {"tmp", "fork", "archive"}:
                root = {"tmp": self.profile_runs, "fork": self.profile_fork, "archive": self.profile_archive}[name]
                return [(root, (leaf,))]
        raise ValueError("Unsupported grouped run identifier")

    def matches(self, runid, wd):
        normalized = os.path.abspath(wd)
        return any(normalized == os.path.abspath(os.path.join(root, *relative))
                   for root, relative in self.candidates(runid))

    def identify(self, wd):
        target = Path(os.path.abspath(wd))
        mappings = ((self.primary, "primary"), (self.legacy, "legacy"),
                    (self.batch, "batch"), (self.culvert, "culvert"),
                    (self.profile_runs, "profile;;tmp"), (self.profile_fork, "profile;;fork"),
                    (self.profile_archive, "profile;;archive"))
        for root, kind in mappings:
            try:
                parts = target.relative_to(os.path.abspath(root)).parts
            except ValueError:
                continue
            suffix = ""
            if "_pups" in parts:
                position = parts.index("_pups")
                child = parts[position + 1:]
                if len(child) != 3 or child[0] != "omni" or child[1] not in {"scenarios", "contrasts"}:
                    continue
                suffix = ";;" + ("omni" if child[1] == "scenarios" else "omni-contrast") + ";;" + child[2]
                parts = parts[:position]
            runid = None
            if kind == "primary" and len(parts) == 2 and parts[0] == parts[1][:2]:
                runid = parts[1]
            elif kind == "legacy" and len(parts) == 1:
                runid = parts[0]
            elif kind.startswith("profile;;") and len(parts) == 1:
                runid = kind + ";;" + parts[0]
            elif kind in {"batch", "culvert"} and len(parts) == 3 and parts[1] == "runs":
                runid = kind + ";;" + parts[0] + ";;" + parts[2]
            elif kind == "batch" and len(parts) == 2 and parts[1] == "_base":
                runid = "batch;;" + parts[0] + ";;_base"
            if runid and self.matches(runid + suffix, wd):
                return runid + suffix
        raise ValueError("Unmapped project location")


def signature(value):
    return (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns)


@contextmanager
def project_directory(root, relative):
    descriptors = []
    try:
        descriptor = os.open(os.path.realpath(root), os.O_PATH | os.O_DIRECTORY | os.O_NOFOLLOW)
        descriptors.append(descriptor)
        for component in relative:
            if component in {"", ".", ".."} or "/" in component:
                raise SourceScopeError(errno.EPERM, "source_scope_mismatch")
            descriptor = os.open(component, os.O_PATH | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
            descriptors.append(descriptor)
        yield descriptor, tuple(signature(os.fstat(value))[:2] for value in descriptors)
    except OSError as error:
        if error.errno in {errno.ELOOP, errno.ENOTDIR}:
            raise SourceScopeError(errno.EPERM, "source_scope_mismatch") from error
        raise
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)


def _source_descriptor(project_fd, name, locators):
    components = deque([name])
    links = 0
    directories = [os.dup(project_fd)]
    try:
        while components:
            component = components.popleft()
            if component in {"", "."}:
                continue
            if component == "..":
                if len(directories) == 1:
                    raise SourceScopeError(errno.EPERM, "source_scope_mismatch")
                os.close(directories.pop())
                continue
            value = os.stat(component, dir_fd=directories[-1], follow_symlinks=False)
            if stat.S_ISLNK(value.st_mode):
                links += 1
                if links > 40:
                    raise SourceScopeError(errno.ELOOP, "source_scope_mismatch")
                target = os.readlink(component, dir_fd=directories[-1])
                if os.path.isabs(target):
                    prefix = next((locator.rstrip("/") for locator in locators
                                   if target == locator.rstrip("/") or target.startswith(locator.rstrip("/") + "/")), None)
                    if prefix is None:
                        raise SourceScopeError(errno.EPERM, "source_scope_mismatch")
                    target = target[len(prefix):].lstrip("/")
                    while len(directories) > 1:
                        os.close(directories.pop())
                components.extendleft(reversed(target.split("/")))
                continue
            final = not components
            flags = (os.O_PATH if name == "READONLY" else os.O_RDONLY | os.O_NONBLOCK) if final else os.O_PATH | os.O_DIRECTORY
            descriptor = os.open(component, flags | os.O_NOFOLLOW, dir_fd=directories[-1])
            if final:
                actual = os.fstat(descriptor)
                if stat.S_ISLNK(actual.st_mode) or (name != "READONLY" and not stat.S_ISREG(actual.st_mode)):
                    os.close(descriptor)
                    raise SourceScopeError(errno.EPERM, "source_scope_mismatch")
                return descriptor, tuple(signature(os.fstat(value))[:2] for value in directories)
            directories.append(descriptor)
        if name == "READONLY":
            return os.dup(directories[-1]), tuple(signature(os.fstat(value))[:2] for value in directories)
        raise SourceScopeError(errno.EPERM, "source_scope_mismatch")
    finally:
        for descriptor in reversed(directories):
            os.close(descriptor)


def read_source(project_fd, name, locators):
    descriptor, chain = _source_descriptor(project_fd, name, locators)
    if name == "READONLY":
        try:
            return b"", os.fstat(descriptor), chain
        finally:
            os.close(descriptor)
    with os.fdopen(descriptor, "rb") as stream:
        before = os.fstat(stream.fileno())
        payload = stream.read() if name != "READONLY" else b""
        after = os.fstat(stream.fileno())
        if signature(before) != signature(after):
            raise OSError(errno.ESTALE, "source_drift")
        return payload, after, chain
