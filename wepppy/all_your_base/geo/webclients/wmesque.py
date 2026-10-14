"""Client helpers for the WMesque raster retrieval service."""

from __future__ import annotations

import base64
import binascii
import json
import logging
import os
from pathlib import Path
import tempfile
import time
from http.client import IncompleteRead, RemoteDisconnected
import shutil
import socket
from collections.abc import Sequence
from urllib.parse import quote, urlsplit
from urllib.error import HTTPError, URLError
from urllib.request import urlopen as _legacy_urlopen
from ._wmesque_http import open_with_deadline as urlopen

from deprecated import deprecated

def isfloat(x: object) -> bool:
    try:
        float(x)
    except (TypeError, ValueError):
        return False
    return True

TIMEOUT = 300
WMESQUE_ENDPOINT = 'https://wepp.cloud/webservices/wmesque/'
WMESQUE2_ENDPOINT = 'https://wepp.cloud/webservices/wmesque2/'

@deprecated
def _wmesque1_retrieve(
    dataset: str,
    extent: Sequence[float],
    fname: str,
    cellsize: float,
    resample: str | None = None,
) -> int:
    """Legacy endpoint that proxies the original WMesque CGI service."""
    global WMESQUE_ENDPOINT

    assert isfloat(cellsize)

    assert all([isfloat(v) for v in extent])
    assert len(extent) == 4

    extent = ','.join([str(v) for v in extent])

    if fname.lower().endswith('.tif'):
        fmt = 'GTiff'

    elif fname.lower().endswith('.asc'):
        fmt = 'AAIGrid'

    elif fname.lower().endswith('.png'):
        fmt = 'PNG'

    else:
        raise ValueError('fname must end with .tif, .asc, or .png')

    url = f'{WMESQUE_ENDPOINT}{dataset}/?bbox={extent}&cellsize={cellsize}&format={fmt}'

    if resample is not None:
        url += f'&resample={resample}'

    try:
        output = _legacy_urlopen(url, timeout=60)
        with open(fname, 'wb') as fp:
            fp.write(output.read())
    except (HTTPError, URLError, socket.timeout, OSError, ValueError) as e:
        raise RuntimeError(f"Error retrieving: {url}") from e

    return 1


def _b64url_to_bytes(s: str) -> bytes:
    """Decode URL-safe base64 that may be missing padding."""

    pad = '=' * ((4 - len(s) % 4) % 4)
    return base64.urlsafe_b64decode(s + pad)


class _InvalidResponse(RuntimeError):
    """Retryable network artifact failure, distinct from local filesystem errors."""


def resolve_endpoints(explicit: str | None = None) -> list[str]:
    raw = os.environ.get("WMESQUE_ENDPOINTS", "").strip()
    values = [explicit] if explicit is not None else (json.loads(raw) if raw else [WMESQUE2_ENDPOINT])
    if not isinstance(values, list) or not values:
        raise ValueError("WMESQUE_ENDPOINTS must be a nonempty JSON array")
    result = []
    for value in values:
        if not isinstance(value, str):
            raise ValueError("WMesque endpoints must be HTTP(S) URLs")
        parsed = urlsplit(value)
        if (parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username
                or parsed.password or parsed.query or parsed.fragment or any(c.isspace() for c in value)):
            raise ValueError("WMesque endpoint must be an HTTP(S) URL without credentials, query, or fragment")
        parsed.port  # Validate malformed ports before performing IO.
        endpoint = value.rstrip("/")
        if endpoint not in result:
            result.append(endpoint)
    return result


def _validate_raster(path: Path) -> None:
    from osgeo import gdal
    try:
        ds = gdal.OpenEx(str(path), gdal.OF_RASTER, allowed_drivers=[{".tif": "GTiff", ".asc": "AAIGrid", ".png": "PNG"}[path.suffix.lower()]])
        if ds is None or ds.RasterCount < 1 or ds.RasterXSize < 1 or ds.RasterYSize < 1:
            raise _InvalidResponse("Response is not a readable raster")
        # Decode every row in bounded blocks, detecting truncated compressed tiles.
        for band_index in range(1, ds.RasterCount + 1):
            band = ds.GetRasterBand(band_index)
            for row in range(0, ds.RasterYSize, 128):
                if band.ReadRaster(0, row, ds.RasterXSize, min(128, ds.RasterYSize - row)) is None:
                    raise _InvalidResponse("Response raster pixels are unreadable")
    except RuntimeError as exc:
        raise _InvalidResponse("Response raster is invalid") from exc


def _publish_download(stage: Path, destination: Path, write_meta: bool) -> None:
    """Rollback on local publication failure; callers consume after return."""
    names = [destination.name + ".meta", destination.name] if write_meta else [destination.name]
    backups = stage / "backup"
    backups.mkdir()
    published = []
    complete = False
    try:
        for name in names:
            target = destination.parent / name
            if target.is_symlink() or (target.exists() and not target.is_file()):
                raise ValueError("WMesque output must be a regular file")
            existed = target.exists()
            if existed:
                shutil.copy2(target, backups / name)
                os.chmod(stage / name, target.stat().st_mode & 0o777)
            os.replace(stage / name, target)
            published.append((target, existed))
        complete = True
    finally:
        if not complete:
            for target, existed in reversed(published):
                if existed:
                    os.replace(backups / target.name, target)
                else:
                    target.unlink()


