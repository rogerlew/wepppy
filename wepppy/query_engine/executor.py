"""DuckDB execution helpers with optional spatial extension loading."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Sequence

import duckdb
import pyarrow as pa
import pyarrow.dataset as pads

from wepppy.query_engine.payload import QuerySource


_GEOMETRY_WKB_COLUMN = "__wepp_geometry_wkb"


def _find_forbidden_function(node: object, function_names: frozenset[str]) -> str | None:
    if isinstance(node, dict):
        function_name = str(node.get("function_name", "")).lower()
        if function_name in function_names:
            return function_name
        for value in node.values():
            found = _find_forbidden_function(value, function_names)
            if found is not None:
                return found
    if isinstance(node, list):
        for value in node:
            found = _find_forbidden_function(value, function_names)
            if found is not None:
                return found
    return None


def _plain_spatial_table(path: str) -> pa.Table:
    """Read a trusted vector source and normalize GeoArrow WKB for DuckDB 1.1."""
    import pyogrio

    _metadata, table = pyogrio.read_arrow(path)
    arrays: list[pa.ChunkedArray] = []
    fields: list[pa.Field] = []
    geometry_found = False
    for field, column in zip(table.schema, table.columns):
        extension_name = (field.metadata or {}).get(b"ARROW:extension:name")
        if extension_name == b"geoarrow.wkb":
            if geometry_found:
                raise ValueError(f"Spatial dataset has multiple geometry columns: {path}")
            geometry_found = True
            fields.append(pa.field(_GEOMETRY_WKB_COLUMN, pa.binary(), nullable=field.nullable))
        else:
            fields.append(pa.field(field.name, field.type, nullable=field.nullable, metadata=field.metadata))
        arrays.append(column)
    if not geometry_found:
        raise ValueError(f"Spatial dataset has no GeoArrow WKB geometry column: {path}")
    return pa.Table.from_arrays(arrays, schema=pa.schema(fields, metadata=table.schema.metadata))


class DuckDBExecutor:
    """Execute DuckDB queries inside a context-scoped connection."""

    def __init__(self, base_dir: Path) -> None:
        self._base_dir = base_dir
        self._logger = logging.getLogger(__name__)

    def execute(
        self,
        sql: str,
        params: Sequence[object] | None = None,
        *,
        use_spatial: bool = False,
        sources: Sequence[QuerySource] = (),
    ) -> pa.Table:
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
                    except Exception as exc:  # broad-except: boundary contract; extension loader varies by DuckDB build
                        self._logger.error("Failed to load DuckDB spatial extension", exc_info=True)
                        raise RuntimeError("DuckDB spatial extension unavailable") from exc
            conn.execute("SET home_directory = ?", [str(self._base_dir)])
            retained_sources: list[object] = []
            for source in sources:
                registered = _plain_spatial_table(source.path) if source.spatial else pads.dataset(source.path, format="parquet")
                retained_sources.append(registered)
                conn.register(source.relation_name, registered)

            serialized = conn.execute(
                "SELECT json_serialize_sql(CAST(? AS VARCHAR))",
                [sql],
            ).fetchone()[0]
            statement = json.loads(serialized)
            if statement.get("error"):
                raise duckdb.ParserException(str(statement.get("error_message", "Invalid SQL")))
            forbidden = _find_forbidden_function(statement, frozenset({"query", "st_transform"}))
            if forbidden == "st_transform":
                raise ValueError("ST_Transform is unavailable in query expressions because it can read external grid files")
            if forbidden == "query":
                raise ValueError("Dynamic SQL is unavailable in query expressions")

            conn.execute("SET autoinstall_known_extensions = false")
            conn.execute("SET autoload_known_extensions = false")
            conn.execute("SET enable_external_access = false")
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
