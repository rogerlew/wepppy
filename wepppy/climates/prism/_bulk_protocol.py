"""Native-cell and wire contracts for the PRISM 800 m bulk service."""
from dataclasses import dataclass
from datetime import date
from functools import lru_cache
import hashlib
import io
import json
import math
from numbers import Integral

import numpy as np
import pandas as pd
from pyproj import Transformer

VARIABLES = ('ppt', 'tmin', 'tmax', 'tdmean', 'soltotal')
UNITS = ('mm', 'degrees C', 'degrees C', 'degrees C', 'MJ/m^2/day')
COLUMNS = [f'{name} ({unit})' for name, unit in zip(VARIABLES, UNITS)]
GEOMETRY = dict(crs='EPSG:4269', width=7025, height=3105,
                x0=-125.02083333333351, y0=49.9374999999995,
                dx=0.008333333333, dy=-0.008333333333)
GRID_ID = 'us-800m-' + hashlib.sha256(json.dumps(GEOMETRY, sort_keys=True).encode()).hexdigest()[:16]
SCHEMA = 1
RPC_URL = 'https://prism.oregonstate.edu/explorer/dataexplorer/rpc.php'
DOWNLOAD_ROOT = 'https://prism.oregonstate.edu/explorer/tmp/'
RELEASE_ROOT = 'https://services.nacse.org/prism/data/get/releaseDate/us/800m'


class PrismError(RuntimeError):
    """Base for explicit acquisition, coverage, freshness and cache failures."""


class PrismProtocolError(PrismError):
    pass


class PrismCoverageError(PrismError):
    pass


class PrismFreshnessError(PrismError):
    pass


class PrismCacheError(PrismError):
    pass


@lru_cache(maxsize=1)
def _native_transformer():
    return Transformer.from_crs('EPSG:4326', GEOMETRY['crs'], always_xy=True, allow_ballpark=False)


@dataclass(frozen=True)
class PrismCell:
    row: int
    col: int

    def __post_init__(self):
        if (any(isinstance(v, bool) or not isinstance(v, Integral) for v in (self.row, self.col))
                or not 0 <= self.row < GEOMETRY['height'] or not 0 <= self.col < GEOMETRY['width']):
            raise ValueError('PRISM cell row/column is outside the native grid')

    @property
    def id(self):
        return f'r{self.row}c{self.col}'

    @property
    def center(self):
        return (GEOMETRY['x0'] + (self.col + .5) * GEOMETRY['dx'],
                GEOMETRY['y0'] + (self.row + .5) * GEOMETRY['dy'])


def snap(lon, lat, *, source_crs='EPSG:4326'):
    """Map a geographic point to its native cell; internal ties go east/south."""
    lon, lat = float(lon), float(lat)
    if not math.isfinite(lon) or not math.isfinite(lat) or not -180 <= lon <= 180 or not -90 <= lat <= 90:
        raise ValueError('Expected finite geographic longitude/latitude')
    if source_crs not in ('EPSG:4326', 'EPSG:4269'):
        raise ValueError('source_crs must be EPSG:4326 or EPSG:4269')
    if source_crs != GEOMETRY['crs']:
        lon, lat = _native_transformer().transform(lon, lat, errcheck=True)
    indices = [(lon - GEOMETRY['x0']) / GEOMETRY['dx'], (lat - GEOMETRY['y0']) / GEOMETRY['dy']]
    # Remove sub-micrometer arithmetic noise at exact affine boundaries.
    col, row = [math.floor(round(v) if abs(v-round(v)) < 1e-9 else v) for v in indices]
    try:
        return PrismCell(row, col)
    except ValueError as exc:
        raise PrismCoverageError('Point is outside the PRISM CONUS grid extent') from exc


def dates_between(start, end):
    return pd.date_range(start, end, name='date')


