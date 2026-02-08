from __future__ import annotations

from collections.abc import Mapping

CANONICAL_ERROR_PAYLOAD = (
    "Canonical error payload: {'error': {'message': '...', 'code': 'optional', 'details': '...'}}."
)

UNAUTHORIZED_DESCRIPTION = (
    "Unauthorized authentication state. Returns the canonical error payload."
)

FORBIDDEN_DESCRIPTION = (
    "Forbidden for missing scope or failed run access checks. Returns the canonical error payload."
)

SERVER_ERROR_DESCRIPTION = (
    "Unexpected server failure. Returns the canonical error payload."
)


def rq_operation_id(name: str) -> str:
    return f"rq_engine_{name}"


def agent_route_responses(
    *,
    success_code: int,
    success_description: str,
    extra: Mapping[int, str] | None = None,
) -> dict[int, dict[str, str]]:
    responses: dict[int, dict[str, str]] = {
        int(success_code): {"description": success_description}
    }
    if extra:
        for code, description in extra.items():
            responses[int(code)] = {"description": description}
    responses[401] = {"description": UNAUTHORIZED_DESCRIPTION}
    responses[403] = {"description": FORBIDDEN_DESCRIPTION}
    responses[500] = {"description": SERVER_ERROR_DESCRIPTION}
    return responses


__all__ = [
    "CANONICAL_ERROR_PAYLOAD",
    "agent_route_responses",
    "rq_operation_id",
]
