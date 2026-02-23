from __future__ import annotations

import logging
import os
import shutil
from os.path import exists as _exists
from typing import Any, Mapping

import redis
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from rq import Queue
from rq.exceptions import NoSuchJobError
from rq.job import Job

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.config.secrets import get_secret
from wepppy.nodb.base import lock_statuses
from wepppy.nodb.core import Ron
from wepppy.nodb.redis_prep import RedisPrep
from wepppy.nodb.status_messenger import StatusMessenger
from wepppy.rq.project_rq import archive_rq, fork_rq, restore_archive_rq
from wepppy.weppcloud.utils.helpers import get_primary_wd, get_run_owners_lazy, get_wd
from wepppy.weppcloud.utils.runid import generate_runid

from .auth import AuthError, authorize_run_access, require_jwt
from .openapi import agent_route_responses, rq_operation_id
from .payloads import parse_request_payload
from .responses import error_response, error_response_with_traceback

logger = logging.getLogger(__name__)

router = APIRouter()

RQ_TIMEOUT = int(os.getenv("RQ_ENGINE_RQ_TIMEOUT", "216000"))
RQ_ENQUEUE_SCOPES = ["rq:enqueue"]


def _is_profile_target_runid(runid: str) -> bool:
    return str(runid).startswith("profile;;")


def _resolve_bearer_claims(request: Request) -> Mapping[str, Any] | None:
    if "authorization" not in {key.lower() for key in request.headers.keys()}:
        return None
    return require_jwt(request, required_scopes=RQ_ENQUEUE_SCOPES)


def has_archive(runid: str) -> bool:
    wd = get_wd(runid)
    archives_dir = os.path.join(wd, "archives")
    if not os.path.isdir(archives_dir):
        return False
    for entry in os.scandir(archives_dir):
        if entry.is_file() and entry.name.endswith(".zip"):
            return True
    return False


_RUNNING_ARCHIVE_JOB_STATUSES = {"queued", "started", "deferred", "scheduled"}
_ARCHIVE_JOB_STATUS_ERROR = "__status_lookup_error__"


def _archive_job_status(job_id: str) -> str | None:
    try:
        conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
        with redis.Redis(**conn_kwargs) as redis_conn:
            job = Job.fetch(job_id, connection=redis_conn)
            return job.get_status(refresh=True)
    except NoSuchJobError:
        return None
    except Exception:
        return _ARCHIVE_JOB_STATUS_ERROR


def _archive_job_in_progress(prep: Any) -> bool:
    existing_job_id = prep.get_archive_job_id()
    if not existing_job_id:
        return False

    status = _archive_job_status(existing_job_id)
    if status in _RUNNING_ARCHIVE_JOB_STATUSES:
        return True
    if status == _ARCHIVE_JOB_STATUS_ERROR:
        return True

    prep.clear_archive_job_id()
    return False


def _ensure_anonymous_access(runid: str, wd: str) -> None:
    owners = list(get_run_owners_lazy(runid) or [])
    if not owners:
        return
    ron = Ron.getInstance(wd)
    if ron.public:
        return
    raise AuthError("Run not found", status_code=404, code="not_found")


def _resolve_user_from_claims(
    claims: Mapping[str, Any],
) -> tuple[Any | None, Any | None, Any | None]:
    token_class = str(claims.get("token_class") or "").strip().lower()
    if token_class not in {"user", "session"}:
        return None, None, None

    from wepppy.weppcloud.utils.helpers import get_user_models
    from wepppy.weppcloud.app import app as flask_app

    Run, User, user_datastore = get_user_models()

    user = None
    sub = claims.get("sub")
    user_id_claim = claims.get("user_id")
    email = claims.get("email")

    with flask_app.app_context():
        for raw_user_id in (user_id_claim, sub):
            try:
                user_id = int(str(raw_user_id))
            except (TypeError, ValueError):
                user_id = None
            if user_id is not None:
                user = User.query.filter(User.id == user_id).first()
                if user is not None:
                    break

        if user is None and email:
            if hasattr(user_datastore, "find_user"):
                try:
                    user = user_datastore.find_user(email=str(email))
                except Exception:
                    user = None

        if user is None and email:
            try:
                user = User.query.filter(User.email == str(email)).first()
            except Exception:
                user = None

    return user, user_datastore, flask_app


