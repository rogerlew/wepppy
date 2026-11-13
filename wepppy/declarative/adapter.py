"""Image-local private operator adapter and two fixed RQ operations."""

from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path
import sys
from uuid import uuid4

from . import records
from .observations import runtime
from .policy import attempt_authority, initialization_authority
from .schema import CONFIG, PROTOCOL, SCHEMA, AdmissionError, identities, loads, validate, verify_evidence

LOGGER = logging.getLogger(__name__)


def connection():
    import redis
    from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
    return redis.Redis(**redis_connection_kwargs(RedisDB.RQ))


def location(submission_id):
    from wepppy.weppcloud.utils.helpers import get_wd
    runid, _ = identities(submission_id)
    return runid, Path(get_wd(runid))


def approvals():
    return loads(Path("/etc/weppcloud/declarative/approved-images.json").read_text())


def _binding(admission, job):
    observed = runtime(job)
    expected = admission["runtime"]
    for key in ("pod_uid", "pod_name", "namespace", "container"):
        if observed[key] != expected[key]:
            raise AdmissionError("Worker does not match observed container")
    if observed["worker_name"] != expected["pod_uid"] or observed["queue"] != admission["queue"]:
        raise AdmissionError("RQ worker does not match observed container")
    return observed


def _state(wd, **changes):
    value = records.read(wd, "provenance/build.json")
    value.update(changes, updated_at=records.utcnow())
    records.write(wd, "provenance/build.json", value)
    return value


def _validate_owner(owner):
    from wepppy.weppcloud.app import User, app, db
    with app.app_context():
        user = db.session.get(User, owner)
        if user is None or not bool(user.active):
            raise AdmissionError("Owner is not an active existing user")


def submit(payload):
    from rq import Queue
    from wepppy.nodb.core import Ron
    from wepppy.query_engine.catalog_refresh import catalog_lifecycle_guard, invalidate_catalog_incarnation
    from wepppy.weppcloud.user_preferences import register_owned_run
    from wepppy.weppcloud.utils.run_ttl import initialize_ttl

    if set(payload) != {"definition", "owner_id", "evidence"}:
        raise AdmissionError("Invalid submission fields")
    definition = validate(payload["definition"], approvals())
    evidence = verify_evidence(definition, payload["evidence"])
    owner = payload["owner_id"]
    if type(owner) is not int or owner <= 0:
        raise AdmissionError("An existing owner ID is required")
    _validate_owner(owner)
    for key, env in (("pod_uid", "DECLARATIVE_POD_UID"), ("pod_name", "DECLARATIVE_POD_NAME"),
                     ("namespace", "DECLARATIVE_NAMESPACE"), ("container", "DECLARATIVE_CONTAINER")):
        if evidence[key] != os.environ.get(env):
            raise AdmissionError("Adapter is not in the observed container")
    if definition["submission_id"] != os.environ.get("DECLARATIVE_SUBMISSION_ID"):
        raise AdmissionError("Dedicated worker belongs to another submission")
    runid, wd = location(definition["submission_id"])
    _, queue = identities(definition["submission_id"])
    wd.parent.mkdir(parents=True, exist_ok=True)
    with catalog_lifecycle_guard(wd, allow_missing=True):
        if wd.exists():
            prior = records.marker(wd)
            if prior is None or prior["definition"] != definition or prior["owner_id"] != owner:
                raise AdmissionError("Conflicting or incomplete project reservation")
            return status(definition["submission_id"])
        wd.mkdir()
        invalidate_catalog_incarnation(wd)
        admission = {"schema": SCHEMA, "runid": runid, "definition": definition,
                     "owner_id": owner, "queue": queue, "attempt_id": str(uuid4()),
                     "finalizer_id": str(uuid4()), "runtime": evidence, "created_at": records.utcnow()}
        records.write(wd, "provenance/declarative.json", admission, exclusive=True)
        records.write(wd, "provenance/build.json", {
            "processing": "admitted", "protection": "pending", "verified": False,
            "error": None, "job_ids": [admission["attempt_id"], admission["finalizer_id"]],
        }, exclusive=True)
        # Initialization has a bounded internal scope, never supplied by an HTTP caller.
        try:
            with initialization_authority(wd):
                ron = Ron(str(wd), CONFIG)
                if ron.dem_db != definition["source"] or ron.cellsize != 30:
                    raise AdmissionError("Image configuration does not implement the admitted DEM contract")
                ron.public = True
                initialize_ttl(str(wd))
                register_owned_run(runid, CONFIG, owner)
        except Exception:  # broad-except: private orchestration boundary
            # Initialization boundary: no science was dispatched; retain a protected failure.
            _state(wd, processing="failed", science_not_dispatched=True,
                   error={"code": "initialization_failed", "message": "Project initialization failed"})
            raise
        # Record dispatch intent before enqueue: a lost response cannot authorize replay.
        _state(wd, dispatch_intent=True)
        try:
            Queue(queue, connection=connection()).enqueue(
                "wepppy.declarative.adapter.execute_dem", runid, job_id=admission["attempt_id"], job_timeout=600,
                result_ttl=604800, failure_ttl=604800,
            )
        except Exception:  # broad-except: private orchestration boundary
            # Enqueue boundary: a lost acknowledgement cannot authorize science replay.
            _state(wd, processing="interrupted",
                   error={"code": "dispatch_uncertain", "message": "Scientific dispatch is uncertain"})
            raise
    return status(definition["submission_id"])


