from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

__all__ = ["totalwatsed_partitioned_dss_export", "archive_dss_export_zip"]

def _channel_wepp_ids(translator: object, network: object, channel_top_id: int) -> List[int]: ...

def _column_units(table: object) -> Dict[str, str]: ...

def _require_pydsstools() -> Tuple[type, type]: ...

def totalwatsed_partitioned_dss_export(
    wd: Path | str,
    export_channel_ids: Optional[List[int]] = ...,
    status_channel: Optional[str] = ...,
) -> None: ...

def archive_dss_export_zip(wd: Path | str, status_channel: Optional[str] = ...) -> None: ...
