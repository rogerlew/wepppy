from __future__ import annotations

from pathlib import Path
from typing import Dict

PASS_FILENAME: str
EVENTS_PARQUET: str
METADATA_PARQUET: str
EVENT_CHUNK_SIZE: int

def run_wepp_watershed_pass_interchange(wepp_output_dir: Path | str) -> Dict[str, Path]: ...
