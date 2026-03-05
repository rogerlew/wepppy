"""OSM roads service orchestration: validation, cache, fetch, clip, and reprojection."""

from __future__ import annotations

import logging
import os
import threading
import time
from contextlib import ExitStack
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from pyproj import CRS, Transformer
from pyproj.exceptions import ProjError
from shapely.geometry import GeometryCollection, MultiLineString, shape
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform as shapely_transform

from .cache import (
    OSMRoadsCacheConfig,
    OSMRoadsMetadataStore,
    PostgresMetadataStore,
    RequestRecord,
    TileRecord,
    bbox_for_tiles,
    build_request_key,
    build_tile_key,
    cleanup_expired,
    evaluate_ttl,
    highway_filter_hash,
    normalize_highway_filter,
    read_tile_payload,
    split_batches,
    tile_bounds,
    tile_cover_for_geojson,
    tile_cover_hash,
    utc_now,
    write_request_geojson,
    write_tile_payload,
)
from .contracts import OSMRoadsRequest, OSMRoadsResult, OSMRoadsService
from .errors import (
    OSMRoadsCacheError,
    OSMRoadsReprojectionError,
    OSMRoadsUpstreamError,
    OSMRoadsValidationError,
)
from .overpass import OverpassClient, OverpassClientProtocol


@dataclass(frozen=True)
class RefreshOutcome:
    """Per-request refresh bookkeeping."""

    refreshed_any: bool
    stale_fallback_used: bool
    expired_fallback_used: bool


