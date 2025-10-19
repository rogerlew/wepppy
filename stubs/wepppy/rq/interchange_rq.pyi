from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional

TIMEOUT: int
_REQUIRED_WATERSHED_OUTPUTS: tuple[str, ...]

def _with_gzip(path: Path) -> Path: ...

def _missing_wepp_outputs(base: Path, filenames: Iterable[str]) -> list[str]: ...

def run_interchange_migration(runid: str, wepp_output_subpath: Optional[str] = ...) -> bool: ...
