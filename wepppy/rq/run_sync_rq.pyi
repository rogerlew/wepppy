from typing import Any, Dict, Optional, Tuple

DEFAULT_TARGET_ROOT: str
DEFAULT_CONFIG: str
STATUS_CHANNEL_SUFFIX: str
STATUS_EVENTS: Tuple[str, ...]

def run_sync_rq(
    runid: str,
    source_host: str,
    owner_email: Optional[str] = ...,
    target_root: str = ...,
    config: Optional[str] = ...,
) -> Dict[str, Any]: ...
