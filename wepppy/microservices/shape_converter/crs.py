"""CRS planning and reprojection helpers for shape-converter convert requests."""

from __future__ import annotations

import math
from dataclasses import dataclass

import utm
from pyproj import CRS, Transformer
from pyproj.exceptions import CRSError, ProjError
from shapely.errors import GEOSException
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform as shapely_transform
from utm.error import OutOfRangeError

from .errors import ShapeConverterError

WGS84_CRS = CRS.from_epsg(4326)
TARGET_CRS_OPTIONS = frozenset({"same_as_shapefile", "wgs84", "utm_wepppy_upper_left"})
SOURCE_PROJECTION_STATUS_OPTIONS = frozenset({"known", "unknown", "invalid"})


@dataclass(frozen=True, slots=True)
class ResolvedTargetCrs:
    """Resolved CRS plan for one convert request."""

    source_crs: CRS | None
    target_crs: CRS | None
    rfc7946_compliant_geojson: bool
    warnings: tuple[str, ...]


def parse_source_crs(*, crs_wkt: str | None, crs_mapping: object | None) -> CRS | None:
    """Parse source CRS from Fiona metadata, returning ``None`` when unavailable."""

    if isinstance(crs_wkt, str) and crs_wkt.strip():
        try:
            return CRS.from_wkt(crs_wkt)
        except (CRSError, TypeError, ValueError):
            pass

    if crs_mapping is not None:
        try:
            return CRS.from_user_input(crs_mapping)
        except (CRSError, TypeError, ValueError):
            return None

    return None


def resolve_target_crs(
    *,
    target_crs_token: str,
    source_crs: CRS | None,
    source_bounds: tuple[float, float, float, float],
    source_projection_status: str = "known",
) -> ResolvedTargetCrs:
    """Resolve conversion target CRS and warnings for the requested mode."""

    if target_crs_token not in TARGET_CRS_OPTIONS:
        raise ShapeConverterError(
            code="invalid_request",
            message="Unsupported target_crs value.",
            details=(
                f"target_crs={target_crs_token!r} is invalid; "
                f"expected one of {sorted(TARGET_CRS_OPTIONS)}."
            ),
        )
    if source_projection_status not in SOURCE_PROJECTION_STATUS_OPTIONS:
        raise ShapeConverterError(
            code="invalid_request",
            message="Source projection status is invalid.",
            details=(
                f"source_projection_status={source_projection_status!r} is invalid; "
                f"expected one of {sorted(SOURCE_PROJECTION_STATUS_OPTIONS)}."
            ),
        )

    if target_crs_token == "same_as_shapefile":
        if source_crs is None:
            if source_projection_status == "invalid":
                warning = (
                    "Source CRS is invalid; coordinates were preserved without reprojection."
                )
            else:
                warning = (
                    "Source CRS is unknown; coordinates were preserved without reprojection."
                )
            return ResolvedTargetCrs(
                source_crs=None,
                target_crs=None,
                rfc7946_compliant_geojson=False,
                warnings=(warning,),
            )

        return ResolvedTargetCrs(
            source_crs=source_crs,
            target_crs=source_crs,
            rfc7946_compliant_geojson=bool(source_crs.equals(WGS84_CRS)),
            warnings=(),
        )

    if source_crs is None:
        if source_projection_status == "invalid":
            raise ShapeConverterError(
                code="invalid_source_crs",
                message="Source CRS is invalid and cannot be used for reprojection.",
                details=(
                    f"target_crs={target_crs_token!r} requires a valid source CRS, "
                    "but the uploaded dataset provides an invalid projection definition."
                ),
            )
        raise ShapeConverterError(
            code="unknown_source_crs",
            message="Source CRS is required for reprojection.",
            details=(
                f"target_crs={target_crs_token!r} requires a known source CRS, "
                "but the uploaded dataset does not provide one."
            ),
        )

    if target_crs_token == "wgs84":
        return ResolvedTargetCrs(
            source_crs=source_crs,
            target_crs=WGS84_CRS,
            rfc7946_compliant_geojson=True,
            warnings=(),
        )

    return _resolve_upper_left_utm(source_crs=source_crs, source_bounds=source_bounds)


