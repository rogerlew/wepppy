"""Historic PRISM 800 m extraction, native-cell deduplication and revision cache.

No model transformations are performed. In particular, dewpoint remains raw.
See docs/dev-notes/prism-800m-client-design.md for the persisted contract.
"""
from dataclasses import dataclass
from datetime import date
import gzip
import logging
import os
from pathlib import Path

import pandas as pd

from ._bulk_cache import BulkCache
from ._bulk_protocol import (
    GEOMETRY, GRID_ID, PrismCacheError, PrismCell, PrismCoverageError, PrismError,
    PrismFreshnessError, PrismProtocolError, parse_bulk, snap,
)
from ._bulk_transport import BulkTransport, now, write_json

__all__ = ['PrismBulkClient', 'PrismBulkResult', 'PrismCell', 'snap', 'PrismError',
           'PrismCacheError', 'PrismCoverageError', 'PrismFreshnessError', 'PrismProtocolError']
LOGGER = logging.getLogger(__name__)


@dataclass
class PrismBulkResult:
    """Independent raw tables by cell, original point mapping and source references."""
    frames: dict[str, pd.DataFrame]
    locations: dict
    provenance: list[dict]


class _RevisionChanged(PrismFreshnessError):
    pass


class PrismBulkClient:
    def __init__(self, cache_dir=None, *, session=None, lock_timeout=600,
                 poll_seconds=5, job_timeout=600):
        location = cache_dir if cache_dir is not None else os.environ.get('PRISM_CACHE_DIR')
        if not location or not Path(location).is_absolute():
            raise ValueError('Set PRISM_CACHE_DIR to an absolute writable persistent path')
        self.cache = BulkCache(location, lock_timeout=lock_timeout)
        self.transport = BulkTransport(session, poll_seconds=poll_seconds, job_timeout=job_timeout)

    def retrieve(self, locations, start_date, end_date, *, source_crs='EPSG:4326'):
        """Retrieve named (longitude, latitude) points, inclusive ISO calendar dates.

        At most 500 unique cells and one calendar year per upstream request.
        Every cache use checks current release manifests. No stale fallback is
        provided. Exact partial-year intervals have separate cache identities.
        """
        start, end = date.fromisoformat(str(start_date)), date.fromisoformat(str(end_date))
        if start < date(1981, 1, 1) or end < start or end > date.today():
            raise ValueError('Expected ordered dates from 1981 through today; unpublished dates fail upstream')
        if not locations or any(not isinstance(name, str) or not name for name in locations):
            raise ValueError('Expected nonempty named point mapping')
        mapped, cells = {}, set()
        for name, (lon, lat) in locations.items():
            cell = snap(lon, lat, source_crs=source_crs)
            mapped[name] = dict(lon=float(lon), lat=float(lat), source_crs=source_crs,
                                cell=cell.id, row=cell.row, col=cell.col, center=cell.center, grid=GRID_ID)
            cells.add(cell)
        cells = sorted(cells, key=lambda cell: (cell.row, cell.col))
        pieces = {c.id: [] for c in cells}
        provenance = []
        for year in range(start.year, end.year + 1):
            first, last = max(start, date(year, 1, 1)), min(end, date(year, 12, 31))
            with self.cache.lock(f'{first}_{last}'):
                for offset in range(0, len(cells), 500):
                    batch = cells[offset:offset+500]
                    for retry in range(2):
                        try:
                            frames, refs = self._attempt(batch, first, last)
                            break
                        except _RevisionChanged:
                            if retry == 1:
                                raise
                    for cell, frame in frames.items():
                        pieces[cell].append(frame)
                    provenance.extend(refs)
        frames = {cell: pd.concat(parts) for cell, parts in pieces.items()}
        return PrismBulkResult(frames=frames, locations=mapped, provenance=provenance)

    def _attempt(self, cells, start, end):
        attempt = self.cache.attempt()
        write_json(attempt / 'status.json', dict(state='running', started_utc=now(),
                   cells=[c.id for c in cells], start=str(start), end=str(end), geometry=GEOMETRY))
        try:
            return self._extract_or_reuse(cells, start, end, attempt)
        except Exception as exc:  # broad-except: retain attempt failure evidence and re-raise unchanged
            # Deliberate attempt boundary: retain failures from HTTP, parse, and
            # filesystem publication, then preserve their original exception.
            LOGGER.exception('PRISM extraction failed; attempt=%s', attempt)
            try:
                write_json(attempt / 'status.json', dict(state='failed', finished_utc=now(),
                           error_type=type(exc).__name__, error=str(exc)))
            except OSError:
                LOGGER.exception('Unable to retain PRISM failure status: %s', attempt)
            raise

    def _extract_or_reuse(self, cells, start, end, attempt):
        before = self.transport.manifests(start, end, attempt, 'before')
        frames, entries, missing, checked = {}, {}, [], {}
        for cell in cells:
            cached = self.cache.load(cell, start, end, before, checked)
            if cached is None:
                missing.append(cell)
            else:
                frames[cell.id], entries[cell.id] = cached
        if missing:
            raw = self.transport.extract(missing, start, end, attempt)
            # Preserve actual payload even if parsing or subsequent freshness fails.
            (attempt / 'bulk.csv.gz').write_bytes(gzip.compress(raw, mtime=0))
            acquired = parse_bulk(raw, missing, start, end)
            after = self.transport.manifests(start, end, attempt, 'after')
            if before != after:
                raise _RevisionChanged('Source manifests changed during PRISM extraction; attempt not published')
            added = self.cache.stage(attempt, acquired, raw, after, start, end)
            self.cache.publish(added, start, end)
            entries.update(added)
            frames.update(acquired)
        acquired_ids = {c.id for c in missing}
        refs = [dict(entries[c.id], cache_root=str(self.cache.root),
                     source_directory=str(self.cache.root / 'attempts' / entries[c.id]['attempt']),
                     freshness_check_attempt=attempt.name, checked_utc=now(),
                     cache_hit=c.id not in acquired_ids) for c in cells]
        write_json(attempt / 'result.json', refs)
        write_json(attempt / 'status.json', dict(state='complete', finished_utc=now(),
                   acquired_cells=len(missing), reused_cells=len(cells)-len(missing)))
        return frames, refs
