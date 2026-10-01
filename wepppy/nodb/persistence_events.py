"""Optional post-commit observer, independent of deployment dependencies."""

from dataclasses import dataclass
from datetime import datetime, timezone
import logging
import os
from typing import Callable

__all__ = ["ProjectCommit", "register_project_commit_observer", "notify_project_commit", "notify_committed", "initialize_project_commits"]

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ProjectCommit:
    runid: str
    wd: str
    source: str
    committed_at: datetime
    controller_filename: str | None = None

    def __post_init__(self):
        if self.source not in {"nodb", "readonly", "ttl", "lifecycle"}:
            raise ValueError("Unknown project commit source")
        if self.committed_at.tzinfo is None:
            raise ValueError("Project commit time must be timezone-aware")


_observer: Callable[[ProjectCommit], None] | None = None
notification_failures = 0


def initialize_project_commits():
    mode = os.getenv("WEPPPY_PROJECT_COMMIT_MODE", "disabled")
    write = os.getenv("WEPPCLOUD_RUN_CATALOG_WRITE_MODE", "timestamp_only")
    read = os.getenv("WEPPCLOUD_RUN_CATALOG_READ_MODE", "legacy")
    if mode not in {"disabled", "postgres"} or write not in {"timestamp_only", "catalog"} or read not in {"legacy", "postgres"}:
        raise ValueError("Unknown project catalog mode")
    if (read == "postgres" and write != "catalog") or (mode == "disabled" and (read == "postgres" or write == "catalog")):
        raise ValueError("Incompatible project catalog modes")
    if mode == "disabled":
        register_project_commit_observer(None)
        return
    if mode != "postgres":
        raise ValueError("Unknown project commit mode")
    from wepppy.weppcloud.run_catalog.adapter import initialize
    initialize()


def notify_committed(wd, runid, source, controller_filename=None):
    if _observer is None:
        return
    parts = os.path.normpath(wd).split(os.sep)
    if "_pups" in parts:
        position = parts.index("_pups")
        suffix = parts[position + 1:]
        if len(suffix) == 3 and suffix[0] == "omni" and suffix[1] in {"scenarios", "contrasts"}:
            kind = "omni" if suffix[1] == "scenarios" else "omni-contrast"
            identifiers = runid.split(";;")
            qualified = len(identifiers) in {3, 5} and identifiers[-2] in {"omni", "omni-contrast"} and not (len(identifiers) == 3 and identifiers[0] in {"batch", "culvert"})
            if not qualified:
                runid = runid + ";;" + kind + ";;" + suffix[2]
    notify_project_commit(ProjectCommit(runid, wd, source, datetime.now(timezone.utc), controller_filename))


def register_project_commit_observer(observer):
    global _observer
    _observer = observer


def notify_project_commit(event):
    global notification_failures
    if _observer is None:
        return
    try:
        _observer(event)
    except Exception:  # broad-except: post-commit observers cannot undo saved files; log bounded failure.
        notification_failures += 1
        logger.warning("project_commit_mirror_failed pid=%s runid=%s source=%s committed_at=%s process_failures=%s",
                       os.getpid(), event.runid, event.source, event.committed_at.isoformat(), notification_failures)