class OSMRoadsModuleService(OSMRoadsService):
    """Default OSM roads service implementation."""

    def __init__(
        self,
        *,
        cache_config: OSMRoadsCacheConfig | None = None,
        metadata_store: OSMRoadsMetadataStore | None = None,
        overpass_client: OverpassClientProtocol | None = None,
        now_fn: callable | None = None,
    ) -> None:
        self.cache_config = cache_config or OSMRoadsCacheConfig.from_env()
        self.cache_config.cache_dir.mkdir(parents=True, exist_ok=True)
        (self.cache_config.cache_dir / "tiles").mkdir(parents=True, exist_ok=True)
        (self.cache_config.cache_dir / "requests").mkdir(parents=True, exist_ok=True)

        if metadata_store is not None:
            self.metadata_store = metadata_store
        else:
            db_url = self.cache_config.db_url or _resolve_default_db_url()
            if not db_url:
                raise OSMRoadsCacheError(
                    "No OSM roads cache metadata DB URL is configured",
                    code="db_url_required",
                    context={"env": "WEPPPY_OSM_ROADS_CACHE_DB_URL"},
                )
            self.metadata_store = PostgresMetadataStore(db_url=db_url, schema=self.cache_config.db_schema)

        self.metadata_store.ensure_schema()
        self.overpass_client = overpass_client or OverpassClient()
        self._now_fn = now_fn or utc_now
        self._cleanup_guard = threading.Lock()
        self._last_cleanup_ts = 0.0

    def get_roads(
        self,
        req: OSMRoadsRequest,
        *,
        logger: logging.Logger | None = None,
    ) -> OSMRoadsResult:
        log = logger or logging.getLogger(__name__)

        aoi_geom, bbox = _validate_request(req)
        normalized_filter = normalize_highway_filter(req.highway_filter)
        filter_hash = highway_filter_hash(normalized_filter)
        tile_ids = tile_cover_for_geojson(req.aoi_wgs84_geojson, self.cache_config.tile_degrees)

        request_tile_cover_hash = tile_cover_hash(tile_ids)
        request_key = build_request_key(request_tile_cover_hash, filter_hash)
        now_utc = self._now_fn()

        tile_features: dict[str, list[dict[str, Any]]] = {}
        refresh_queue: list[str] = []

        for tile_id in tile_ids:
            tile_key = build_tile_key(tile_id, filter_hash)
            row = self.metadata_store.get_tile(tile_key)
            decision = evaluate_ttl(
                fetched_at_utc=row.fetched_at_utc if row else None,
                now_utc=now_utc,
                soft_ttl_days=self.cache_config.soft_ttl_days,
                hard_ttl_days=self.cache_config.hard_ttl_days,
                max_expired_staleness_days=self.cache_config.max_expired_staleness_days,
                force_refresh=req.force_refresh,
                allow_stale_on_error=req.allow_stale_on_error,
                allow_expired_on_error=req.allow_expired_on_error,
            )
            if not decision.should_refresh and row is not None:
                tile_features[tile_id] = read_tile_payload(Path(row.payload_path))
            else:
                refresh_queue.append(tile_id)

        refresh_outcome = RefreshOutcome(
            refreshed_any=False,
            stale_fallback_used=False,
            expired_fallback_used=False,
        )

        if refresh_queue:
            refresh_outcome = self._refresh_tiles(
                tile_ids=refresh_queue,
                req=req,
                normalized_filter=normalized_filter,
                filter_hash=filter_hash,
                now_utc=now_utc,
                tile_features=tile_features,
            )

        merged = _merge_features(tile_ids, tile_features)
        clipped = _clip_features_to_aoi(merged, aoi_geom)
        projected = _reproject_features(clipped, req.target_epsg)

        request_geojson_path = self.cache_config.cache_dir / "requests" / f"{request_key}.geojson"
        write_request_geojson(request_geojson_path, features=projected, target_epsg=req.target_epsg)

        fetched_at = self._latest_fetched_at(tile_ids=tile_ids, filter_hash=filter_hash, fallback=now_utc)
        self.metadata_store.upsert_request(
            RequestRecord(
                request_key=request_key,
                tile_cover_hash=request_tile_cover_hash,
                highway_filter_hash=filter_hash,
                roads_geojson_path=str(request_geojson_path),
                fetched_at_utc=fetched_at,
                feature_count=len(projected),
            )
        )

        source = _result_source(refresh_outcome)
        cache_hit = source != "overpass"
        stale_served = source in {"stale_cache", "expired_cache"}

        self._log_event(
            log,
            event="osm_roads_fetch",
            cache_key=request_key,
            tile_count=len(tile_ids),
            cache_hit_count=len(tile_ids) - len(refresh_queue),
            query_batch_count=len(split_batches(refresh_queue, self.cache_config.max_tiles_per_query)) if refresh_queue else 0,
            feature_count=len(projected),
            stale_served=stale_served,
            expired_served=source == "expired_cache",
        )

        self._maybe_cleanup()

        return OSMRoadsResult(
            roads_geojson_path=str(request_geojson_path.resolve()),
            cache_key=request_key,
            cache_hit=cache_hit,
            stale_served=stale_served,
            fetched_at_utc=fetched_at.astimezone(timezone.utc).isoformat(),
            source=source,
            feature_count=len(projected),
            target_epsg=req.target_epsg,
            bbox_wgs84=bbox,
        )

    def _refresh_tiles(
        self,
        *,
        tile_ids: Sequence[str],
        req: OSMRoadsRequest,
        normalized_filter: tuple[str, ...],
        filter_hash: str,
        now_utc: datetime,
        tile_features: dict[str, list[dict[str, Any]]],
    ) -> RefreshOutcome:
        refreshed_any = False
        stale_fallback_used = False
        expired_fallback_used = False

        for batch in split_batches(list(tile_ids), self.cache_config.max_tiles_per_query):
            with ExitStack() as lock_stack:
                locked: list[tuple[str, str]] = []
                for tile_id in sorted(batch):
                    tile_key = build_tile_key(tile_id, filter_hash)
                    lock_stack.enter_context(
                        self.metadata_store.acquire_lock(
                            tile_key,
                            self.cache_config.lock_timeout_sec,
                            self.cache_config.lock_poll_ms,
                        )
                    )
                    locked.append((tile_id, tile_key))

                pending: list[tuple[str, str, TileRecord | None, Any]] = []
                for tile_id, tile_key in locked:
                    row = self.metadata_store.get_tile(tile_key)
                    decision = evaluate_ttl(
                        fetched_at_utc=row.fetched_at_utc if row else None,
                        now_utc=now_utc,
                        soft_ttl_days=self.cache_config.soft_ttl_days,
                        hard_ttl_days=self.cache_config.hard_ttl_days,
                        max_expired_staleness_days=self.cache_config.max_expired_staleness_days,
                        force_refresh=req.force_refresh,
                        allow_stale_on_error=req.allow_stale_on_error,
                        allow_expired_on_error=req.allow_expired_on_error,
                    )
                    if not decision.should_refresh and row is not None:
                        tile_features[tile_id] = read_tile_payload(Path(row.payload_path))
                    else:
                        pending.append((tile_id, tile_key, row, decision))

                if not pending:
                    continue

                fetch_bbox = bbox_for_tiles([item[0] for item in pending], self.cache_config.tile_degrees)

                try:
                    fetched = self.overpass_client.fetch_roads(
                        bbox_wgs84=fetch_bbox,
                        highway_filter=normalized_filter,
                        include_tags=req.include_tags,
                    )
                except OSMRoadsUpstreamError:
                    for tile_id, _, row, decision in pending:
                        if row is None or decision.fallback_kind == "none":
                            raise
                        tile_features[tile_id] = read_tile_payload(Path(row.payload_path))
                        if decision.fallback_kind == "stale":
                            stale_fallback_used = True
                        elif decision.fallback_kind == "expired":
                            expired_fallback_used = True
                    continue

                per_tile = _split_features_by_tile(
                    fetched,
                    tile_ids=[item[0] for item in pending],
                    tile_degrees=self.cache_config.tile_degrees,
                )

                for tile_id, tile_key, _, _ in pending:
                    rows = per_tile.get(tile_id, [])
                    payload_path = _tile_payload_path(
                        cache_dir=self.cache_config.cache_dir,
                        tile_id=tile_id,
                        filter_hash=filter_hash,
                    )
                    write_tile_payload(payload_path, rows)
                    self.metadata_store.upsert_tile(
                        TileRecord(
                            tile_key=tile_key,
                            tile_id=tile_id,
                            highway_filter_hash=filter_hash,
                            payload_path=str(payload_path),
                            fetched_at_utc=now_utc,
                            feature_count=len(rows),
                        )
                    )
                    tile_features[tile_id] = rows
                    refreshed_any = True

        return RefreshOutcome(
            refreshed_any=refreshed_any,
            stale_fallback_used=stale_fallback_used,
            expired_fallback_used=expired_fallback_used,
        )

    def _latest_fetched_at(self, *, tile_ids: Sequence[str], filter_hash: str, fallback: datetime) -> datetime:
        latest = fallback
        for tile_id in tile_ids:
            row = self.metadata_store.get_tile(build_tile_key(tile_id, filter_hash))
            if row is None:
                continue
            if row.fetched_at_utc > latest:
                latest = row.fetched_at_utc
        return latest

    def _maybe_cleanup(self) -> None:
        now_mono = time.monotonic()
        with self._cleanup_guard:
            if (now_mono - self._last_cleanup_ts) < self.cache_config.cleanup_min_interval_sec:
                return
            cleanup_expired(
                metadata_store=self.metadata_store,
                cache_dir=self.cache_config.cache_dir,
                hard_ttl_days=self.cache_config.hard_ttl_days,
                max_expired_staleness_days=self.cache_config.max_expired_staleness_days,
                now_utc=self._now_fn(),
                lock_timeout_sec=self.cache_config.lock_timeout_sec,
                lock_poll_ms=self.cache_config.lock_poll_ms,
            )
            self._last_cleanup_ts = now_mono

    @staticmethod
    def _log_event(logger: logging.Logger, *, event: str, **fields: Any) -> None:
        payload = {"event": event, **fields}
        logger.info("osm_roads_event=%s", payload)


