"""DuckDB execution helpers with optional spatial extension loading."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Sequence

import duckdb
import pyarrow as pa


class DuckDBExecutor:
    """Execute DuckDB queries inside a context-scoped connection."""

    def __init__(self, base_dir: Path) -> None:
        self._base_dir = base_dir
        self._logger = logging.getLogger(__name__)

    def execute(self, sql: str, params: Sequence[object] | None = None, *, use_spatial: bool = False) -> pa.Table:
        """Execute SQL and return a PyArrow table.

        Args:
            sql: Parameterised SQL string to execute.
            params: Optional positional parameters bound to the query.
            use_spatial: When True, ensure the DuckDB spatial extension is loaded.

        Returns:
            PyArrow table containing the result set.

        Raises:
            RuntimeError: If the spatial extension cannot be installed/loaded.
            duckdb.ParserException: If DuckDB rejects the SQL string.
        """
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
            try:
                cursor = conn.execute(sql, params or [])
            except duckdb.ParserException as err:
                details = [str(err).rstrip(), "SQL:", sql]
                if params:
                    details.append(f"Parameters: {params!r}")
                message = "\n".join(details)
                self._logger.error("DuckDB parser error when executing query", exc_info=True)
                raise duckdb.ParserException(message) from err
            return cursor.fetch_arrow_table()
