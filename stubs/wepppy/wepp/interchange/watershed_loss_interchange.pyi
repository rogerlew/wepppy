from __future__ import annotations

from pathlib import Path
from typing import Dict

LOSS_FILENAME: str
AVERAGE_FILENAMES: Dict[str, str]
ALL_YEARS_FILENAMES: Dict[str, str]

def run_wepp_watershed_loss_interchange(wepp_output_dir: Path | str) -> Dict[str, Path]: ...
