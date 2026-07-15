from __future__ import annotations

from pathlib import Path
from typing import Any

PASS_FAMILY_AUTO: str
PASS_FAMILY_LEGACY_ASCII: str
PASS_FAMILY_HBP: str
PASS_FAMILY_CHOICES: set[str]
SCHEMA: Any

def run_wepp_hillslope_pass_interchange(
    wepp_output_dir: Path | str,
    *,
    expected_hillslopes: int | None = ...,
    pass_family: str | None = ...,
    max_workers: int | None = ...,
) -> Path: ...
