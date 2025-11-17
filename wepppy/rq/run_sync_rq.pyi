from typing import Any, Dict, Optional, Tuple

DEFAULT_TARGET_ROOT: str
STATUS_CHANNEL_SUFFIX: str
STATUS_EVENTS: Tuple[str, ...]

def run_sync_rq(
    runid: str,
    config: str,
    source_host: str,
    owner_email: Optional[str] = ...,
    target_root: str = ...,
    auth_token: Optional[str] = ...,
    allow_push: bool = ...,
    overwrite: bool = ...,
    expected_size: Optional[int] = ...,
    expected_sha256: Optional[str] = ...,
) -> Dict[str, Any]: ...
