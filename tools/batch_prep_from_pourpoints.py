#!/usr/bin/env python3
"""
Delineate named watersheds from pourpoints using an existing WEPPcloud WBT workspace.

Given a CSV or JSON file of (name, lon, lat) pourpoints and a WBT working directory
that already contains flow direction (flovec.tif) and stream (netful.tif) rasters,
this tool:

1. Snaps each pourpoint to the nearest stream cell via WBT find_outlet
2. Deduplicates pourpoints that snap to the same cell
3. Runs WBT watershed to delineate drainage basins
4. Polygonizes and dissolves into a single-feature-per-watershed GeoJSON
5. Writes watersheds.WGS.geojson suitable for the WEPPcloud batch runner

Usage:
    python -m tools.batch_prep_from_pourpoints \\
        --wbt-wd /path/to/run/dem/wbt \\
        --pourpoints pourpoints.csv \\
        --output-dir /path/to/output

    # CSV format: name,lon,lat
    # JSON format: [{"name": "Leech", "lon": -123.71, "lat": 48.49}, ...]

    # Or pipe pourpoints inline:
    python -m tools.batch_prep_from_pourpoints \\
        --wbt-wd /path/to/run/dem/wbt \\
        --pourpoint "Leech,-123.714,48.494" \\
        --pourpoint "Deception,-123.715,48.517" \\
        --output-dir /path/to/output
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import sys
from dataclasses import dataclass, field
from io import StringIO
from os.path import exists as _exists, join as _join
from typing import Dict, List, Optional, Tuple

import numpy as np
import rasterio
from pyproj import Transformer
from rasterio.features import shapes
from shapely.geometry import mapping, shape
from shapely.ops import unary_union

from whitebox_tools import WhiteboxTools


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class Pourpoint:
    name: str
    lon: float
    lat: float


@dataclass
class SnappedPourpoint:
    name: str
    lon: float
    lat: float
    row: int
    col: int
    utm_coords: Tuple[float, float]
    outlet_geojson: str
    properties: Dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Pourpoint loading
# ---------------------------------------------------------------------------

def load_pourpoints_csv(path: str) -> List[Pourpoint]:
    """Load pourpoints from a CSV with columns: name, lon, lat."""
    points = []
    with open(path, newline='') as f:
        reader = csv.DictReader(f)
        # Normalize header names
        if reader.fieldnames is None:
            raise ValueError(f"CSV file {path} has no header row")
        header_map = {h.strip().lower(): h for h in reader.fieldnames}

        for row in reader:
            name = row.get(header_map.get('name', ''), '').strip()
            lon = float(row.get(header_map.get('lon', header_map.get('longitude', '')), 0))
            lat = float(row.get(header_map.get('lat', header_map.get('latitude', '')), 0))
            if name:
                points.append(Pourpoint(name, lon, lat))
    return points


def load_pourpoints_json(path: str) -> List[Pourpoint]:
    """Load pourpoints from a JSON array of {name, lon, lat} objects."""
    with open(path) as f:
        data = json.load(f)

    if isinstance(data, dict):
        data = data.get('pourpoints', data.get('features', []))

    points = []
    for item in data:
        if 'properties' in item:
            # GeoJSON Feature
            props = item['properties']
            coords = item.get('geometry', {}).get('coordinates', [0, 0])
            name = props.get('name', props.get('Name', ''))
            points.append(Pourpoint(name, coords[0], coords[1]))
        else:
            name = item.get('name', item.get('Name', ''))
            lon = float(item.get('lon', item.get('longitude', item.get('lng', 0))))
            lat = float(item.get('lat', item.get('latitude', 0)))
            points.append(Pourpoint(name, lon, lat))
    return points


def parse_pourpoint_string(s: str) -> Pourpoint:
    """Parse 'name,lon,lat' from a --pourpoint argument."""
    parts = s.strip().split(',')
    if len(parts) != 3:
        raise ValueError(f"Expected 'name,lon,lat' but got: {s!r}")
    return Pourpoint(parts[0].strip(), float(parts[1]), float(parts[2]))


def load_pourpoints(args) -> List[Pourpoint]:
    """Load pourpoints from CLI arguments."""
    points = []

    if args.pourpoints:
        path = args.pourpoints
        if path.endswith('.json') or path.endswith('.geojson'):
            points.extend(load_pourpoints_json(path))
        else:
            points.extend(load_pourpoints_csv(path))

    if args.pourpoint:
        for s in args.pourpoint:
            points.append(parse_pourpoint_string(s))

    if not points:
        raise ValueError("No pourpoints provided. Use --pourpoints <file> or --pourpoint 'name,lon,lat'")

    return points


# ---------------------------------------------------------------------------
# WBT operations
# ---------------------------------------------------------------------------

class WatershedDelineator:
    """Delineate watersheds from pourpoints using an existing WBT workspace."""

    def __init__(
        self,
        wbt_wd: str,
        output_dir: str,
        flovec: str = 'flovec.tif',
        streams: str = 'netful.tif',
        verbose: bool = False,
    ):
        self.wbt_wd = os.path.abspath(wbt_wd)
        self.output_dir = os.path.abspath(output_dir)
        os.makedirs(self.output_dir, exist_ok=True)

        self.flovec_path = _join(self.wbt_wd, flovec)
        self.streams_path = _join(self.wbt_wd, streams)

        if not _exists(self.flovec_path):
            raise FileNotFoundError(f"Flow direction raster not found: {self.flovec_path}")
        if not _exists(self.streams_path):
            raise FileNotFoundError(f"Streams raster not found: {self.streams_path}")

        # Open the flow direction raster for coordinate transforms
        self._ds = rasterio.open(self.flovec_path)
        self._to_projected = Transformer.from_crs('EPSG:4326', self._ds.crs, always_xy=True)
        self._to_wgs = Transformer.from_crs(self._ds.crs, 'EPSG:4326', always_xy=True)

        self.wbt = WhiteboxTools()
        self.wbt.set_whitebox_dir(self._find_wbt_bin_dir())
        self.wbt.set_working_dir(self.output_dir)
        self.wbt.set_verbose_mode(verbose)

    @staticmethod
    def _find_wbt_bin_dir() -> str:
        """Locate the WhiteboxTools binary directory."""
        candidates = [
            os.environ.get('WBT_BIN_DIR', ''),
            '/workdir/weppcloud-wbt/target/release',
            os.path.expanduser('~/weppcloud-wbt/target/release'),
        ]
        for path in candidates:
            if path and _exists(_join(path, 'whitebox_tools')):
                return path
        raise FileNotFoundError(
            "Cannot find whitebox_tools binary. Set WBT_BIN_DIR environment variable "
            "or ensure /workdir/weppcloud-wbt/target/release/whitebox_tools exists."
        )

    def lonlat_to_rowcol(self, lon: float, lat: float) -> Tuple[int, int]:
        """Convert WGS84 lon/lat to raster row/col."""
        x, y = self._to_projected.transform(lon, lat)
        return self._ds.index(x, y)

    def is_in_bounds(self, lon: float, lat: float) -> bool:
        """Check if a lon/lat point falls within the DEM bounds."""
        x, y = self._to_projected.transform(lon, lat)
        row, col = self._ds.index(x, y)
        return 0 <= row < self._ds.height and 0 <= col < self._ds.width

    # ------------------------------------------------------------------
    # Step 1: Snap pourpoints
    # ------------------------------------------------------------------

    def snap_pourpoints(self, pourpoints: List[Pourpoint]) -> List[SnappedPourpoint]:
        """Snap each pourpoint to the nearest stream cell using find_outlet."""
        snapped = []

        for pp in pourpoints:
            if not self.is_in_bounds(pp.lon, pp.lat):
                print(f'  SKIP {pp.name}: ({pp.lon}, {pp.lat}) is outside DEM bounds')
                continue

            row, col = self.lonlat_to_rowcol(pp.lon, pp.lat)
            outlet_path = _join(self.output_dir, f'outlet_{pp.name}.geojson')
            print(f'  {pp.name} ({pp.lon:.6f}, {pp.lat:.6f}) -> row={row}, col={col}', end=' ', flush=True)

            ret = self.wbt.find_outlet(
                d8_pntr=self.flovec_path,
                streams=self.streams_path,
                output=outlet_path,
                requested_outlet_row_col=(row, col),
            )

            if ret != 0 or not _exists(outlet_path):
                print(f'FAILED (return code {ret})')
                continue

            with open(outlet_path) as f:
                gj = json.load(f)

            feat = gj['features'][0]
            coords = feat['geometry']['coordinates']
            props = feat['properties']
            steps = props.get('steps_from_start', '?')
            print(f'-> snapped ({coords[0]:.1f}, {coords[1]:.1f}) steps={steps}')

            snapped.append(SnappedPourpoint(
                name=pp.name,
                lon=pp.lon,
                lat=pp.lat,
                row=row,
                col=col,
                utm_coords=tuple(coords),
                outlet_geojson=outlet_path,
                properties=props,
            ))

        return snapped

    # ------------------------------------------------------------------
    # Step 2: Deduplicate
    # ------------------------------------------------------------------

    @staticmethod
    def deduplicate(snapped: List[SnappedPourpoint]) -> List[SnappedPourpoint]:
        """Remove pourpoints that snapped to the same cell, keeping the first."""
        seen = {}
        unique = []
        dropped = []
        for sp in snapped:
            key = sp.utm_coords
            if key in seen:
                dropped.append((sp.name, seen[key]))
                continue
            seen[key] = sp.name
            unique.append(sp)

        for name, kept in dropped:
            print(f'  DEDUP: dropped {name} (same cell as {kept})')

        return unique

    # ------------------------------------------------------------------
    # Step 3: Build combined pourpoints GeoJSON
    # ------------------------------------------------------------------

    def build_combined_pourpoints(self, snapped: List[SnappedPourpoint]) -> str:
        """Write a combined pourpoints GeoJSON for the watershed tool."""
        # Read CRS from first outlet
        with open(snapped[0].outlet_geojson) as f:
            first_gj = json.load(f)

        features = []
        for i, sp in enumerate(snapped):
            features.append({
                'type': 'Feature',
                'geometry': {'type': 'Point', 'coordinates': list(sp.utm_coords)},
                'properties': {'Id': i + 1, 'name': sp.name},
            })

        combined = {
            'type': 'FeatureCollection',
            'crs': first_gj.get('crs', {}),
            'features': features,
        }

        path = _join(self.output_dir, 'pourpoints_snapped.geojson')
        with open(path, 'w') as f:
            json.dump(combined, f, indent=2)

        print(f'\n  Wrote {len(features)} pourpoints to {path}')
        return path

    # ------------------------------------------------------------------
    # Step 4: Watershed delineation
    # ------------------------------------------------------------------

    def delineate(self, pourpoints_path: str) -> str:
        """Run WBT watershed delineation."""
        watershed_path = _join(self.output_dir, 'watersheds.tif')
        self.wbt.set_verbose_mode(False)

        ret = self.wbt.watershed(
            d8_pntr=self.flovec_path,
            pour_pts=pourpoints_path,
            output=watershed_path,
        )

        if ret != 0:
            raise RuntimeError(f'Watershed delineation failed (return code {ret})')

        print(f'  Watershed raster: {watershed_path}')
        return watershed_path

    # ------------------------------------------------------------------
    # Step 5: Polygonize and dissolve
    # ------------------------------------------------------------------

    def polygonize(self, watershed_path: str, snapped: List[SnappedPourpoint]) -> str:
        """Polygonize the watershed raster into dissolved, named WGS84 GeoJSON."""
        id_to_name = {i + 1: sp.name for i, sp in enumerate(snapped)}

        with rasterio.open(watershed_path) as ds:
            data = ds.read(1)
            transform = ds.transform
            crs = ds.crs
            nodata = ds.nodata

        mask = data != nodata if nodata is not None else np.ones_like(data, dtype=bool)

        # Collect and dissolve geometries per watershed ID
        geoms_by_id: Dict[int, list] = {}
        for geom, value in shapes(data.astype('int32'), mask=mask, transform=transform):
            value = int(value)
            if value == 0:
                continue
            geoms_by_id.setdefault(value, []).append(shape(geom))

        features_utm = []
        for wid in sorted(geoms_by_id.keys()):
            dissolved = unary_union(geoms_by_id[wid])
            name = id_to_name.get(wid, f'Unknown_{wid}')
            area_km2 = dissolved.area / 1e6
            features_utm.append({
                'type': 'Feature',
                'geometry': mapping(dissolved),
                'properties': {
                    'id': wid,
                    'name': name,
                    'area_km2': round(area_km2, 2),
                },
            })

        # Transform to WGS84
        def _transform_coords(coords):
            if isinstance(coords[0], (list, tuple)):
                return [_transform_coords(c) for c in coords]
            x, y = self._to_wgs.transform(coords[0], coords[1])
            return [x, y]

        features_wgs = []
        for feat in features_utm:
            geom = feat['geometry']
            features_wgs.append({
                'type': 'Feature',
                'geometry': {
                    'type': geom['type'],
                    'coordinates': _transform_coords(geom['coordinates']),
                },
                'properties': feat['properties'],
            })

        wgs_geojson = {
            'type': 'FeatureCollection',
            'features': features_wgs,
        }
        wgs_path = _join(self.output_dir, 'watersheds.WGS.geojson')
        with open(wgs_path, 'w') as f:
            json.dump(wgs_geojson, f)

        # Also write UTM version
        utm_geojson = {
            'type': 'FeatureCollection',
            'crs': {
                'type': 'name',
                'properties': {'name': f'urn:ogc:def:crs:EPSG::{crs.to_epsg()}'},
            },
            'features': features_utm,
        }
        utm_path = _join(self.output_dir, 'watersheds.geojson')
        with open(utm_path, 'w') as f:
            json.dump(utm_geojson, f)

        return wgs_path

    # ------------------------------------------------------------------
    # Full pipeline
    # ------------------------------------------------------------------

    def run(self, pourpoints: List[Pourpoint]) -> str:
        """Run the full delineation pipeline. Returns path to watersheds.WGS.geojson."""
        print(f'WBT workspace: {self.wbt_wd}')
        print(f'Output dir:    {self.output_dir}')
        print(f'DEM CRS:       {self._ds.crs}')
        print(f'DEM size:      {self._ds.width} x {self._ds.height} ({self._ds.res[0]}m)')
        print(f'Pourpoints:    {len(pourpoints)}')

        print(f'\nStep 1: Snapping pourpoints to stream cells...')
        snapped = self.snap_pourpoints(pourpoints)
        if not snapped:
            raise RuntimeError('No pourpoints were successfully snapped.')

        print(f'\nStep 2: Deduplicating...')
        snapped = self.deduplicate(snapped)
        print(f'  {len(snapped)} unique pourpoints')

        print(f'\nStep 3: Building combined pourpoints GeoJSON...')
        pourpoints_path = self.build_combined_pourpoints(snapped)

        print(f'\nStep 4: Running watershed delineation...')
        watershed_path = self.delineate(pourpoints_path)

        print(f'\nStep 5: Polygonizing and dissolving...')
        wgs_path = self.polygonize(watershed_path, snapped)

        # Summary
        with open(wgs_path) as f:
            result = json.load(f)

        print(f'\n{"="*60}')
        print(f'Output: {wgs_path}')
        print(f'Watersheds: {len(result["features"])}')
        print(f'{"="*60}')
        print(f'{"ID":>4}  {"Name":<20}  {"Area (km2)":>10}')
        print(f'{"-"*4}  {"-"*20}  {"-"*10}')
        for feat in result['features']:
            p = feat['properties']
            print(f'{p["id"]:4d}  {p["name"]:<20}  {p["area_km2"]:10.2f}')

        return wgs_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='Delineate named watersheds from pourpoints using a WBT workspace.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # From a CSV file
  python -m tools.batch_prep_from_pourpoints \\
      --wbt-wd /wc1/runs/my-run/dem/wbt \\
      --pourpoints pourpoints.csv \\
      --output-dir ./batch_watersheds

  # From inline arguments
  python -m tools.batch_prep_from_pourpoints \\
      --wbt-wd /wc1/runs/my-run/dem/wbt \\
      --pourpoint "Leech,-123.714644,48.494946" \\
      --pourpoint "Deception,-123.715526,48.517161" \\
      --output-dir ./batch_watersheds

  # From a JSON file
  python -m tools.batch_prep_from_pourpoints \\
      --wbt-wd /wc1/runs/my-run/dem/wbt \\
      --pourpoints pourpoints.json \\
      --output-dir ./batch_watersheds

CSV format (header required):
  name,lon,lat
  Leech,-123.714644,48.494946
  Deception,-123.715526,48.517161

JSON format:
  [{"name": "Leech", "lon": -123.714644, "lat": 48.494946}, ...]
""",
    )
    parser.add_argument(
        '--wbt-wd', required=True,
        help='Path to WBT working directory containing flovec.tif and netful.tif',
    )
    parser.add_argument(
        '--pourpoints',
        help='Path to CSV or JSON file with pourpoints (name, lon, lat)',
    )
    parser.add_argument(
        '--pourpoint', action='append', default=[],
        help='Inline pourpoint as "name,lon,lat" (repeatable)',
    )
    parser.add_argument(
        '--output-dir', default=None,
        help='Output directory (default: <wbt-wd>/batch_watersheds)',
    )
    parser.add_argument(
        '--flovec', default='flovec.tif',
        help='Flow direction raster filename (default: flovec.tif)',
    )
    parser.add_argument(
        '--streams', default='netful.tif',
        help='Streams raster filename (default: netful.tif)',
    )
    parser.add_argument(
        '--verbose', action='store_true',
        help='Enable verbose WBT output',
    )
    return parser


def main(argv: Optional[List[str]] = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    output_dir = args.output_dir or _join(args.wbt_wd, 'batch_watersheds')

    pourpoints = load_pourpoints(args)

    delineator = WatershedDelineator(
        wbt_wd=args.wbt_wd,
        output_dir=output_dir,
        flovec=args.flovec,
        streams=args.streams,
        verbose=args.verbose,
    )

    delineator.run(pourpoints)


if __name__ == '__main__':
    main()
