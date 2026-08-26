from __future__ import annotations

import logging
import os
from pathlib import Path
import fcntl
import shutil
import stat
import time
from os.path import exists as _exists
from typing import Any, Callable, Mapping
from contextlib import ExitStack, contextmanager

import redis
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from rq import Queue
from rq.exceptions import NoSuchJobError
from rq.job import Job
from rq.registry import (
    CanceledJobRegistry,
    DeferredJobRegistry,
    FailedJobRegistry,
    FinishedJobRegistry,
    ScheduledJobRegistry,
    StartedJobRegistry,
)

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.config.secrets import get_secret
from wepppy.nodb.base import lock_statuses, run_replacement_guard
from wepppy.nodb.core import Ron
from wepppy.nodb.redis_prep import RedisPrep
from wepppy.nodb.status_messenger import StatusMessenger
from wepppy.rq.job_id import new_rq_job_id
from wepppy.rq.job_dependencies import reconcile_deferred_workflow
from wepppy.rq.submission_recovery import (
    RqEnqueueVerificationError,
    RqSubmissionConflict,
    prepare_redisprep_job_id,
    rq_submission_lock,
)
from wepppy.rq.project_rq import _finish_fork_rq, archive_rq, fork_rq, restore_archive_rq
from wepppy.rq.wepp_rq import (
    WeppSingleFlightConflict,
    bootstrap_enable_rq,
    _wepp_job_targets_run,
    ensure_no_active_wepp_job,
    reconcile_deferred_wepp_jobs,
)
from wepppy.weppcloud.utils.helpers import get_primary_wd, get_run_owners_lazy, get_wd
from wepppy.weppcloud.utils.runid import generate_runid

from .auth import AuthError, authorize_run_access, require_jwt
from .openapi import agent_route_responses, rq_operation_id
from .payloads import parse_request_payload
from .responses import error_response, error_response_with_traceback

logger = logging.getLogger(__name__)


class ArchiveAdmissionUnavailable(RuntimeError):
    """Archive receipt reconciliation or enqueue storage is unavailable."""


@contextmanager
def _archive_admission_boundary():
    try:
        yield
    except (OSError, redis.RedisError) as exc:
        raise ArchiveAdmissionUnavailable from exc

router = APIRouter()

RQ_TIMEOUT = int(os.getenv("RQ_ENGINE_RQ_TIMEOUT", "216000"))
RQ_ENQUEUE_SCOPES = ["rq:enqueue"]
PROFILE_FORK_CLAIM_STALE_SECONDS = 900
FORK_DESTINATION_RECEIPT_KEY_PREFIX = "rq:fork:destination"
FORK_DESTINATION_PLANNED_KEY_PREFIX = "rq:fork:planned"
TARGET_MUTATION_POLICY: dict[str, tuple[frozenset[str], int]] = {
    name: (frozenset({"default"}), 0)
    for name in (
        "wepppy.rq.project_rq.build_climate_rq",
        "wepppy.rq.project_rq.build_landuse_rq",
        "wepppy.rq.project_rq.build_rangeland_cover_rq",
        "wepppy.rq.project_rq.build_rusle_rq",
        "wepppy.rq.project_rq.build_soils_rq",
        "wepppy.rq.project_rq.build_subcatchments_and_abstract_watershed_rq",
        "wepppy.rq.project_rq.build_treatments_rq",
        "wepppy.rq.project_rq.delete_run_rq",
        "wepppy.rq.project_rq.fetch_and_align_polaris_rq",
        "wepppy.rq.project_rq.fetch_and_analyze_openet_ts_rq",
        "wepppy.rq.project_rq.fetch_and_analyze_rap_ts_rq",
        "wepppy.rq.project_rq.fetch_dem_and_build_channels_rq",
        "wepppy.rq.project_rq.modify_landuse_mapping_rq",
        "wepppy.rq.project_rq.run_ash_rq",
        "wepppy.rq.project_rq.run_debris_flow_rq",
        "wepppy.rq.project_rq.run_rhem_rq",
        "wepppy.rq.project_rq.set_outlet_rq",
        "wepppy.rq.project_rq.set_run_readonly_rq",
        "wepppy.rq.project_rq.upload_cli_rq",
        "wepppy.rq.land_and_soil_rq.land_and_soil_rq",
        "wepppy.rq.wepp_rq.post_dss_export_rq",
        "wepppy.rq.weppcloudr_rq.render_deval_details_rq",
        "wepppy.rq.ag_fields_rq.run_ag_fields_watershed_rq",
        "wepppy.rq.ag_fields_rq.run_ag_fields_watershed_suite_rq",
        "wepppy.rq.ermit_export_rq.run_ermit_export_rq",
        "wepppy.rq.features_export_rq.run_features_export_rq",
        "wepppy.rq.features_export_rq.run_features_export_cache_hit_rq",
        "wepppy.rq.geneva_rq.run_geneva_build_frequency_panel_rq",
        "wepppy.rq.geneva_rq.run_geneva_prepare_hrus_rq",
        "wepppy.rq.geneva_rq.run_geneva_run_batch_rq",
        "wepppy.rq.interchange_rq.run_interchange_migration",
        "wepppy.rq.omni_rq.delete_omni_contrasts_rq",
        "wepppy.rq.omni_rq.run_omni_contrasts_rq",
        "wepppy.rq.omni_rq.run_omni_scenarios_rq",
        "wepppy.rq.path_ce_rq.run_path_cost_effective_rq",
        "wepppy.rq.roads_rq.run_roads_prepare_rq",
        "wepppy.rq.roads_rq.run_roads_rq",
        "wepppy.rq.swat_rq.run_swat_rq",
        "wepppy.rq.run_sync_rq.run_sync_rq",
    )
}
TARGET_MUTATION_POLICY["wepppy.rq.migrations_rq.migrations_rq"] = (
    frozenset({"default"}),
    1,
)
for _omni_func in (
    "delete_omni_contrasts_rq",
    "run_omni_contrast_rq",
    "run_omni_contrasts_rq",
    "run_omni_scenario_rq",
    "run_omni_scenarios_rq",
    "_compile_hillslope_summaries_rq",
    "_finalize_omni_contrasts_rq",
    "_finalize_omni_scenarios_rq",
):
    TARGET_MUTATION_POLICY[f"wepppy.rq.omni_rq.{_omni_func}"] = (
        frozenset({"batch"}),
        0,
    )