class TerrainProcessorRoadsResolver:
    """Consumer seam for TerrainProcessor-style road source resolution."""

    def __init__(self, service: OSMRoadsService) -> None:
        self.service = service

    def resolve(
        self,
        *,
        roads_source: str | None,
        roads_path: str | None,
        aoi_wgs84_geojson: Mapping[str, Any] | None,
        target_epsg: int | None,
        osm_highway_filter: Sequence[str],
        logger: logging.Logger | None = None,
    ) -> str | None:
        if roads_source is None:
            return None
        if roads_source == "upload":
            if not roads_path:
                raise OSMRoadsValidationError("roads_path is required for roads_source='upload'", code="missing_uploaded_roads")
            return roads_path
        if roads_source == "osm":
            if aoi_wgs84_geojson is None:
                raise OSMRoadsValidationError("aoi_wgs84_geojson is required for roads_source='osm'", code="missing_aoi")
            if target_epsg is None:
                raise OSMRoadsValidationError("target_epsg is required for roads_source='osm'", code="missing_target_epsg")
            result = self.service.get_roads(
                OSMRoadsRequest(
                    aoi_wgs84_geojson=dict(aoi_wgs84_geojson),
                    target_epsg=int(target_epsg),
                    highway_filter=tuple(osm_highway_filter),
                ),
                logger=logger,
            )
            return result.roads_geojson_path
        raise OSMRoadsValidationError(
            "Unsupported roads_source",
            code="unsupported_roads_source",
            context={"roads_source": roads_source},
        )


