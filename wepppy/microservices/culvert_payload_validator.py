from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Optional

import rasterio
from pyproj import CRS

METADATA_SCHEMA_VERSION = "culvert-metadata-v1"
MODEL_PARAMS_SCHEMA_VERSION = "culvert-model-params-v1"
POINT_ID_FIELD = "Point_ID"
MAX_CULVERT_COUNT = 300

REQUIRED_PAYLOAD_PATHS = (
    "metadata.json",
    "model-parameters.json",
    "topo/breached_filled_DEM_UTM.tif",
    "topo/streams.tif",
    "culverts/culvert_points.geojson",
    "culverts/watersheds.geojson",
)


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str
    path: Optional[str] = None
    detail: Optional[dict[str, Any]] = None


def format_validation_errors(errors: Iterable[ValidationIssue]) -> list[dict[str, Any]]:
    return [_format_issue(issue) for issue in errors]


def validate_zip_members(members: Iterable[str]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    member_set = {member for member in members if member and not member.endswith("/")}

    for member in member_set:
        path = PurePosixPath(member)
        if path.is_absolute() or ".." in path.parts:
            issues.append(
                ValidationIssue(
                    code="invalid_member_path",
                    message="Zip member path is not allowed.",
                    path=member,
                )
            )

    missing = sorted(set(REQUIRED_PAYLOAD_PATHS) - member_set)
    for path in missing:
        issues.append(
            ValidationIssue(code="missing_file", message="Required file missing.", path=path)
        )

    return issues


def validate_payload_root(root: Path) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    payload_paths = {path: root / path for path in REQUIRED_PAYLOAD_PATHS}

    for relpath, fullpath in payload_paths.items():
        if not fullpath.is_file():
            issues.append(
                ValidationIssue(
                    code="missing_file",
                    message="Required file missing after extraction.",
                    path=relpath,
                )
            )

    metadata = _load_json(payload_paths["metadata.json"], issues, "metadata.json")
    model_params = _load_json(payload_paths["model-parameters.json"], issues, "model-parameters.json")

    if metadata is None:
        return issues

    _validate_metadata(metadata, issues)
    if model_params is not None:
        _validate_model_params(model_params, issues)

    dem_path = payload_paths["topo/breached_filled_DEM_UTM.tif"]
    streams_path = payload_paths["topo/streams.tif"]
    _validate_rasters(dem_path, streams_path, metadata, issues)

    culvert_points_path = payload_paths["culverts/culvert_points.geojson"]
    watersheds_path = payload_paths["culverts/watersheds.geojson"]
    _validate_geojsons(culvert_points_path, watersheds_path, metadata, issues)

    return issues


def _format_issue(issue: ValidationIssue) -> dict[str, Any]:
    payload: dict[str, Any] = {"code": issue.code, "message": issue.message}
    if issue.path:
        payload["path"] = issue.path
    if issue.detail:
        payload["detail"] = issue.detail
    return payload


def _load_json(path: Path, issues: list[ValidationIssue], label: str) -> Optional[dict[str, Any]]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        return None
    except (OSError, json.JSONDecodeError) as exc:
        issues.append(
            ValidationIssue(
                code="invalid_json",
                message=f"{label} could not be parsed.",
                path=str(path.name),
                detail={"error": str(exc)},
            )
        )
        return None

    if not isinstance(data, dict):
        issues.append(
            ValidationIssue(
                code="invalid_json",
                message=f"{label} must contain a JSON object.",
                path=str(path.name),
            )
        )
        return None

    return data


def _validate_metadata(metadata: dict[str, Any], issues: list[ValidationIssue]) -> None:
    schema_version = metadata.get("schema_version")
    if schema_version != METADATA_SCHEMA_VERSION:
        issues.append(
            ValidationIssue(
                code="invalid_schema_version",
                message="metadata.json schema_version is invalid.",
                path="metadata.json",
                detail={"expected": METADATA_SCHEMA_VERSION, "found": schema_version},
            )
        )

    crs = metadata.get("crs") or {}
    proj4 = crs.get("proj4")
    if not proj4:
        issues.append(
            ValidationIssue(
                code="missing_metadata_field",
                message="metadata.json crs.proj4 is required.",
                path="metadata.json",
            )
        )
        return

    metadata_crs = _parse_crs(proj4, issues, "metadata.json", "crs.proj4")
    if metadata_crs is not None and not _crs_is_meter_projected(metadata_crs):
        issues.append(
            ValidationIssue(
                code="invalid_crs_units",
                message="CRS must be projected in meters.",
                path="metadata.json",
            )
        )

    for section, relpath in (
        ("dem", "topo/breached_filled_DEM_UTM.tif"),
        ("streams", "topo/streams.tif"),
        ("culvert_points", "culverts/culvert_points.geojson"),
        ("watersheds", "culverts/watersheds.geojson"),
    ):
        path_value = (metadata.get(section) or {}).get("path")
        if path_value and path_value != relpath:
            issues.append(
                ValidationIssue(
                    code="path_mismatch",
                    message=f"metadata.json {section}.path does not match payload.",
                    path="metadata.json",
                    detail={"expected": relpath, "found": path_value},
                )
            )

    for section in ("culvert_points", "watersheds"):
        point_field = (metadata.get(section) or {}).get("point_id_field")
        if point_field and point_field != POINT_ID_FIELD:
            issues.append(
                ValidationIssue(
                    code="invalid_point_id_field",
                    message=f"metadata.json {section}.point_id_field must be {POINT_ID_FIELD}.",
                    path="metadata.json",
                    detail={"expected": POINT_ID_FIELD, "found": point_field},
                )
            )

    culvert_count = metadata.get("culvert_count")
    if culvert_count is None:
        issues.append(
            ValidationIssue(
                code="missing_metadata_field",
                message="metadata.json culvert_count is required.",
                path="metadata.json",
            )
        )
    elif not isinstance(culvert_count, int):
        issues.append(
            ValidationIssue(
                code="invalid_metadata_field",
                message="metadata.json culvert_count must be an integer.",
                path="metadata.json",
            )
        )
    elif culvert_count > MAX_CULVERT_COUNT:
        issues.append(
            ValidationIssue(
                code="culvert_count_exceeds_limit",
                message="metadata.json culvert_count exceeds limit.",
                path="metadata.json",
                detail={"max": MAX_CULVERT_COUNT, "found": culvert_count},
            )
        )

    _validate_optional_metadata_int(metadata, "flow_accum_threshold", issues)


def _validate_model_params(model_params: dict[str, Any], issues: list[ValidationIssue]) -> None:
    schema_version = model_params.get("schema_version")
    if schema_version != MODEL_PARAMS_SCHEMA_VERSION:
        issues.append(
            ValidationIssue(
                code="invalid_schema_version",
                message="model-parameters.json schema_version is invalid.",
                path="model-parameters.json",
                detail={"expected": MODEL_PARAMS_SCHEMA_VERSION, "found": schema_version},
            )
        )
    _validate_optional_model_param_str(model_params, "base_project_runid", issues)
    _validate_optional_model_param_str(model_params, "nlcd_db", issues)
    _validate_optional_model_param_int(model_params, "flow_accum_threshold", issues)
    _validate_optional_model_param_int(model_params, "order_reduction_passes", issues)


def _validate_rasters(
    dem_path: Path,
    streams_path: Path,
    metadata: dict[str, Any],
    issues: list[ValidationIssue],
) -> None:
    dem_crs = _raster_crs(dem_path, issues, "topo/breached_filled_DEM_UTM.tif")
    streams_crs = _raster_crs(streams_path, issues, "topo/streams.tif")

    metadata_crs = _parse_crs(
        (metadata.get("crs") or {}).get("proj4"),
        issues,
        "metadata.json",
        "crs.proj4",
    )

    if dem_crs and metadata_crs and not dem_crs.equals(metadata_crs):
        issues.append(
            ValidationIssue(
                code="crs_mismatch",
                message="DEM CRS does not match metadata CRS.",
                path="topo/breached_filled_DEM_UTM.tif",
            )
        )

    if streams_crs and metadata_crs and not streams_crs.equals(metadata_crs):
        issues.append(
            ValidationIssue(
                code="crs_mismatch",
                message="Streams CRS does not match metadata CRS.",
                path="topo/streams.tif",
            )
        )

    if dem_crs and streams_crs and not dem_crs.equals(streams_crs):
        issues.append(
            ValidationIssue(
                code="crs_mismatch",
                message="DEM and streams CRS do not match.",
                path="topo/streams.tif",
            )
        )

    try:
        with rasterio.open(dem_path) as dem_ds, rasterio.open(streams_path) as streams_ds:
            if dem_ds.width != streams_ds.width or dem_ds.height != streams_ds.height:
                issues.append(
                    ValidationIssue(
                        code="raster_mismatch",
                        message="DEM and streams dimensions do not match.",
                        path="topo/streams.tif",
                        detail={
                            "dem": {"width": dem_ds.width, "height": dem_ds.height},
                            "streams": {"width": streams_ds.width, "height": streams_ds.height},
                        },
                    )
                )
            if not dem_ds.transform.almost_equals(streams_ds.transform):
                issues.append(
                    ValidationIssue(
                        code="raster_mismatch",
                        message="DEM and streams transforms do not match.",
                        path="topo/streams.tif",
                    )
                )
    except (OSError, rasterio.errors.RasterioIOError) as exc:
        issues.append(
            ValidationIssue(
                code="raster_read_failed",
                message="Failed to read raster during validation.",
                path="topo/streams.tif",
                detail={"error": str(exc)},
            )
        )


def _validate_geojsons(
    culvert_points_path: Path,
    watersheds_path: Path,
    metadata: dict[str, Any],
    issues: list[ValidationIssue],
) -> None:
    culvert_points = _load_json(culvert_points_path, issues, "culvert_points.geojson")
    watersheds = _load_json(watersheds_path, issues, "watersheds.geojson")

    if culvert_points is None or watersheds is None:
        return

    metadata_crs = _parse_crs(
        (metadata.get("crs") or {}).get("proj4"),
        issues,
        "metadata.json",
        "crs.proj4",
    )

    culvert_points_crs = _geojson_crs(culvert_points, issues, "culverts/culvert_points.geojson")
    watersheds_crs = _geojson_crs(watersheds, issues, "culverts/watersheds.geojson")

    _validate_geojson_geometry(
        culvert_points,
        {"Point"},
        issues,
        "culverts/culvert_points.geojson",
    )
    _validate_geojson_geometry(
        watersheds,
        {"Polygon", "MultiPolygon"},
        issues,
        "culverts/watersheds.geojson",
    )

    if metadata_crs and culvert_points_crs and not culvert_points_crs.equals(metadata_crs):
        issues.append(
            ValidationIssue(
                code="crs_mismatch",
                message="Culvert points CRS does not match metadata CRS.",
                path="culverts/culvert_points.geojson",
            )
        )

    if metadata_crs and watersheds_crs and not watersheds_crs.equals(metadata_crs):
        issues.append(
            ValidationIssue(
                code="crs_mismatch",
                message="Watersheds CRS does not match metadata CRS.",
                path="culverts/watersheds.geojson",
            )
        )

    culvert_ids, culvert_feature_count = _extract_point_ids(
        culvert_points,
        POINT_ID_FIELD,
        issues,
        "culverts/culvert_points.geojson",
    )
    watershed_ids, _ = _extract_point_ids(
        watersheds,
        POINT_ID_FIELD,
        issues,
        "culverts/watersheds.geojson",
    )

    if culvert_ids and watershed_ids:
        missing = sorted(watershed_ids - culvert_ids)
        if missing:
            issues.append(
                ValidationIssue(
                    code="point_id_missing",
                    message="Watershed Point_ID values are missing from culvert points.",
                    path="culverts/watersheds.geojson",
                    detail={"count": len(missing), "sample": missing[:10]},
                )
            )

    if culvert_feature_count > MAX_CULVERT_COUNT:
        issues.append(
            ValidationIssue(
                code="culvert_count_exceeds_limit",
                message="Culvert count exceeds limit.",
                path="culverts/culvert_points.geojson",
                detail={"max": MAX_CULVERT_COUNT, "found": culvert_feature_count},
            )
        )

    culvert_count = metadata.get("culvert_count")
    if isinstance(culvert_count, int) and culvert_count != culvert_feature_count:
        issues.append(
            ValidationIssue(
                code="culvert_count_mismatch",
                message="metadata.json culvert_count does not match culvert points.",
                path="metadata.json",
                detail={"expected": culvert_count, "found": culvert_feature_count},
            )
        )

    feature_count = (metadata.get("culvert_points") or {}).get("feature_count")
    if isinstance(feature_count, int) and feature_count != culvert_feature_count:
        issues.append(
            ValidationIssue(
                code="feature_count_mismatch",
                message="metadata.json culvert_points.feature_count does not match features.",
                path="metadata.json",
                detail={"expected": feature_count, "found": culvert_feature_count},
            )
        )


def _validate_optional_metadata_int(
    metadata: dict[str, Any],
    key: str,
    issues: list[ValidationIssue],
) -> None:
    if key not in metadata:
        return
    value = metadata.get(key)
    if value is None:
        return
    if isinstance(value, bool):
        issues.append(
            ValidationIssue(
                code="invalid_metadata_field",
                message=f"metadata.json {key} must be an integer.",
                path="metadata.json",
            )
        )
        return
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        issues.append(
            ValidationIssue(
                code="invalid_metadata_field",
                message=f"metadata.json {key} must be an integer.",
                path="metadata.json",
            )
        )
        return
    if parsed < 0:
        issues.append(
            ValidationIssue(
                code="invalid_metadata_field",
                message=f"metadata.json {key} must be >= 0.",
                path="metadata.json",
            )
        )


def _validate_optional_model_param_str(
    model_params: dict[str, Any],
    key: str,
    issues: list[ValidationIssue],
) -> None:
    if key not in model_params:
        return
    value = model_params.get(key)
    if value is None:
        return
    if not isinstance(value, str) or value.strip() == "":
        issues.append(
            ValidationIssue(
                code="invalid_model_param",
                message=f"model-parameters.json {key} must be a non-empty string.",
                path="model-parameters.json",
            )
        )


def _validate_optional_model_param_int(
    model_params: dict[str, Any],
    key: str,
    issues: list[ValidationIssue],
) -> None:
    if key not in model_params:
        return
    value = model_params.get(key)
    if value is None:
        return
    if isinstance(value, bool):
        issues.append(
            ValidationIssue(
                code="invalid_model_param",
                message=f"model-parameters.json {key} must be an integer.",
                path="model-parameters.json",
            )
        )
        return
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        issues.append(
            ValidationIssue(
                code="invalid_model_param",
                message=f"model-parameters.json {key} must be an integer.",
                path="model-parameters.json",
            )
        )
        return
    if parsed < 0:
        issues.append(
            ValidationIssue(
                code="invalid_model_param",
                message=f"model-parameters.json {key} must be >= 0.",
                path="model-parameters.json",
            )
        )


def _validate_geojson_geometry(
    collection: dict[str, Any],
    expected: set[str],
    issues: list[ValidationIssue],
    relpath: str,
) -> None:
    features = collection.get("features")
    if not isinstance(features, list):
        return
    for idx, feature in enumerate(features):
        geometry = (feature or {}).get("geometry") or {}
        geom_type = geometry.get("type")
        if geom_type not in expected:
            issues.append(
                ValidationIssue(
                    code="invalid_geometry_type",
                    message=f"GeoJSON geometry must be one of {sorted(expected)}.",
                    path=relpath,
                    detail={"feature_index": idx, "found": geom_type},
                )
            )


def _extract_point_ids(
    collection: dict[str, Any],
    field: str,
    issues: list[ValidationIssue],
    relpath: str,
) -> tuple[set[str], int]:
    features = collection.get("features")
    if not isinstance(features, list):
        issues.append(
            ValidationIssue(
                code="invalid_geojson",
                message="GeoJSON features must be a list.",
                path=relpath,
            )
        )
        return set(), 0

    feature_count = len(features)
    point_ids: set[str] = set()
    counts: dict[str, int] = {}
    for idx, feature in enumerate(features):
        props = (feature or {}).get("properties") or {}
        if field not in props:
            issues.append(
                ValidationIssue(
                    code="missing_point_id",
                    message=f"Feature missing {field} property.",
                    path=relpath,
                    detail={"feature_index": idx},
                )
            )
            continue
        value = props.get(field)
        if value is None or value == "":
            issues.append(
                ValidationIssue(
                    code="invalid_point_id",
                    message=f"Feature {field} property is empty.",
                    path=relpath,
                    detail={"feature_index": idx},
                )
            )
            continue
        value_str = str(value)
        invalid_reason = _invalid_point_id(value_str)
        if invalid_reason:
            issues.append(
                ValidationIssue(
                    code="invalid_point_id",
                    message=f"{field} value is invalid.",
                    path=relpath,
                    detail={
                        "feature_index": idx,
                        "value": value_str,
                        "reason": invalid_reason,
                    },
                )
            )
            continue
        counts[value_str] = counts.get(value_str, 0) + 1
        point_ids.add(value_str)

    duplicates = sorted(pid for pid, count in counts.items() if count > 1)
    if duplicates:
        issues.append(
            ValidationIssue(
                code="duplicate_point_id",
                message=f"Duplicate {field} values detected.",
                path=relpath,
                detail={"count": len(duplicates), "sample": duplicates[:10]},
            )
        )

    if not point_ids:
        issues.append(
            ValidationIssue(
                code="missing_point_id",
                message=f"No {field} values found.",
                path=relpath,
            )
        )

    return point_ids, feature_count


def _invalid_point_id(value: str) -> Optional[str]:
    if value in {".", ".."}:
        return "dot_path"
    separators = {"/", "\\", os.sep}
    if os.path.altsep:
        separators.add(os.path.altsep)
    if any(sep for sep in separators if sep and sep in value):
        return "path_separator"
    return None


def _geojson_crs(collection: dict[str, Any], issues: list[ValidationIssue], relpath: str) -> Optional[CRS]:
    crs_obj = collection.get("crs")
    if not crs_obj:
        issues.append(
            ValidationIssue(
                code="missing_crs",
                message="GeoJSON is missing CRS definition.",
                path=relpath,
            )
        )
        return None

    props = crs_obj.get("properties") or {}
    name = props.get("name")
    if not name:
        issues.append(
            ValidationIssue(
                code="missing_crs",
                message="GeoJSON CRS name is missing.",
                path=relpath,
            )
        )
        return None

    return _parse_crs(name, issues, relpath, "crs")


def _raster_crs(path: Path, issues: list[ValidationIssue], relpath: str) -> Optional[CRS]:
    try:
        with rasterio.open(path) as dataset:
            if dataset.crs is None:
                issues.append(
                    ValidationIssue(
                        code="missing_crs",
                        message="Raster CRS is missing.",
                        path=relpath,
                    )
                )
                return None
            return CRS.from_user_input(dataset.crs)
    except (OSError, rasterio.errors.RasterioIOError) as exc:
        issues.append(
            ValidationIssue(
                code="raster_read_failed",
                message="Failed to read raster CRS.",
                path=relpath,
                detail={"error": str(exc)},
            )
        )
        return None


def _parse_crs(
    value: Optional[str],
    issues: list[ValidationIssue],
    relpath: str,
    field: str,
) -> Optional[CRS]:
    if not value:
        return None
    try:
        return CRS.from_user_input(value)
    except Exception as exc:
        issues.append(
            ValidationIssue(
                code="invalid_crs",
                message="CRS could not be parsed.",
                path=relpath,
                detail={"field": field, "error": str(exc)},
            )
        )
        return None


def _crs_is_meter_projected(crs: CRS) -> bool:
    if not crs.is_projected:
        return False
    for axis in crs.axis_info:
        unit = (axis.unit_name or "").lower()
        if unit not in {"metre", "meter", "meters", "metres"}:
            return False
    return True


__all__ = [
    "METADATA_SCHEMA_VERSION",
    "MODEL_PARAMS_SCHEMA_VERSION",
    "POINT_ID_FIELD",
    "REQUIRED_PAYLOAD_PATHS",
    "ValidationIssue",
    "format_validation_errors",
    "validate_payload_root",
    "validate_zip_members",
]
