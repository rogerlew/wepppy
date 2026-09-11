"""Visible, persistent attempt records independent of RQ retention."""
import json
import os
from pathlib import Path
import traceback

__all__ = ['write_json', 'record_attempts', 'record_error', 'require_visible_storage']


def write_json(path, value):
    """Atomic metadata replacement with an inspectable pending file."""
    path = Path(path)
    pending = path.with_name(path.name + '.pending')
    if path.is_symlink() or pending.is_symlink():
        raise ValueError('Artifact metadata must not use symbolic links.')
    pending.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')
    os.replace(pending, path)


def require_visible_storage(wd):
    """Do not mix new writes with an unmigrated legacy attempt tree."""
    from .production import WorkflowError
    legacy = Path(wd)/'postfire_debris_flow'/'.staging'
    if legacy.exists() or legacy.is_symlink():
        raise WorkflowError('migration_required', 'Project artifacts need migration before another operation.', 409)


def record_attempts(wd, state):
    """Called under the NoDb lock before replacement and after durable commit."""
    from .production import directory, safe
    require_visible_storage(wd)
    for kind in ('upload_attempt', 'run_attempt'):
        attempt = state[kind]
        if attempt is None:
            continue
        root = directory(wd, attempt['id'])
        root.mkdir(parents=True, exist_ok=True)
        path = safe(wd, root/'status.json', exists=False)
        write_json(path, {'schema_version': 1, 'kind': kind, 'attempt': attempt})


def record_error(wd, identity):
    """Retain the worker traceback, using the existing run exception convention."""
    from .production import directory, safe
    require_visible_storage(wd)
    root = directory(wd, identity)
    root.mkdir(parents=True, exist_ok=True)
    path = safe(wd, root/'error.log', exists=False)
    with path.open('a') as stream:
        stream.write(traceback.format_exc() + '\n')