def build_default_service() -> OSMRoadsModuleService:
    """Build service from environment-backed runtime configuration."""

    return OSMRoadsModuleService()


def _result_source(outcome: RefreshOutcome) -> str:
    if outcome.expired_fallback_used:
        return "expired_cache"
    if outcome.stale_fallback_used:
        return "stale_cache"
    if outcome.refreshed_any:
        return "overpass"
    return "cache"


def _validate_request(req: OSMRoadsRequest) -> tuple[BaseGeometry, tuple[float, float, float, float]]:
    if not isinstance(req.target_epsg, int) or req.target_epsg <= 0:
        raise OSMRoadsValidationError(
            "target_epsg must be a positive integer",
            code="invalid_target_epsg",
            context={"target_epsg": req.target_epsg},
        )

    try:
        CRS.from_epsg(req.target_epsg)
    except (ProjError, ValueError) as exc:
        raise OSMRoadsValidationError(
            "target_epsg is not a valid CRS",
            code="invalid_target_epsg",
            context={"target_epsg": req.target_epsg},
        ) from exc

    try:
        geom = shape(req.aoi_wgs84_geojson)
    except (TypeError, ValueError) as exc:
        raise OSMRoadsValidationError("Invalid AOI GeoJSON", code="invalid_aoi_geojson") from exc

    if geom.geom_type not in {"Polygon", "MultiPolygon"}:
        raise OSMRoadsValidationError(
            "AOI must be Polygon or MultiPolygon",
            code="invalid_aoi_type",
            context={"geom_type": geom.geom_type},
        )
    if geom.is_empty:
        raise OSMRoadsValidationError("AOI geometry is empty", code="empty_aoi")

    bbox = geom.bounds
    return geom, (float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3]))


def _split_features_by_tile(
    fetched: Sequence[Mapping[str, Any]],
    *,
    tile_ids: Sequence[str],
    tile_degrees: float,
) -> dict[str, list[dict[str, Any]]]:
    from shapely.geometry import box

    out: dict[str, list[dict[str, Any]]] = {tile_id: [] for tile_id in tile_ids}

    for tile_id in tile_ids:
        tgeom = box(*tile_bounds(tile_id, tile_degrees))
        for feature in fetched:
            geom = feature.get("geometry")
            if not isinstance(geom, BaseGeometry):
                continue
            clipped = geom.intersection(tgeom)
            for part in _iter_line_parts(clipped):
                row = dict(feature)
                row["geometry"] = part
                out[tile_id].append(row)

    return out