def execute_dem(runid):
    from rq import get_current_job
    from wepppy.rq.project_rq import fetch_dem_rq
    from wepppy.weppcloud.utils.helpers import get_wd
    wd = Path(get_wd(runid))
    job = get_current_job()
    with attempt_authority(wd, job) as admission:
        observed = _binding(admission, job)
        with records.guard(wd):
            records.write(wd, f"provenance/claims/{job.id}.json", {
                "attempt_id": job.id, "started_at": records.utcnow(), "runtime": observed,
            }, exclusive=True)
            _state(wd, processing="running")
        try:
            fetch_dem_rq(runid, admission["definition"]["extent"], None, None)
        except Exception:  # broad-except: private orchestration boundary
            # Adapter orchestration boundary: retain outcome; RQ owns failure reporting.
            with records.guard(wd):
                _state(wd, processing="failed", science_returned=True,
                       error={"code": "dem_failed", "message": "DEM acquisition or evidence failed"})
            raise
        with records.guard(wd):
            _state(wd, processing="succeeded", science_returned=True)


def status(submission_id):
    from rq.job import Job
    from rq.exceptions import NoSuchJobError
    runid, wd = location(submission_id)
    admission = records.marker(wd)
    if admission is None:
        raise AdmissionError("No admitted project")
    state = records.read(wd, "provenance/build.json")
    states = {}
    for key in ("attempt_id", "finalizer_id"):
        try:
            job = Job.fetch(admission[key], connection=connection())
            states[key] = str(job.get_status().value)
        except NoSuchJobError:
            states[key] = "missing"
    if (state["processing"] in {"admitted", "running"}
            and states["attempt_id"] in {"missing", "failed", "stopped", "canceled"}
            and not state.get("science_returned")):
        state = {**state, "processing": "interrupted", "error": {
            "code": "execution_uncertain", "message": "Execution is incomplete; automatic replay is prohibited"}}
    return {"protocol": PROTOCOL, "command": "status", "submission_id": submission_id,
            "runid": runid, **state, "jobs": states}


