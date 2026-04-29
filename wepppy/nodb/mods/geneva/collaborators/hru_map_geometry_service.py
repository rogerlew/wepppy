from __future__ import annotations

import math
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterable, Mapping, Sequence

from wepppy.nodb.mods.geneva.errors import GenevaKernelError

if TYPE_CHECKING:
    from wepppy.nodb.mods.geneva.geneva import Geneva


HRU_MAP_FEATURE_SCHEMA_VERSION = 1
HRU_MAP_FEATURES_RELPATH = "hru_map_features.wgs.geojson"
HRU_MAP_SOURCE_RELPATH = "hru_map.tif"
HRU_MAP_LEGEND_RELPATH = "hru_map_legend.json"


class GenevaHruMapGeometryService:
    """Build and serve run-scoped HRU map vector geometry for deck.gl choropleths."""

    def query_feature_collection(self, geneva: "Geneva") -> dict[str, Any]:
        if not geneva.artifact_io.exists(geneva.wd, HRU_MAP_SOURCE_RELPATH):
            return self._unavailable_payload(
                reason_code="hru_map_missing",
                message="Geneva HRU map raster artifact is not available for this run.",
                artifact_path=f"geneva/{HRU_MAP_SOURCE_RELPATH}",
            )
        if not geneva.artifact_io.exists(geneva.wd, HRU_MAP_LEGEND_RELPATH):
            return self._unavailable_payload(
                reason_code="hru_map_legend_missing",
                message="Geneva HRU map legend artifact is not available for this run.",
                artifact_path=f"geneva/{HRU_MAP_LEGEND_RELPATH}",
            )

        self._ensure_feature_collection_artifact(geneva)
        feature_collection = geneva.artifact_io.read_json(geneva.wd, HRU_MAP_FEATURES_RELPATH)
        if str(feature_collection.get("type", "")) != "FeatureCollection":
            raise GenevaKernelError(
                "Geneva HRU map features artifact must be a FeatureCollection.",
                code="contract_violation",
                details={"artifact": f"geneva/{HRU_MAP_FEATURES_RELPATH}"},
                status_code=500,
            )

        features = feature_collection.get("features")
        if not isinstance(features, list):
            raise GenevaKernelError(
                "Geneva HRU map features artifact must contain a feature list.",
                code="contract_violation",
                details={"artifact": f"geneva/{HRU_MAP_FEATURES_RELPATH}"},
                status_code=500,
            )

        bounds = self._extract_bounds(feature_collection, features)

        return {
            "schema_version": HRU_MAP_FEATURE_SCHEMA_VERSION,
            "availability": {
                "status": "available",
                "reason_code": None,
                "artifact_path": f"geneva/{HRU_MAP_FEATURES_RELPATH}",
            },
            "join_keys": {
                "primary": "hru_value",
                "secondary": "hru_id",
            },
            "feature_collection": feature_collection,
            "feature_count": len(features),
            "bounds_wgs84": bounds,
            "warnings": [],
            "errors": [],
        }

    def _unavailable_payload(
        self,
        *,
        reason_code: str,
        message: str,
        artifact_path: str,
    ) -> dict[str, Any]:
        return {
            "schema_version": HRU_MAP_FEATURE_SCHEMA_VERSION,
            "availability": {
                "status": "unavailable",
                "reason_code": reason_code,
                "artifact_path": artifact_path,
            },
            "join_keys": {
                "primary": "hru_value",
                "secondary": "hru_id",
            },
            "feature_collection": {
                "type": "FeatureCollection",
                "features": [],
            },
            "feature_count": 0,
            "bounds_wgs84": None,
            "warnings": [
                {
                    "code": reason_code,
                    "message": message,
                }
            ],
            "errors": [],
        }

    def _ensure_feature_collection_artifact(self, geneva: "Geneva") -> None:
        source_path = geneva.artifact_io.resolve_path(geneva.wd, HRU_MAP_SOURCE_RELPATH)
        legend_path = geneva.artifact_io.resolve_path(geneva.wd, HRU_MAP_LEGEND_RELPATH)
        feature_path = geneva.artifact_io.resolve_path(geneva.wd, HRU_MAP_FEATURES_RELPATH)

        if feature_path.exists() and not self._is_cache_stale(feature_path, source_path, legend_path):
            return
        self._materialize_feature_collection_from_raster(geneva, source_path=source_path)

    def _is_cache_stale(self, feature_path: Path, source_path: Path, legend_path: Path) -> bool:
        try:
            feature_mtime = feature_path.stat().st_mtime
            return (
                source_path.stat().st_mtime > feature_mtime
                or legend_path.stat().st_mtime > feature_mtime
            )
        except FileNotFoundError:
            return True

    def _materialize_feature_collection_from_raster(
        self,
        geneva: "Geneva",
        *,
        source_path: Path,
    ) -> None:
        try:
            import rasterio
            from rasterio.features import shapes
            from rasterio.warp import transform_geom
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise GenevaKernelError(
                "rasterio is required to build Geneva HRU map vector features.",
                code="contract_violation",
                details=str(exc),
                status_code=500,
            ) from exc

        hru_row_by_value = self._load_hru_row_by_value(geneva)

        features: list[dict[str, Any]] = []
        with rasterio.open(source_path) as dataset:
            band = dataset.read(1, masked=True)
            value_array = band.data if hasattr(band, "data") else band
            mask = (~band.mask) if hasattr(band, "mask") else None
            source_crs = dataset.crs

            for geometry, raw_value in shapes(value_array, mask=mask, transform=dataset.transform):
                hru_value = self._raster_value_to_positive_int(raw_value)
                if hru_value is None:
                    continue

                hru_row = hru_row_by_value.get(hru_value)
                if hru_row is None:
                    raise GenevaKernelError(
                        "Geneva HRU raster contains hru_value with no legend crosswalk.",
                        code="contract_violation",
                        details={"hru_value": hru_value},
                        status_code=500,
                    )

                projected_geometry: dict[str, Any]
                if source_crs:
                    projected_geometry = transform_geom(
                        str(source_crs),
                        "EPSG:4326",
                        geometry,
                        precision=6,
                    )
                else:
                    projected_geometry = geometry

                features.append(
                    {
                        "type": "Feature",
                        "properties": {
                            "hru_value": hru_value,
                            "hru_id": str(hru_row["hru_id"]),
                            "landuse_class": hru_row.get("landuse_class"),
                            "hsg_group": hru_row.get("hsg_group"),
                            "burn_severity_class": hru_row.get("burn_severity_class"),
                            "hydrophobic_class": hru_row.get("hydrophobic_class"),
                            "is_water": hru_row.get("is_water"),
                        },
                        "geometry": projected_geometry,
                    }
                )

        feature_collection: dict[str, Any] = {
            "type": "FeatureCollection",
            "features": features,
        }
        bounds = self._compute_bounds_from_features(features)
        if bounds is not None:
            feature_collection["bbox"] = bounds

        # Route through artifact_io to keep run-scoped path guardrails consistent.
        geneva.artifact_io.write_json(
            geneva.wd,
            HRU_MAP_FEATURES_RELPATH,
            feature_collection,
        )

    def _load_hru_row_by_value(self, geneva: "Geneva") -> dict[int, dict[str, Any]]:
        legend = geneva.artifact_io.read_json(geneva.wd, HRU_MAP_LEGEND_RELPATH)
        rows = legend.get("rows")
        if not isinstance(rows, list):
            raise GenevaKernelError(
                "hru_map_legend rows payload must be a list.",
                code="contract_violation",
                details={"artifact": f"geneva/{HRU_MAP_LEGEND_RELPATH}"},
                status_code=500,
            )

        index: dict[int, dict[str, Any]] = {}
        for row in rows:
            if not isinstance(row, Mapping):
                raise GenevaKernelError(
                    "hru_map_legend rows must be objects.",
                    code="contract_violation",
                    details={"artifact": f"geneva/{HRU_MAP_LEGEND_RELPATH}"},
                    status_code=500,
                )

            hru_id = str(row.get("hru_id") or "").strip()
            if not hru_id:
                raise GenevaKernelError(
                    "hru_map_legend rows must include non-empty hru_id.",
                    code="contract_violation",
                    details={"artifact": f"geneva/{HRU_MAP_LEGEND_RELPATH}"},
                    status_code=500,
                )

            hru_value = self._coerce_positive_int(
                row.get("hru_value"),
                field="hru_map_legend.rows[].hru_value",
            )
            if hru_value in index:
                raise GenevaKernelError(
                    "hru_map_legend contains duplicate hru_value values.",
                    code="contract_violation",
                    details={"hru_value": hru_value},
                    status_code=500,
                )
            index[hru_value] = dict(row)

        return index

    def _extract_bounds(
        self,
        feature_collection: Mapping[str, Any],
        features: list[dict[str, Any]],
    ) -> list[float] | None:
        bbox = feature_collection.get("bbox")
        if self._is_valid_bbox(bbox):
            return [float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])]
        return self._compute_bounds_from_features(features)

    def _compute_bounds_from_features(self, features: Iterable[Mapping[str, Any]]) -> list[float] | None:
        min_x = float("inf")
        min_y = float("inf")
        max_x = float("-inf")
        max_y = float("-inf")

        for feature in features:
            geometry = feature.get("geometry")
            if not isinstance(geometry, Mapping):
                continue
            coordinates = geometry.get("coordinates")
            for x, y in self._iterate_coordinate_pairs(coordinates):
                if x < min_x:
                    min_x = x
                if x > max_x:
                    max_x = x
                if y < min_y:
                    min_y = y
                if y > max_y:
                    max_y = y

        if not all(math.isfinite(value) for value in [min_x, min_y, max_x, max_y]):
            return None
        return [min_x, min_y, max_x, max_y]

    def _iterate_coordinate_pairs(self, coordinates: Any) -> Iterable[tuple[float, float]]:
        if not isinstance(coordinates, Sequence) or isinstance(coordinates, (str, bytes)):
            return []

        if len(coordinates) >= 2 and all(isinstance(value, (int, float)) for value in coordinates[:2]):
            return [(float(coordinates[0]), float(coordinates[1]))]

        pairs: list[tuple[float, float]] = []
        for item in coordinates:
            pairs.extend(self._iterate_coordinate_pairs(item))
        return pairs

    def _raster_value_to_positive_int(self, value: Any) -> int | None:
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            return None
        if not parsed.is_integer():
            return None
        integer = int(parsed)
        if integer <= 0:
            return None
        return integer

    def _coerce_positive_int(self, value: Any, *, field: str) -> int:
        try:
            parsed = int(value)
        except (TypeError, ValueError) as exc:
            raise GenevaKernelError(
                f"{field} must be an integer.",
                code="contract_violation",
                details={"field": field, "value": value},
                status_code=500,
            ) from exc
        if parsed <= 0:
            raise GenevaKernelError(
                f"{field} must be > 0.",
                code="contract_violation",
                details={"field": field, "value": value},
                status_code=500,
            )
        return parsed

    def _is_valid_bbox(self, value: Any) -> bool:
        if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or len(value) != 4:
            return False
        return all(isinstance(item, (int, float)) for item in value)


__all__ = [
    "HRU_MAP_FEATURE_SCHEMA_VERSION",
    "HRU_MAP_FEATURES_RELPATH",
    "HRU_MAP_SOURCE_RELPATH",
    "HRU_MAP_LEGEND_RELPATH",
    "GenevaHruMapGeometryService",
]
