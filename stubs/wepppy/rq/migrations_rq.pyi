"""Type stubs for wepppy.rq.migrations_rq."""

from typing import List, Optional

STATUS_CHANNEL_SUFFIX: str

def migrations_rq(
    wd: str,
    runid: str,
    *,
    archive_before: bool = ...,
    migrations: Optional[List[str]] = ...,
    restore_readonly: bool = ...,
) -> dict: ...

__all__: list[str] = [
    "migrations_rq",
    "STATUS_CHANNEL_SUFFIX",
]