for _ag_fields_func in (
    "build_ag_fields_subfields_rq",
    "finalize_ag_fields_watershed_suite_rq",
    "process_ag_fields_plant_db_rq",
    "run_ag_fields_wepp_rq",
):
    TARGET_MUTATION_POLICY[f"wepppy.rq.ag_fields_rq.{_ag_fields_func}"] = (
        frozenset({"default"}),
        0,
    )
for _watershed_func in (
    "abstract_watershed_rq",
    "build_channels_rq",
    "build_subcatchments_rq",
    "fetch_dem_rq",
):
    TARGET_MUTATION_POLICY[f"wepppy.rq.project_rq.{_watershed_func}"] = (
        frozenset({"default"}),
        0,
    )
TARGET_MUTATION_POLICY[f"{fork_rq.__module__}.{fork_rq.__qualname__}"] = (
    frozenset({"fork-archive"}),
    1,
)
TARGET_MUTATION_POLICY[f"{_finish_fork_rq.__module__}.{_finish_fork_rq.__qualname__}"] = (
    frozenset({"default"}),
    1,
)
TARGET_MUTATION_POLICY[f"{archive_rq.__module__}.{archive_rq.__qualname__}"] = (
    frozenset({"fork-archive"}),
    0,
)
TARGET_MUTATION_POLICY[f"{restore_archive_rq.__module__}.{restore_archive_rq.__qualname__}"] = (
    frozenset({"fork-archive"}),
    0,
)
TARGET_MUTATION_POLICY[f"{bootstrap_enable_rq.__module__}.{bootstrap_enable_rq.__qualname__}"] = (
    frozenset({"default"}),
    0,
)


def _fork_job_belongs_to_lineage(job: Job, source_runid: str, target_runid: str) -> bool:
    args = tuple(job.args or ())
    func_name = str(job.func_name)
    if func_name == f"{fork_rq.__module__}.{fork_rq.__qualname__}":
        return (
            len(args) > 1
            and str(args[0]) == source_runid
            and str(args[1]) == target_runid
            and str(job.origin) == FORK_ARCHIVE_QUEUE
        )
    if func_name == f"{_finish_fork_rq.__module__}.{_finish_fork_rq.__qualname__}":
        return (
            len(args) > 1
            and str(args[0]) == source_runid
            and str(args[1]) == target_runid
            and str(job.origin) == "default"
        )
    return _wepp_job_targets_run(job, target_runid)


def _fork_root_belongs_to_destination(
    job: Job, source_runid: str, target_runid: str
) -> bool:
    args = tuple(job.args or ())
    return (
        str(job.func_name) == f"{fork_rq.__module__}.{fork_rq.__qualname__}"
        and str(job.origin) == FORK_ARCHIVE_QUEUE
        and len(args) > 1
        and str(args[0]) == source_runid
        and str(args[1]) == target_runid
    )


def _discover_legacy_fork_root(
    redis_conn: Any, source_runid: str, target_runid: str
) -> str | None:
    queue = Queue(FORK_ARCHIVE_QUEUE, connection=redis_conn)
    candidate_ids: set[str] = set(queue.get_job_ids())
    for registry_class in (
        StartedJobRegistry,
        DeferredJobRegistry,
        ScheduledJobRegistry,
        FinishedJobRegistry,
        FailedJobRegistry,
        CanceledJobRegistry,
    ):
        candidate_ids.update(
            str(job_id)
            for job_id in registry_class(
                queue=queue, connection=redis_conn
            ).get_job_ids()
        )
    matches: list[str] = []
    for candidate_id in candidate_ids:
        try:
            candidate = Job.fetch(candidate_id, connection=redis_conn)
        except NoSuchJobError:
            continue
        if _fork_root_belongs_to_destination(
            candidate, source_runid, target_runid
        ):
            matches.append(str(candidate.id))
    if len(matches) > 1:
        raise RqSubmissionConflict(
            "Multiple legacy fork workflows match this destination."
        )
    return matches[0] if matches else None


