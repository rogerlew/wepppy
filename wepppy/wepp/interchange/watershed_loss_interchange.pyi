from __future__ import annotations

from collections import OrderedDict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple, TypedDict

LOSS_FILENAME: str
AVERAGE_FILENAMES: Dict[str, str]
ALL_YEARS_FILENAMES: Dict[str, str]
SCHEMA_VERSION: bytes
unit_consistency_map: Dict[Optional[str], str]
HILL_HEADER: Tuple[str, ...]
HILL_AVG_HEADER: Tuple[str, ...]
HILL_UNITS: Tuple[Optional[str], ...]
HILL_AVG_UNITS: Tuple[Optional[str], ...]
HILL_TYPES: Tuple[Any, ...]
HILL_AVG_TYPES: Tuple[Any, ...]
CHN_HEADER: Tuple[str, ...]
CHN_AVG_HEADER: Tuple[str, ...]
CHN_UNITS: Tuple[Optional[str], ...]
CHN_AVG_UNITS: Tuple[Optional[str], ...]
CHN_TYPES: Tuple[Any, ...]
CHN_AVG_TYPES: Tuple[Any, ...]
CLASS_HEADER: Tuple[str, ...]
CLASS_UNITS: Tuple[Optional[str], ...]
HILL_ALL_YEARS_SCHEMA: Any
HILL_AVERAGE_SCHEMA: Any
CHN_ALL_YEARS_SCHEMA: Any
CHN_AVERAGE_SCHEMA: Any
OUT_ALL_YEARS_SCHEMA: Any
OUT_AVERAGE_SCHEMA: Any
CLASS_ALL_YEARS_SCHEMA: Any
CLASS_AVERAGE_SCHEMA: Any


class ParsedLossData(TypedDict):
    yearly_hill: List[Dict[str, object]]
    yearly_chn: List[Dict[str, object]]
    yearly_out: List[Dict[str, object]]
    yearly_class: List[Dict[str, object]]
    average_hill: List[Dict[str, object]]
    average_chn: List[Dict[str, object]]
    average_out: List[Dict[str, object]]
    average_class: List[Dict[str, object]]
    average_years: Optional[int]


def _coerce_value(value: object, field: Any) -> object: ...


def _rows_to_table(rows: Iterable[Dict[str, object]], schema: Any) -> Any: ...


def _find_tbl_starts(section_index: int, lines: List[str]) -> Tuple[int, int, int]: ...


def _parse_tbl(lines: Iterable[str], header: Tuple[str, ...]) -> List[OrderedDict[str, object]]: ...


def _parse_out(lines: Iterable[str]) -> List[Dict[str, object]]: ...


def _extract_class_data(lines: List[str]) -> List[OrderedDict[str, object]]: ...


def _collect_class_block(lines: List[str], start: int, end: int) -> List[OrderedDict[str, object]]: ...


def _parse_loss_file(path: Path) -> ParsedLossData: ...


def _build_tables(parsed: ParsedLossData) -> Dict[str, Any]: ...


def _enrich_loss_tables(tables: Dict[str, Any]) -> Dict[str, Any]: ...


def run_wepp_watershed_loss_interchange(wepp_output_dir: Path | str) -> Dict[str, Path]: ...