def _merge_features(tile_ids: Sequence[str], tile_features: Mapping[str, Sequence[Mapping[str, Any]]]) -> list[dict[str, Any]]:
    from shapely.wkb import dumps as dump_wkb

    merged: list[dict[str, Any]] = []
    seen: set[tuple[str, bytes]] = set()

    for tile_id in tile_ids:
        for feature in tile_features.get(tile_id, []):
            geom = feature.get("geometry")
            if not isinstance(geom, BaseGeometry):
                continue
            signature = (str(feature.get("osm_id", "")), dump_wkb(geom, hex=False))
            if signature in seen:
                continue
            seen.add(signature)
            merged.append(dict(feature))
    return merged


def _clip_features_to_aoi(features: Sequence[Mapping[str, Any]], aoi_geom: BaseGeometry) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for feature in features:
        geom = feature.get("geometry")
        if not isinstance(geom, BaseGeometry):
            continue
        clipped = geom.intersection(aoi_geom)
        for part in _iter_line_parts(clipped):
            row = dict(feature)
            row["geometry"] = part
            out.append(row)
    return out


def _reproject_features(features: Sequence[Mapping[str, Any]], target_epsg: int) -> list[dict[str, Any]]:
    if target_epsg == 4326:
        return [dict(item) for item in features]

    try:
        transformer = Transformer.from_crs("EPSG:4326", f"EPSG:{target_epsg}", always_xy=True)
    except (ProjError, ValueError) as exc:
        raise OSMRoadsReprojectionError(
            "Failed creating CRS transformer",
            code="reprojection_transformer_error",
            context={"target_epsg": target_epsg},
        ) from exc

    out: list[dict[str, Any]] = []
    for feature in features:
        geom = feature.get("geometry")
        if not isinstance(geom, BaseGeometry):
            continue
        try:
            projected = shapely_transform(transformer.transform, geom)
        except (ProjError, ValueError, TypeError) as exc:
            raise OSMRoadsReprojectionError(
                "Failed to reproject geometry",
                code="reprojection_geometry_error",
                context={"target_epsg": target_epsg},
            ) from exc
        row = dict(feature)
        row["geometry"] = projected
        out.append(row)
    return out


def _iter_line_parts(geom: BaseGeometry) -> list[BaseGeometry]:
    if geom.is_empty:
        return []
    if geom.geom_type == "LineString":
        return [geom]
    if isinstance(geom, MultiLineString):
        return [part for part in geom.geoms if not part.is_empty]
    if isinstance(geom, GeometryCollection):
        parts: list[BaseGeometry] = []
        for sub in geom.geoms:
            parts.extend(_iter_line_parts(sub))
        return parts
    return []


def _tile_payload_path(*, cache_dir: Path, tile_id: str, filter_hash: str) -> Path:
    return cache_dir / "tiles" / tile_id / f"{filter_hash}.parquet"


def _resolve_default_db_url() -> str | None:
    # Order of precedence keeps OSM module-specific URL first.
    env_order = (
        "WEPPPY_OSM_ROADS_CACHE_DB_URL",
        "SQLALCHEMY_DATABASE_URI",
        "DATABASE_URL",
    )
    for name in env_order:
        value = (os.getenv(name) or "").strip()
        if value:
            return value

    host = (os.getenv("POSTGRES_HOST") or "").strip()
    if not host:
        return None
    port = (os.getenv("POSTGRES_PORT") or "5432").strip() or "5432"
    db = (os.getenv("POSTGRES_DB") or "wepppy").strip() or "wepppy"
    user = (os.getenv("POSTGRES_USER") or "wepppy").strip() or "wepppy"
    password = (os.getenv("POSTGRES_PASSWORD") or "").strip()
    if password:
        return f"postgresql://{user}:{password}@{host}:{port}/{db}"
    return f"postgresql://{user}@{host}:{port}/{db}"


__all__ = [
    "OSMRoadsModuleService",
    "TerrainProcessorRoadsResolver",
    "build_default_service",
]
