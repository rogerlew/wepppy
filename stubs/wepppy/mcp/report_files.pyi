from typing import Any, Dict, Mapping, Optional

MAX_FILE_BYTES: int

def describe_run_contents(runid: str, category: Optional[str] = ..., _jwt_claims: Mapping[str, Any] | None = ...) -> Dict[str, Any]: ...

def read_run_file(runid: str, path: str, *, encoding: str = ..., _jwt_claims: Mapping[str, Any] | None = ...) -> str: ...

