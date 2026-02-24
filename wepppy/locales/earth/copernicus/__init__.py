"""Copernicus DEM retrieval helpers."""

from __future__ import annotations

import math
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

import requests
from requests import Response
from requests.exceptions import RequestException

from wepppy.all_your_base.geo import utm_raster_transform

Extent = Tuple[float, float, float, float]

__all__ = [
    "CopernicusConfigurationError",
    "CopernicusDemError",
    "CopernicusRetryableError",
    "copernicus_retrieve",
]

_STAC_BASE_URL = "https://copernicus-dem-30m-stac.s3.amazonaws.com"
_COG_BASE_URL = "https://copernicus-dem-30m.s3.eu-central-1.amazonaws.com"
_COG_BASE_HOST = urlparse(_COG_BASE_URL).netloc
_DEFAULT_DATASET = "dem_cop_30"


class CopernicusDemError(RuntimeError):
    """Base class for Copernicus DEM retrieval errors."""


class CopernicusRetryableError(CopernicusDemError):
    """Retryable retrieval errors where Ron may fallback to OpenTopography."""


class CopernicusConfigurationError(CopernicusDemError):
    """Non-retryable input/configuration/data-contract errors."""


def _tile_id_for_degree(lat_degree: int, lon_degree: int) -> str:
    lat_hemisphere = "N" if lat_degree >= 0 else "S"
    lon_hemisphere = "E" if lon_degree >= 0 else "W"
    return (
        "Copernicus_DSM_COG_10_"
        f"{lat_hemisphere}{abs(lat_degree):02d}_00_"
        f"{lon_hemisphere}{abs(lon_degree):03d}_00"
    )


def _iter_candidate_tile_ids(extent: Extent) -> List[str]:
    west, south, east, north = extent
    west_i = math.floor(west)
    east_i = math.ceil(east)
    south_i = math.floor(south)
    north_i = math.ceil(north)

    tile_ids: List[str] = []
    for lat_degree in range(south_i, north_i):
        for lon_degree in range(west_i, east_i):
            tile_ids.append(_tile_id_for_degree(lat_degree, lon_degree))
    return tile_ids


def _normalize_dataset(dataset: str) -> str:
    normalized = dataset.strip().lower()
    if normalized.startswith("copernicus://"):
        normalized = normalized.split("://", 1)[1].strip().lower()
    return normalized or _DEFAULT_DATASET


def _request_stac_item(tile_id: str) -> Optional[Dict]:
    url = f"{_STAC_BASE_URL}/items/{tile_id}.json"
    try:
        response: Response = requests.get(url, timeout=30)
    except RequestException as exc:
        raise CopernicusRetryableError(f"Failed to query Copernicus STAC item for tile {tile_id}.") from exc

    if response.status_code == 404:
        return None
    if response.status_code != 200:
        raise CopernicusRetryableError(
            f"Copernicus STAC request failed for tile {tile_id} with status={response.status_code}."
        )

    try:
        payload = response.json()
    except ValueError as exc:
        raise CopernicusRetryableError(
            f"Copernicus STAC item for tile {tile_id} did not return valid JSON."
        ) from exc

    if not isinstance(payload, dict):
        raise CopernicusRetryableError(f"Copernicus STAC item for tile {tile_id} returned unexpected payload.")

    return payload


def _extract_elevation_href(item_payload: Dict, tile_id: str) -> str:
    assets = item_payload.get("assets")
    if not isinstance(assets, dict):
        raise CopernicusConfigurationError(f"Copernicus STAC item {tile_id} has no assets dictionary.")

    elevation_asset = assets.get("elevation")
    if not isinstance(elevation_asset, dict):
        raise CopernicusConfigurationError(f"Copernicus STAC item {tile_id} has no elevation asset.")

    href = elevation_asset.get("href")
    if not isinstance(href, str) or not href:
        raise CopernicusConfigurationError(f"Copernicus STAC item {tile_id} has an invalid elevation href.")

    parsed_href = urlparse(href)
    if parsed_href.scheme != "https":
        raise CopernicusConfigurationError(f"Copernicus STAC item {tile_id} returned non-HTTPS href.")
    if parsed_href.netloc != _COG_BASE_HOST:
        raise CopernicusConfigurationError(
            f"Copernicus STAC item {tile_id} returned unexpected elevation host '{parsed_href.netloc}'."
        )
    if not parsed_href.path.lower().endswith(".tif"):
        raise CopernicusConfigurationError(f"Copernicus STAC item {tile_id} returned a non-TIFF elevation asset.")

    return href


def _build_dem_urls(extent: Extent) -> List[str]:
    dem_urls: List[str] = []
    for tile_id in _iter_candidate_tile_ids(extent):
        item_payload = _request_stac_item(tile_id)
        if item_payload is None:
            continue
        href = _extract_elevation_href(item_payload, tile_id)
        dem_urls.append(href)
    return dem_urls


def _build_vrt_from_urls(urls: List[str], vrt_path: Path) -> None:
    source_list_path = vrt_path.with_suffix(".sources.txt")
    source_list_path.write_text(
        "".join(f"/vsicurl/{href}\n" for href in urls),
        encoding="utf-8",
    )

    try:
        try:
            result = subprocess.run(
                [
                    "gdalbuildvrt",
                    "-overwrite",
                    "-input_file_list",
                    str(source_list_path),
                    str(vrt_path),
                ],
                capture_output=True,
                check=False,
                text=True,
            )
        except (FileNotFoundError, OSError) as exc:
            raise CopernicusRetryableError("Failed to execute gdalbuildvrt while assembling Copernicus DEM.") from exc
    finally:
        if source_list_path.exists():
            source_list_path.unlink()

    if result.returncode != 0:
        stderr = (result.stderr or "").strip().replace("\n", " | ")
        raise CopernicusRetryableError(f"gdalbuildvrt failed while assembling Copernicus DEM VRT: {stderr}")

    if not vrt_path.exists():
        raise CopernicusRetryableError("Copernicus DEM VRT build succeeded but no VRT file was created.")


def copernicus_retrieve(
    extent: Extent,
    dst_fn: str,
    cellsize: float,
    dataset: str = _DEFAULT_DATASET,
    resample: str = "bilinear",
) -> None:
    """Download and reproject Copernicus DEM coverage for ``extent`` into ``dst_fn``."""

    normalized_dataset = _normalize_dataset(dataset)
    if normalized_dataset != _DEFAULT_DATASET:
        raise CopernicusConfigurationError(
            f"Unsupported Copernicus dataset '{dataset}'. Supported dataset is '{_DEFAULT_DATASET}'."
        )

    data_dir = Path(os.path.abspath(dst_fn)).parent
    data_dir.mkdir(parents=True, exist_ok=True)

    dem_urls = _build_dem_urls(extent)
    if not dem_urls:
        raise CopernicusConfigurationError("Copernicus DEM request found no public tiles for the requested extent.")

    with tempfile.TemporaryDirectory(prefix="copernicus-dem-", dir=str(data_dir)) as temp_dir:
        vrt_path = Path(temp_dir) / "copernicus-dem.vrt"
        _build_vrt_from_urls(dem_urls, vrt_path)
        try:
            utm_raster_transform(extent, str(vrt_path), dst_fn, cellsize, resample=resample)
        except AssertionError as exc:
            raise CopernicusRetryableError("Failed to transform Copernicus DEM VRT into the run workspace.") from exc
