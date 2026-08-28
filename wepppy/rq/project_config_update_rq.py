"""RQ task for one reviewed project configuration amendment."""

from __future__ import annotations

from typing import Any, Mapping

import redis
from rq import get_current_job

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.microservices.rq_engine.auth import AuthError, authorize_run_mutation
from wepppy.nodb.project_config_update import apply_project_config_update
from wepppy.rq.exception_logging import with_exception_logging
from wepppy.weppcloud.utils.helpers import get_wd

__all__ = ["CONFIG_UPDATE_ACTIVE_PREFIX", "run_project_config_update_rq"]

CONFIG_UPDATE_ACTIVE_PREFIX = "rq:project-config-update:active:"


def _release_active(runid: str, job_id: str) -> None:
    key = f"{CONFIG_UPDATE_ACTIVE_PREFIX}{runid}"
    with redis.Redis(**redis_connection_kwargs(RedisDB.RQ)) as redis_conn:
        current = redis_conn.get(key)
        if isinstance(current, bytes):
            current = current.decode("utf-8")
        if str(current or "") == job_id:
            redis_conn.delete(key)


@with_exception_logging
def run_project_config_update_rq(
    runid: str,
    config: str,
    preview_id: str,
    application_revision: str,
    trigger_section: str | None,
    trigger_option: str | None,
    capability_acknowledgment_accepted: bool = False,
    capability_acknowledgment_revision: str | None = None,
) -> dict[str, Any]:
    """Reauthorize the submitter and apply the complete reviewed delta."""

    job = get_current_job()
    job_id = str(getattr(job, "id", "") or "unknown-job")
    metadata = getattr(job, "meta", {}) if job is not None else {}
    actor: Mapping[str, Any] = metadata.get("auth_actor", {}) if isinstance(metadata, dict) else {}
    try:
        authorize_run_mutation(actor, runid)
        result = apply_project_config_update(
            get_wd(runid),
            preview_id,
            trigger_section=trigger_section,
            trigger_option=trigger_option,
            application_revision=application_revision,
            capability_acknowledgment_accepted=capability_acknowledgment_accepted,
            capability_acknowledgment_revision=capability_acknowledgment_revision,
        )
        return {
            "applied": result.applied,
            "recovered": result.recovered,
            "sequence": result.sequence,
            "prior_digest": result.prior_digest,
            "resulting_digest": result.resulting_digest,
        }
    except AuthError:
        raise
    finally:
        _release_active(runid, job_id)