def _target_executable_job_ids(redis_conn: Any, target_runid: str) -> tuple[str, ...]:
    """Return a WATCH-stable inventory of executable work for one run."""
    for _attempt in range(5):
        pipe = redis_conn.pipeline()
        try:
            pipe.watch("rq:queues")
            queues = Queue.all(connection=redis_conn)
            watched_keys: list[str] = []
            registries: list[Any] = []
            for queue in queues:
                watched_keys.extend((queue.key, queue.intermediate_queue_key))
                registries.extend(
                    registry_class(queue=queue, connection=redis_conn)
                    for registry_class in (
                        StartedJobRegistry,
                        DeferredJobRegistry,
                        ScheduledJobRegistry,
                    )
                )
            watched_keys.extend(registry.key for registry in registries)
            if watched_keys:
                pipe.watch(*watched_keys)

            candidate_ids: set[str] = set()
            for queue in queues:
                candidate_ids.update(str(job_id) for job_id in queue.get_job_ids())
                candidate_ids.update(
                    job_id.decode("utf-8") if isinstance(job_id, bytes) else str(job_id)
                    for job_id in redis_conn.lrange(queue.intermediate_queue_key, 0, -1)
                )
            for registry in registries:
                candidate_ids.update(str(job_id) for job_id in registry.get_job_ids())

            if candidate_ids:
                pipe.watch(*(Job.key_for(candidate_id) for candidate_id in candidate_ids))
            jobs: list[Job] = []
            for candidate_id in candidate_ids:
                try:
                    jobs.append(Job.fetch(candidate_id, connection=redis_conn))
                except NoSuchJobError:
                    continue
            matches: list[str] = []
            for candidate in jobs:
                raw_status = candidate.get_status(refresh=True)
                status = str(getattr(raw_status, "value", raw_status)).lower()
                if status in {"queued", "started", "scheduled", "deferred"} and _job_plausibly_targets_destination(
                    candidate, target_runid
                ):
                    matches.append(str(candidate.id))
            pipe.multi()
            pipe.ping()
            pipe.execute()
            return tuple(sorted(matches))
        except redis.WatchError:
            continue
        finally:
            pipe.reset()
    raise RqSubmissionConflict("Target job inventory changed during replacement.")


def _job_targets_destination(candidate: Job, target_runid: str) -> bool:
    """Apply authoritative metadata or an explicit legacy argument policy."""
    policy = TARGET_MUTATION_POLICY.get(str(candidate.func_name))
    if policy is None:
        return False
    allowed_origins, legacy_arg_index = policy
    if str(candidate.origin) not in allowed_origins:
        return False
    metadata = candidate.meta if isinstance(candidate.meta, dict) else {}
    metadata_runid = str(metadata.get("runid") or "")
    args = tuple(str(value) for value in tuple(candidate.args or ()))
    args_match = len(args) > legacy_arg_index and args[legacy_arg_index] == target_runid
    if metadata_runid:
        return metadata_runid == target_runid and args_match
    return args_match


def _job_plausibly_targets_destination(candidate: Job, target_runid: str) -> bool:
    """Conservatively identify same-resource work that must at least block."""
    metadata = candidate.meta if isinstance(candidate.meta, dict) else {}
    metadata_runid = str(metadata.get("runid") or "")
    args = tuple(str(value) for value in tuple(candidate.args or ()))
    policy = TARGET_MUTATION_POLICY.get(str(candidate.func_name))
    if policy is None:
        args_target = target_runid in args
    else:
        arg_index = policy[1]
        args_target = len(args) > arg_index and args[arg_index] == target_runid
    return metadata_runid == target_runid or args_target


def _reconcile_target_deferred_jobs(
    redis_conn: Any,
    target_runid: str,
    *,
    lease_checkpoint: Callable[[], None],
) -> tuple[str, ...]:
    """Cancel exact deferred target workflows, then return live conflicts."""
    candidate_ids = _target_executable_job_ids(redis_conn, target_runid)

    def belongs_to_target(candidate: Job) -> bool:
        return _job_targets_destination(candidate, target_runid)

    for candidate_id in candidate_ids:
        try:
            candidate = Job.fetch(candidate_id, connection=redis_conn)
        except NoSuchJobError:
            continue
        raw_status = candidate.get_status(refresh=True)
        status = str(getattr(raw_status, "value", raw_status)).lower()
        if status != "deferred":
            continue
        if not _job_targets_destination(candidate, target_runid):
            continue
        reconcile_deferred_workflow(
            candidate_id,
            connection=redis_conn,
            association=belongs_to_target,
            root_association=belongs_to_target,
            lease_checkpoint=lease_checkpoint,
        )
    return _target_executable_job_ids(redis_conn, target_runid)


def _is_profile_target_runid(runid: str) -> bool:
    parts = str(runid).split(";;")
    return len(parts) == 3 and parts[0] == "profile" and parts[1] == "fork" and bool(parts[2])


def _owner_snapshot(owners: list[Any]) -> str:
    identities = sorted(
        f"{getattr(owner, 'id', '')}\0{getattr(owner, 'email', '')}"
        for owner in owners
    )
    return "\n".join(identities)


def _profile_fork_claim_path(target_wd: str) -> str:
    target = target_wd.rstrip("/")
    return os.path.join(os.path.dirname(target), f".{os.path.basename(target)}.fork-claim")


