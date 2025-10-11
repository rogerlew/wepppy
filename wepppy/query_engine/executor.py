from __future__ import annotations

from pathlib import Path
from typing import Iterable, Sequence

import duckdb
import pyarrow as pa
import logging


class DuckDBExecutor:
    def __init__(self, base_dir: Path) -> None:
        self._base_dir = base_dir
        self._logger = logging.getLogger(__name__)

    def execute(self, sql: str, params: Sequence[object] | None = None, *, use_spatial: bool = False) -> pa.Table:
        with duckdb.connect() as conn:
            if use_spatial:
                try:
                    conn.execute("SET home_directory='/tmp';")
                    conn.load_extension("spatial")
                except duckdb.IOException:
                    try:
                        conn.install_extension("spatial")
                        conn.load_extension("spatial")
                    except Exception as exc:  # pragma: no cover - environment dependent
                        self._logger.error("Failed to load DuckDB spatial extension", exc_info=True)
                        raise RuntimeError("DuckDB spatial extension unavailable") from exc
            conn.execute("SET home_directory = ?", [str(self._base_dir)])
            cursor = conn.execute(sql, params or [])
            return cursor.fetch_arrow_table()