def _settled_science(wd, admission):
    from rq.job import Job
    state = records.read(wd, "provenance/build.json")
    if state.get("science_not_dispatched") and not state.get("dispatch_intent"):
        return "failed"
    job = Job.fetch(admission["attempt_id"], connection=connection())
    outcome = job.get_status().value
    if outcome not in {"finished", "failed", "stopped", "canceled"} or job.get_executions():
        raise AdmissionError("Scientific writer is not settled")
    if outcome in {"failed", "stopped"} and not state.get("science_returned"):
        cleanup = job.meta.get("directory_lock_cleanup", {})
        if cleanup.get("state") != "complete":
            raise AdmissionError("Interrupted writer cleanup is unverified")
    return "canceled" if state.get("cancel_requested") or outcome == "canceled" else (
        "succeeded" if outcome == "finished" and state["processing"] == "succeeded" else "failed")


def _verify_science_boundary(wd, admission):
    from wepppy.nodb.core import Ron
    state = records.read(wd, "provenance/build.json")
    record = records.read(wd, f"provenance/attempts/{admission['attempt_id']}.json")
    records.verify_checkpoint(wd, state.get("checkpoint"), admission["attempt_id"])
    # Verification must observe disk state after the separate science work horse.
    ron = Ron.load_detached(str(wd))
    from wepppy.microservices.elevationquery import _locate_dem
    inputs = record["inputs"]
    if (record["outcome"] != "succeeded" or record["attempt_id"] != admission["attempt_id"]
            or _locate_dem(Path(wd)) != Path(ron.dem_fn)
            or records.digest(ron.dem_fn) != record["output"]["sha256"]
            or ron.dem_db != inputs["source"] or list(ron.map.extent) != inputs["extent"]
            or ron.map.cellsize != inputs["cellsize"]):
        raise AdmissionError("Science boundary changed before finalization")


def finalize(submission_id, evidence):
    from rq import Queue
    _, wd = location(submission_id)
    with records.guard(wd):
        admission = records.marker(wd)
        verify_evidence(admission["definition"], evidence, admission["runtime"])
        outcome = _settled_science(wd, admission)
        state = records.read(wd, "provenance/build.json")
        if not state.get("finalization_intent"):
            _state(wd, processing=outcome, finalization_intent=True)
            Queue(admission["queue"], connection=connection()).enqueue(
                "wepppy.declarative.adapter.finalize_dem", admission["runid"], job_id=admission["finalizer_id"],
                job_timeout=600, result_ttl=604800, failure_ttl=604800,
            )
    return status(submission_id)


def finalize_dem(runid):
    from rq import get_current_job
    from wepppy.rq.project_rq import set_run_readonly_rq
    from wepppy.weppcloud.utils.helpers import get_wd
    wd = Path(get_wd(runid))
    job = get_current_job()
    with attempt_authority(wd, job, finalizer=True) as admission, records.guard(wd):
        # Duplicate delivery must never overwrite an earlier finalization outcome.
        if records.safe_path(wd, f"provenance/claims/{job.id}.json").exists():
            raise AdmissionError("Finalization was already attempted")
        try:
            observed = _binding(admission, job)
            outcome = _settled_science(wd, admission)
            if outcome == "succeeded":
                _verify_science_boundary(wd, admission)
            records.write(wd, f"provenance/claims/{job.id}.json", {
                "attempt_id": job.id, "runtime": observed, "started_at": records.utcnow(),
            }, exclusive=True)
            records.write(wd, "provenance/protected.json", records.protected_manifest(wd), exclusive=True)
            finalizer_record = {"schema": "dem-finalization-v1", "attempt_id": job.id,
                                "runtime": observed, "outcome": "pending", "started_at": records.utcnow()}
            records.write(wd, f"provenance/attempts/{job.id}.json", finalizer_record, exclusive=True)
            set_run_readonly_rq(runid, True)
            finalizer_record.update(outcome="succeeded", ended_at=records.utcnow())
            records.write(wd, f"provenance/attempts/{job.id}.json", finalizer_record)
            finalizer_commit = records.checkpoint(wd, job.id, [f"attempts/{job.id}.json"])
        except Exception:  # broad-except: private orchestration boundary
            # Finalization boundary: protection failure cannot become verified success.
            _state(wd, protection="failed", error={"code": "protection_failed",
                                                 "message": "Read-only finalization failed"})
            raise
        _state(wd, processing=outcome, protection="readonly", finalizer_runtime=observed,
               finalizer_checkpoint=finalizer_commit)