def _token_class_from_claims(claims: Mapping[str, Any] | None) -> str:
    if claims is None:
        return ""
    return str(claims.get("token_class") or "").strip().lower()


def _resolve_cap_config(request: Request) -> tuple[str, str, str]:
    base_url = os.getenv("CAP_BASE_URL", "")
    site_key = os.getenv("CAP_SITE_KEY", "")
    secret = get_secret("CAP_SECRET") or ""

    if not base_url:
        raise AuthError("CAP_BASE_URL is required for CAPTCHA verification.", status_code=500)
    if not site_key:
        raise AuthError("CAP_SITE_KEY is required for CAPTCHA verification.", status_code=500)
    if not secret:
        raise AuthError("CAP_SECRET is required for CAPTCHA verification.", status_code=500)

    base_url = base_url.rstrip("/")
    if base_url.startswith("/"):
        base_root = str(request.base_url).rstrip("/")
        base_url = f"{base_root}{base_url}"

    return base_url, site_key, secret


def _verify_cap_token(request: Request, token: str) -> None:
    import requests

    if not token:
        raise AuthError("CAPTCHA token is required.", status_code=403, code="forbidden")

    base_url, site_key, secret = _resolve_cap_config(request)
    verify_url = f"{base_url}/{site_key}/siteverify"

    try:
        response = requests.post(
            verify_url,
            json={"secret": secret, "response": token},
            timeout=6,
        )
    except requests.RequestException as exc:
        raise AuthError(f"CAPTCHA verification failed: {exc}", status_code=500) from exc

    if response.status_code != 200:
        raise AuthError(
            f"CAPTCHA verification failed (status {response.status_code}).",
            status_code=500,
        )

    try:
        payload = response.json()
    except ValueError as exc:
        raise AuthError("CAPTCHA verification failed (invalid response).", status_code=500) from exc

    if not isinstance(payload, dict):
        raise AuthError("CAPTCHA verification failed (invalid response).", status_code=500)

    if not payload.get("success"):
        raise AuthError("CAPTCHA verification failed.", status_code=403, code="forbidden")


