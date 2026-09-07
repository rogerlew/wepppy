"""Private publication primitives shared by Climate and RAP derived builders."""

from contextlib import ExitStack, contextmanager
import os
from pathlib import Path
import shutil
import tempfile
from typing import Iterator

import jsonpickle

__all__ = ["file_signature", "require_output_directory", "finalize", "publish_files"]


class _CommitOutcomeUnknown(RuntimeError):
    """Keep both artifact generations when the durable commit cannot be read."""


def file_signature(path: str | Path) -> tuple[str, int, int]:
    """Fingerprint a required input file without suppressing filesystem errors."""
    path = Path(path)
    stat = path.stat()
    return (str(path.resolve()), stat.st_mtime_ns, stat.st_size)


def _identity(path: str | Path) -> tuple[int, int, int, int]:
    stat = Path(path).stat()
    return (stat.st_dev, stat.st_ino, stat.st_mtime_ns, stat.st_size)


def require_output_directory(path: str | Path, wd: str) -> None:
    if not Path(path).resolve().is_relative_to(Path(wd).resolve()):
        raise ValueError("Derived output directory is outside the run working directory")


@contextmanager
def finalize(controller) -> Iterator[ExitStack]:
    """Hold the lock across fresh disk hydration, publication, and one dump."""
    controller.lock()
    committed = False
    try:
        lock_key = controller._distributed_lock_key
        fresh = type(controller)._hydrate_instance(
            os.path.abspath(controller.wd), False, False, False, use_redis_cache=False
        )
        if fresh._distributed_lock_key != lock_key:
            raise RuntimeError("derived build superseded by changed controller identity")
        # This is durable hydration, not a merge of collected controller state.
        controller.__dict__.clear()
        controller.__dict__.update(fresh.__dict__)
        with ExitStack() as publications:
            yield publications
            # Capture the intended *fresh final transaction*, solely to identify
            # an own commit if dump raises after replace. This is not collected
            # state, a mutation base, or a payload used to retry persistence.
            intended_payload = jsonpickle.encode(controller)
            try:
                controller.dump()
            except Exception as commit_error:  # broad-except: classify commit outcome before artifact cleanup
                # Commit boundary: dump can fail after replacing the NoDb file.
                # Never roll artifacts back beneath possibly committed metadata.
                try:
                    own_commit = Path(controller._nodb).read_text() == intended_payload
                except OSError:
                    # Unknown commit outcome: restoring files could corrupt an
                    # already committed controller. Keep the failure explicit.
                    raise _CommitOutcomeUnknown(
                        "Derived build commit outcome unknown; artifacts and recovery copies retained"
                    ) from commit_error
                if own_commit:
                    controller.logger.error("Derived build commit interrupted after possible NoDb commit; retaining artifacts")
                    publications.close()
                raise
            committed = True
    finally:
        if not committed:
            # Force the next singleton read to discard any uncommitted fields.
            controller._nodb_mtime = None
        controller.unlock()


@contextmanager
def publish_files(staged: str | Path, destination: str | Path, controller, *, remove=()) -> Iterator[None]:
    """Replace staged flat artifacts; restore previous files if commit fails.

    Call only inside the owning controller's finalization lock. A process crash
    remains a retryable interrupted build; this is not a multi-file transaction.
    """
    destination = Path(destination)
    require_output_directory(destination, controller.wd)
    if Path(staged).resolve().parent != destination.resolve():
        raise ValueError("Staged artifacts must be in the output directory")
    destination.mkdir(parents=True, exist_ok=True)
    published = []
    completed = False
    unknown_commit = False
    backup = Path(tempfile.mkdtemp(prefix=".derived-backup-", dir=destination))
    cleanup = False
    try:
        try:
            sources = {source.name: source for source in Path(staged).iterdir()}
            for name in sorted(set(sources) | set(remove)):
                controller._assert_lock_owned_for_dump()
                source = sources.get(name)
                if Path(name).name != name:
                    raise ValueError("Derived artifact must have a flat filename")
                if source is not None and (source.is_symlink() or not source.is_file()):
                    raise ValueError(f"Expected a regular staged artifact: {source.name}")
                target = destination / name
                previous = backup / name
                existed = os.path.lexists(target)
                if existed:
                    if target.is_symlink() or not target.is_file():
                        raise ValueError(f"Expected a regular output artifact: {target.name}")
                    shutil.copy2(target, previous)
                    if source is not None:
                        os.chmod(source, target.stat().st_mode & 0o777)
                if source is not None:
                    identity = _identity(source)
                    controller._assert_lock_owned_for_dump()
                    os.replace(source, target)
                else:
                    if existed:
                        controller._assert_lock_owned_for_dump()
                        target.unlink()
                    identity = None
                published.append((target, previous, existed, identity))
            try:
                yield
            except _CommitOutcomeUnknown:
                unknown_commit = True
                raise
            completed = True
        finally:
            if not completed and not unknown_commit:
                for target, previous, existed, identity in reversed(published):
                    controller._assert_lock_owned_for_dump()
                    current = _identity(target) if os.path.lexists(target) else None
                    if current != identity:
                        raise RuntimeError(f"Derived artifact changed during rollback: {target.name}")
                    if existed:
                        os.replace(previous, target)
                    elif identity is not None:
                        target.unlink()
            cleanup = not unknown_commit
    finally:
        if cleanup:
            shutil.rmtree(backup)
        else:
            controller.logger.error("Derived publication interrupted; recovery copies retained at %s", backup)
