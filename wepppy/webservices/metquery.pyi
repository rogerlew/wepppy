from __future__ import annotations

from typing import Any, Dict, Iterable, Optional, Tuple

from flask import Flask, Response


SCRATCH_DIR: str
geodata_dir: str
static_dir: Optional[str]
monthly_catalog: Dict[str, Dict[str, str]]
daily_catalog: Dict[str, Dict[str, str]]


def isint(x: object) -> bool: ...


def gdal_error_handler(err_class: int, err_num: int, err_msg: str) -> None: ...


def crop_nc(nc: str, bbox: Tuple[float, float, float, float], dst: str) -> None: ...


def merge_nc(fn_list: Iterable[str], dst: str) -> None: ...


def safe_float_parse(x: object) -> Optional[float]: ...


def parse_bbox(bbox: str) -> Tuple[Optional[float], Optional[float], Optional[float], Optional[float]]: ...


app: Flask


def health() -> Response: ...


def query_daily_catalog() -> Response: ...


def query_daily_singlepoint() -> Any: ...


def daily_worker(args: Tuple[int, str, Tuple[float, float, float, float]]) -> Tuple[str, str]: ...


def query_daily() -> Response: ...


def query_monthly_catalog() -> Response: ...


def query_monthly() -> Response: ...