@router.post(
    "/runs/{runid}/{config}/fork",
    summary="Fork a run",
    description=(
        "Supports optional JWT Bearer auth (`rq:enqueue`) with run access checks, or anonymous CAPTCHA flow "
        "for eligible public runs. Asynchronously enqueues fork work after preparing target run metadata."
    ),
    tags=["rq-engine", "runs"],
    operation_id=rq_operation_id("fork_project"),
    responses=agent_route_responses(
        success_code=200,
        success_description="Fork job accepted and fork target metadata returned.",
        extra={
            404: "Source run was not found or not anonymously accessible. Returns the canonical error payload.",
        },
    ),
)
async def fork_project(runid: str, config: str, request: Request) -> JSONResponse:
    try:
        claims = _resolve_bearer_claims(request)
        if claims is not None:
            authorize_run_access(claims, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:
        logger.exception("rq-engine fork auth failed")
        return error_response_with_traceback("Failed to authorize request", status_code=401)

    try:
        wd = get_wd(runid)
        if not _exists(wd):
            return error_response(
                f"Error forking project, run_id={runid} does not exist",
                status_code=404,
            )

        token_class = _token_class_from_claims(claims)
        resolved_user = None
        resolved_user_datastore = None
        resolved_user_flask_app = None
        if claims is not None and token_class in {"user", "session"}:
            (
                resolved_user,
                resolved_user_datastore,
                resolved_user_flask_app,
            ) = _resolve_user_from_claims(claims)

        is_anonymous_session = token_class == "session" and resolved_user is None

        if claims is None or is_anonymous_session:
            _ensure_anonymous_access(runid, wd)

        payload = await parse_request_payload(request, boolean_fields={"undisturbify"})
        undisturbify = bool(payload.get("undisturbify", False))
        requested_runid = payload.get("target_runid")
        if isinstance(requested_runid, list):
            requested_runid = requested_runid[0] if requested_runid else None
        if requested_runid is not None and not isinstance(requested_runid, str):
            return error_response("Invalid target_runid", status_code=400, code="validation_error")
        if isinstance(requested_runid, str):
            requested_runid = requested_runid.strip() or None
        requested_wd = None
        if requested_runid:
            try:
                requested_wd = get_wd(requested_runid, prefer_active=False)
            except ValueError:
                return error_response("Invalid target_runid", status_code=400, code="validation_error")

        if claims is None or is_anonymous_session:
            cap_token = payload.get("cap_token", "")
            if isinstance(cap_token, list):
                cap_token = cap_token[0] if cap_token else ""
            _verify_cap_token(request, str(cap_token).strip())

        source_config = Ron.getInstance(wd).config_stem
        owners = list(get_run_owners_lazy(runid) or [])

        dir_created = False
        while not dir_created:
            if requested_runid:
                new_runid = requested_runid
                new_wd = requested_wd
            else:
                email = ""
                if claims is not None:
                    email = str(claims.get("email") or "")
                if not email and resolved_user is not None:
                    email = str(getattr(resolved_user, "email", "") or "")
                new_runid = generate_runid(email)
                new_wd = get_primary_wd(new_runid)

            if requested_runid:
                dir_created = True
            else:
                if _exists(new_wd):
                    continue
                dir_created = True

        if requested_runid:
            if _exists(new_wd):
                if not _is_profile_target_runid(new_runid):
                    return error_response(
                        "target_runid already exists",
                        status_code=409,
                        code="conflict",
                    )
                shutil.rmtree(new_wd)
            parent_dir = os.path.dirname(new_wd.rstrip("/"))
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)
            os.makedirs(new_wd, exist_ok=True)
        else:
            if _exists(new_wd):
                raise RuntimeError(f"Run directory already exists: {new_wd}")

        register_run = not new_runid.startswith("profile;;")
        is_user_token = token_class == "user"
        is_authenticated_session_token = token_class == "session" and resolved_user is not None
        should_register = register_run and (owners or is_user_token or is_authenticated_session_token)
        if should_register:
            user = None
            user_datastore = None
            flask_app = None
            if is_user_token or is_authenticated_session_token:
                user = resolved_user
                user_datastore = resolved_user_datastore
                flask_app = resolved_user_flask_app
                if user is None or user_datastore is None or flask_app is None:
                    if is_user_token:
                        return error_response("Could not add run to user database", status_code=500)

            if user_datastore is None or flask_app is None:
                from wepppy.weppcloud.app import app as flask_app, user_datastore

            with flask_app.app_context():
                from wepppy.weppcloud.utils.helpers import get_user_models

                _, User, _ = get_user_models()

                def _resolve_user_in_session(candidate: Any | None) -> Any | None:
                    if candidate is None:
                        return None

                    raw_user_id = getattr(candidate, "id", None)
                    if raw_user_id is not None:
                        try:
                            user_id = int(str(raw_user_id))
                        except (TypeError, ValueError):
                            user_id = None
                        if user_id is not None:
                            model = User.query.filter_by(id=user_id).first()
                            if model is not None:
                                return model

                    email_value = getattr(candidate, "email", None)
                    if email_value:
                        model = User.query.filter_by(email=str(email_value)).first()
                        if model is not None:
                            return model

                    return None

                owner_models: list[Any] = []
                owner_ids: set[int] = set()
                for owner in owners:
                    owner_model = _resolve_user_in_session(owner)
                    if owner_model is None:
                        continue
                    raw_owner_id = getattr(owner_model, "id", None)
                    if raw_owner_id is None:
                        continue
                    try:
                        owner_id = int(str(raw_owner_id))
                    except (TypeError, ValueError):
                        continue
                    if owner_id in owner_ids:
                        continue
                    owner_ids.add(owner_id)
                    owner_models.append(owner_model)

                user_model = _resolve_user_in_session(user)
                if user is not None and user_model is None:
                    return error_response("Could not add run to user database", status_code=500)

                run_record = None
                if user_model is not None:
                    run_record = user_datastore.create_run(new_runid, source_config, user_model)
                elif owner_models:
                    run_record = user_datastore.create_run(new_runid, source_config, owner_models[0])

                if run_record is not None:
                    for owner in owner_models:
                        if run_record not in owner.runs:
                            user_datastore.add_run_to_user(owner, run_record)
                    if user_model is not None and run_record not in user_model.runs:
                        user_datastore.add_run_to_user(user_model, run_record)

        prep = RedisPrep.getInstance(wd)

        conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
        with redis.Redis(**conn_kwargs) as redis_conn:
            q = Queue(connection=redis_conn)
            job = q.enqueue_call(fork_rq, (runid, new_runid, undisturbify), timeout=RQ_TIMEOUT)
            prep.set_rq_job_id("fork_rq", job.id)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:
        logger.exception("rq-engine fork failed")
        return error_response_with_traceback("Error forking project", status_code=500)

    return JSONResponse(
        {"job_id": job.id, "new_runid": new_runid, "undisturbify": undisturbify}
    )


