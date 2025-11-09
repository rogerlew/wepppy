from __future__ import annotations

from pathlib import Path
from typing import Any, List, Sequence, Tuple

HILLSLOPE_DOC_ORDER: List[Tuple[str, str]]
WATERSHED_DOC_ORDER: List[Tuple[str, str]]
MAX_SAMPLE_ROWS: int

def _format_units(field: Any) -> str: ...

def _format_description(field: Any) -> str: ...

def _schema_markdown(schema: Any) -> str: ...

def _table_preview_markdown(table: Any) -> str: ...

def _summarize_file(parquet_path: Path, description: str) -> str: ...

def generate_interchange_documentation(interchange_dir: Path | str, to_readme_md: bool = ...) -> str: ...
