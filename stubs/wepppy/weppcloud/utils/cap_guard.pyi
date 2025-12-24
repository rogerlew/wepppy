from typing import Any, Callable, Optional

CAP_SESSION_KEY: str
DEFAULT_TTL_SECONDS: int

def mark_cap_verified() -> None: ...
def cap_gate_response(next_url: Optional[str] = ..., reason: Optional[str] = ...) -> Any: ...
def requires_cap(
    ttl_seconds: Optional[int] = ...,
    gate_reason: Optional[str] = ...,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]: ...