@router.post(
    "/runs/{runid}/{config}/archive",
    summary="Archive a run",
    description=(
        "Requires JWT Bearer scope `rq:enqueue` and run access via `authorize_run_access`. "
        "Validates lock/job state and asynchronously enqueues archive creation."
    ),
    tags=["rq-engine", "runs"],
    operation_id=rq_operation_id("archive_run"),
    responses=agent_route_responses(
        success_code=200,
        success_description="Archive job accepted and `job_id` returned.",
        extra={
            400: "Archive request failed validation/business rules (locks, running archive job). Returns the canonical error payload.",
            404: "Run was not found. Returns the canonical error payload.",
        },
    ),
)
async def archive_run(runid: str, config: str, request: Request) -> JSONResponse:
    try:
        claims = require_jwt(request, required_scopes=RQ_ENQUEUE_SCOPES)
        authorize_run_access(claims, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:
        logger.exception("rq-engine archive auth failed")
        return error_response_with_traceback("Failed to authorize request", status_code=401)

    try:
        payload = await parse_request_payload(request)
        comment = payload.get("comment")
        if isinstance(comment, list):
            comment = comment[0] if comment else None
        if comment is not None:
            comment = str(comment).strip()
            if len(comment) > 40:
                comment = comment[:40]
        else:
            comment = ""

        wd = get_wd(runid)
        if not _exists(wd):
            return error_response(f"Project {runid} not found", status_code=404)

        locked = [name for name, state in lock_statuses(runid).items() if name.endswith(".nodb") and state]
        if locked:
            return error_response(
                "Cannot archive while files are locked: " + ", ".join(locked),
                status_code=400,
            )

        prep = RedisPrep.getInstance(wd)
        if _archive_job_in_progress(prep):
            return error_response(
                "An archive job is already running for this project",
                status_code=400,
            )

        conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
        with redis.Redis(**conn_kwargs) as redis_conn:
            queue = Queue(connection=redis_conn)
            job = queue.enqueue_call(archive_rq, (runid, comment), timeout=RQ_TIMEOUT)

        prep.set_archive_job_id(job.id)
        StatusMessenger.publish(f"{runid}:archive", f"rq:{job.id} ENQUEUED archive_rq({runid})")
        return JSONResponse({"job_id": job.id})
    except Exception:
        logger.exception("rq-engine archive enqueue failed")
        return error_response_with_traceback("Error enqueueing archive job", status_code=500)


@router.post(
    "/runs/{runid}/{config}/restore-archive",
    summary="Restore a run archive",
    description=(
        "Requires JWT Bearer scope `rq:enqueue` and run access via `authorize_run_access`. "
        "Validates archive/lock state and asynchronously enqueues archive restoration."
    ),
    tags=["rq-engine", "runs"],
    operation_id=rq_operation_id("restore_archive"),
    responses=agent_route_responses(
        success_code=200,
        success_description="Restore job accepted and `job_id` returned.",
        extra={
            400: "Restore request failed validation/business rules (missing params, locks, running archive job). Returns the canonical error payload.",
            404: "Run or archive was not found. Returns the canonical error payload.",
        },
    ),
)
async def restore_archive(runid: str, config: str, request: Request) -> JSONResponse:
    try:
        claims = require_jwt(request, required_scopes=RQ_ENQUEUE_SCOPES)
        authorize_run_access(claims, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:
        logger.exception("rq-engine restore auth failed")
        return error_response_with_traceback("Failed to authorize request", status_code=401)

    try:
        payload = await parse_request_payload(request)
        archive_name = payload.get("archive_name")
        if isinstance(archive_name, list):
            archive_name = archive_name[0] if archive_name else None
        if not archive_name:
            return error_response("Missing archive_name parameter", status_code=400)

        wd = get_wd(runid)
        if not _exists(wd):
            return error_response(f"Project {runid} not found", status_code=404)

        locked = [name for name, state in lock_statuses(runid).items() if name.endswith(".nodb") and state]
        if locked:
            return error_response(
                "Cannot restore while files are locked: " + ", ".join(locked),
                status_code=400,
            )

        archive_path = os.path.join(wd, "archives", str(archive_name))
        if not os.path.exists(archive_path):
            return error_response(f"Archive {archive_name} not found", status_code=404)

        prep = RedisPrep.getInstance(wd)
        if _archive_job_in_progress(prep):
            return error_response(
                "An archive job is already running for this project",
                status_code=400,
            )

        conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
        with redis.Redis(**conn_kwargs) as redis_conn:
            queue = Queue(connection=redis_conn)
            job = queue.enqueue_call(
                restore_archive_rq,
                (runid, archive_name),
                timeout=RQ_TIMEOUT,
            )

        prep.set_archive_job_id(job.id)
        StatusMessenger.publish(
            f"{runid}:archive",
            f"rq:{job.id} ENQUEUED restore_archive_rq({runid}, {archive_name})",
        )

        return JSONResponse({"job_id": job.id})
    except Exception:
        logger.exception("rq-engine restore enqueue failed")
        return error_response_with_traceback("Error enqueueing restore job", status_code=500)


@router.post(
    "/runs/{runid}/{config}/delete-archive",
    summary="Delete a run archive",
    description=(
        "Requires JWT Bearer scope `rq:enqueue` and run access via `authorize_run_access`. "
        "Validates archive/lock state and synchronously deletes archive content; no queue enqueue."
    ),
    tags=["rq-engine", "runs"],
    operation_id=rq_operation_id("delete_archive"),
    responses=agent_route_responses(
        success_code=200,
        success_description="Archive deleted.",
        extra={
            400: "Delete request failed validation/business rules (missing params, locks, running archive job). Returns the canonical error payload.",
            404: "Run or archive was not found. Returns the canonical error payload.",
        },
    ),
)
async def delete_archive(runid: str, config: str, request: Request) -> JSONResponse:
    try:
        claims = require_jwt(request, required_scopes=RQ_ENQUEUE_SCOPES)
        authorize_run_access(claims, runid)
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except Exception:
        logger.exception("rq-engine delete-archive auth failed")
        return error_response_with_traceback("Failed to authorize request", status_code=401)

    try:
        payload = await parse_request_payload(request)
        archive_name = payload.get("archive_name")
        if isinstance(archive_name, list):
            archive_name = archive_name[0] if archive_name else None
        if not archive_name:
            return error_response("Missing archive_name parameter", status_code=400)

        wd = get_wd(runid)
        if not _exists(wd):
            return error_response(f"Project {runid} not found", status_code=404)

        locked = [name for name, state in lock_statuses(runid).items() if name.endswith(".nodb") and state]
        if locked:
            return error_response(
                "Cannot delete while files are locked: " + ", ".join(locked),
                status_code=400,
            )

        archive_path = os.path.join(wd, "archives", str(archive_name))
        if not os.path.exists(archive_path):
            return error_response(f"Archive {archive_name} not found", status_code=404)

        prep = RedisPrep.getInstance(wd)
        if _archive_job_in_progress(prep):
            return error_response(
                "An archive job is already running for this project",
                status_code=400,
            )

        os.remove(archive_path)
        StatusMessenger.publish(f"{runid}:archive", f"Archive deleted: {archive_name}")

        return JSONResponse({})
    except Exception:
        logger.exception("rq-engine delete-archive failed")
        return error_response_with_traceback("Error deleting archive", status_code=500)


__all__ = ["router"]
