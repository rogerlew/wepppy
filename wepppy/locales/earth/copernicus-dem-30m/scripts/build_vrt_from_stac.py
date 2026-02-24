#!/usr/bin/env python3
"""Build a GDAL VRT for Copernicus DEM GLO-30 tiles listed in the public STAC bucket.

This script discovers tile item JSON files from:
  https://copernicus-dem-30m-stac.s3.amazonaws.com

Then it writes a source list of `/vsicurl/https://...tif` DEM URLs and builds
the VRT with `gdalbuildvrt`.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
import re
from typing import Iterable, Iterator, Optional, Tuple

S3_XML_NS = "{http://s3.amazonaws.com/doc/2006-03-01/}"
STAC_BASE_URL = "https://copernicus-dem-30m-stac.s3.amazonaws.com"
DATA_BASE_URL = "https://copernicus-dem-30m.s3.eu-central-1.amazonaws.com"
ITEM_PREFIX = "items/"
ITEM_SUFFIX = ".json"
TILE_ID_RE = re.compile(
    r"^(Copernicus_DSM_COG_10_"
    r"(?P<lat_hem>[NS])(?P<lat>\d{2})_00_"
    r"(?P<lon_hem>[EW])(?P<lon>\d{3})_00)$"
)


BBox = Tuple[float, float, float, float]


def _s3_tag(name: str) -> str:
    return f"{S3_XML_NS}{name}"


def _iter_stac_item_keys(stac_base_url: str) -> Iterator[str]:
    continuation_token: Optional[str] = None
    while True:
        params = {
            "list-type": "2",
            "max-keys": "1000",
            "prefix": ITEM_PREFIX,
        }
        if continuation_token:
            params["continuation-token"] = continuation_token

        url = f"{stac_base_url}/?{urllib.parse.urlencode(params)}"
        with urllib.request.urlopen(url, timeout=60) as response:
            payload = response.read()

        root = ET.fromstring(payload)
        for content in root.findall(_s3_tag("Contents")):
            key = content.findtext(_s3_tag("Key"))
            if not key:
                continue
            if key.startswith(ITEM_PREFIX) and key.endswith(ITEM_SUFFIX):
                yield key

        is_truncated = root.findtext(_s3_tag("IsTruncated"), default="false").lower() == "true"
        if not is_truncated:
            break

        continuation_token = root.findtext(_s3_tag("NextContinuationToken"))
        if not continuation_token:
            raise RuntimeError("S3 listing is truncated but NextContinuationToken is missing.")


def _tile_id_from_item_key(item_key: str) -> Optional[str]:
    tile_id = Path(item_key).stem
    if TILE_ID_RE.match(tile_id) is None:
        return None
    return tile_id


def _tile_bbox(tile_id: str) -> BBox:
    match = TILE_ID_RE.match(tile_id)
    if match is None:
        raise ValueError(f"Unexpected tile id format: {tile_id}")

    lat_val = float(match.group("lat"))
    lon_val = float(match.group("lon"))
    lat_sign = 1.0 if match.group("lat_hem") == "N" else -1.0
    lon_sign = 1.0 if match.group("lon_hem") == "E" else -1.0

    south = lat_sign * lat_val
    west = lon_sign * lon_val
    north = south + 1.0
    east = west + 1.0
    return (west, south, east, north)


def _intersects(a: BBox, b: BBox) -> bool:
    aw, as_, ae, an = a
    bw, bs, be, bn = b
    return not (ae <= bw or aw >= be or an <= bs or as_ >= bn)


def _build_dem_href(tile_id: str, data_base_url: str) -> str:
    return f"{data_base_url}/{tile_id}_DEM/{tile_id}_DEM.tif"


def _iter_source_urls(
    *,
    stac_base_url: str,
    data_base_url: str,
    bbox: Optional[BBox],
    limit: Optional[int],
) -> Iterator[str]:
    emitted = 0
    for item_key in _iter_stac_item_keys(stac_base_url):
        tile_id = _tile_id_from_item_key(item_key)
        if tile_id is None:
            continue

        if bbox is not None and not _intersects(_tile_bbox(tile_id), bbox):
            continue

        href = _build_dem_href(tile_id, data_base_url)
        yield f"/vsicurl/{href}"
        emitted += 1
        if limit is not None and emitted >= limit:
            return


def _parse_bbox(values: Optional[Iterable[float]]) -> Optional[BBox]:
    if values is None:
        return None

    bbox_values = tuple(float(v) for v in values)
    if len(bbox_values) != 4:
        raise ValueError("bbox must have 4 values: west south east north")
    west, south, east, north = bbox_values
    if west >= east:
        raise ValueError("bbox west must be less than east")
    if south >= north:
        raise ValueError("bbox south must be less than north")
    return (west, south, east, north)


def _run_gdalbuildvrt(output_vrt: Path, source_list_path: Path) -> None:
    cmd = [
        "gdalbuildvrt",
        "-overwrite",
        "-input_file_list",
        str(source_list_path),
        str(output_vrt),
    ]
    subprocess.run(cmd, check=True)


def _run_gdalinfo(path: Path) -> None:
    cmd = ["gdalinfo", str(path)]
    subprocess.run(cmd, check=True)


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-vrt",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "data/copernicus-dem-30m.vrt",
        help="Output VRT path.",
    )
    parser.add_argument(
        "--source-list",
        type=Path,
        default=None,
        help="Optional output source list path. Defaults to <output-vrt>.sources.txt",
    )
    parser.add_argument(
        "--bbox",
        nargs=4,
        type=float,
        metavar=("WEST", "SOUTH", "EAST", "NORTH"),
        help="Optional bounding box to reduce sources.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional max number of source tiles (useful for quick smoke tests).",
    )
    parser.add_argument(
        "--stac-base-url",
        default=STAC_BASE_URL,
        help="Base URL for the public Copernicus DEM STAC bucket.",
    )
    parser.add_argument(
        "--data-base-url",
        default=DATA_BASE_URL,
        help="Base URL for the public Copernicus DEM COG bucket.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Write the source list but skip gdalbuildvrt.",
    )
    parser.add_argument(
        "--verify-gdalinfo",
        action="store_true",
        help="Run gdalinfo on the output VRT after building it.",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.limit is not None and args.limit <= 0:
        raise ValueError("--limit must be positive when provided.")

    bbox = _parse_bbox(args.bbox)
    output_vrt = args.output_vrt.resolve()
    source_list = args.source_list.resolve() if args.source_list else output_vrt.with_suffix(".sources.txt")

    output_vrt.parent.mkdir(parents=True, exist_ok=True)
    source_list.parent.mkdir(parents=True, exist_ok=True)

    source_urls = list(
        _iter_source_urls(
            stac_base_url=args.stac_base_url.rstrip("/"),
            data_base_url=args.data_base_url.rstrip("/"),
            bbox=bbox,
            limit=args.limit,
        )
    )
    if not source_urls:
        raise RuntimeError("No matching DEM source URLs were discovered.")

    source_list.write_text("\n".join(source_urls) + "\n", encoding="utf-8")

    print(f"Discovered {len(source_urls)} source URLs.")
    print(f"Wrote source list: {source_list}")

    if args.dry_run:
        return 0

    _run_gdalbuildvrt(output_vrt=output_vrt, source_list_path=source_list)
    print(f"Built VRT: {output_vrt}")

    if args.verify_gdalinfo:
        _run_gdalinfo(output_vrt)

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # deliberate CLI boundary
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
