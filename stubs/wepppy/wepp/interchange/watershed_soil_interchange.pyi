from __future__ import annotations

from pathlib import Path
from typing import Any

SOIL_FILENAME: str
SOIL_PARQUET: str
CHUNK_SIZE: int
SCHEMA: Any

def run_wepp_watershed_soil_interchange(wepp_output_dir: Path | str) -> Path: ...
