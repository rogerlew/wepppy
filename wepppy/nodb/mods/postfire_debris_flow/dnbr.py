"""Local dNBR normalization; no uploads, network acquisition or NoDb mutation.

Scientific and file contracts: docs/dnbr_upload.md and ADR-0054.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import date
import hashlib
import json
import math
from pathlib import Path
import tempfile
from xml.etree import ElementTree as ET

import numpy as np
import rasterio
from rasterio.enums import ColorInterp, Resampling
from rasterio.io import MemoryFile
from rasterio.warp import reproject

__all__ = ["DnbrError", "normalize_dnbr", "summarize_dnbr"]
MAX_BYTES = 100 * 1024 * 1024
MAX_CELLS = 25_000_000
MAX_VRT_BYTES = 64 * 1024
DRIVERS = {".tif": "GTiff", ".tiff": "GTiff", ".img": "HFA"}


class DnbrError(ValueError):
    """An expected input failure with a stable machine-readable code."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _fail(code, message):
    raise DnbrError(code, message)


def _file(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        _fail("invalid_input", f"Expected a regular nonsymlink file: {path}")
    if path.stat().st_size > MAX_BYTES:
        _fail("resource_limit", "Raster file exceeds 100 MiB")
    return path.resolve()


def _hash(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _identity_vrt(path, refs):
    if path.stat().st_size > MAX_VRT_BYTES:
        _fail("resource_limit", "Identity VRT exceeds 64 KiB")
    raw = path.read_bytes()
    if b"<!" in raw or b"\x00" in raw:
        _fail("unsafe_reference", "VRT declarations/entities are not supported")
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise DnbrError("unsupported_vrt", "Invalid VRT XML") from exc
    allowed = {"VRTDataset": {"rasterXSize", "rasterYSize"},
               "SRS": {"dataAxisToSRSAxisMapping"}, "GeoTransform": set(),
               "VRTRasterBand": {"dataType", "band"}, "SimpleSource": set(),
               "SourceFilename": {"relativeToVRT"}, "SourceBand": set(),
               "SrcRect": {"xOff", "yOff", "xSize", "ySize"},
               "DstRect": {"xOff", "yOff", "xSize", "ySize"}}
    for node in root.iter():
        if node.tag not in allowed or set(node.attrib) - allowed[node.tag]:
            _fail("unsupported_vrt", "Only a simple identity VRT is supported")
    if root.tag != "VRTDataset" or sorted(c.tag for c in root) != ["GeoTransform", "SRS", "VRTRasterBand"]:
        _fail("unsupported_vrt", "VRT needs one band, SRS and GeoTransform")
    band = root.find("VRTRasterBand")
    if band.get("band") != "1" or [c.tag for c in band] != ["SimpleSource"]:
        _fail("unsupported_vrt", "VRT must contain only band 1 SimpleSource")
    source = band.find("SimpleSource")
    tags = [c.tag for c in source]
    if set(tags) - {"SourceFilename", "SourceBand", "SrcRect", "DstRect"} or len(tags) != len(set(tags)):
        _fail("unsupported_vrt", "Invalid VRT source elements")
    filename = source.find("SourceFilename")
    if filename is None or filename.get("relativeToVRT") != "1" or source.findtext("SourceBand") != "1":
        _fail("unsupported_vrt", "VRT requires a relative band-1 source")
    name = filename.text or ""
    relative = Path(name)
    if not name or relative.is_absolute() or ".." in relative.parts or ":" in name or "\\" in name:
        _fail("unsafe_reference", "VRT source must be an allowed local relative file")
    leaf = _file(path.parent / relative)
    if leaf not in {_file(p) for p in refs} or leaf.suffix.lower() not in DRIVERS:
        _fail("unsafe_reference", "VRT source was not explicitly allowlisted")
    try:
        width, height = int(root.get("rasterXSize")), int(root.get("rasterYSize"))
        transform = rasterio.Affine.from_gdal(*map(float, root.findtext("GeoTransform").split(",")))
        crs = rasterio.crs.CRS.from_user_input(root.findtext("SRS"))
        for tag in ("SrcRect", "DstRect"):
            rect = source.find(tag)
            if rect is not None and {k: float(v) for k, v in rect.attrib.items()} != {
                "xOff": 0, "yOff": 0, "xSize": width, "ySize": height
            }:
                _fail("unsupported_vrt", "VRT rectangles must be full-size identity mappings")
    except (TypeError, ValueError, rasterio.errors.CRSError) as exc:
        raise DnbrError("unsupported_vrt", "Invalid VRT grid metadata") from exc
    return leaf, (width, height, transform, crs, band.get("dataType"))


@contextmanager
def _raster(path):
    """Decode only self-contained allowed drivers, detached from source folders."""
    driver = DRIVERS.get(path.suffix.lower())
    if driver is None:
        _fail("invalid_raster", "Expected GeoTIFF or self-contained IMG")
    # Detaching bytes must not silently discard support/encoding metadata.
    sidecars = {path.name.lower() + suffix for suffix in (".msk", ".aux.xml", ".ovr")}
    sidecars.update(path.stem.lower() + suffix for suffix in (".ige", ".rrd", ".aux", ".aux.xml"))
    if any(p.name.lower() in sidecars for p in path.parent.iterdir()):
        _fail("invalid_raster", "Materialize raster sidecars into a self-contained file first")
    try:
        with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", GDAL_VRT_ENABLE_PYTHON="NO"):
            with MemoryFile(path.read_bytes(), ext=path.suffix) as memory:
                with memory.open(driver=driver) as raster:
                    if raster.driver != driver or raster.count != 1:
                        _fail("invalid_raster", "Expected one numeric raster band and matching driver")
                    if raster.width * raster.height > MAX_CELLS:
                        _fail("resource_limit", "Raster exceeds 25 million cells")
                    for rows, cols in raster.block_shapes:
                        if rows * cols > MAX_CELLS or rows * cols * np.dtype(raster.dtypes[0]).itemsize > MAX_BYTES:
                            _fail("resource_limit", "Decoded raster block exceeds resource limits")
                    if np.dtype(raster.dtypes[0]).kind not in "iuf":
                        _fail("invalid_raster", "Complex or nonnumeric rasters are unsupported")
                    if any(c in raster.colorinterp for c in (ColorInterp.palette, ColorInterp.red,
                                                             ColorInterp.green, ColorInterp.blue, ColorInterp.alpha)):
                        _fail("invalid_raster", "Color-rendered rasters are not continuous dNBR")
                    a = raster.transform
                    if (raster.crs is None or not all(math.isfinite(v) for v in a[:6])
                            or a.determinant == 0 or a == rasterio.Affine.identity()):
                        _fail("invalid_grid", "Raster requires CRS and finite georeferencing")
                    yield raster
    except rasterio.errors.RasterioError as exc:
        raise DnbrError("invalid_raster", "Unable to decode self-contained raster") from exc


def _grid(raster):
    a = raster.transform
    if (not raster.crs.is_projected or raster.crs.linear_units != "metre"
            or a.b != 0 or a.d != 0 or a.a <= 0 or a.e != -a.a):
        _fail("invalid_grid", "Reference grid must be north-up square projected meters")
    return (raster.height, raster.width), a, raster.crs


def _read(raster):
    a = raster.read(1, masked=True).astype(np.float64)
    return a.filled(np.nan), ~np.ma.getmaskarray(a) & np.isfinite(a.data)


def _mask(raster, grid):
    if _grid(raster) != grid:
        _fail("invalid_grid", "Mask must match reference grid exactly")
    values, valid = _read(raster)
    if np.any(valid & ~np.isin(values, [0, 1])):
        _fail("invalid_mask", "Mask values must be 0 or 1")
    inside = valid & (values == 1)
    if not np.any(inside):
        _fail("invalid_mask", "Catchment mask is empty")
    return inside


def _summary(values, inside):
    valid = inside & np.isfinite(values)
    total, observed = int(inside.sum()), int(valid.sum())
    mean = float(np.mean(values[valid], dtype=np.float64)) if observed else None
    return {"status": "unavailable" if not observed else "complete" if observed == total else "partial",
            "total_cells": total, "valid_cells": observed, "coverage_fraction": observed / total,
            "mean_dnbr": mean, "m1_f": mean,
            "warning": "partial_dnbr_coverage" if 0 < observed < total else None}


def summarize_dnbr(dnbr, catchment_mask) -> dict:
    """Summarize normalized dNBR over observed equal-area target cells."""
    with _raster(_file(dnbr)) as raster, _raster(_file(catchment_mask)) as mask:
        grid = _grid(raster)
        values, valid = _read(raster)
        values[~valid] = np.nan
        return _summary(values, _mask(mask, grid))


def _encoding(scale_factor, add_offset):
    try:
        scale, offset = float(scale_factor), float(add_offset)
    except (TypeError, ValueError, OverflowError) as exc:
        raise DnbrError("invalid_encoding", "Encoding must be finite numeric values") from exc
    if isinstance(scale_factor, bool) or isinstance(add_offset, bool) or not math.isfinite(scale) or scale <= 0 or not math.isfinite(offset):
        _fail("invalid_encoding", "Scale must be finite positive and offset finite")
    return scale, offset


def _dates(prefire, postfire, assessment):
    try:
        for value in (prefire, postfire):
            if value is not None and (not isinstance(value, str) or date.fromisoformat(value).isoformat() != value):
                raise ValueError("Expected ISO date")
        if prefire is not None and postfire is not None and prefire >= postfire:
            raise ValueError("Prefire must precede postfire")
        if assessment not in (None, "initial", "extended"):
            raise ValueError("Expected initial or extended assessment")
    except (TypeError, ValueError) as exc:
        raise DnbrError("invalid_dates", str(exc)) from exc


def normalize_dnbr(source, dem, watershed_mask, output_dir, *, scale_factor,
                   add_offset=0, source_refs=(), prefire_date=None, postfire_date=None,
                   assessment_type=None) -> dict:
    """Create a new completed normalized artifact directory; never replace one."""
    scale, offset = _encoding(scale_factor, add_offset)
    _dates(prefire_date, postfire_date, assessment_type)
    source, dem, watershed_mask = map(_file, (source, dem, watershed_mask))
    output = Path(output_dir)
    if output.exists() or output.is_symlink():
        _fail("output_exists", "Output directory already exists")
    leaf, identity = _identity_vrt(source, source_refs) if source.suffix.lower() == ".vrt" else (source, None)
    inputs = {str(p): _hash(p) for p in (source, leaf, dem, watershed_mask)}
    with _raster(dem) as reference, _raster(watershed_mask) as mask, _raster(leaf) as src:
        grid = _grid(reference)
        inside = _mask(mask, grid)
        _, dem_valid = _read(reference)
        if np.any(inside & ~dem_valid):
            _fail("invalid_mask", "Watershed includes invalid DEM cells")
        if identity:
            dtype = rasterio.dtypes._gdal_typename(src.dtypes[0])
            if identity != (src.width, src.height, src.transform, src.crs, dtype):
                _fail("unsupported_vrt", "VRT must match its physical source grid and dtype")
        metadata_encoding = (src.scales[0], src.offsets[0])
        if metadata_encoding != (1.0, 0.0) and metadata_encoding != (scale, offset):
            _fail("encoding_conflict", "Explicit encoding conflicts with nondefault raster metadata")
        values, valid = _read(src)
        with np.errstate(over="ignore", invalid="ignore"):
            values = values * scale + offset
        if np.any(valid & (~np.isfinite(values) | (np.abs(values) > np.finfo(np.float32).max))):
            _fail("invalid_encoding", "Normalized values cannot be represented as Float32")
        values[~valid] = np.nan
        target = np.full(grid[0], np.nan, dtype=np.float32)
        reproject(values, target, src_transform=src.transform, src_crs=src.crs,
                  src_nodata=np.nan, dst_transform=grid[1], dst_crs=grid[2],
                  dst_nodata=np.nan, resampling=Resampling.nearest)
        target[~dem_valid] = np.nan
        summary = _summary(target, inside)
        if not summary["valid_cells"]:
            _fail("no_valid_target_overlap", "No valid dNBR samples overlap the watershed at project resolution")
        finite = target[np.isfinite(target)]
        manifest = {"schema_version": 1, "source": str(source), "physical_source": str(leaf),
                    "input_sha256": inputs, "source_dtype": src.dtypes[0],
                    "source_driver": src.driver, "source_band": 1,
                    "source_valid_cells": int(valid.sum()),
                    "source_grid": {"shape": list(src.shape), "crs": str(src.crs), "transform": list(src.transform)[:6]},
                    "source_nodata": str(src.nodata), "metadata_encoding": list(metadata_encoding),
                    "scale_factor": scale, "add_offset": offset, "resampling": "nearest",
                    "target_grid": {"shape": list(grid[0]), "crs": str(grid[2]), "transform": list(grid[1])[:6]},
                    "normalized_range": [float(finite.min()), float(finite.max())],
                    "outside_ideal_range_cells": int(np.count_nonzero(np.abs(finite) > 2)),
                    "prefire_date": prefire_date, "postfire_date": postfire_date,
                    "assessment_type": assessment_type, "watershed": summary}
    # Reserve a previously absent destination so concurrent calls cannot replace it.
    try:
        output.mkdir()
    except FileExistsError as exc:
        raise DnbrError("output_exists", "Output directory already exists") from exc
    completed = False
    try:
        with tempfile.TemporaryDirectory(prefix=".dnbr-", dir=output.parent) as temporary:
            stage = Path(temporary) / "complete"
            stage.mkdir()
            with rasterio.open(stage / "dnbr.tif", "w", driver="GTiff", height=grid[0][0],
                               width=grid[0][1], count=1, dtype="float32", nodata=np.nan,
                               crs=grid[2], transform=grid[1], compress="deflate") as dst:
                dst.write(target, 1)
            for path, digest in inputs.items():
                if _hash(Path(path)) != digest:
                    _fail("source_changed", "Input changed during normalization")
            manifest["dnbr_sha256"] = _hash(stage / "dnbr.tif")
            (stage / "manifest.json").write_text(json.dumps(manifest, indent=2, allow_nan=False) + "\n")
            stage.replace(output)
            completed = True
    finally:
        if not completed:
            output.rmdir()
    return manifest
