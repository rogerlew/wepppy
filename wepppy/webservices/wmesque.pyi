from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

from flask import Flask, Response


geodata_dir: str
resample_methods: Tuple[str, ...]
ext_d: Dict[str, str]
format_drivers: Tuple[str, ...]
gdaldem_modes: Tuple[str, ...]
SCRATCH_DIR: str
app: Flask


def _b64url(obj: Dict[str, object]) -> str: ...


def raster_stats(src: str) -> Dict[str, float]: ...


def format_convert(src: str, _format: str) -> Optional[str]: ...


def determine_band_type(vrt: str) -> Optional[str]: ...


def find_maps(geodata: str) -> List[str]: ...


def safe_float_parse(value: object) -> Optional[float]: ...


def parse_bbox(bbox: str) -> Tuple[Optional[float], Optional[float], Optional[float], Optional[float]]: ...


def health() -> Response: ...


def catalog() -> Response: ...


def api_dataset_year(
    dataset: str,
    year: str,
    layer: str = ...,
    foo: str = ...,
    bar: str = ...,
    foo2: str = ...,
    bar2: str = ...,
    methods: Sequence[str] = ...,
) -> Response: ...
