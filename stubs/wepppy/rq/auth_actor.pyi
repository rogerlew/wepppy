from typing import Any, Mapping
from contextvars import Token

def current_auth_actor() -> dict[str, Any] | None: ...
def set_auth_actor(actor: Mapping[str, Any] | None) -> Token: ...
def reset_auth_actor(token: Token) -> None: ...
def install_rq_auth_actor_hook() -> None: ...

__all__: list[str] = [
    "current_auth_actor",
    "install_rq_auth_actor_hook",
    "reset_auth_actor",
    "set_auth_actor",
]
