from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from fastapi import BackgroundTasks, Depends, FastAPI, Path, Query
from fastapi.responses import FileResponse


logger: logging.Logger
geodata_dir: str
SCRATCH_DIR: str
_catalog: str
resample_methods: tuple[str, ...]
ext_d: Dict[str, str]
format_drivers: tuple[str, ...]
gdaldem_modes: tuple[str, ...]
ROOT_PATH: str
app: FastAPI


def _b64url(obj: Dict[str, Any]) -> str: ...


def from_b64url(s: str) -> Dict[str, Any]: ...


def b64url_compact(obj: Dict[str, Any]) -> str: ...


def from_b64url_compact(s: str) -> Dict[str, Any]: ...


def determine_band_type(vrt: str) -> Optional[str]: ...


def load_maps(geodata: str) -> List[str]: ...


def raster_stats(src: str) -> Dict[str, float]: ...


def format_convert(src: str, _format: str) -> str: ...


def process_raster(
    dataset: str,
    bbox: Tuple[float, float, float, float],
    cellsize: float,
    resample: Optional[str],
    _format: str,
    gdaldem: Optional[str],
) -> Tuple[str, Dict[str, Any], List[str]]: ...


def parse_bbox(bbox: Any = Query(...)) -> Tuple[float, float, float, float]: ...


def cleanup_files(files: List[str]) -> None: ...


async def health() -> Dict[str, str]: ...


async def catalog() -> List[str]: ...


async def api_dataset_retrieve(
    background_tasks: BackgroundTasks,
    dataset: Any = Path(...),
    bbox: Any = Depends(parse_bbox),
    cellsize: Any = Query(30.0),
    resample: Any = Query(None),
    _format: Any = Query("GTiff"),
    gdaldem: Any = Query(None),
) -> FileResponse: ...
