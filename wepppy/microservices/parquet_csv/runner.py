"""Async process ownership with cross-process, artifact-lifetime admission."""
from __future__ import annotations

import asyncio
import fcntl
import errno
import hashlib
import math
import logging
import os
from pathlib import Path
import shutil
import signal
import stat
import json
import time
from dataclasses import dataclass

from .provenance import HEX, ROOT, strict_json, validate

LOGGER = logging.getLogger(__name__)

MAX_INPUT = 512 * 1024 * 1024
DIAGNOSTIC_LIMIT = 4096
CLI_ERRORS = {2: 'arguments', 3: 'input_rejected', 4: 'resource_limit', 5: 'io_error', 6: 'validation_error', 7: 'no_rows_matched_filter', 8: 'parquet_filter_row_limit_exceeded'}


class ConversionError(RuntimeError):
    def __init__(self, code: str, *, input_sha256=None, input_bytes=None):
        self.input_sha256 = input_sha256
        self.input_bytes = input_bytes
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class Limits:
    memory_bytes: int = 1024 * 1024 * 1024
    cpu_seconds: int = 100
    output_bytes: int = 2 * 1024 * 1024 * 1024
    wall_seconds: float = 120
    staging_seconds: float = 30

    def __post_init__(self):
        for field, ceiling in [('memory_bytes', 1024**3), ('cpu_seconds', 120), ('output_bytes', 2 * 1024**3)]:
            value = getattr(self, field)
            if type(value) is not int or not 0 < value <= ceiling:
                raise ValueError(f'invalid {field}')
        for field in ['wall_seconds', 'staging_seconds']:
            value = getattr(self, field)
            if type(value) not in (int, float) or not 0 < value <= 180 or not math.isfinite(value):
                raise ValueError(f'invalid {field}')