@contextmanager
def _profile_fork_claim_lock(target_wd: str):
    lock_path = f"{_profile_fork_claim_path(target_wd)}.lock"
    lock_fd = os.open(lock_path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        os.close(lock_fd)


def _release_profile_fork_claim(target_wd: str, job_id: str) -> None:
    with _profile_fork_claim_lock(target_wd):
        claim_path = _profile_fork_claim_path(target_wd)
        try:
            with open(claim_path, encoding="utf-8") as claim_file:
                if claim_file.read().strip() != job_id:
                    return
            os.unlink(claim_path)
        except FileNotFoundError:
            return


def _recover_stale_profile_fork_claim(
    target_wd: str,
    target_runid: str,
    *,
    redis_conn: Any,
    lease_checkpoint: Callable[[], None],
) -> bool:
    claim_path = _profile_fork_claim_path(target_wd)
    try:
        claim_stat = os.stat(claim_path, follow_symlinks=False)
        if not stat.S_ISREG(claim_stat.st_mode):
            return False
        with open(claim_path, encoding="utf-8") as claim_file:
            job_id = claim_file.read().strip()
        try:
            finalizer = Job.fetch(job_id, connection=redis_conn)
        except NoSuchJobError:
            os.unlink(claim_path)
            return True
        args = tuple(finalizer.args or ())
        source_runid = str(args[0]) if args else ""
        if (
            str(finalizer.func_name)
            != f"{_finish_fork_rq.__module__}.{_finish_fork_rq.__qualname__}"
            or str(finalizer.origin) != "default"
            or len(args) < 2
            or str(args[1]) != target_runid
            or not source_runid
        ):
            return False
        result = reconcile_deferred_workflow(
            job_id,
            connection=redis_conn,
            association=lambda candidate: _fork_job_belongs_to_lineage(
                candidate, source_runid, target_runid
            ),
            root_association=lambda candidate: (
                str(candidate.func_name)
                == f"{_finish_fork_rq.__module__}.{_finish_fork_rq.__qualname__}"
                and str(candidate.origin) == "default"
                and tuple(candidate.args or ())[:2]
                == (source_runid, target_runid)
            ),
            lease_checkpoint=lease_checkpoint,
        )
        if result.state == "canceled":
            os.unlink(claim_path)
            StatusMessenger.publish(
                f"{source_runid}:fork",
                f"rq:{job_id} TRIGGER   fork FORK_FAILED",
            )
            return True
        if result.state in {"active", "mismatch"}:
            return False
        finalizer_status = str(
            getattr(
                finalizer.get_status(refresh=True),
                "value",
                finalizer.get_status(refresh=False),
            )
        ).lower()
        if finalizer_status in {"failed", "stopped", "canceled"}:
            os.unlink(claim_path)
            return True
        if time.time() - claim_stat.st_mtime < PROFILE_FORK_CLAIM_STALE_SECONDS:
            return False
        os.unlink(claim_path)
        return True
    except FileNotFoundError:
        return True


async def _strict_request_boolean(request: Request, field: str) -> bool:
    content_type = request.headers.get("content-type", "").lower()
    if "application/json" in content_type:
        raw = await request.json()
        if not isinstance(raw, dict) or field not in raw:
            return False
        value = raw[field]
        if not isinstance(value, bool):
            raise ValueError(field)
        return value

    form = await request.form()
    values = form.getlist(field)
    if not values:
        return False
    if len(values) != 1 or not isinstance(values[0], str):
        raise ValueError(field)
    token = values[0].strip().lower()
    if token in {"1", "true", "yes", "on"}:
        return True
    if token in {"0", "false", "no", "off"}:
        return False
    raise ValueError(field)


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


_RUNNING_ARCHIVE_JOB_STATUSES = {"queued", "started", "scheduled"}
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
        # API boundary: treat status lookup failures as "in progress" to avoid double-enqueue.
        logger.exception("rq-engine archive job status lookup failed", extra={"job_id": job_id})
        return _ARCHIVE_JOB_STATUS_ERROR


def _archive_job_in_progress(prep: Any) -> bool:
    existing_job_id = prep.get_archive_job_id()
    if not existing_job_id:
        return False

    status = _archive_job_status(existing_job_id)
    if status in _RUNNING_ARCHIVE_JOB_STATUSES:
        return True
    if status == "deferred":
        return False
    if status == _ARCHIVE_JOB_STATUS_ERROR:
        return True

    return False


def _reconcile_archive_receipt(
    prep: Any,
    redis_conn: Any,
    runid: str,
    *,
    lease_checkpoint: Callable[[], None] | None = None,
) -> str:
    prior_job_id = prep.get_archive_job_id()
    if not prior_job_id:
        return "missing"
    allowed_functions = {
        f"{archive_rq.__module__}.{archive_rq.__qualname__}",
        f"{restore_archive_rq.__module__}.{restore_archive_rq.__qualname__}",
    }
    result = reconcile_deferred_workflow(
        prior_job_id,
        connection=redis_conn,
        association=lambda candidate: (
            bool(candidate.args)
            and str(candidate.args[0]) == runid
            and str(candidate.origin) == FORK_ARCHIVE_QUEUE
            and str(candidate.func_name) in allowed_functions
        ),
        root_association=lambda candidate: (
            bool(candidate.args)
            and str(candidate.args[0]) == runid
            and str(candidate.origin) == FORK_ARCHIVE_QUEUE
            and str(candidate.func_name) in allowed_functions
        ),
        lease_checkpoint=lease_checkpoint,
    )
    return result.state


def _resolve_run_archive_path(wd: str, archive_name: str) -> str:
    """Resolve one ordinary zip basename directly below this run's archives."""
    name = str(archive_name).strip()
    if (
        not name
        or name != os.path.basename(name)
        or name in {".", ".."}
        or not name.lower().endswith(".zip")
    ):
        raise ValueError("Invalid archive_name")
    canonical_wd = os.path.realpath(wd)
    archives_entry = os.path.join(canonical_wd, "archives")
    if os.path.islink(archives_entry) or not os.path.isdir(archives_entry):
        raise ValueError("Invalid archives directory")
    archives_root = os.path.realpath(archives_entry)
    if archives_root != archives_entry:
        raise ValueError("Invalid archives directory")
    archive_path = os.path.join(archives_root, name)
    if os.path.lexists(archive_path) and os.path.islink(archive_path):
        raise ValueError("Invalid archive_name")
    resolved = os.path.realpath(archive_path)
    if os.path.dirname(resolved) != archives_root:
        raise ValueError("Invalid archive_name")
    return resolved


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
                    # Best-effort user lookup: failures should not block fork flow.
                    logger.exception("rq-engine fork user_datastore lookup failed")
                    user = None

        if user is None and email:
            try:
                user = User.query.filter(User.email == str(email)).first()
            except Exception:
                # Best-effort user lookup: failures should not block fork flow.
                logger.exception("rq-engine fork user query by email failed")
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
    profile_claimed = False
    profile_claim_handed_off = False
    fork_job_id = ""
    new_wd = ""
    fork_admission = ExitStack()
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

        try:
            skip_omni_scenarios_contrasts = await _strict_request_boolean(
                request,
                "skip_omni_scenarios_contrasts",
            )
        except (ValueError, TypeError):
            return error_response(
                "Invalid skip_omni_scenarios_contrasts",
                status_code=400,
                code="validation_error",
            )

        payload = await parse_request_payload(
            request,
            boolean_fields={"undisturbify", "skip_wepp_runs_output"},
        )
        undisturbify = bool(payload.get("undisturbify", False))
        skip_wepp_runs_output = bool(payload.get("skip_wepp_runs_output", False))
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
            source_path = Path(wd).resolve()
            target_path = Path(requested_wd).resolve()
            if (
                requested_runid == runid
                or source_path == target_path
                or source_path in target_path.parents
                or target_path in source_path.parents
            ):
                return error_response(
                    "Fork target must differ from the source run",
                    status_code=400,
                    code="validation_error",
                )
            if requested_runid.startswith("profile;;") and not _is_profile_target_runid(requested_runid):
                return error_response("Invalid target_runid", status_code=400, code="validation_error")
            if _is_profile_target_runid(requested_runid) and (claims is None or is_anonymous_session):
                return error_response("Profile fork targets require authentication", status_code=403, code="forbidden")
            if _is_profile_target_runid(requested_runid):
                profile_root = os.path.realpath(
                    os.path.dirname(get_wd("profile;;fork;;__root_probe__", prefer_active=False))
                )
                resolved_target = os.path.realpath(requested_wd)
                if os.path.dirname(resolved_target) != profile_root:
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

        fork_job_id = new_rq_job_id()
        conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
        redis_conn = fork_admission.enter_context(redis.Redis(**conn_kwargs))
        lease = fork_admission.enter_context(
            rq_submission_lock(redis_conn, f"{new_runid}:fork", lifecycle_key=new_runid)
        )
        receipt_key = f"{FORK_DESTINATION_RECEIPT_KEY_PREFIX}:{new_runid}"
        planned_key = f"{FORK_DESTINATION_PLANNED_KEY_PREFIX}:{new_runid}"
        planned = redis_conn.hgetall(planned_key)
        planned_values = {
            (key.decode("utf-8") if isinstance(key, bytes) else str(key)): (
                value.decode("utf-8") if isinstance(value, bytes) else str(value)
            )
            for key, value in planned.items()
        }
        claim_identity = ""
        if claims is not None:
            claim_identity = str(
                claims.get("sub")
                or claims.get("user_id")
                or claims.get("email")
                or ""
            )
        target_owners = list(get_run_owners_lazy(new_runid) or [])
        if _exists(new_wd) or target_owners:
            anonymous_recovery = (
                (claims is None or is_anonymous_session)
                and not target_owners
                and planned_values.get("source_runid") == runid
                and planned_values.get("target_runid") == new_runid
                and planned_values.get("state", "planned") != "succeeded"
            )
            if not anonymous_recovery:
                if claims is None or is_anonymous_session:
                    return error_response(
                        "Authentication is required to replace an existing target.",
                        status_code=403,
                        code="forbidden",
                    )
                try:
                    authorize_run_access(
                        claims, new_runid, allow_fork_preparing=True
                    )
                except AuthError as exc:
                    unchanged_owner_snapshot = (
                        bool(target_owners)
                        and planned_values.get("owner_snapshot")
                        == _owner_snapshot(target_owners)
                    )
                    principal_bound_recovery = (
                        planned_values.get("source_runid") == runid
                        and planned_values.get("target_runid") == new_runid
                        and planned_values.get("state", "planned") != "succeeded"
                        and bool(claim_identity)
                        and planned_values.get("claim_identity") == claim_identity
                        and planned_values.get("token_class") == token_class
                        and (not target_owners or unchanged_owner_snapshot)
                    )
                    if not principal_bound_recovery:
                        return error_response(
                            exc.message, status_code=exc.status_code, code=exc.code
                        )
        prior_job_id = redis_conn.get(receipt_key)
        if isinstance(prior_job_id, bytes):
            prior_job_id = prior_job_id.decode("utf-8")
        if not prior_job_id:
            source_prep = RedisPrep.getInstance(wd)
            legacy_job_id = source_prep.get_rq_job_id("fork_rq")
            if legacy_job_id:
                try:
                    legacy_job = Job.fetch(str(legacy_job_id), connection=redis_conn)
                except NoSuchJobError:
                    legacy_job = None
                if legacy_job is not None and _fork_root_belongs_to_destination(
                    legacy_job, runid, new_runid
                ):
                    prior_job_id = str(legacy_job_id)
                    redis_conn.set(receipt_key, prior_job_id)
            if not prior_job_id:
                prior_job_id = _discover_legacy_fork_root(
                    redis_conn, runid, new_runid
                )
                if prior_job_id:
                    redis_conn.set(receipt_key, prior_job_id)
        prior_state = "missing"
        prior_failed_terminal = False
        if prior_job_id:
            try:
                recorded_root = Job.fetch(str(prior_job_id), connection=redis_conn)
            except NoSuchJobError:
                recorded_root = None
            if recorded_root is not None and not _fork_root_belongs_to_destination(
                recorded_root, runid, new_runid
            ):
                return error_response(
                    "Recorded fork job does not belong to this destination.",
                    status_code=409,
                    code="conflict",
                )
            prior_result = reconcile_deferred_workflow(
                str(prior_job_id),
                connection=redis_conn,
                association=lambda candidate: _fork_job_belongs_to_lineage(
                    candidate, runid, new_runid
                ),
                root_association=lambda candidate: _fork_root_belongs_to_destination(
                    candidate, runid, new_runid
                ),
                lease_checkpoint=lease.checkpoint,
            )
            prior_state = prior_result.state
            if prior_state == "terminal":
                for terminal_job_id in prior_result.job_ids:
                    try:
                        terminal_job = Job.fetch(
                            terminal_job_id, connection=redis_conn
                        )
                    except NoSuchJobError:
                        continue
                    terminal_status = str(
                        getattr(
                            terminal_job.get_status(refresh=True),
                            "value",
                            terminal_job.get_status(refresh=False),
                        )
                    ).lower()
                    if terminal_status in {"failed", "stopped", "canceled"}:
                        prior_failed_terminal = True
                        break
            if prior_state in {"active", "mismatch"}:
                return error_response(
                    "A fork to this destination is already active.",
                    status_code=409,
                    code="conflict",
                )
        recoverable_planned_mutation = (
            prior_state == "missing"
            and bool(prior_job_id)
            and planned_values.get("job_id") == str(prior_job_id)
            and planned_values.get("source_runid") == runid
            and planned_values.get("target_runid") == new_runid
            and planned_values.get("state", "planned") != "succeeded"
        )
        replacement_lease = None
        if requested_runid:
            if _exists(new_wd):
                replacement_lease = fork_admission.enter_context(
                    run_replacement_guard(new_runid)
                )
            if _is_profile_target_runid(new_runid):
                parent_dir = os.path.dirname(new_wd.rstrip("/"))
                os.makedirs(parent_dir, exist_ok=True)
                claim_path = _profile_fork_claim_path(new_wd)
                with _profile_fork_claim_lock(new_wd):
                    for attempt in range(2):
                        try:
                            claim_fd = os.open(
                                claim_path,
                                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                                0o600,
                            )
                            break
                        except FileExistsError:
                            if attempt == 0 and _recover_stale_profile_fork_claim(
                                new_wd,
                                new_runid,
                                redis_conn=redis_conn,
                                lease_checkpoint=lease.checkpoint,
                            ):
                                continue
                            return error_response(
                                "target_runid is already being prepared",
                                status_code=409,
                                code="conflict",
                            )
                with os.fdopen(claim_fd, "w", encoding="utf-8") as claim_file:
                    claim_file.write(fork_job_id)
                    claim_file.flush()
                    os.fsync(claim_file.fileno())
                profile_claimed = True
            if _exists(new_wd):
                # Every existing destination, including ownerless profile
                # targets, requires exact failed/canceled recovery proof.
                if not (
                    (prior_state == "canceled" and prior_job_id)
                    or prior_failed_terminal
                    or recoverable_planned_mutation
                ):
                    return error_response(
                        "target_runid already exists",
                        status_code=409,
                        code="conflict",
                    )
                if _is_profile_target_runid(new_runid) and not (
                    planned_values.get("source_runid") == runid
                    and planned_values.get("target_runid") == new_runid
                    and planned_values.get("state", "planned") != "succeeded"
                    and bool(claim_identity)
                    and planned_values.get("claim_identity") == claim_identity
                    and planned_values.get("token_class") == token_class
                ):
                    return error_response(
                        "Profile fork recovery is not authorized for this principal.",
                        status_code=403,
                        code="forbidden",
                    )
                    target_locks = [
                        name
                        for name, locked in lock_statuses(new_runid).items()
                        if locked
                    ]
                    if target_locks:
                        return error_response(
                            "Target project is currently being modified.",
                            status_code=409,
                            code="conflict",
                        )
                    target_prep = RedisPrep.getInstance(new_wd)
                    reconcile_deferred_wepp_jobs(
                        new_runid,
                        target_prep,
                        redis_conn,
                        lease_checkpoint=lease.checkpoint,
                    )
                    ensure_no_active_wepp_job(new_runid, target_prep, redis_conn)
                    for target_job_id in target_prep.get_rq_job_ids().values():
                        if not target_job_id:
                            continue
                        try:
                            target_job = Job.fetch(
                                str(target_job_id), connection=redis_conn
                            )
                        except NoSuchJobError:
                            continue
                        target_status = str(
                            getattr(
                                target_job.get_status(refresh=True),
                                "value",
                                target_job.get_status(refresh=False),
                            )
                        ).lower()
                        if target_status in {
                            "queued",
                            "started",
                            "scheduled",
                        }:
                            return error_response(
                                "Target project has other active work.",
                                status_code=409,
                                code="conflict",
                            )
                    target_executable_jobs = _reconcile_target_deferred_jobs(
                        redis_conn,
                        new_runid,
                        lease_checkpoint=lease.checkpoint,
                    )
                    if target_executable_jobs:
                        return error_response(
                            "Target project has queued or running work.",
                            status_code=409,
                            code="conflict",
                        )
                else:
                    target_locks = [
                        name
                        for name, locked in lock_statuses(new_runid).items()
                        if locked
                    ]
                    if target_locks:
                        return error_response(
                            "Target project is currently being modified.",
                            status_code=409,
                            code="conflict",
                        )
                    target_prep = RedisPrep.getInstance(new_wd)
                    reconcile_deferred_wepp_jobs(
                        new_runid,
                        target_prep,
                        redis_conn,
                        lease_checkpoint=lease.checkpoint,
                    )
                    ensure_no_active_wepp_job(new_runid, target_prep, redis_conn)
                    if _reconcile_target_deferred_jobs(
                        redis_conn,
                        new_runid,
                        lease_checkpoint=lease.checkpoint,
                    ):
                        return error_response(
                            "Target project has queued or running work.",
                            status_code=409,
                            code="conflict",
                        )
            redis_conn.hset(
                planned_key,
                mapping={
                    "job_id": fork_job_id,
                    "source_runid": runid,
                    "target_runid": new_runid,
                    "state": "planned",
                    "claim_identity": claim_identity,
                    "token_class": token_class,
                    # Fork registration inherits this exact source-owner set.
                    # A later ownership change revokes claim-based recovery.
                    "owner_snapshot": _owner_snapshot(owners),
                },
            )
            redis_conn.set(receipt_key, fork_job_id)
            lease.checkpoint()
            if _exists(new_wd):
                if replacement_lease is None:
                    raise RqSubmissionConflict("Target replacement fence is missing.")
                replacement_lease.checkpoint()
                current_target_owners = list(get_run_owners_lazy(new_runid) or [])
                if _owner_snapshot(current_target_owners) != _owner_snapshot(target_owners):
                    raise RqSubmissionConflict(
                        "Target ownership changed during fork recovery."
                    )
                tombstone_wd = os.path.join(
                    os.path.dirname(new_wd.rstrip("/")),
                    f".{os.path.basename(new_wd.rstrip('/'))}.replacing-{fork_job_id}",
                )
                os.replace(new_wd, tombstone_wd)
                # Once renamed, new target-path mutations cannot overlap the
                # old tree even if recursive cleanup is slow.
                shutil.rmtree(tombstone_wd)
                replacement_lease.checkpoint()
            lease.checkpoint()
            if replacement_lease is not None:
                replacement_lease.checkpoint()
            parent_dir = os.path.dirname(new_wd.rstrip("/"))
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)
            os.makedirs(new_wd, exist_ok=True)
            if replacement_lease is not None:
                replacement_lease.checkpoint()
            if profile_claimed:
                with open(os.path.join(new_wd, ".redisprep-run-id"), "x", encoding="utf-8") as namespace_file:
                    namespace_file.write(new_runid)
        else:
            if _exists(new_wd):
                raise RuntimeError(f"Run directory already exists: {new_wd}")
            redis_conn.hset(
                planned_key,
                mapping={
                    "job_id": fork_job_id,
                    "source_runid": runid,
                    "target_runid": new_runid,
                    "state": "planned",
                    "claim_identity": claim_identity,
                    "token_class": token_class,
                    "owner_snapshot": _owner_snapshot(owners),
                },
            )
            redis_conn.set(receipt_key, fork_job_id)
            lease.checkpoint()

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

                Run, User, _ = get_user_models()

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

                run_record = Run.query.filter_by(runid=new_runid).first()
                if run_record is None and user_model is not None:
                    run_record = user_datastore.create_run(new_runid, source_config, user_model)
                elif run_record is None and owner_models:
                    run_record = user_datastore.create_run(new_runid, source_config, owner_models[0])

                if run_record is not None:
                    for owner in owner_models:
                        if run_record not in owner.runs:
                            user_datastore.add_run_to_user(owner, run_record)
                    if user_model is not None and run_record not in user_model.runs:
                        user_datastore.add_run_to_user(user_model, run_record)

        prep = RedisPrep.getInstance(wd)
        q = Queue(FORK_ARCHIVE_QUEUE, connection=redis_conn)
        lease.checkpoint()
        if replacement_lease is not None:
            replacement_lease.checkpoint()
        prep.set_rq_job_id("fork_rq", fork_job_id)
        redis_conn.set(receipt_key, fork_job_id)
        lease.checkpoint()
        if replacement_lease is not None:
            replacement_lease.checkpoint()
        job = q.enqueue_call(
            fork_rq,
            (
                runid,
                new_runid,
                undisturbify,
                skip_wepp_runs_output,
                skip_omni_scenarios_contrasts,
            ),
            timeout=RQ_TIMEOUT,
            job_id=fork_job_id,
        )
        profile_claim_handed_off = profile_claimed
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except (RqSubmissionConflict, WeppSingleFlightConflict) as exc:
        return error_response(str(exc), status_code=409, code="conflict")
    except RqEnqueueVerificationError:
        logger.exception("rq-engine fork enqueue commit could not be verified")
        return error_response_with_traceback(
            "Fork submission state could not be verified", status_code=503
        )
    except Exception:
        if profile_claimed and not profile_claim_handed_off:
            _release_profile_fork_claim(new_wd, fork_job_id)
        logger.exception("rq-engine fork failed")
        return error_response_with_traceback("Error forking project", status_code=500)
    finally:
        fork_admission.close()

    return JSONResponse(
        {
            "job_id": job.id,
            "new_runid": new_runid,
            "undisturbify": undisturbify,
            "skip_wepp_runs_output": skip_wepp_runs_output,
            "skip_omni_scenarios_contrasts": skip_omni_scenarios_contrasts,
        }
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
        with _archive_admission_boundary(), redis.Redis(**conn_kwargs) as redis_conn, rq_submission_lock(
            redis_conn, f"{runid}:archive", lifecycle_key=runid
        ) as lease:
            queue = Queue(FORK_ARCHIVE_QUEUE, connection=redis_conn)
            state = _reconcile_archive_receipt(
                prep, redis_conn, runid, lease_checkpoint=lease.checkpoint
            )
            if state in {"active", "mismatch"}:
                return error_response(
                    "An archive job is already running for this project",
                    status_code=400,
                )
            job_id = new_rq_job_id()
            lease.checkpoint()
            prep.set_archive_job_id(job_id)
            lease.checkpoint()
            job = queue.enqueue_call(
                archive_rq,
                (runid, comment),
                timeout=RQ_TIMEOUT,
                job_id=job_id,
            )
        try:
            StatusMessenger.publish(f"{runid}:archive", f"rq:{job.id} ENQUEUED archive_rq({runid})")
        except redis.RedisError:
            logger.warning("Status publish failed after archive enqueue for %s", runid, exc_info=True)
        return JSONResponse({"job_id": job.id})
    except RqSubmissionConflict as exc:
        return error_response(str(exc), status_code=409, code="conflict")
    except ArchiveAdmissionUnavailable:
        logger.exception("rq-engine archive admission unavailable")
        return error_response("Submission admission is temporarily unavailable", status_code=503, code="service_unavailable")
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

        try:
            archive_path = _resolve_run_archive_path(wd, str(archive_name))
        except ValueError as exc:
            return error_response(str(exc), status_code=400, code="validation_error")
        if not os.path.exists(archive_path):
            return error_response(f"Archive {archive_name} not found", status_code=404)

        prep = RedisPrep.getInstance(wd)
        if _archive_job_in_progress(prep):
            return error_response(
                "An archive job is already running for this project",
                status_code=400,
            )

        conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
        with _archive_admission_boundary(), redis.Redis(**conn_kwargs) as redis_conn, rq_submission_lock(
            redis_conn, f"{runid}:archive", lifecycle_key=runid
        ) as lease:
            queue = Queue(FORK_ARCHIVE_QUEUE, connection=redis_conn)
            state = _reconcile_archive_receipt(
                prep, redis_conn, runid, lease_checkpoint=lease.checkpoint
            )
            if state in {"active", "mismatch"}:
                return error_response(
                    "An archive job is already running for this project",
                    status_code=400,
                )
            job_id = new_rq_job_id()
            lease.checkpoint()
            prep.set_archive_job_id(job_id)
            lease.checkpoint()
            job = queue.enqueue_call(
                restore_archive_rq,
                (runid, archive_name),
                timeout=RQ_TIMEOUT,
                job_id=job_id,
            )
        try:
            StatusMessenger.publish(
                f"{runid}:archive",
                f"rq:{job.id} ENQUEUED restore_archive_rq({runid}, {archive_name})",
            )
        except redis.RedisError:
            logger.warning("Status publish failed after restore enqueue for %s", runid, exc_info=True)

        return JSONResponse({"job_id": job.id})
    except RqSubmissionConflict as exc:
        return error_response(str(exc), status_code=409, code="conflict")
    except ArchiveAdmissionUnavailable:
        logger.exception("rq-engine restore admission unavailable")
        return error_response("Submission admission is temporarily unavailable", status_code=503, code="service_unavailable")
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

        try:
            archive_path = _resolve_run_archive_path(wd, str(archive_name))
        except ValueError as exc:
            return error_response(str(exc), status_code=400, code="validation_error")
        if not os.path.exists(archive_path):
            return error_response(f"Archive {archive_name} not found", status_code=404)

        prep = RedisPrep.getInstance(wd)
        if _archive_job_in_progress(prep):
            return error_response(
                "An archive job is already running for this project",
                status_code=400,
            )

        conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
        with _archive_admission_boundary(), redis.Redis(**conn_kwargs) as redis_conn, rq_submission_lock(
            redis_conn, f"{runid}:archive", lifecycle_key=runid
        ) as lease:
            state = _reconcile_archive_receipt(
                prep, redis_conn, runid, lease_checkpoint=lease.checkpoint
            )
            if state in {"active", "mismatch"}:
                return error_response(
                    "An archive job is already running for this project",
                    status_code=400,
                )
            lease.checkpoint()
            os.remove(archive_path)
            prep.clear_archive_job_id()
        StatusMessenger.publish(f"{runid}:archive", f"Archive deleted: {archive_name}")

        return JSONResponse({})
    except RqSubmissionConflict as exc:
        return error_response(str(exc), status_code=409, code="conflict")
    except ArchiveAdmissionUnavailable:
        logger.exception("rq-engine delete-archive admission unavailable")
        return error_response(
            "Submission admission is temporarily unavailable",
            status_code=503,
            code="service_unavailable",
        )
    except Exception:
        logger.exception("rq-engine delete-archive failed")
        return error_response_with_traceback("Error deleting archive", status_code=500)

FORK_ARCHIVE_QUEUE = "fork-archive"

__all__ = ["router"]
