#!/usr/bin/env python3
"""Audit and optionally correct NED1 VRT placement against source tiles.

Compares each VRT ComplexSource/SimpleSource placement to the source tile
geotransform via GDAL vsicurl, reports offsets, and can emit a corrected VRT.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import statistics
import sys
from dataclasses import dataclass
from typing import Iterable, Iterator, Optional

from osgeo import gdal
import xml.etree.ElementTree as ET


@dataclass
class SourceEntry:
    index: int
    source_path: str
    x_off: float
    y_off: float
    x_size: float
    y_size: float


@dataclass
class AuditResult:
    entry: SourceEntry
    vrt_ul_x: float
    vrt_ul_y: float
    tile_ul_x: Optional[float]
    tile_ul_y: Optional[float]
    dx_deg: Optional[float]
    dy_deg: Optional[float]
    dx_arcsec: Optional[float]
    dy_arcsec: Optional[float]
    dx_px: Optional[float]
    dy_px: Optional[float]
    error: Optional[str] = None


def _parse_geotransform(text: str) -> tuple[float, float, float, float, float, float]:
    parts = [p.strip() for p in text.replace("\n", " ").split(",")]
    if len(parts) != 6:
        raise ValueError(f"GeoTransform must have 6 values, got {len(parts)}")
    return tuple(float(p) for p in parts)  # type: ignore[return-value]


def _format_geotransform(gt: Iterable[float]) -> str:
    return ",  ".join(f"{v:.16e}" for v in gt)


def _resolve_source_path(vrt_path: str, source: str, relative_to_vrt: Optional[str]) -> str:
    if relative_to_vrt and relative_to_vrt != "0":
        return os.path.abspath(os.path.join(os.path.dirname(vrt_path), source))
    return source


def _iter_sources(vrt_path: str) -> Iterator[SourceEntry]:
    tree = ET.parse(vrt_path)
    root = tree.getroot()

    band_idx = 0
    entry_idx = 0
    for band in root.findall(".//VRTRasterBand"):
        band_idx += 1
        for tag in ("ComplexSource", "SimpleSource"):
            for src in band.findall(tag):
                source_filename = src.find("SourceFilename")
                dst_rect = src.find("DstRect")
                if source_filename is None or dst_rect is None:
                    continue

                source_path = source_filename.text or ""
                rel = source_filename.attrib.get("relativeToVRT")
                source_path = _resolve_source_path(vrt_path, source_path, rel)

                x_off = float(dst_rect.attrib.get("xOff", "0"))
                y_off = float(dst_rect.attrib.get("yOff", "0"))
                x_size = float(dst_rect.attrib.get("xSize", "0"))
                y_size = float(dst_rect.attrib.get("ySize", "0"))

                entry_idx += 1
                yield SourceEntry(
                    index=entry_idx,
                    source_path=source_path,
                    x_off=x_off,
                    y_off=y_off,
                    x_size=x_size,
                    y_size=y_size,
                )


def _get_vrt_geotransform(vrt_path: str) -> tuple[float, float, float, float, float, float]:
    tree = ET.parse(vrt_path)
    root = tree.getroot()
    node = root.find("GeoTransform")
    if node is None or not node.text:
        raise ValueError("VRT is missing GeoTransform")
    return _parse_geotransform(node.text)


def _compute_vrt_ul(gt: tuple[float, float, float, float, float, float], x_off: float, y_off: float) -> tuple[float, float]:
    origin_x, px_w, rot1, origin_y, rot2, px_h = gt
    x = origin_x + x_off * px_w + y_off * rot1
    y = origin_y + x_off * rot2 + y_off * px_h
    return x, y


def _open_dataset(path: str) -> gdal.Dataset:
    ds = gdal.Open(path)
    if ds is None:
        raise RuntimeError(f"GDAL could not open {path}")
    return ds


def audit_vrt(
    vrt_path: str,
    limit: Optional[int] = None,
    stride: int = 1,
) -> tuple[list[AuditResult], tuple[float, float, float, float, float, float]]:
    gdal.UseExceptions()
    gdal.SetConfigOption("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")
    gdal.SetConfigOption("CPL_VSIL_CURL_ALLOWED_EXTENSIONS", ".tif,.tiff")

    gt = _get_vrt_geotransform(vrt_path)
    results: list[AuditResult] = []

    processed = 0
    for idx, entry in enumerate(_iter_sources(vrt_path), start=1):
        if stride > 1 and (idx - 1) % stride != 0:
            continue
        if limit is not None and processed >= limit:
            break

        processed += 1
        vrt_ul_x, vrt_ul_y = _compute_vrt_ul(gt, entry.x_off, entry.y_off)

        try:
            ds = _open_dataset(entry.source_path)
            tile_gt = ds.GetGeoTransform()
            ds = None
            tile_ul_x = float(tile_gt[0])
            tile_ul_y = float(tile_gt[3])
            dx_deg = vrt_ul_x - tile_ul_x
            dy_deg = vrt_ul_y - tile_ul_y
            dx_arcsec = dx_deg * 3600.0
            dy_arcsec = dy_deg * 3600.0
            dx_px = dx_deg / float(tile_gt[1]) if tile_gt[1] else None
            dy_px = dy_deg / float(tile_gt[5]) if tile_gt[5] else None

            result = AuditResult(
                entry=entry,
                vrt_ul_x=vrt_ul_x,
                vrt_ul_y=vrt_ul_y,
                tile_ul_x=tile_ul_x,
                tile_ul_y=tile_ul_y,
                dx_deg=dx_deg,
                dy_deg=dy_deg,
                dx_arcsec=dx_arcsec,
                dy_arcsec=dy_arcsec,
                dx_px=dx_px,
                dy_px=dy_px,
            )
        except Exception as exc:
            result = AuditResult(
                entry=entry,
                vrt_ul_x=vrt_ul_x,
                vrt_ul_y=vrt_ul_y,
                tile_ul_x=None,
                tile_ul_y=None,
                dx_deg=None,
                dy_deg=None,
                dx_arcsec=None,
                dy_arcsec=None,
                dx_px=None,
                dy_px=None,
                error=str(exc),
            )

        results.append(result)

    return results, gt


def _summarize(results: list[AuditResult]) -> dict:
    dx = [r.dx_deg for r in results if r.dx_deg is not None]
    dy = [r.dy_deg for r in results if r.dy_deg is not None]
    dx_arc = [r.dx_arcsec for r in results if r.dx_arcsec is not None]
    dy_arc = [r.dy_arcsec for r in results if r.dy_arcsec is not None]
    dx_px = [r.dx_px for r in results if r.dx_px is not None]
    dy_px = [r.dy_px for r in results if r.dy_px is not None]

    def _stats(values: list[float]) -> dict:
        if not values:
            return {}
        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "mean": statistics.fmean(values),
            "median": statistics.median(values),
            "stdev": statistics.pstdev(values),
        }

    errors = [r for r in results if r.error]
    return {
        "total": len(results),
        "ok": len(results) - len(errors),
        "errors": len(errors),
        "dx_deg": _stats(dx),
        "dy_deg": _stats(dy),
        "dx_arcsec": _stats(dx_arc),
        "dy_arcsec": _stats(dy_arc),
        "dx_px": _stats(dx_px),
        "dy_px": _stats(dy_px),
    }


def _write_csv(results: list[AuditResult], out_path: str) -> None:
    fieldnames = [
        "index",
        "source",
        "x_off",
        "y_off",
        "x_size",
        "y_size",
        "vrt_ul_x",
        "vrt_ul_y",
        "tile_ul_x",
        "tile_ul_y",
        "dx_deg",
        "dy_deg",
        "dx_arcsec",
        "dy_arcsec",
        "dx_px",
        "dy_px",
        "error",
    ]
    with open(out_path, "w", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            writer.writerow({
                "index": r.entry.index,
                "source": r.entry.source_path,
                "x_off": r.entry.x_off,
                "y_off": r.entry.y_off,
                "x_size": r.entry.x_size,
                "y_size": r.entry.y_size,
                "vrt_ul_x": r.vrt_ul_x,
                "vrt_ul_y": r.vrt_ul_y,
                "tile_ul_x": r.tile_ul_x,
                "tile_ul_y": r.tile_ul_y,
                "dx_deg": r.dx_deg,
                "dy_deg": r.dy_deg,
                "dx_arcsec": r.dx_arcsec,
                "dy_arcsec": r.dy_arcsec,
                "dx_px": r.dx_px,
                "dy_px": r.dy_px,
                "error": r.error,
            })


def _write_summary(summary: dict, out_path: str) -> None:
    with open(out_path, "w") as fp:
        json.dump(summary, fp, indent=2, sort_keys=True)


def _apply_geotransform_correction(
    vrt_path: str,
    out_path: str,
    dx_deg: float,
    dy_deg: float,
) -> None:
    tree = ET.parse(vrt_path)
    root = tree.getroot()
    node = root.find("GeoTransform")
    if node is None or not node.text:
        raise ValueError("VRT missing GeoTransform")
    gt = _parse_geotransform(node.text)
    corrected = (
        gt[0] - dx_deg,
        gt[1],
        gt[2],
        gt[3] - dy_deg,
        gt[4],
        gt[5],
    )
    node.text = _format_geotransform(corrected)
    tree.write(out_path)


def _apply_dstrect_correction(
    vrt_path: str,
    out_path: str,
    results: list[AuditResult],
) -> None:
    tree = ET.parse(vrt_path)
    root = tree.getroot()
    gt = _get_vrt_geotransform(vrt_path)

    result_lookup = {r.entry.index: r for r in results if r.dx_deg is not None}
    entry_idx = 0

    for band in root.findall(".//VRTRasterBand"):
        for tag in ("ComplexSource", "SimpleSource"):
            for src in band.findall(tag):
                dst_rect = src.find("DstRect")
                if dst_rect is None:
                    continue
                entry_idx += 1
                result = result_lookup.get(entry_idx)
                if result is None:
                    continue

                tile_ul_x = result.tile_ul_x
                tile_ul_y = result.tile_ul_y
                if tile_ul_x is None or tile_ul_y is None:
                    continue

                origin_x, px_w, rot1, origin_y, rot2, px_h = gt
                if rot1 != 0.0 or rot2 != 0.0:
                    raise ValueError("Rotation terms are non-zero; dstrect correction unsupported")

                x_off = (tile_ul_x - origin_x) / px_w
                y_off = (tile_ul_y - origin_y) / px_h

                dst_rect.attrib["xOff"] = f"{x_off:.6f}"
                dst_rect.attrib["yOff"] = f"{y_off:.6f}"

    tree.write(out_path)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit and correct NED1 VRT placement.")
    parser.add_argument("--vrt", required=True, help="Path to the VRT file.")
    parser.add_argument("--out-dir", required=True, help="Output directory for reports.")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of tiles processed.")
    parser.add_argument("--stride", type=int, default=1, help="Process every Nth tile.")
    parser.add_argument("--strict", action="store_true", help="Fail on any missing tiles.")
    parser.add_argument(
        "--write-corrected-vrt",
        default=None,
        help="Write corrected VRT to this path.",
    )
    parser.add_argument(
        "--correction-mode",
        choices=["geotransform", "dstrect"],
        default="geotransform",
        help="Correction strategy (default: geotransform).",
    )
    parser.add_argument(
        "--tolerance-arcsec",
        type=float,
        default=0.1,
        help="Warn if offsets deviate from median by more than this.",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = _parse_args(argv)
    os.makedirs(args.out_dir, exist_ok=True)

    results, gt = audit_vrt(args.vrt, limit=args.limit, stride=args.stride)
    summary = _summarize(results)

    csv_path = os.path.join(args.out_dir, "audit.csv")
    summary_path = os.path.join(args.out_dir, "summary.json")
    _write_csv(results, csv_path)
    _write_summary(summary, summary_path)

    errors = [r for r in results if r.error]
    if errors:
        print(f"Encountered {len(errors)} errors", file=sys.stderr)
        if args.strict:
            return 2

    if args.write_corrected_vrt:
        dx_arc = summary.get("dx_arcsec", {})
        dy_arc = summary.get("dy_arcsec", {})
        if not dx_arc or not dy_arc:
            raise RuntimeError("No valid offsets available for correction.")

        median_dx = summary["dx_deg"]["median"]
        median_dy = summary["dy_deg"]["median"]
        tol = args.tolerance_arcsec

        for axis, values, median in (
            ("dx_arcsec", summary["dx_arcsec"], summary["dx_arcsec"]["median"]),
            ("dy_arcsec", summary["dy_arcsec"], summary["dy_arcsec"]["median"]),
        ):
            if values:
                spread = max(abs(values["min"] - median), abs(values["max"] - median))
                if spread > tol:
                    print(
                        f"Warning: {axis} spread {spread:.4f} exceeds tolerance {tol:.4f}",
                        file=sys.stderr,
                    )

        if args.correction_mode == "geotransform":
            _apply_geotransform_correction(args.vrt, args.write_corrected_vrt, median_dx, median_dy)
        else:
            _apply_dstrect_correction(args.vrt, args.write_corrected_vrt, results)

    print(f"Wrote {csv_path}")
    print(f"Wrote {summary_path}")
    if args.write_corrected_vrt:
        print(f"Wrote {args.write_corrected_vrt}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
