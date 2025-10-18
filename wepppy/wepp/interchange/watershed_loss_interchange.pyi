from __future__ import annotations

from collections import OrderedDict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple, TypedDict

import pyarrow as pa


__all__ = ["ParsedLossData", "run_wepp_watershed_loss_interchange"]


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


def _coerce_value(value: object, field: pa.Field) -> object: ...


def _rows_to_table(rows: Iterable[Dict[str, object]], schema: pa.Schema) -> pa.Table: ...


def _find_tbl_starts(section_index: int, lines: List[str]) -> Tuple[int, int, int]: ...


def _parse_tbl(lines: Iterable[str], header: Tuple[str, ...]) -> List[OrderedDict[str, object]]: ...


def _parse_out(lines: Iterable[str]) -> List[Dict[str, object]]: ...


def _extract_class_data(lines: List[str]) -> List[OrderedDict[str, object]]: ...


def _collect_class_block(lines: List[str], start: int, end: int) -> List[OrderedDict[str, object]]: ...


def _parse_loss_file(path: Path) -> ParsedLossData: ...


def _build_tables(parsed: ParsedLossData) -> Dict[str, pa.Table]: ...


def _enrich_loss_tables(tables: Dict[str, pa.Table]) -> Dict[str, pa.Table]: ...


def run_wepp_watershed_loss_interchange(wepp_output_dir: Path | str) -> Dict[str, Path]: ...
