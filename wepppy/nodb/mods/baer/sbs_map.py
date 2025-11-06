# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

"""Utility helpers for working with Soil Burn Severity (SBS) rasters."""

from __future__ import annotations

import os
from os.path import exists as _exists
from os.path import join as _join
from os.path import split as _split
from collections import Counter
from functools import lru_cache
from collections.abc import Mapping, Sequence
from typing import Literal, Optional, Tuple, TypeAlias

import numpy as np
from osgeo import gdal
from osgeo.gdalconst import GDT_Byte

from subprocess import Popen, PIPE, run

from numpy.typing import NDArray

from wepppy.all_your_base import isint
from wepppy.all_your_base.geo import read_raster, validate_srs

from wepppy.landcover import LandcoverMap

SeverityClass: TypeAlias = Literal["unburned", "low", "mod", "high"]
RGBColor: TypeAlias = Tuple[int, int, int]
ColorIndexMap: TypeAlias = dict[SeverityClass, list[int]]
ColorCounts: TypeAlias = list[tuple[int, int]]
ColorLookup: TypeAlias = dict[RGBColor, Optional[str]]
HashableBreaks: TypeAlias = tuple[int | float, ...]
HashableNoData: TypeAlias = Optional[tuple[int | float, ...]]

__all__ = [
    "classify",
    "ct_classify",
    "get_sbs_color_table",
    "sbs_map_sanity_check",
    "SoilBurnSeverityMap",
]

def get_sbs_color_table(
    fn: str,
    color_to_severity_map: Optional[Mapping[RGBColor, str]] = None,
) -> tuple[Optional[ColorIndexMap], ColorCounts, Optional[ColorLookup]]:
    """Read the SBS raster color table and map entries to severity classes.

    Args:
        fn: Path to the SBS raster on disk.
        color_to_severity_map: Optional mapping from RGB triplets to
            severity class strings to override the defaults.

    Returns:
        A tuple of ``(class_index_map, counts, color_map)`` where:

        * ``class_index_map`` maps severity classes to color-table indices
          (``None`` when the raster does not define a color table).
        * ``counts`` contains raster value frequencies derived from the band data.
        * ``color_map`` provides the reverse mapping of RGB colors to severity
          class names (or ``None`` when no table is present).
    """
    ds = gdal.Open(fn)
    band = ds.GetRasterBand(1)
    data = band.ReadAsArray(0, 0, ds.RasterXSize, ds.RasterYSize)
    counts: ColorCounts = Counter(list(data.flatten())).most_common()

    if color_to_severity_map is None:
        color_to_severity_map = {
            (0, 100, 0): "unburned",
            (0, 0, 0): "unburned",
            (0, 115, 74): "unburned",
            (0, 175, 166): "unburned",
            (102, 204, 204): "low",
            (102, 205, 205): "low",
            (115, 255, 223): "low",
            (127, 255, 212): "low",
            (0, 255, 255): "low",
            (102, 205, 205): "low",
            (77, 230, 0): "low",
            (255, 255, 0): "mod",
            (255, 232, 32): "mod",
            (255, 0, 0): "high",
        }

    ct = band.GetRasterColorTable()
    if ct is None:
        return None, counts, None

    color_map: ColorLookup = {}
    class_index_map: ColorIndexMap = {
        "unburned": [],
        "low": [],
        "mod": [],
        "high": [],
    }
    for i in range(ct.GetCount()):
        entry = tuple(int(v) for v in ct.GetColorEntry(i)[:3])

        severity = color_to_severity_map.get(entry)
        color_map[entry] = severity

        if severity:
            class_index_map[severity].append(i)

    ds = None

    return class_index_map, counts, color_map


def make_hashable(
    v: int | float,
    breaks: Sequence[int | float],
    nodata_vals: Optional[Sequence[int | float]],
    offset: int,
) -> tuple[int | float, HashableBreaks, HashableNoData, int]:
    """Convert classify arguments to an immutable tuple for caching.

    Args:
        v: Pixel value under evaluation.
        breaks: Sequence of severity breakpoints.
        nodata_vals: Optional pixel values representing NoData.
        offset: Classification offset applied during :func:`classify`.

    Returns:
        Hashable tuple suitable for use with :func:`functools.lru_cache`.
    """
    nodata_tuple: HashableNoData = tuple(nodata_vals) if nodata_vals is not None else None
    return v, tuple(breaks), nodata_tuple, offset