def _identity(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _private_root(root: Path):
    try:
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
        info = root.lstat()
    except OSError as exc:
        raise ConversionError('io_error') from exc
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid() or info.st_mode & 0o077:
        raise ConversionError('io_error')


def _admit(root: Path) -> tuple[int, Path]:
    for index in range(2):
        path = root / f'slot-{index}.lock'
        fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or info.st_mode & 0o077 or info.st_nlink != 1:
            os.close(fd)
            raise ConversionError('io_error')
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            if _identity(os.stat(path, follow_symlinks=False)) != _identity(info):
                raise ConversionError('io_error')
            return fd, root / f'slot-{index}'
        except BlockingIOError:
            os.close(fd)
        except BaseException:  # broad-except: release admission descriptor on any failure
            # Admission boundary: never leak a descriptor on failed lock validation.
            os.close(fd)
            raise
    raise ConversionError('busy')


@dataclass
class Artifact:
    path: Path
    rows: int
    bytes: int
    input_sha256: str
    wall_seconds: float
    peak_rss_kib: int
    cpu_seconds: float
    _slot: int | None
    input_bytes: int | None = None

    def cleanup(self):
        if self._slot is None:
            return
        try:
            shutil.rmtree(self.path.parent)
        except OSError as exc:
            # Keep the slot held: capacity has not been reclaimed.
            raise ConversionError('cleanup_failed') from exc
        os.close(self._slot)
        self._slot = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.cleanup()


async def _owned_thread(func, *args):
    """Do not release file/slot ownership while an uncancellable I/O thread runs."""
    task = asyncio.create_task(asyncio.to_thread(func, *args))
    try:
        return await asyncio.shield(task)
    except asyncio.CancelledError:
        # A late I/O failure must not replace the caller's cancellation. Observe
        # the drained outcome without exposing paths or dropping diagnostics.
        results = await _finish_despite_cancellation(asyncio.gather(task, return_exceptions=True))
        if isinstance(results[0], BaseException):
            LOGGER.warning('CSV I/O failed during cancellation type=%s', type(results[0]).__name__)
        raise


async def _drain(stream):
    result = bytearray()
    while True:
        chunk = await stream.read(min(1024, DIAGNOSTIC_LIMIT + 1 - len(result)))
        if not chunk:
            return bytes(result)
        result.extend(chunk)
        if len(result) > DIAGNOSTIC_LIMIT:
            raise ConversionError('diagnostic_overflow')


async def _finish_despite_cancellation(task):
    """Drain owned cleanup even if the caller cancels repeatedly."""
    while not task.done():
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError:
            continue
    return task.result()


async def _kill_and_reap(process):
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass  # The process group has already exited.
    # SIGKILL may be pending in a descendant's kernel wait. Retain capacity and
    # scratch until all non-zombie group members have actually stopped.
    while _group_alive(process.pid):
        await asyncio.sleep(.01)
    await process.wait()


def _group_alive(pgid):
    try:
        for entry in Path('/proc').iterdir():
            if not entry.name.isdigit():
                continue
            try:
                fields = (entry / 'stat').read_text().rpartition(') ')[2].split()
            except (FileNotFoundError, ProcessLookupError):
                continue  # Process exited before open or between open and read.
            if len(fields) < 3:
                raise ConversionError('cleanup_failed')
            if int(fields[2]) == pgid and fields[0] != 'Z':
                return True
    except OSError as exc:
        # Cleanup observation boundary: do not release ownership if /proc cannot
        # establish that every live process-group member has stopped.
        raise ConversionError('cleanup_failed') from exc
    return False


async def _stage(source: Path, destination: Path, deadline: float) -> str:
    h = hashlib.sha256()
    try:
        fd = os.open(source, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    except OSError as exc:
        code = 'source_rejected' if exc.errno in (errno.ENOENT, errno.ENOTDIR, errno.ELOOP) else 'io_error'
        raise ConversionError(code) from exc
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size < 12:
            raise ConversionError('source_rejected')
        if before.st_size > MAX_INPUT:
            raise ConversionError('input_too_large')
        with os.fdopen(fd, 'rb', closefd=False) as src:
            with destination.open('xb') as out:
                total = 0
                while True:
                    if time.monotonic() > deadline:
                        raise ConversionError('staging_timeout')
                    chunk = await _owned_thread(src.read, 1024 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > MAX_INPUT:
                        raise ConversionError('input_too_large')
                    await _owned_thread(out.write, chunk)
                    h.update(chunk)
                    await asyncio.sleep(0)
            if _identity(before) != _identity(os.fstat(src.fileno())) or total != before.st_size:
                raise ConversionError('source_changed')
        destination.chmod(0o400)
    except OSError as exc:
        raise ConversionError('io_error') from exc
    finally:
        os.close(fd)
    return h.hexdigest()


def _result(stdout, stderr, returncode, path, digest, limits):
    if returncode == -signal.SIGALRM:
        raise ConversionError("timeout")
    if returncode != 0:
        if returncode not in CLI_ERRORS:
            raise ConversionError('child_failed')
        try:
            value = strict_json(stderr)
        except (ValueError, UnicodeError) as exc:
            raise ConversionError('protocol_error') from exc
        if stdout or type(value) is not dict or set(value) != {'version', 'status', 'code'} or type(value['version']) is not int or value['version'] != 2 or value['status'] != 'error' or value['code'] != CLI_ERRORS[returncode]:
            raise ConversionError('protocol_error')
        raise ConversionError(value['code'])
    try:
        value = strict_json(stdout)
    except (ValueError, UnicodeError) as exc:
        raise ConversionError('protocol_error') from exc
    keys = {'version', 'status', 'rows', 'bytes', 'input_sha256', 'peak_rss_kib', 'cpu_seconds'}
    if stderr or type(value) is not dict or set(value) != keys:
        raise ConversionError('protocol_error')
    if type(value['version']) is not int or value['version'] != 2 or value['status'] != 'ok':
        raise ConversionError('protocol_error')
    for field, lower, upper in [('rows', 0, 10_000_000), ('bytes', 1, limits.output_bytes), ('peak_rss_kib', 1, limits.memory_bytes // 1024)]:
        if type(value[field]) is not int or not lower <= value[field] <= upper:
            raise ConversionError('protocol_error')
    if type(value['cpu_seconds']) not in (int, float) or not 0 <= value['cpu_seconds'] <= limits.cpu_seconds + 1 or not math.isfinite(value['cpu_seconds']):
        raise ConversionError('protocol_error')
    if not isinstance(value['input_sha256'], str) or not HEX.fullmatch(value['input_sha256']) or value['input_sha256'] != digest:
        raise ConversionError('protocol_error')
    try:
        info = path.lstat()
    except OSError as exc:
        raise ConversionError('output_invalid') from exc
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != os.geteuid() or info.st_mode & 0o077 or info.st_size != value['bytes']:
        raise ConversionError('output_invalid')
    return value


class Converter:
    def __init__(self, binary: Path, provenance: Path, scratch_root: Path, limits: Limits = Limits(), *, source_root: Path = ROOT):
        self.source_root = Path(source_root).absolute()
        self.binary = Path(binary).absolute()
        self.provenance = Path(provenance).absolute()
        self.root = Path(scratch_root).absolute()
        self.limits = limits

    async def convert(self, source: Path, filter_tree: dict | None = None) -> Artifact:
        started = time.monotonic()
        _private_root(self.root)
        try:
            slot, request = _admit(self.root)
        except OSError as exc:
            raise ConversionError('io_error') from exc
        digest = None
        input_bytes = None
        request_owned = False
        process = None
        spawn = None
        io_tasks = []
        try:
            try:
                await _owned_thread(validate, self.binary, self.provenance, self.source_root)
            except (ValueError, OSError, UnicodeError, TypeError) as exc:
                raise ConversionError('provenance_invalid') from exc
            # The inherited flock proves no live child/response owns this slot.
            if request.exists() or request.is_symlink():
                info = request.lstat()
                if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid() or info.st_mode & 0o077:
                    raise ConversionError('cleanup_failed')
                request_owned = True
                shutil.rmtree(request)
            request.mkdir(mode=0o700)
            request_owned = True
            try:
                raw = json.dumps({'version': 2, 'filter': filter_tree}, ensure_ascii=False,
                                 allow_nan=False, separators=(',', ':')).encode('utf-8')
            except (ValueError, UnicodeError, TypeError) as exc:
                raise ConversionError('validation_error') from exc
            if len(raw) > 131072:
                raise ConversionError('validation_error')
            fd = os.open(request / 'request.json', os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, 'wb') as stream:
                stream.write(raw)
            digest = await _stage(Path(source), request / 'input.parquet', time.monotonic() + self.limits.staging_seconds)
            input_bytes = (request / 'input.parquet').stat().st_size
            env = {'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8', 'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1', 'RAYON_NUM_THREADS': '1'}
            argv = [str(self.binary), '--request-root', str(request), '--max-memory-bytes', str(self.limits.memory_bytes), '--max-cpu-seconds', str(self.limits.cpu_seconds), '--max-output-bytes', str(self.limits.output_bytes), '--parent-pid', str(os.getpid()), '--admission-fd', str(slot), '--max-wall-seconds', str(math.ceil(self.limits.wall_seconds))]
            spawn = asyncio.create_task(asyncio.create_subprocess_exec(*argv, env=env, stdin=asyncio.subprocess.DEVNULL, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, start_new_session=True, close_fds=True, pass_fds=(slot,)))
            try:
                process = await asyncio.shield(spawn)
            except OSError as exc:
                raise ConversionError('spawn_failed') from exc
            io_tasks = [asyncio.create_task(_drain(process.stdout)), asyncio.create_task(_drain(process.stderr)), asyncio.create_task(process.wait())]
            try:
                stdout, stderr, code = await asyncio.wait_for(asyncio.gather(*io_tasks), self.limits.wall_seconds)
            except TimeoutError as exc:
                raise ConversionError('timeout') from exc
            await _kill_and_reap(process)
            path = request / 'output.csv'
            value = _result(stdout, stderr, code, path, digest, self.limits)
            return Artifact(path, value['rows'], value['bytes'], digest, time.monotonic() - started, value['peak_rss_kib'], value['cpu_seconds'], slot, input_bytes)
        except BaseException as failure:  # broad-except: reap owned child and drain cancellation
            if isinstance(failure, ConversionError):
                failure.input_sha256 = digest
                failure.input_bytes = input_bytes
            # Deliberate ownership boundary: cleanup/reap even for repeated task
            # cancellation or caller exceptions; preserve the original failure.
            async def cleanup():
                child = process
                if child is None and spawn is not None:
                    try:
                        child = await spawn
                    except OSError:
                        pass  # Spawn failed: there is no owned process to reap.
                if child is not None:
                    await _kill_and_reap(child)
                for task in io_tasks:
                    if not task.done():
                        task.cancel()
                if io_tasks:
                    await asyncio.gather(*io_tasks, return_exceptions=True)
                try:
                    if request_owned and request.exists():
                        shutil.rmtree(request)
                except OSError as exc:
                    raise ConversionError('cleanup_failed') from exc
                os.close(slot)
            await _finish_despite_cancellation(asyncio.create_task(cleanup()))
            if isinstance(failure, OSError):
                raise ConversionError('io_error', input_sha256=digest, input_bytes=input_bytes) from failure
            raise
