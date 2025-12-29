#!/usr/bin/env python3
"""Smoke test for Climate Engine OpenET timeseries endpoints."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import requests

DEFAULT_GEOJSON = (
    "/wc1/runs/rl/rlew-tortious-snake/dem/topaz/SUBCATCHMENTS.WGS.JSON"
)

TIME_SERIES_URL = "https://api.climateengine.org/timeseries/native/coordinates"
METADATA_VARIABLES_URL = "https://api.climateengine.org/metadata/dataset_variables"
METADATA_DATES_URL = "https://api.climateengine.org/metadata/dataset_dates"

DATASETS: Dict[str, Dict[str, Any]] = {
    "ensemble": {
        "id": "OPENET_CONUS",
        "variables": ["et_ensemble_mad"],
        "description": "OpenET Ensemble Median (MAD)"
    },
    "eemetric": {
        "id": "OPENET_CONUS",
        "variables": ["et_eemetric"],
        "description": "OpenET eeMETRIC model"
    },
    "ssebop": {
        "id": "OPENET_CONUS",
        "variables": ["et_ssebop"],
        "description": "OpenET SSEBop model"
    },
}


def _find_env_file() -> Path | None:
    for base in [Path.cwd(), *Path(__file__).resolve().parents]:
        candidate = base / "docker" / ".env"
        if candidate.exists():
            return candidate
    return None


def _load_api_key() -> str:
    api_key = os.environ.get("CLIMATE_ENGINE_API_KEY")
    if api_key:
        return api_key

    env_path = _find_env_file()
    if env_path:
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            if key.strip() == "CLIMATE_ENGINE_API_KEY":
                return value.strip().strip("'\"")

    raise RuntimeError(
        "Missing CLIMATE_ENGINE_API_KEY. Export it or add it to docker/.env."
    )


def _parse_year(value: Any) -> int | None:
    if value is None:
        return None
    text = str(value)
    digits = "".join(ch for ch in text if ch.isdigit())
    if len(digits) < 4:
        return None
    return int(digits[:4])


def _fetch_json(
    session: requests.Session, url: str, headers: Dict[str, str], params: Dict[str, Any]
) -> Dict[str, Any]:
    response = session.get(url, headers=headers, params=params, timeout=60)
    response.raise_for_status()
    return response.json()


def _validate_dataset(
    session: requests.Session,
    headers: Dict[str, str],
    dataset_key: str,
    dataset_id: str,
    variables: List[str],
    start_date: str,
    end_date: str,
) -> None:
    meta_vars = _fetch_json(
        session, METADATA_VARIABLES_URL, headers, {"dataset": dataset_id}
    )
    available_vars = set(meta_vars.get("Data", {}).get("variables", []))
    missing = [var for var in variables if var not in available_vars]
    if missing:
        raise RuntimeError(
            f"{dataset_key}: missing variables {missing} (available: {sorted(available_vars)})"
        )

    meta_dates = _fetch_json(
        session, METADATA_DATES_URL, headers, {"dataset": dataset_id}
    )
    date_min = _parse_year(meta_dates.get("Data", {}).get("min"))
    date_max = _parse_year(meta_dates.get("Data", {}).get("max"))
    if date_min and date_max:
        start_year = _parse_year(start_date)
        end_year = _parse_year(end_date)
        if start_year and end_year:
            if start_year < date_min or end_year > date_max:
                raise RuntimeError(
                    f"{dataset_key}: requested {start_year}-{end_year} outside {date_min}-{date_max}"
                )
    print(f"{dataset_key}: metadata ok (variables={variables})")


def _normalize_topaz_id(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return str(value)


def _load_features(path: str, limit: int, skip_channels: bool) -> List[Tuple[str, Any]]:
    geojson = json.loads(Path(path).read_text(encoding="utf-8"))
    features = geojson.get("features", [])
    selected: List[Tuple[str, Any]] = []

    for feature in features:
        props = feature.get("properties", {})
        geometry = feature.get("geometry", {})
        coords = geometry.get("coordinates")
        if not coords:
            continue
        topaz_id = _normalize_topaz_id(
            props.get("TopazID", props.get("topaz_id", props.get("TOPAZ_ID")))
        )
        label = topaz_id or f"feature_{len(selected)}"
        if skip_channels and topaz_id and topaz_id.endswith("4"):
            continue
        selected.append((label, coords))
        if limit and len(selected) >= limit:
            break

    if not selected:
        raise RuntimeError("No polygon features found for smoke test.")
    return selected


def _fetch_timeseries(
    session: requests.Session,
    headers: Dict[str, str],
    dataset_id: str,
    variable: str,
    start_date: str,
    end_date: str,
    area_reducer: str,
    coordinates: Any,
) -> Dict[str, Any]:
    params = {
        "dataset": dataset_id,
        "variable": variable,
        "start_date": start_date,
        "end_date": end_date,
        "area_reducer": area_reducer,
        "coordinates": json.dumps(coordinates),
    }
    response = session.get(
        TIME_SERIES_URL, headers=headers, params=params, timeout=120
    )
    response.raise_for_status()
    return response.json()


def _summarize_timeseries(
    dataset_key: str, topaz_id: str, variable: str, payload: Dict[str, Any]
) -> None:
    data_list = payload.get("Data") or []
    if not data_list:
        raise RuntimeError(f"{dataset_key}:{topaz_id} missing Data payload")
    rows = data_list[0].get("Data", []) if isinstance(data_list[0], dict) else []
    if not rows:
        raise RuntimeError(f"{dataset_key}:{topaz_id} returned 0 rows")

    # Find the actual variable key (may include units like "eto (mm)")
    sample_row = rows[0]
    var_key = None
    for key in sample_row.keys():
        if key.startswith(variable):
            var_key = key
            break

    if not var_key:
        raise RuntimeError(f"{dataset_key}:{topaz_id} variable {variable} not found in response keys: {list(sample_row.keys())}")

    values = [row.get(var_key) for row in rows]
    missing = sum(1 for value in values if value in (None, -9999))
    non_null_vals = [v for v in values if v not in (None, -9999)]
    avg = sum(non_null_vals) / len(non_null_vals) if non_null_vals else 0
    sample_date = rows[0].get("Date")
    print(
        f"{dataset_key}:{topaz_id} rows={len(rows)} missing={missing} avg={avg:.2f} sample={non_null_vals[:3] if non_null_vals else []} sample_date={sample_date}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Smoke test Climate Engine OpenET datasets."
    )
    parser.add_argument("--geojson", default=DEFAULT_GEOJSON)
    parser.add_argument("--limit", type=int, default=2)
    parser.add_argument("--start-date", default="2020-01-01")
    parser.add_argument("--end-date", default="2020-12-31")
    parser.add_argument("--area-reducer", default="median")
    parser.add_argument(
        "--dataset",
        action="append",
        choices=sorted(DATASETS.keys()),
        help="Limit datasets (repeatable).",
    )
    parser.add_argument(
        "--include-channels", action="store_true", help="Do not skip channel ids."
    )
    args = parser.parse_args()

    api_key = _load_api_key()
    headers = {"Accept": "application/json", "Authorization": api_key}

    datasets = args.dataset or list(DATASETS.keys())
    start_date = args.start_date
    end_date = args.end_date

    try:
        datetime.strptime(start_date, "%Y-%m-%d")
        datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError as exc:
        raise RuntimeError("Dates must be YYYY-MM-DD.") from exc

    with requests.Session() as session:
        for dataset_key in datasets:
            dataset = DATASETS[dataset_key]
            _validate_dataset(
                session=session,
                headers=headers,
                dataset_key=dataset_key,
                dataset_id=dataset["id"],
                variables=dataset["variables"],
                start_date=start_date,
                end_date=end_date,
            )

        features = _load_features(
            path=args.geojson,
            limit=args.limit,
            skip_channels=not args.include_channels,
        )

        for dataset_key in datasets:
            dataset = DATASETS[dataset_key]
            dataset_id = dataset["id"]
            variable = dataset["variables"][0]
            for topaz_id, coords in features:
                payload = _fetch_timeseries(
                    session=session,
                    headers=headers,
                    dataset_id=dataset_id,
                    variable=variable,
                    start_date=start_date,
                    end_date=end_date,
                    area_reducer=args.area_reducer,
                    coordinates=coords,
                )
                _summarize_timeseries(dataset_key, topaz_id, variable, payload)

    print("Smoke test completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
