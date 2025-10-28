from typing import Any, Callable, Mapping, TypeVar

F = TypeVar("F", bound=Callable[..., Any])

TOKEN_ENV_VAR: str
ALGORITHMS_ENV_VAR: str
CLAIMS_KWARG: str

def mcp_tool(*, tier: str = ...) -> Callable[[F], F]: ...

def validate_run_scope(runid: str, claims: Mapping[str, Any], *, config: str | None = ...) -> None: ...

def validate_runid(runid: str, claims: Mapping[str, Any]) -> None: ...

