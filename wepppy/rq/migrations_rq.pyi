"""Type stubs for wepppy.rq.migrations_rq."""

from typing import Dict, List, Optional

STATUS_CHANNEL_SUFFIX: str

def migrations_rq(
    wd: str,
    runid: str,
    *,
    archive_before: bool = ...,
    migrations: Optional[List[str]] = ...,
) -> dict: ...