def parse_release(body, variable, start, end):
    """Normalize a complete variable/day manifest; version inequality invalidates."""
    try:
        rows = json.loads(body)
        if not isinstance(rows, list):
            raise ValueError('Expected array')
        result = {}
        for row in rows:
            if not isinstance(row, list) or len(row) != 5:
                raise ValueError('Expected five manifest fields')
            day, release, name, count, url = row
            if name != variable or not isinstance(day, str) or day in result:
                raise ValueError('Duplicate date or wrong variable')
            if date.fromisoformat(day).isoformat() != day or date.fromisoformat(release).isoformat() != release:
                raise ValueError('Noncanonical date')
            if isinstance(count, bool) or str(int(count)) != str(count) or int(count) < 0:
                raise ValueError('Invalid update count')
            expected_url = f'https://services.nacse.org/prism/data/get/us/800m/{variable}/{day.replace("-", "")}'
            if url != expected_url:
                raise ValueError('Unexpected grid URL')
            result[day] = [release, int(count), url]
        expected = [d.date().isoformat() for d in dates_between(start, end)]
        if set(result) != set(expected):
            raise ValueError('Incomplete release manifest')
        return {day: result[day] for day in expected}
    except (ValueError, TypeError, OverflowError) as exc:
        raise PrismFreshnessError(f'Invalid {variable} release manifest: {exc}') from exc


def validate_frame(frame, start, end):
    if list(frame.columns) != list(VARIABLES) or not frame.index.equals(dates_between(start, end)):
        raise PrismProtocolError('Climate columns/calendar differ from request')
    values = frame.to_numpy(dtype=float)
    if not np.isfinite(values).all() or (values == -9999).any():
        raise PrismProtocolError('Missing or nonfinite PRISM values')
    if (frame.ppt < 0).any() or (frame.soltotal < 0).any() or (frame.tmin > frame.tmax).any():
        raise PrismProtocolError('Negative precipitation/radiation or reversed temperatures')
    # Daily mean dewpoint below Tmin is preserved, never silently repaired here.


def parse_bulk(raw, cells, start, end):
    try:
        lines = raw.decode('utf-8-sig').splitlines()
        index = next(i for i, line in enumerate(lines) if line.startswith('Name,Longitude,Latitude,'))
        header = lines[:index]
        if 'Spatial resolution: 800m' not in header or 'Grid Cell Interpolation: Off' not in header:
            raise ValueError('Unexpected resolution/interpolation')
        if f'Period: {start.isoformat()} - {end.isoformat()}' not in header:
            raise ValueError('Unexpected period')
        df = pd.read_csv(io.StringIO('\n'.join(lines[index:])), dtype={'Name': str})
        if list(df.columns) != ['Name', 'Longitude', 'Latitude', 'Elevation (m)', 'Date', *COLUMNS]:
            raise ValueError('Unexpected columns/units')
        expected = {c.id for c in cells}
        if set(df.Name) != expected:
            raise PrismCoverageError(f'PRISM cell inventory mismatch; missing={sorted(expected-set(df.Name))}, unexpected={sorted(set(df.Name)-expected)}')
        result = {}
        groups = df.groupby('Name', sort=False)
        for cell in cells:
            sub = groups.get_group(cell.id)
            lon, lat = cell.center
            if not np.isfinite(sub[['Longitude', 'Latitude', 'Elevation (m)']].to_numpy(dtype=float)).all():
                raise ValueError('Invalid coordinate/elevation metadata')
            if (abs(sub.Longitude-lon) > .000051).any() or (abs(sub.Latitude-lat) > .000051).any():
                raise ValueError('Returned cell center differs from request')
            frame = sub[COLUMNS].copy()
            frame.columns = list(VARIABLES)
            frame.index = pd.DatetimeIndex(pd.to_datetime(sub.Date, format='%Y-%m-%d', errors='raise'), name='date')
            validate_frame(frame, start, end)
            result[cell.id] = frame
        return result
    except (ValueError, TypeError, UnicodeError, StopIteration, pd.errors.ParserError) as exc:
        raise PrismProtocolError(f'Invalid bulk CSV: {exc}') from exc
