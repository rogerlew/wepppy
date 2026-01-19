from __future__ import annotations

from typing import Any, Dict

CAO_BASE_URL: str
CAO_AGENT_PROFILE: str
CAO_REQUEST_TIMEOUT: float
ENV_TTL_SECONDS: int
REDIS_RESPONSE_TEMPLATE: str
REDIS_CHAT_TEMPLATE: str
ENV_KEY_TEMPLATE: str

def spawn_wojak_session(
    runid: str,
    config: str,
    session_id: str,
    jwt_token: str,
    user_id: str,
    jwt_secret: str,
) -> Dict[str, Any]: ...
