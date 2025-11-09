from __future__ import annotations

from pathlib import Path
from typing import Sequence

import pyarrow as pa

class DuckDBExecutor:
    def __init__(self, base_dir: Path) -> None: ...
    def execute(self, sql: str, params: Sequence[object] | None = ..., *, use_spatial: bool = ...) -> pa.Table: ...