@lru_cache(maxsize=None)
def memoized_classify(
    args: tuple[int | float, HashableBreaks, HashableNoData, int],
) -> int:
    """Memoized wrapper for :func:`classify` to speed pixel iteration."""
    v, breaks, nodata_vals, offset = args
    return _classify(v, breaks, nodata_vals, offset)


def _classify(
    v: int | float,
    breaks: Sequence[int | float],
    nodata_vals: Optional[Sequence[int | float]],
    offset: int = 0,
) -> int:
    """Classify a single pixel value using numeric thresholds.

    Args:
        v: Raster pixel value to evaluate.
        breaks: Ordered breakpoints that separate severity classes.
        nodata_vals: Optional pixel values representing NoData cells.
        offset: Optional offset applied to the resulting class code.

    Returns:
        Integer class code adjusted by ``offset``.
    """
    idx = 0

    if nodata_vals is not None:
        for _no_data in nodata_vals:
            if int(v) == int(_no_data):
                return idx + offset

    for idx, brk in enumerate(breaks):
        if v <= brk:
            break
    return idx + offset


def classify(
    v: int | float,
    breaks: Sequence[int | float],
    nodata_vals: Optional[Sequence[int | float]] = None,
    offset: int = 0,
) -> int:
    """Classify a raster value using breakpoints plus memoization.

    Args:
        v: Raster value to classify.
        breaks: Ordered breakpoints that separate severity classes.
        nodata_vals: Optional pixel values representing NoData cells.
        offset: Optional offset applied to the resulting class code.

    Returns:
        Integer class code adjusted by ``offset``.
    """
    args = make_hashable(v, breaks, nodata_vals, offset)
    return memoized_classify(args)


def make_hashable_ct(
    v: int | float,
    ct: Mapping[SeverityClass, Sequence[int]],
    offset: int,
    nodata_vals: Optional[Sequence[int | float]],
) -> tuple[int | float, tuple[tuple[SeverityClass, tuple[int, ...]], ...], int, HashableNoData]:
    """Create a cache key for color-table-based classification.

    Args:
        v: Pixel value under evaluation.
        ct: Mapping of severity labels to color-table indices.
        offset: Classification offset applied during :func:`ct_classify`.
        nodata_vals: Optional list of NoData values to include in cache key.

    Returns:
        Immutable tuple describing the classification problem.
    """
    ct_tuple = tuple(
        (key, tuple(sorted(values)))
        for key, values in sorted(ct.items(), key=lambda item: item[0])
    )
    nodata_tuple: HashableNoData = tuple(nodata_vals) if nodata_vals is not None else None
    return v, ct_tuple, offset, nodata_tuple


@lru_cache(maxsize=None)
def _get_ct_classification_code(
    v: int | float,
    ct_tuple: tuple[tuple[SeverityClass, tuple[int, ...]], ...],
) -> Optional[int]:
    """Look up the SBS classification code for a value using a cached table.

    Args:
        v: Raster pixel value to map to a class code.
        ct_tuple: Immutable representation of the color table.

    Returns:
        Class code in the range ``0-3`` or ``None`` when the pixel is unknown.
    """
    ct = {k: set(int(x) for x in vs) for k, vs in ct_tuple}
    v = int(v)

    class_to_code = {"unburned": 0, "low": 1, "mod": 2, "high": 3}
    for cls, code in class_to_code.items():
        if v in ct.get(cls, set()):
            return code
    return None


def ct_classify(
    v: int | float,
    ct: Mapping[SeverityClass, Sequence[int]],
    offset: int = 0,
    nodata_vals: Optional[Sequence[int | float]] = None,
) -> int:
    """Classify a pixel using an SBS color table.

    Args:
        v: Raster pixel value to map to a class.
        ct: Mapping of severity classes to the pixel values associated with each.
        offset: Optional offset applied to the numeric class code. A value of 130
            retains the legacy raster band encodings used across the project.
        nodata_vals: Optional sequence of pixel values representing NoData cells.

    Returns:
        An integer class code in the range ``[offset, offset + 3]`` for recognized
        classes, ``offset`` for NoData, or ``255`` when the value is unknown.
    """
    if nodata_vals is not None:
        for _no_data in nodata_vals:
            if int(v) == int(_no_data):
                return offset

    cache_key = make_hashable_ct(v, ct, offset, nodata_vals)
    code = _get_ct_classification_code(v, cache_key[1])

    if code is None:
        return 255
    return code + offset
    