def complete(submission_id, evidence):
    from rq.job import Job
    _, wd = location(submission_id)
    with records.guard(wd):
        admission = records.marker(wd)
        verify_evidence(admission["definition"], evidence, admission["runtime"])
        state = records.read(wd, "provenance/build.json")
        if state.get("verified"):
            return status(submission_id)
        job = Job.fetch(admission["finalizer_id"], connection=connection())
        if job.get_status().value != "finished" or job.get_executions():
            raise AdmissionError("Finalization is not complete")
        if state["protection"] != "readonly" or not (wd / "READONLY").is_file():
            raise AdmissionError("Project is not protected")
        records.verify_protected(wd)
        records.verify_checkpoint(wd, state.get("finalizer_checkpoint"), admission["finalizer_id"])
        if state["processing"] != "succeeded":
            return status(submission_id)
        _verify_science_boundary(wd, admission)
        record = records.read(wd, f"provenance/attempts/{admission['attempt_id']}.json")
        for observed in (record["runtime"], state["finalizer_runtime"]):
            for key in ("pod_uid", "pod_name", "namespace", "container"):
                if observed[key] != evidence[key]:
                    raise AdmissionError("Attempt/runtime mismatch")
            if observed["worker_name"] != evidence["pod_uid"] or observed["queue"] != admission["queue"]:
                raise AdmissionError("Attempt worker mismatch")
        if state["processing"] == "succeeded":
            if not state.get("checkpoint") or record["outcome"] != "succeeded":
                raise AdmissionError("Required science checkpoint is missing")
            records.verify_checkpoint(wd, state["checkpoint"], admission["attempt_id"])
            _state(wd, verified=True, runtime_final=evidence)
    return status(submission_id)


def cancel(submission_id):
    from rq.command import send_stop_job_command
    from rq.job import Job
    _, wd = location(submission_id)
    with records.guard(wd):
        admission = records.marker(wd)
        state = records.read(wd, "provenance/build.json")
        if state["protection"] == "readonly":
            return status(submission_id)
        _state(wd, cancel_requested=True)
        job = Job.fetch(admission["attempt_id"], connection=connection())
        if job.origin != admission["queue"]:
            raise AdmissionError("Cancellation ownership mismatch")
        if job.get_status().value == "started":
            send_stop_job_command(connection(), job.id)
        elif job.get_status().value in {"queued", "deferred", "scheduled"}:
            job.cancel()
    return status(submission_id)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("submit", "status", "cancel", "finalize", "complete", "worker"))
    args = parser.parse_args()
    if args.command == "worker":
        from wepppy.rq.rq_worker import WepppyRqWorker
        _, queue = identities(os.environ["DECLARATIVE_SUBMISSION_ID"])
        WepppyRqWorker([queue], connection=connection(), name=os.environ["DECLARATIVE_POD_UID"]).work()
        return 0
    try:
        payload = loads(sys.stdin.read())
        if args.command == "submit":
            result = submit(payload)
        elif args.command in {"finalize", "complete"}:
            function = finalize if args.command == "finalize" else complete
            result = function(payload["submission_id"], payload["evidence"])
        else:
            result = (status if args.command == "status" else cancel)(payload["submission_id"])
        result["command"] = args.command
        print(json.dumps(result, sort_keys=True, allow_nan=False))
        return 0
    except Exception as exc:  # broad-except: private orchestration boundary
        # Private CLI boundary: do not expose secrets from provider/database exceptions.
        LOGGER.error("Declarative adapter command failed command=%s error_type=%s",
                     args.command, type(exc).__name__)
        print(json.dumps({"protocol": PROTOCOL, "command": args.command, "verified": False,
                          "error": {"code": "adapter_failed", "message": "Command failed; inspect operator logs"}}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
