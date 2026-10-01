"""Optional, deployment-owned project metadata projection."""

import logging
import os

__all__ = ["notify_path_commit"]


def notify_path_commit(wd, source):
    if os.getenv("WEPPPY_PROJECT_COMMIT_MODE", "disabled") == "disabled":
        return
    from wepppy.nodb.persistence_events import notify_committed
    from .paths import Roots
    try:
        runid = Roots.from_environ().identify(str(wd))
    except ValueError:
        logging.getLogger(__name__).warning("project_commit_identity_unmapped source=%s", source)
    else:
        notify_committed(str(wd), runid, source)
