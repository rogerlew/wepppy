from __future__ import annotations

from pathlib import Path

from wepppy.wepp.management.managements import Management

def downgrade_to_98_4_format(
    management: Management,
    filepath: str | Path,
    resurfacing_fraction_mode: str = ...,
    unsupported_operation_mode: str = ...,
    first_year_only: bool = ...,
) -> Path: ...
