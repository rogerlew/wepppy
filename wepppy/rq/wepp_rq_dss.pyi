from __future__ import annotations

from typing import Any, Dict, Iterable, Optional

def _cleanup_dss_export_dir(wd: str) -> None: ...

def _copy_dss_readme(wd: str, status_channel: Optional[str] = None) -> None: ...

def _resolve_downstream_channel_ids(network: Any, seeds: Iterable[int]) -> set[int]: ...

def _extract_channel_topaz_id(feature: Dict[str, Any]) -> int | None: ...

def _write_dss_channel_geojson(
    wd: str,
    channel_ids: Optional[list[int]],
    *,
    boundary_width_m: float = ...,
) -> None: ...
