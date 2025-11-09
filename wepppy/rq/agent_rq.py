from __future__ import annotations

import json
import os
import shlex
from typing import Any, Dict, Optional

import redis
import requests
from rq.decorators import job

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.weppcloud.utils.helpers import get_wd

CAO_BASE_URL = os.getenv("CAO_BASE_URL", "http://localhost:9889")
CAO_AGENT_PROFILE = os.getenv("WOJAK_AGENT_PROFILE", "wojak_interactive")
CAO_REQUEST_TIMEOUT = float(os.getenv("CAO_REQUEST_TIMEOUT", "10"))
ENV_TTL_SECONDS = int(os.getenv("WOJAK_AGENT_ENV_TTL", "300"))
REDIS_RESPONSE_TEMPLATE = "agent_response-{session_id}"
REDIS_CHAT_TEMPLATE = "agent_chat-{session_id}"
ENV_KEY_TEMPLATE = "agent:session:{session_id}:env"

_redis_client: Optional[redis.StrictRedis] = None
_rq_connection: redis.Redis = redis.Redis(**redis_connection_kwargs(RedisDB.RQ))


def _redis() -> redis.StrictRedis:
    """Return a cached StrictRedis client for agent coordination channels."""
    global _redis_client
    if _redis_client is None:
        pool = redis.ConnectionPool(
            **redis_connection_kwargs(
                RedisDB.STATUS,
                decode_responses=True,
                extra={"max_connections": 10},
            )
        )
        _redis_client = redis.StrictRedis(connection_pool=pool)
    return _redis_client


def _publish(channel: str, payload: Dict[str, Any]) -> None:
    """Publish a JSON payload to the provided Redis pub/sub channel."""
    _redis().publish(channel, json.dumps(payload, separators=(",", ":")))


def _store_env(session_id: str, payload: Dict[str, Any]) -> str:
    """Persist agent session metadata in Redis and return the storage key."""
    env_key = ENV_KEY_TEMPLATE.format(session_id=session_id)
    _redis().setex(env_key, ENV_TTL_SECONDS, json.dumps(payload))
    return env_key


def _bootstrap_command(
    *,
    runid: str,
    config: str,
    session_id: str,
    chat_channel: str,
    response_channel: str,
    env_key: str,
) -> str:
    """Build the shell command used to bootstrap a Wojak CAO session."""
    exports = {
        "SESSION_ID": session_id,
        "RUNID": runid,
        "CONFIG": config,
        "REDIS_CHAT_CHANNEL": chat_channel,
        "REDIS_RESPONSE_CHANNEL": response_channel,
        "AGENT_ENV_REDIS_KEY": env_key,
    }
    export_parts = [
        f"{key}={shlex.quote(value)}"
        for key, value in exports.items()
    ]
    export_cmd = "export " + " ".join(export_parts)
    script_path = os.getenv(
        "WOJAK_BOOTSTRAP_SCRIPT",
        "/workdir/wepppy/services/cao/scripts/wojak_bootstrap.py",
    )
    python_cmd = os.getenv("WOJAK_BOOTSTRAP_PYTHON", "python3")
    return f"{export_cmd} && {python_cmd} {shlex.quote(script_path)}"


def _start_bootstrap(terminal_id: str, command: str) -> None:
    """Send the bootstrap command to the CAO terminal."""
    response = requests.post(
        f"{CAO_BASE_URL}/terminals/{terminal_id}/input",
        params={"message": command},
        timeout=CAO_REQUEST_TIMEOUT,
    )
    response.raise_for_status()


@job("default", connection=_rq_connection)
def spawn_wojak_session(
    runid: str,
    config: str,
    session_id: str,
    jwt_token: str,
    user_id: str,
    jwt_secret: str,
) -> Dict[str, Any]:
    """Spawn a CAO/Ash (Wojak) session and persist its runtime metadata.

    Args:
        runid: Identifier used to locate the working directory.
        config: Configuration stem for the run (ex. ``disturbed9002``).
        session_id: CAO session identifier (mirrors UI socket ids).
        jwt_token: Wojak JWT token used for downstream API calls.
        user_id: Authenticated WEPPcloud user identifier.
        jwt_secret: Signing secret so the bootstrapper can mint tokens.

    Returns:
        Dictionary describing the CAO terminal plus Redis channel names.
    """

    chat_channel = REDIS_CHAT_TEMPLATE.format(session_id=session_id)
    response_channel = REDIS_RESPONSE_TEMPLATE.format(session_id=session_id)

    run_dir = get_wd(runid)

    env_payload = {
        "AGENT_JWT_TOKEN": jwt_token,
        "AGENT_JWT_SECRET": jwt_secret,
        "AGENT_JWT_ALGORITHMS": "HS256",
        "RUNID": runid,
        "CONFIG": config,
        "SESSION_ID": session_id,
        "USER_ID": user_id,
        "REDIS_CHAT_CHANNEL": chat_channel,
        "REDIS_RESPONSE_CHANNEL": response_channel,
        "RUN_DIR": run_dir,
    }
    env_key = _store_env(session_id, env_payload)

    params = {
        "provider": "codex",
        "agent_profile": CAO_AGENT_PROFILE,
        "session_name": f"wojak-{session_id}",
    }

    try:
        response = requests.post(
            f"{CAO_BASE_URL}/sessions",
            params=params,
            timeout=CAO_REQUEST_TIMEOUT,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        _publish(
            f"{runid}:{response_channel}",
            {
                "type": "error",
                "content": f"Failed to spawn agent session: {exc}",
            },
        )
        raise

    terminal_info = response.json()
    full_response_channel = f"{runid}:{response_channel}"
    _publish(
        full_response_channel,
        {
            "type": "system",
            "content": "Agent session initialized. Connecting Wojak...",
            "env_key": env_key,
        },
    )

    command = _bootstrap_command(
        runid=runid,
        config=config,
        session_id=session_id,
        chat_channel=chat_channel,
        response_channel=response_channel,
        env_key=env_key,
    )

    terminal_id = terminal_info.get("id")
    if terminal_id:
        try:
            _start_bootstrap(terminal_id, command)
        except requests.RequestException as exc:
            _publish(
                full_response_channel,
                {
                    "type": "error",
                    "content": f"Failed to launch Wojak bootstrap: {exc}",
                },
            )
            raise

    return {
        "terminal": terminal_info,
        "env_key": env_key,
        "chat_channel": chat_channel,
        "response_channel": response_channel,
    }
