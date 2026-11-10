"""Declarative-only mutation ownership; ordinary projects keep existing behavior."""

from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path

from .records import ProtectedProjectError, marker, read

_authority = ContextVar("declarative_attempt", default=None)


def reject_mutation(wd):
    if marker(wd) is not None:
        raise ProtectedProjectError("Declarative projects are protected from editing")


def require_controller_mutation(wd):
    admission = marker(wd)
    if admission is None:
        return
    active = _authority.get()
    if active and active[0] == str(Path(wd).resolve()) and active[1] in {
        admission["attempt_id"], admission["finalizer_id"], "initialize",
    }:
        return
    raise ProtectedProjectError("Declarative configuration is protected")


@contextmanager
def initialization_authority(wd):
    token = _authority.set((str(Path(wd).resolve()), "initialize"))
    try:
        yield
    finally:
        _authority.reset(token)


def require_task(wd, operation):
    admission = marker(wd)
    if admission is None:
        return
    active = _authority.get()
    if active and active[0] == str(Path(wd).resolve()):
        expected = "fetch_dem_rq" if active[1] == admission["attempt_id"] else "set_run_readonly_rq"
        if operation == expected and active[1] in (admission["attempt_id"], admission["finalizer_id"]):
            return
    if operation in {"archive_rq", "restore_archive_rq"}:
        require_settled(wd)
        return
    raise ProtectedProjectError("Task cannot change a declarative project")


def require_settled(wd):
    if marker(wd) is None:
        return
    state = read(wd, "provenance/build.json")
    if state.get("processing") not in {"succeeded", "failed", "canceled"} or state.get("protection") != "readonly":
        raise ProtectedProjectError("Declarative writers are not confirmed settled")
    if not (Path(wd) / "READONLY").is_file():
        raise ProtectedProjectError("Declarative protection is incomplete")


@contextmanager
def attempt_authority(wd, job, *, finalizer=False):
    admission = marker(wd)
    key = "finalizer_id" if finalizer else "attempt_id"
    if (admission is None or job is None or job.id != admission[key]
            or job.origin != admission["queue"]):
        raise ProtectedProjectError("Attempt does not own this declarative project")
    token = _authority.set((str(Path(wd).resolve()), job.id))
    try:
        yield admission
    finally:
        _authority.reset(token)


def require_queued_job(wd, job):
    admission = marker(wd)
    if admission is None:
        return
    operations = {
        "wepppy.declarative.adapter.execute_dem": "attempt_id",
        "wepppy.declarative.adapter.finalize_dem": "finalizer_id",
    }
    field = operations.get(job.func_name)
    if field and job.id == admission[field] and job.origin == admission["queue"]:
        return
    require_task(wd, job.func_name.rsplit(".", 1)[-1])