def wmesque_retrieve(
    dataset: str,
    extent: Sequence[float],
    fname: str,
    cellsize: float,
    resample: str | None = None,
    v: int = 2,
    write_meta: bool = True,
    wmesque_endpoint: str | None = None,
    extent_crs: str | None = None,
    expected_revision: str | None = None,
) -> int:
    """Retrieve from explicit/deployment/default endpoints, preserving output on failure."""
    if int(v) == 1:
        if extent_crs is not None or expected_revision is not None:
            raise ValueError("extent_crs and expected_revision are only supported by WMesque v2")
        return _wmesque1_retrieve(dataset, extent, fname, cellsize, resample)
    from wepppy.webservices.wmesque_catalog import dataset_id, revision_id
    dataset_id(dataset.strip("/"))
    if expected_revision is not None:
        revision_id(expected_revision)
    assert isfloat(cellsize)
    assert len(extent) == 4 and all(isfloat(value) for value in extent)
    formats = {".tif": "GTiff", ".asc": "AAIGrid", ".png": "PNG"}
    destination = Path(fname)
    if destination.suffix.lower() not in formats:
        raise ValueError("fname must end with .tif, .asc, or .png")
    endpoints = resolve_endpoints(wmesque_endpoint)
    bbox = ",".join(str(value) for value in extent)
    query = f"bbox={bbox}&cellsize={cellsize}&format={formats[destination.suffix.lower()]}"
    if extent_crs is not None:
        query += f"&bbox_crs={quote(extent_crs)}"
    if resample is not None:
        query += f"&resample={quote(resample)}"
    if expected_revision is not None:
        query += f"&expected_revision={expected_revision}"
    deadline = time.monotonic() + TIMEOUT
    attempts = []
    last_error = None
    for index, endpoint in enumerate(endpoints):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        attempt_deadline = time.monotonic() + remaining / (len(endpoints) - index)
        url = f"{endpoint}/retrieve/{quote(dataset.strip('/'), safe='/')}/?{query}"
        with tempfile.TemporaryDirectory(prefix=".wmesque-", dir=destination.parent) as temporary:
            stage = Path(temporary)
            output = stage / destination.name
            try:
                with urlopen(url, timeout=max(0.001, attempt_deadline - time.monotonic())) as response:
                    metadata = {}
                    header = response.headers.get("WMesque-Meta")
                    if header:
                        try:
                            metadata = json.loads(_b64url_to_bytes(header).decode("utf-8"))
                            if not isinstance(metadata, dict):
                                raise _InvalidResponse("Invalid response metadata")
                        except (binascii.Error, UnicodeError, ValueError) as exc:
                            raise _InvalidResponse("Invalid response metadata") from exc
                    source = metadata.get("wmesque", {})
                    if not isinstance(source, dict):
                        raise _InvalidResponse("Invalid source metadata")
                    if expected_revision is not None and source.get("revision") != expected_revision:
                        raise _InvalidResponse("Expected revision not supplied by endpoint")
                    size = 0
                    with output.open("wb") as stream:
                        while True:
                            allowance = attempt_deadline - time.monotonic()
                            if allowance <= 0:
                                raise socket.timeout("WMesque attempt deadline exceeded")
                            # urllib's socket timeout alone is an idle timeout. Refresh it
                            # per read to bound a slow response by the attempt deadline.
                            sock = getattr(getattr(getattr(response, "fp", None), "raw", None), "_sock", None)
                            if sock is not None:
                                sock.settimeout(allowance)
                            block = response.read1(1024 * 1024)
                            if not block:
                                break
                            size += len(block)
                            stream.write(block)
                    length = response.headers.get("Content-Length")
                    if length is not None and (not length.isdigit() or size != int(length)):
                        raise _InvalidResponse("Incomplete response body")
                _validate_raster(output)
                metadata["wmesque_retrieve"] = {"url": url, "wmesque_endpoint": endpoint,
                    "bbox_crs": extent_crs, "expected_revision": expected_revision, "attempts": attempts + [{"endpoint": endpoint, "status": "success"}]}
                if write_meta:
                    (stage / (destination.name + ".meta")).write_text(json.dumps(metadata, indent=2))
            except HTTPError as exc:
                if exc.code not in {404, 409, 429, 500, 502, 503, 504}:
                    raise RuntimeError(f"HTTPError {exc.code} retrieving WMesque dataset {dataset}") from exc
                last_error = exc
                attempts.append({"endpoint": endpoint, "status": f"HTTP {exc.code}"})
            except (URLError, socket.timeout, IncompleteRead, RemoteDisconnected, ConnectionError, _InvalidResponse) as exc:
                last_error = exc
                attempts.append({"endpoint": endpoint, "status": type(exc).__name__})
            else:
                _publish_download(stage, destination, write_meta)
                return 1
        logging.getLogger(__name__).warning("WMesque attempt failed: %s", attempts[-1])
    raise RuntimeError(f"WMesque retrieval failed for {dataset}; attempts={attempts}") from last_error
