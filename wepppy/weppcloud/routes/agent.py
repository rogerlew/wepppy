from __future__ import annotations

import json
import time
import uuid
from typing import Any, Dict, Optional

import redis
from flask import Blueprint, Response, current_app, jsonify, request
from flask_login import current_user, login_required

from wepppy.config.redis_settings import (
    RedisDB,
    redis_connection_kwargs,
)
from wepppy.weppcloud.utils.agent_auth import (
    AGENT_JWT_SECRET_KEY,
    generate_agent_token,
)
from wepppy.rq.agent_rq import spawn_wojak_session

agent_bp = Blueprint("agent", __name__)

_redis_client: Optional[redis.StrictRedis] = None


def _redis() -> redis.StrictRedis:
    global _redis_client
    if _redis_client is None:
        pool = redis.ConnectionPool(
            **redis_connection_kwargs(
                RedisDB.STATUS,
                decode_responses=True,
                extra={"max_connections": 20},
            )
        )
        _redis_client = redis.StrictRedis(connection_pool=pool)
    return _redis_client


def _session_activity_key(session_id: str) -> str:
    return f"agent:session:{session_id}:last_activity"


def _publish(channel: str, payload: Dict[str, Any]) -> None:
    serialized = json.dumps(payload, separators=(",", ":"))
    _redis().publish(channel, serialized)


def _update_last_activity(session_id: str, ttl_seconds: int) -> None:
    timestamp = int(time.time())
    _redis().setex(_session_activity_key(session_id), ttl_seconds, timestamp)


def _agent_secret() -> str:
    secret = current_app.config.get(AGENT_JWT_SECRET_KEY)
    if not secret:
        raise RuntimeError("Agent JWT secret is not configured")
    return secret


@agent_bp.route("/runs/<runid>/<config>/agent/chat", methods=["POST"])
@login_required
def initialize_agent_chat(runid: str, config: str) -> Response:
    """
    Initialize a Wojak agent session for the authenticated user.
    """

    payload = request.get_json(silent=True) or {}
    ttl_seconds = int(payload.get("ttl_seconds") or 1800)  # 30 minutes inactivity TTL
    session_id = str(uuid.uuid4())

    token = generate_agent_token(
        user_id=current_user.get_id(),
        runid=runid,
        config=config,
        session_id=session_id,
    )

    secret = _agent_secret()

    try:
        job = spawn_wojak_session.delay(
            runid,
            config,
            session_id,
            token,
            current_user.get_id(),
            secret,
        )
    except Exception as exc:  # pragma: no cover - enqueuing failure is rare
        current_app.logger.exception("Failed to enqueue agent session: %s", exc)
        return jsonify({"error": "Failed to start agent session"}), 500

    _update_last_activity(session_id, ttl_seconds)

    response_payload = {
        "session_id": session_id,
        "job_id": job.id if job else None,
        "redis_channel": f"agent_response-{session_id}",
        "status": "initializing",
        "ttl_seconds": ttl_seconds,
    }
    return jsonify(response_payload), 202


@agent_bp.route("/runs/<runid>/<config>/agent/chat/<session_id>", methods=["POST"])
@login_required
def send_agent_message(runid: str, config: str, session_id: str) -> Response:
    """
    Publish a user message to the Wojak agent channel.
    """

    payload = request.get_json(silent=True) or {}
    message = (payload.get("message") or "").strip()
    if not message:
        return jsonify({"error": "message is required"}), 400

    ttl_seconds = int(payload.get("ttl_seconds") or 1800)

    chat_channel = f"agent_chat-{session_id}"
    _publish(
        chat_channel,
        {
            "type": "user_message",
            "content": message,
            "user_id": current_user.get_id(),
            "timestamp": time.time(),
        },
    )
    _update_last_activity(session_id, ttl_seconds)

    return jsonify({"status": "sent", "redis_channel": chat_channel})


@agent_bp.route("/runs/<runid>/<config>/agent/chat/<session_id>", methods=["DELETE"])
@login_required
def terminate_agent_session(runid: str, config: str, session_id: str) -> Response:
    """
    Signal the Wojak agent session to terminate and clear activity metadata.
    """

    _publish(
        f"agent_chat-{session_id}",
        {
            "type": "terminate",
            "user_id": current_user.get_id(),
            "timestamp": time.time(),
        },
    )

    _redis().delete(_session_activity_key(session_id))
    return jsonify({"status": "terminated"})
