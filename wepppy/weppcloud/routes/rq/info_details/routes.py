from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Sequence

import redis

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.rq.job_listings import (
    DEFAULT_RECENT_LOOKBACK_SECONDS,
    DEFAULT_QUEUES,
    list_active_jobs,
    list_recently_completed_jobs,
)
from wepppy.weppcloud.app import User, get_run_owners
from wepppy.weppcloud.utils.helpers import exception_factory

from ..._common import *  # noqa: F401,F403


rq_info_details_bp = Blueprint("rq_info_details", __name__, template_folder="templates")


def _utc_iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_queues(raw: str | None) -> Sequence[str]:
    if not raw:
        return DEFAULT_QUEUES
    tokens = [token.strip() for token in str(raw).split(",") if token.strip()]
    return tokens or DEFAULT_QUEUES


def _format_auth_actor(auth_actor: Any) -> str | None:
    if not isinstance(auth_actor, dict) or not auth_actor:
        return None
    token_class = str(auth_actor.get("token_class") or "").strip().lower()
    if token_class == "user":
        user_id = auth_actor.get("user_id")
        return f"user:{user_id}" if user_id is not None else None
    if token_class == "session":
        session_id = auth_actor.get("session_id")
        return f"session:{session_id}" if session_id else None
    if token_class == "service":
        sub = str(auth_actor.get("sub") or "").strip()
        return f"service:{sub}" if sub else None
    if token_class == "mcp":
        sub = str(auth_actor.get("sub") or "").strip()
        return f"mcp:{sub}" if sub else None
    return token_class or None


def _hydrate_submitter(job: dict[str, Any], *, user_cache: dict[int, Any], run_owner_cache: dict[str, Any]) -> None:
    submitter_email = None
    submitter_ip = None

    auth_actor = job.get("auth_actor")
    if isinstance(auth_actor, dict):
        token_class = str(auth_actor.get("token_class") or "").strip().lower()
        if token_class == "user":
            raw_user_id = auth_actor.get("user_id")
            try:
                user_id = int(str(raw_user_id).strip())
            except (TypeError, ValueError):
                user_id = None
            if user_id is not None:
                user = user_cache.get(user_id)
                if user is None and user_id not in user_cache:
                    user = User.query.filter(User.id == user_id).first()
                    user_cache[user_id] = user
                if user is not None:
                    submitter_email = getattr(user, "email", None) or None
                    submitter_ip = (
                        getattr(user, "current_login_ip", None)
                        or getattr(user, "last_login_ip", None)
                        or None
                    )

    if not submitter_email:
        runid = job.get("runid")
        if isinstance(runid, str) and runid:
            owner = run_owner_cache.get(runid)
            if owner is None and runid not in run_owner_cache:
                owners = get_run_owners(runid)
                owner = owners[0] if owners else None
                run_owner_cache[runid] = owner
            if owner is not None:
                submitter_email = getattr(owner, "email", None) or None
                submitter_ip = (
                    getattr(owner, "current_login_ip", None)
                    or getattr(owner, "last_login_ip", None)
                    or None
                )

    if submitter_email:
        job["submitter"] = submitter_email
    elif submitter_ip:
        job["submitter"] = submitter_ip
    else:
        actor_text = _format_auth_actor(auth_actor)
        if actor_text:
            job["submitter"] = actor_text


@rq_info_details_bp.route("/rq/info-details", strict_slashes=False)
@login_required
@roles_accepted("Admin", "Root")
def rq_info_details():
    try:
        queue_names = _parse_queues(request.args.get("queues"))
        lookback_seconds = DEFAULT_RECENT_LOOKBACK_SECONDS

        conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
        with redis.Redis(**conn_kwargs) as redis_conn:
            recent_jobs = list_recently_completed_jobs(
                redis_conn,
                queue_names=queue_names,
                lookback_seconds=lookback_seconds,
            )
            active_jobs = list_active_jobs(redis_conn, queue_names=queue_names)

        user_cache: dict[int, Any] = {}
        run_owner_cache: dict[str, Any] = {}
        for job in recent_jobs:
            _hydrate_submitter(job, user_cache=user_cache, run_owner_cache=run_owner_cache)
        for job in active_jobs:
            _hydrate_submitter(job, user_cache=user_cache, run_owner_cache=run_owner_cache)

        actions = [
            {
                "label": "Refresh",
                "href": url_for_run("rq_info_details.rq_info_details"),
                "variant": "pure-button-secondary",
                "target": "_self",
            }
        ]

        subtitle = (
            f"Static snapshot (no polling). Generated { _utc_iso_now() }. "
            f"Recently completed lookback: {lookback_seconds // 3600}h."
        )

        return render_template(
            "info_details.htm",
            actions=actions,
            subtitle=subtitle,
            queues=list(queue_names),
            lookback_seconds=lookback_seconds,
            recent_jobs=recent_jobs,
            active_jobs=active_jobs,
        )
    except Exception:
        current_app.logger.exception("Failed to load RQ info details page")
        return exception_factory("Failed to load RQ info details")


__all__ = ["rq_info_details_bp"]
