"""Bounded, anonymous EDDE v2 daily point extraction (experimental).

Source values are retained in their published units. This module does not perform
bias correction, interpolate between cells, or synthesize missing records.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import time
import xml.etree.ElementTree as ET

import netCDF4
import numpy as np
import pandas as pd
from pyproj import Transformer
import requests

ROOT = 'https://epa-edde-v2.s3.amazonaws.com/'
NS = {'s': 'http://s3.amazonaws.com/doc/2006-03-01/'}
TOKEN = re.compile(r'^[A-Za-z0-9_.-]+$')


class EligibilityError(ValueError):
    """Requested coordinate is outside the native land-cell domain."""


class AvailabilityError(ValueError):
    """Requested model, scenario, date, or variable is unavailable."""


class DataQualityError(ValueError):
    """Source metadata, grid, dates, or values violate the extraction contract."""


@dataclass(frozen=True)
class Point:
    name: str
    longitude: float
    latitude: float

    def __post_init__(self):
        if not TOKEN.fullmatch(self.name) or self.name in {'.', '..'}:
            raise ValueError('Point name must be a safe nonempty identifier')
        if not np.isfinite([self.longitude, self.latitude]).all():
            raise ValueError('Coordinates must be finite')
        if not (-180 <= self.longitude <= 180 and -90 <= self.latitude <= 90):
            raise ValueError('Coordinates must be WGS84 longitude/latitude')


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def _token(value: str) -> str:
    if not TOKEN.fullmatch(value) or value in {'.', '..'}:
        raise ValueError(f'Invalid archive identifier: {value!r}')
    return value


def locate(path: Path, points: list[Point]) -> list[dict]:
    """Select native cells only inside cell-face bounds; reject ocean cells."""
    with netCDF4.Dataset(path) as ds:
        x, y = np.asarray(ds['x'][:]), np.asarray(ds['y'][:])
        if len(x) < 2 or len(y) < 2:
            raise DataQualityError('Grid must have at least two cells per axis')
        dx, dy = np.diff(x), np.diff(y)
        if not (np.all(dx > 0) and np.all(dy > 0)
                and np.allclose(dx, dx[0]) and np.allclose(dy, dy[0])):
            raise DataQualityError('Expected regular increasing projected axes')
        transform = Transformer.from_crs('EPSG:4326', ds.CRS, always_xy=True)
        cells = []
        for point in points:
            px, py = transform.transform(point.longitude, point.latitude)
            if not (x[0] - dx[0]/2 <= px < x[-1] + dx[0]/2
                    and y[0] - dy[0]/2 <= py < y[-1] + dy[0]/2):
                raise EligibilityError(f'{point.name}: outside EDDE cell-face bounds')
            col, row = int(np.argmin(abs(x-px))), int(np.argmin(abs(y-py)))
            mask = ds['LANDMASK'][row, col]
            if np.ma.is_masked(mask) or float(mask) != 1:
                raise EligibilityError(f'{point.name}: selected cell is not valid land')
            cells.append(dict(**asdict(point), row=row, col=col,
                              cell_longitude=float(ds['lon'][row, col]),
                              cell_latitude=float(ds['lat'][row, col]),
                              projected_distance_m=float(np.hypot(px-x[col], py-y[row])),
                              edge_cells=min(row, col, len(y)-1-row, len(x)-1-col)))
        return cells


class EddeClient:
    """Use one instance/cache per process; no concurrent cache writers supported."""

    def __init__(self, cache: str | Path, *, max_download_bytes: int = 4_000_000_000,
                 timeout: float = 60):
        if max_download_bytes <= 0 or timeout <= 0:
            raise ValueError('Download budget and timeout must be positive')
        self.cache = Path(cache)
        self.cache.mkdir(parents=True, exist_ok=True)
        self.max_download_bytes = max_download_bytes
        self.timeout = timeout
        self.session = requests.Session()
        # This fixed public endpoint must not receive ambient netrc credentials.
        # Direct HTTPS uses requests' default CA bundle, without environment proxies.
        self.session.trust_env = False
        self.downloaded_bytes = 0

    def listing(self, prefix: str, *, delimiter: str | None = None) -> tuple[list[dict], list[str]]:
        if not prefix.startswith('EDDE_V2/') or '..' in prefix or '\\' in prefix:
            raise ValueError('Invalid EDDE prefix')
        params = {'list-type': '2', 'prefix': prefix}
        if delimiter:
            params['delimiter'] = delimiter
        objects: list[dict] = []
        prefixes: list[str] = []
        while True:
            response = self.session.get(ROOT, params=params, timeout=self.timeout, allow_redirects=False)
            response.raise_for_status()
            if response.status_code != 200:
                raise DataQualityError('Expected HTTP 200 for source listing')
            root = ET.fromstring(response.content)
            for obj in root.findall('s:Contents', NS):
                key = obj.findtext('s:Key', namespaces=NS)
                size = obj.findtext('s:Size', namespaces=NS)
                etag = obj.findtext('s:ETag', namespaces=NS)
                modified = obj.findtext('s:LastModified', namespaces=NS)
                if key is None or size is None or etag is None or modified is None:
                    raise DataQualityError('Incomplete S3 object metadata')
                objects.append(dict(key=key, size=int(size), etag=etag, modified=modified))
            for prefix_node in root.findall('s:CommonPrefixes/s:Prefix', NS):
                if prefix_node.text is None:
                    raise DataQualityError('Empty S3 prefix')
                prefixes.append(prefix_node.text)
            if root.findtext('s:IsTruncated', namespaces=NS) != 'true':
                break
            token = root.findtext('s:NextContinuationToken', namespaces=NS)
            if not token or token == params.get('continuation-token'):
                raise DataQualityError('Invalid S3 continuation token')
            params['continuation-token'] = token
        return objects, prefixes

    def inventory(self, model: str, scenario: str, year: int) -> list[dict]:
        prefix = f'EDDE_V2/daily/{_token(model)}/{_token(scenario)}/'
        _, periods = self.listing(prefix, delimiter='/')
        matches = []
        for period in periods:
            objects, _ = self.listing(f'{period}{int(year)}/')
            matches.extend(objects)
        if not matches:
            raise AvailabilityError(f'No daily records: {model}/{scenario}/{year}')
        return matches

    def fetch(self, obj: dict) -> tuple[Path, dict]:
        key = obj['key']
        if not key.startswith('EDDE_V2/') or any(
                not TOKEN.fullmatch(part) or part in {'.', '..'} for part in key.split('/')):
            raise ValueError('Unsafe source key')
        # Hash the complete key: cache paths cannot be chosen by the remote listing.
        ident = hashlib.sha256(key.encode()).hexdigest()
        path = self.cache / f'{ident}.nc'
        meta = self.cache / f'{ident}.json'
        if path.exists() and meta.exists():
            saved = json.loads(meta.read_text())
            if (saved['source'] == obj and path.stat().st_size == obj['size']
                    and sha256(path) == saved['sha256']):
                return path, dict(saved, cache_hit=True, transferred_bytes=0)
        if self.downloaded_bytes + obj['size'] > self.max_download_bytes:
            raise ValueError('Download byte budget exceeded; use a smaller query or explicit larger budget')
        partial = path.with_suffix('.partial')
        started = time.monotonic()
        attempt = path.with_suffix('.attempt.json')
        write_json(attempt, dict(status='incomplete', source=obj, partial=partial.name))
        with self.session.get(ROOT + key, headers={'If-Match': obj['etag']},
                              stream=True, timeout=self.timeout, allow_redirects=False) as response:
            response.raise_for_status()
            if response.status_code != 200:
                raise DataQualityError('Expected a complete HTTP 200 source response')
            if response.headers.get('ETag') != obj['etag']:
                raise DataQualityError(f'Object identity changed: {key}')
            count = 0
            with partial.open('wb') as stream:
                for block in response.iter_content(1024 * 1024):
                    count += len(block)
                    self.downloaded_bytes += len(block)
                    if count > obj['size'] or self.downloaded_bytes > self.max_download_bytes:
                        raise DataQualityError('Response exceeds listed size/download budget')
                    stream.write(block)
        if count != obj['size']:
            raise DataQualityError(f'Truncated object: {key}')
        saved = dict(source=obj, sha256=sha256(partial), downloaded_utc=datetime.now(timezone.utc).isoformat())
        partial.replace(path)
        write_json(meta, saved)
        write_json(attempt, dict(status='complete', source=obj, sha256=saved['sha256']))
        return path, dict(saved, cache_hit=False, transferred_bytes=count,
                          seconds=time.monotonic()-started)

    def grid(self, model: str) -> tuple[Path, dict]:
        objects, _ = self.listing(f'EDDE_V2/static/{_token(model)}/')
        masks = [o for o in objects if o['key'].split('/')[-1].startswith('lmask.')]
        if len(masks) != 1:
            raise AvailabilityError(f'Expected one static land mask for {model}')
        return self.fetch(masks[0])

    def query(self, points: list[Point], model: str, scenario: str, start: str, end: str,
              variables: list[str]) -> tuple[pd.DataFrame, dict]:
        """Read inclusive UTC model-calendar days; keep native values and metadata."""
        begin, finish = pd.Timestamp(start), pd.Timestamp(end)
        if (pd.isna(begin) or pd.isna(finish) or begin.tzinfo or finish.tzinfo
                or begin != begin.normalize() or finish != finish.normalize() or finish < begin):
            raise ValueError('Require ordered timezone-free calendar dates')
        if not points or len({p.name for p in points}) != len(points):
            raise ValueError('Require nonempty uniquely named points')
        if not variables or len(set(variables)) != len(variables):
            raise ValueError('Require unique variable identifiers')
        for variable in variables:
            _token(variable)
        selected = []
        for year in range(begin.year, finish.year+1):
            objects = self.inventory(model, scenario, year)
            for month in pd.period_range(max(begin, pd.Timestamp(year, 1, 1)),
                                         min(finish, pd.Timestamp(year, 12, 31)), freq='M'):
                for variable in variables:
                    found = [o for o in objects if o['key'].split('/')[-1].startswith(variable+'.')
                             and f'.{month}.raw.nc' in o['key']]
                    if len(found) != 1:
                        raise AvailabilityError(f'Expected one {variable} file for {model}/{scenario}/{month}')
                    selected.extend(found)
        # Conservative preflight includes cached objects. Raising this explicit
        # budget permits warm queries but never grants unbounded acquisition.
        if sum(o['size'] for o in selected) + 4_000_000 > self.max_download_bytes:
            raise ValueError('Query source footprint exceeds download budget')
        started = time.monotonic()
        self.downloaded_bytes = 0
        grid, grid_meta = self.grid(model)
        cells = locate(grid, points)
        frames, provenance = [], []
        variable_metadata: dict[str, tuple[str, str, str]] = {}
        with netCDF4.Dataset(grid) as ds:
            gx, gy = np.asarray(ds['x'][:]), np.asarray(ds['y'][:])
            grid_crs = ds.CRS
        for obj in selected:
            path, record = self.fetch(obj)
            variable = obj['key'].split('/')[-1].split('.')[0]
            with netCDF4.Dataset(path) as ds:
                if not (np.array_equal(gx, ds['x'][:]) and np.array_equal(gy, ds['y'][:]) and ds.CRS == grid_crs):
                    raise DataQualityError('Source axes differ from selected static grid')
                candidates = [v for v in ds.variables.values() if v.dimensions == ('time','y','x')]
                if len(candidates) != 1:
                    raise DataQualityError('Expected one time/y/x source variable')
                field = candidates[0]
                timevar = ds['time']
                calendar = getattr(timevar, 'calendar', 'standard')
                signature = (field.name, field.units, calendar)
                if variable in variable_metadata and variable_metadata[variable] != signature:
                    raise DataQualityError(f'Inconsistent metadata across {variable} files')
                variable_metadata[variable] = signature
                if calendar not in {'standard', 'gregorian', 'proleptic_gregorian'}:
                    raise DataQualityError(f'Unsupported calendar: {calendar}')
                date_values = netCDF4.num2date(timevar[:], timevar.units, calendar=calendar,
                                              only_use_cftime_datetimes=False)
                dates = pd.DatetimeIndex(np.asarray(date_values))
                if not dates.equals(dates.normalize()):
                    raise DataQualityError('Daily timestamp is not midnight; aggregation convention needs review')
                if not dates.equals(pd.date_range(dates[0], dates[-1])):
                    raise DataQualityError('Incomplete or duplicate daily source times')
                record.update(variable=variable, netcdf_variable=field.name, units=field.units,
                              long_name=getattr(field, 'long_name', ''), calendar=calendar,
                              cell_methods=getattr(field, 'cell_methods', ''),
                              standard_name=getattr(field, 'standard_name', ''),
                              time_units=timevar.units, first=str(dates[0]), last=str(dates[-1]),
                              data_model=ds.data_model)
                for cell in cells:
                    values = field[:, cell['row'], cell['col']]
                    if np.ma.getmaskarray(values).any() or not np.isfinite(values).all():
                        raise DataQualityError(f'Missing/nonfinite {variable}: {cell["name"]}')
                    frames.append(pd.DataFrame({'date': dates, 'point': cell['name'],
                                                'variable': variable, 'value': np.asarray(values)}))
            provenance.append(record)
        raw = pd.concat(frames, ignore_index=True)
        raw = raw[(raw.date >= begin) & (raw.date <= finish)]
        if raw.duplicated(['point','date','variable']).any():
            raise DataQualityError('Duplicate extracted point/date/variable')
        table = raw.pivot(index=['point','date'], columns='variable', values='value').reset_index()
        expected = len(pd.date_range(begin, finish)) * len(points)
        if len(table) != expected or table[variables].isna().any().any():
            raise DataQualityError('Incomplete requested date/variable coverage')
        manifest = dict(schema='edde-daily-query-v1', status='complete', model=model, scenario=scenario,
                        start=str(begin.date()), end=str(finish.date()), points=cells,
                        grid=grid_meta, objects=provenance, source_bytes=sum(o['size'] for o in selected),
                        transferred_bytes=self.downloaded_bytes, seconds=time.monotonic()-started,
                        generated_utc=datetime.now(timezone.utc).isoformat(),
                        attribution='EPA EDDE v2; simulated climate, not a weather forecast; no bias correction')
        return table, manifest