def _resolve_upper_left_utm(*, source_crs: CRS, source_bounds: tuple[float, float, float, float]) -> ResolvedTargetCrs:
    west, south, east, north = source_bounds

    ul_lon, ul_lat = _transform_xy_to_wgs84(x=west, y=north, source_crs=source_crs)
    lr_lon, lr_lat = _transform_xy_to_wgs84(x=east, y=south, source_crs=source_crs)

    if not (-80.0 <= ul_lat <= 84.0):
        raise ShapeConverterError(
            code="utm_not_supported_for_extent",
            message="Upper-left extent lies outside supported UTM latitude domain.",
            details=(
                f"Upper-left latitude {ul_lat:.6f} is outside [-80, 84] degrees."
            ),
        )

    if not (-180.0 <= ul_lon <= 180.0):
        raise ShapeConverterError(
            code="utm_not_supported_for_extent",
            message="Upper-left extent has invalid longitude for UTM zone selection.",
            details=f"Upper-left longitude {ul_lon:.6f} is outside [-180, 180] degrees.",
        )

    try:
        _, _, utm_zone, _ = utm.from_latlon(ul_lat, ul_lon)
    except (OutOfRangeError, ValueError, TypeError) as exc:
        raise ShapeConverterError(
            code="utm_not_supported_for_extent",
            message="Failed to determine UTM zone from upper-left extent.",
            details=str(exc),
        ) from exc

    northern = ul_lat > 0.0
    target_crs = CRS.from_epsg(32600 + utm_zone if northern else 32700 + utm_zone)

    warnings: list[str] = []
    if -80.0 <= lr_lat <= 84.0 and -180.0 <= lr_lon <= 180.0:
        try:
            _, _, lower_right_zone, _ = utm.from_latlon(lr_lat, lr_lon)
            if lower_right_zone != utm_zone:
                warnings.append(
                    "Source extent spans multiple UTM zones; using upper-left corner zone per WEPPpy behavior."
                )
        except (OutOfRangeError, ValueError, TypeError):
            # Lower-right checks are advisory only; upper-left corner remains authoritative.
            pass

    return ResolvedTargetCrs(
        source_crs=source_crs,
        target_crs=target_crs,
        rfc7946_compliant_geojson=False,
        warnings=tuple(warnings),
    )


def _transform_xy_to_wgs84(*, x: float, y: float, source_crs: CRS) -> tuple[float, float]:
    if not (math.isfinite(x) and math.isfinite(y)):
        raise ShapeConverterError(
            code="utm_not_supported_for_extent",
            message="Source bounds are not finite.",
            details=f"Encountered non-finite coordinate ({x}, {y}) while planning UTM target CRS.",
        )

    if source_crs.equals(WGS84_CRS):
        return float(x), float(y)

    try:
        transformer = Transformer.from_crs(source_crs, WGS84_CRS, always_xy=True)
        lon, lat = transformer.transform(x, y)
    except (CRSError, ProjError, RuntimeError, TypeError, ValueError) as exc:
        raise ShapeConverterError(
            code="reprojection_failed",
            message="Failed to transform source bounds to WGS84.",
            details=str(exc),
        ) from exc

    if not (math.isfinite(lon) and math.isfinite(lat)):
        raise ShapeConverterError(
            code="reprojection_failed",
            message="Failed to transform source bounds to WGS84.",
            details=f"Transformed coordinate ({lon}, {lat}) is not finite.",
        )

    return float(lon), float(lat)


def reproject_geometries(
    *,
    geometries: tuple[BaseGeometry | None, ...],
    source_crs: CRS | None,
    target_crs: CRS | None,
) -> tuple[BaseGeometry | None, ...]:
    """Reproject geometries from source to target CRS."""

    if source_crs is None or target_crs is None or source_crs.equals(target_crs):
        return geometries

    try:
        transformer = Transformer.from_crs(source_crs, target_crs, always_xy=True)
    except (CRSError, ProjError, RuntimeError, TypeError, ValueError) as exc:
        raise ShapeConverterError(
            code="reprojection_failed",
            message="Failed to initialize reprojection transformer.",
            details=str(exc),
        ) from exc

    transformed: list[BaseGeometry | None] = []
    for geometry in geometries:
        if geometry is None:
            transformed.append(None)
            continue

        try:
            transformed.append(shapely_transform(transformer.transform, geometry))
        except (GEOSException, ProjError, RuntimeError, TypeError, ValueError) as exc:
            raise ShapeConverterError(
                code="reprojection_failed",
                message="Failed to reproject one or more geometries.",
                details=str(exc),
            ) from exc

    return tuple(transformed)


def crs_to_response_payload(crs: CRS | None) -> dict[str, object] | None:
    """Convert a CRS object into response metadata payload."""

    if crs is None:
        return None

    payload: dict[str, object] = {"wkt": crs.to_wkt()}
    authority = crs.to_authority()
    if authority is not None:
        payload["authority"] = f"{authority[0]}:{authority[1]}"
    return payload


def crs_identifier(crs: CRS | None) -> str | None:
    """Return the most concise stable identifier for a CRS."""

    if crs is None:
        return None

    authority = crs.to_authority()
    if authority is not None:
        return f"{authority[0]}:{authority[1]}"

    return crs.to_string()


__all__ = [
    "TARGET_CRS_OPTIONS",
    "SOURCE_PROJECTION_STATUS_OPTIONS",
    "WGS84_CRS",
    "ResolvedTargetCrs",
    "crs_identifier",
    "crs_to_response_payload",
    "parse_source_crs",
    "reproject_geometries",
    "resolve_target_crs",
]
