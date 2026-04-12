"""Subprocess worker for parsing shapefile features via Fiona/GDAL."""

from __future__ import annotations

import argparse
import collections.abc as cabc
import pickle
import sys
from pathlib import Path

import fiona
import fiona.errors as fiona_errors

from .crs import parse_source_crs

_PARSER_GDAL_OPTIONS = {
    "CPL_VSIL_CURL_ALLOWED_EXTENSIONS": "",
    "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
    "GDAL_HTTP_MAX_RETRY": "0",
}
_ALLOWED_OGR_DRIVERS = ["ESRI Shapefile"]


def _load_shapefile_payload(*, shp_path: Path, max_features: int) -> dict[str, object]:
    if shp_path.suffix.lower() != ".shp":
        raise ValueError(f"Expected .shp input but received '{shp_path.name}'.")

    properties: list[dict[str, object]] = []
    geometries: list[dict[str, object] | None] = []

    try:
        with fiona.Env(**_PARSER_GDAL_OPTIONS):
            with fiona.open(
                shp_path.as_posix(),
                enabled_drivers=_ALLOWED_OGR_DRIVERS,
            ) as dataset:
                raw_bounds = dataset.bounds
                source_bounds = (
                    float(raw_bounds[0]),
                    float(raw_bounds[1]),
                    float(raw_bounds[2]),
                    float(raw_bounds[3]),
                )
                source_crs = parse_source_crs(
                    crs_wkt=getattr(dataset, "crs_wkt", None),
                    crs_mapping=getattr(dataset, "crs", None),
                )

                for index, feature in enumerate(dataset):
                    if not isinstance(feature, cabc.Mapping):
                        raise ValueError(f"Feature at index {index} is not an object.")

                    raw_properties = feature.get("properties")
                    if raw_properties is None:
                        normalized_properties: dict[str, object] = {}
                    elif isinstance(raw_properties, cabc.Mapping):
                        normalized_properties = {
                            str(key): value for key, value in raw_properties.items()
                        }
                    else:
                        normalized_properties = {
                            str(key): value for key, value in dict(raw_properties).items()
                        }

                    geometry_payload = feature.get("geometry")
                    if geometry_payload is None:
                        normalized_geometry = None
                    elif isinstance(geometry_payload, cabc.Mapping):
                        normalized_geometry = dict(geometry_payload)
                    else:
                        raise ValueError(
                            f"Feature at index {index} has non-object geometry payload."
                        )

                    properties.append(normalized_properties)
                    geometries.append(normalized_geometry)

                    if len(properties) > max_features:
                        raise OverflowError(
                            f"Feature count exceeded limit {max_features} while reading shapefile."
                        )
    except (fiona_errors.FionaError, OSError, RuntimeError, ValueError, TypeError) as exc:
        raise ValueError(str(exc)) from exc

    source_crs_wkt: str | None = source_crs.to_wkt() if source_crs is not None else None
    return {
        "properties": properties,
        "geometries": geometries,
        "source_bounds": source_bounds,
        "source_crs_wkt": source_crs_wkt,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="shape-converter-parser-worker",
        description="Parse shapefile features in an isolated subprocess.",
    )
    parser.add_argument("--shp-path", required=True)
    parser.add_argument("--output-path", required=True)
    parser.add_argument("--max-features", required=True, type=int)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    shp_path = Path(args.shp_path)
    output_path = Path(args.output_path)
    max_features = int(args.max_features)
    if max_features < 1:
        print("--max-features must be >= 1", file=sys.stderr)
        return 2

    try:
        payload = _load_shapefile_payload(
            shp_path=shp_path,
            max_features=max_features,
        )
    except Exception as exc:  # noqa: BLE001
        # Worker boundary: parent maps this stderr text into canonical API errors.
        print(str(exc), file=sys.stderr)
        return 1

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("wb") as handle:
            pickle.dump(payload, handle, protocol=pickle.HIGHEST_PROTOCOL)
    except OSError as exc:
        print(f"Failed to write parser payload: {exc}", file=sys.stderr)
        return 3

    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["main", "_load_shapefile_payload"]
