from __future__ import annotations

from pathlib import Path
from typing import Iterable, Sequence

import duckdb
import pyarrow as pa


class DuckDBExecutor:
    def __init__(self, base_dir: Path) -> None:
        self._base_dir = base_dir

    def execute(self, sql: str, params: Sequence[object] | None = None, *, use_spatial: bool = False) -> pa.Table:
        with duckdb.connect() as conn:
            if use_spatial:
                conn.install_extension("spatial")
                conn.load_extension("spatial")
            conn.execute("SET home_directory = ?", [str(self._base_dir)])
            cursor = conn.execute(sql, params or [])
            return cursor.fetch_arrow_table()
