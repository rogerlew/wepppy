"""Publish accepted model outputs in the ordinary project module directory."""
import hashlib
import os
from pathlib import Path
import uuid
from redis.exceptions import LockError

from .observability import write_json

from .postfire_debris_flow import PostfireDebrisFlow

__all__ = ['publish_outputs']


def publish_outputs(wd):
    """Publish the latest accepted bundle; also repairs older completed projects."""
    from .production import FILES, WorkflowError, digest, directory, safe, signature

    controller = PostfireDebrisFlow.tryGetInstance(str(wd))
    if controller is None:
        return []
    with controller._mutation_gate() as gate:
        controller = PostfireDebrisFlow.getInstance(str(wd))
        controller.lock()
        try:
            # Refresh under the same lock used to accept model results. A delayed
            # callback publishes the latest accepted run, never its earlier snapshot.
            PostfireDebrisFlow.getInstance(str(wd))
            accepted = controller.state['last_successful_run']
            if accepted is None:
                return []
            root = safe(wd, Path(wd)/'postfire_debris_flow', exists=False)
            source = directory(wd, accepted['id'])/'results'
            files = []
            for name in FILES:  # The canonical inventory places manifest.json last.
                src = safe(wd, source/name)
                dst = safe(wd, root/name, exists=False)
                if dst.exists() and not dst.is_file():
                    raise WorkflowError('invalid_path', 'Model output path is not a file.', 409)
                expected = accepted['artifacts'].get(str(src.relative_to(Path(wd).absolute())))
                if (not isinstance(expected, list) or len(expected) != 5
                        or signature(wd, src) != expected[:4]):
                    raise WorkflowError('changed_file', 'Accepted model files changed.', 409)
                files.append((src, dst, expected))
            work_root = safe(wd, root/'publication_work', exists=False)
            work_root.mkdir(exist_ok=True)
            staged = work_root/uuid.uuid4().hex
            staged.mkdir()
            write_json(staged/'status.json', {'status': 'incomplete', 'accepted_id': accepted['id']})
            for src, dst, expected in files:
                checksum = hashlib.sha256()
                remaining = expected[1]
                # Ordinary creation honors the worker umask, as other module
                # outputs do. Bound reads to the accepted artifact's size.
                with src.open('rb') as incoming, (staged/dst.name).open('xb') as outgoing:
                    while remaining:
                        block = incoming.read(min(1024*1024, remaining))
                        if not block:
                            raise WorkflowError('changed_file', 'Accepted model files changed.', 409)
                        outgoing.write(block)
                        checksum.update(block)
                        remaining -= len(block)
                    if incoming.read(1) or checksum.hexdigest() != expected[4]:
                        raise WorkflowError('changed_file', 'Accepted model files changed.', 409)
                if digest(staged/dst.name) != expected[4]:
                    raise WorkflowError('changed_file', 'Copied model files changed.', 409)
            # Every file is ready before exposing any replacement. The manifest
            # follows the tables; interrupted publication can be rerun unchanged.
            for _, dst, _ in files:
                safe(wd, dst, exists=False)
            if not gate.owned():
                raise LockError('Postfire publication lease expired.')
            controller._assert_lock_owned_for_dump()
            for _, dst, _ in files:
                safe(wd, dst, exists=False)
                os.replace(staged/dst.name, dst)
            write_json(staged/'status.json', {'status': 'complete', 'accepted_id': accepted['id']})
            return [str(dst) for _, dst, _ in files]
        finally:
            controller.unlock()
