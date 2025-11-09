from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Tuple

AVERAGE_FILENAMES: Dict[str, str]

def _ensure_interchange_assets(output_dir: Path) -> Dict[str, Path]: ...

def _read_table(path: Path) -> Tuple[object, Dict[bytes, bytes]]: ...

def _augment_hill_channel_frames(
    hill_df: object,
    chn_df: object,
    wd: Optional[str],
    has_phosphorus: bool,
) -> Tuple[object, object]: ...

class Loss:
    def __init__(self, fn: str | Path, has_phosphorus: bool = ..., wd: Optional[str] = ...) -> None: ...
    @property
    def hill_tbl(self) -> List[Dict[str, object]]: ...
    @property
    def chn_tbl(self) -> List[Dict[str, object]]: ...
    @property
    def out_tbl(self) -> List[Dict[str, object]]: ...
    def outlet_fraction_under(self, particle_size: float = ...) -> float: ...

__all__ = ["Loss"]