def sbs_map_sanity_check(fname: str) -> tuple[int, str]:
    """Validate raster suitability for Soil Burn Severity processing.

    Args:
        fname: Path to the candidate raster.

    Returns:
        A tuple ``(status_code, message)`` where ``0`` signals success and ``1``
        indicates a validation failure along with a human-readable explanation.
    """
    if not _exists(fname):
        return 1, "File does not exist"

    if not validate_srs(fname):
        return 1, "Map contains an invalid projection. Try reprojecting to UTM."

    ds = gdal.Open(fname)
    band = ds.GetRasterBand(1)
    data = band.ReadAsArray(0, 0, ds.RasterXSize, ds.RasterYSize)
    classes = np.unique(data)
    ds = None

    if len(classes) > 256:
        return 1, "Map has more than 256 classes"

    for v in classes:
        if not isint(v):
            return 1, "Map has non-integer classes"

    ct, _counts, color_map = get_sbs_color_table(fname, color_to_severity_map=None)
    if ct is not None and color_map is not None:
        for _, sev in color_map.items():
            if sev in ("low", "mod", "high"):
                return 0, "Map has valid color table"

        return 1, "Map has no valid color table"

    return 0, "Map has valid classes"

    
class SoilBurnSeverityMap(LandcoverMap):
    """Wraps an SBS raster with helpers for classification and export."""

    def __init__(
        self,
        fname: str,
        breaks: Optional[Sequence[int | float]] = None,
        nodata_vals: Optional[Sequence[int | float]] = None,
        color_map: Optional[Mapping[RGBColor, str]] = None,
        ignore_ct: bool = False,
    ) -> None:
        """Instantiate an SBS map wrapper.

        Args:
            fname: Path to the on-disk raster.
            breaks: Optional custom severity breakpoints.
            nodata_vals: Optional pixel values that should map to the NoData class.
            color_map: Optional mapping from RGB colors to severity labels; defaults
                to the canonical BAER palette.
            ignore_ct: When ``True`` forces the code path to treat the raster as
                lacking a color table, even if one exists.
        """
        if isinstance(nodata_vals, str):
            raise ValueError("nodata_vals should be a None or list, not a string")

        nodata_list: list[int | float]
        if nodata_vals is None:
            nodata_list = []

            ds = gdal.Open(fname)
            band = ds.GetRasterBand(1)
            _nodata = band.GetNoDataValue()
            ds = None

            if _nodata is not None:
                nodata_list.append(int(_nodata) if isint(_nodata) else float(_nodata))
        else:
            nodata_list = list(nodata_vals)

        assert _exists(fname)

        ct, counts, explicit_color_map = get_sbs_color_table(
            fname, color_to_severity_map=color_map
        )
        if ignore_ct:
            ct = None

        classes: set[int | float] = set()
        for value, _count in counts:
            if isint(value):
                if int(value) in nodata_list:
                    continue
                classes.add(int(value))
            else:
                if value in nodata_list:
                    continue
                classes.add(value)

        is256: Optional[bool] = None

        sorted_classes = sorted(classes)
        derived_breaks: Optional[list[int | float]] = list(breaks) if breaks else None
        if ct is None:
            if derived_breaks is None:
                # need to intuit breaks
                min_val = min(sorted_classes)
                max_val = max(sorted_classes)

                run = 1
                max_run_val = min_val
                while min_val + run in classes:
                    max_run_val = min_val + run
                    run += 1

                is256 = run > 5 or len(sorted_classes) > 7

                if is256:
                    derived_breaks = [0, 75, 109, 187]
                else:
                    derived_breaks = [max_run_val - i for i in range(3, -1, -1)]

                if max_val not in derived_breaks and not is256 and (max_val - 1) not in classes:
                    nodata_list.append(max_val)
                    sorted_classes.remove(max_val)

        else:
            derived_breaks = None

        self.ct: Optional[ColorIndexMap] = ct
        self.is256 = bool(is256)
        self.classes = sorted_classes
        self.counts: ColorCounts = counts
        self.color_map: Optional[ColorLookup] = explicit_color_map
        self.breaks: Optional[Sequence[int | float]] = derived_breaks
        self._data: Optional[NDArray[np.uint8]] = None
        self.fname = fname
        self.nodata_vals = nodata_list
        self._nodata_vals: Optional[list[int | float]] = None

    @property
    def transform(self) -> tuple[float, float, float, float, float, float]:
        """Return the GDAL geotransform for the SBS raster."""
        _data, transform, _proj = read_raster(self.fname, dtype=np.uint8)
        return transform

    @property
    def proj(self) -> str:
        """Return the projection WKT for the SBS raster."""
        _data, _transform, proj = read_raster(self.fname, dtype=np.uint8)
        return proj

    @property
    def burn_class_counts(self) -> dict[str, int]:
        """Aggregate class counts across severity categories."""
        counter: Counter[str] = Counter()
        for _, severity, count in self.class_map:
            counter[severity] += count
        return dict(counter)

    @property
    def data(self) -> NDArray[np.uint8]:
        """Return the SBS raster values reclassified into 4 severity buckets."""
        if self._data is not None:
            return self._data

        fname = self.fname
        ct = self.ct
        breaks = self.breaks
        nodata_vals = self.nodata_vals

        data, _transform, _proj = read_raster(fname, dtype=np.uint8)
        n, m = data.shape

        if ct is None:
            for brk in breaks:
                assert isint(brk), breaks

            assert breaks is not None, breaks
            for i in range(n):
                for j in range(m):
                    data[i, j] = classify(data[i, j], breaks, nodata_vals, offset=130)
        else:
            for i in range(n):
                for j in range(m):
                    data[i, j] = ct_classify(
                        data[i, j], ct, offset=130, nodata_vals=nodata_vals
                    )

        self._data = data
        return data

    def export_wgs_map(self, fn: str) -> list[list[float]]:
        """Reproject the SBS raster to WGS84 for web display.

        Args:
            fn: Destination GeoTIFF path.

        Returns:
            Bounding box coordinates formatted as ``[[sw_lat, sw_lon], [ne_lat, ne_lon]]``.
        """
        ds = gdal.Open(self.fname)
        assert ds is not None
        del ds

        # transform to WGS1984 to display on map
        if _exists(fn):
            os.remove(fn)

        cmd = [
            "gdalwarp",
            "-t_srs", "EPSG:4326",    # or "+proj=longlat +datum=WGS84 +no_defs +type=crs"
            "-r", "near",
            "-dstnodata", "255",
            "-of", "GTiff",
            "-co", "COMPRESS=LZW", "-co", "TILED=YES",
            self.fname, fn,
        ]

        res = run(cmd, stdout=PIPE, stderr=PIPE, text=True)
        if res.returncode != 0:
            raise RuntimeError(f"gdalwarp failed ({res.returncode}):\n{res.stderr}\ncmd: {' '.join(cmd)}")


        ds = gdal.Open(fn)
        assert ds is not None

        transform = ds.GetGeoTransform()
        band = ds.GetRasterBand(1)
        data = np.array(band.ReadAsArray(), dtype=np.int64)

        nodata = band.GetNoDataValue()
        if nodata is not None:
            self._nodata_vals = [np.int64(nodata)]

        del ds

        # need the bounds for Leaflet
        sw_x = transform[0]
        sw_y = transform[3] + transform[5] * data.shape[0]

        ne_x = transform[0] + transform[1] * data.shape[1]
        ne_y = transform[3]

        return [[sw_y, sw_x], [ne_y, ne_x]]

    @property
    def class_map(self) -> list[tuple[int, str, int]]:
        """List original raster values with their severity labels and counts."""
        ct = self.ct
        breaks = self.breaks
        nodata_vals = self.nodata_vals

        severity_lookup = {
            "255": "No Data",
            "130": "No Burn",
            "131": "Low Severity Burn",
            "132": "Moderate Severity Burn",
            "133": "High Severity Burn",
        }

        class_map = []
        for v, cnt in self.counts:
            if ct is None:
                assert breaks is not None
                k = classify(v, breaks, nodata_vals, offset=130)
            else:
                k = ct_classify(v, ct, offset=130, nodata_vals=nodata_vals)

            sev = severity_lookup[str(k)]
            class_map.append((int(v), sev, cnt))

        return sorted(class_map, key=lambda x: x[0])

    @property
    def class_pixel_map(self) -> dict[str, str]:
        """Map raw raster pixel values to their classified code strings."""
        ct = self.ct
        breaks = self.breaks
        nodata_vals = self.nodata_vals

        class_map = {}
        for v, cnt in self.counts:
            if ct is None:
                assert breaks is not None
                k = classify(v, breaks, nodata_vals, offset=130)
            else:
                k = ct_classify(v, ct, offset=130, nodata_vals=nodata_vals)

            _v = str(v)
            if _v.endswith('.0'):
                _v = _v[:-2]
            class_map[_v] = str(k)

        return class_map

    def _write_color_table(self, color_tbl_path: str) -> None:
        """Write out a GDAL color-relief table for export helpers.

        Args:
            color_tbl_path: Destination file for the color table.
        """
        ct = self.ct

        if ct is None:
            breaks = self.breaks
            nodata_vals = self.nodata_vals

            _map = {
                "255": "0 0 0 0",
                "130": "0 115 74 255",
                "131": "77 230 0 255",
                "132": "255 255 0 255",
                "133": "255 0 0 255",
            }

            with open(color_tbl_path, 'w') as fp:
                for v, cnt in self.counts:
                    k = classify(v, breaks, nodata_vals, offset=130)
                    fp.write('{} {}\n'.format(v, _map[str(k)]))
                fp.write("nv 0 0 0 0\n")
        else:
            _map = {
                "nv": "0 0 0 0",
                "unburned": "0 115 74 255",
                "low": "77 230 0 255",
                "mod": "255 255 0 255",
                "high": "255 0 0 255",
            }

            d = {}
            for burn_class in ct:
                color = _map[burn_class]
                for px in ct[burn_class]:
                    d[int(px)] = color

            with open(color_tbl_path, 'w') as fp:
                for v, color in sorted(d.items()):
                    fp.write(f'{v} {color}\n')
                fp.write("nv 0 0 0 0\n")


    def export_rgb_map(self, wgs_fn: str, fn: str, rgb_png: str) -> None:
        """Generate color-relief output (VRT + PNG) using the derived palette.

        Args:
            wgs_fn: Path to the WGS84 GeoTIFF produced by :meth:`export_wgs_map`.
            fn: Destination path for the VRT file.
            rgb_png: Destination path for the rendered PNG.
        """
        head, _ = _split(fn)

        color_tbl_path = _join(head, 'color_table.txt')
        self._write_color_table(color_tbl_path)

        disturbed_rgb = fn
        if _exists(disturbed_rgb):
            os.remove(disturbed_rgb)

        cmd = ['gdaldem', 'color-relief', '-of', 'VRT', '-alpha',
               wgs_fn, color_tbl_path, disturbed_rgb]
        p = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        p.wait()

        assert _exists(disturbed_rgb), ' '.join(cmd)

        disturbed_rgb_png = rgb_png
        if _exists(disturbed_rgb_png):
            os.remove(disturbed_rgb_png)

        cmd = ['gdal_translate', '-of', 'PNG', disturbed_rgb, disturbed_rgb_png]
        p = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        p.wait()

        assert _exists(disturbed_rgb_png), ' '.join(cmd)


    def export_4class_map(self, fn: str, cellsize: Optional[float] = None) -> None:
        """Export a 4-class GeoTIFF with palette encoding for GIS clients.

        Args:
            fn: Destination GeoTIFF path.
            cellsize: Optional output cell size, inferred from the source when
                omitted.
        """
        if cellsize is None:
            transform = self.transform
            assert round(transform[1], 1) == round(abs(transform[5]), 1)
            cellsize = transform[1]

        fname = self.fname
        assert _exists(fname)

        ct = self.ct

        _data, transform, proj = read_raster(fname, dtype=np.uint8)
        data = np.ones(_data.shape) * 255
        n, m = _data.shape

        if ct is None:
            for i in range(n):
                for j in range(m):
                    data[i, j] = classify(_data[i, j], self.breaks, self.nodata_vals)
        else:
            for i in range(n):
                for j in range(m):
                    data[i, j] = ct_classify(_data[i, j], ct, nodata_vals=self.nodata_vals)

        src_ds = gdal.Open(fname)
        wkt = src_ds.GetProjection()

        num_cols, num_rows = _data.shape
        driver = gdal.GetDriverByName("GTiff")
        dst = driver.Create(fn, num_cols, num_rows,
                            1, GDT_Byte,
                            ["COMPRESS=LZW", "PHOTOMETRIC=PALETTE"])

        dst.SetProjection(wkt)
        dst.SetGeoTransform(transform)
        band = dst.GetRasterBand(1)

        color_table = gdal.ColorTable()
        color_table.SetColorEntry(0, (0, 100, 0, 255))  # unburned
        color_table.SetColorEntry(1, (127, 255, 212, 255))  # low
        color_table.SetColorEntry(2, (255, 255, 0, 255))  # moderate
        color_table.SetColorEntry(3, (255, 0, 0, 255))  # high
        color_table.SetColorEntry(255, (255, 255, 255, 0))  # n/a
        band.SetColorTable(color_table)
        band.SetNoDataValue(255)

        band.WriteArray(data.T)

        del dst

        assert _exists(fn)


if __name__ == "__main__":
    import sys
    print(sys.argv)
    assert len(sys.argv) >= 3
    sbs_fn = sys.argv[-2]
    dst_fn = sys.argv[-1]

    sbs = SoilBurnSeverityMap(sbs_fn)
    sbs.export_4class_map(dst_fn)
