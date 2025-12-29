"""OpenET Climate Engine time-series controller for monthly ET."""

from __future__ import annotations

import json
import os
import time
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from os.path import exists as _exists
from os.path import join as _join
from pathlib import Path
from typing import Any, ClassVar, Dict, List, Optional, Tuple

import pandas as pd
import requests

from wepppy.nodb.base import NoDbBase, TriggerEvents, nodb_setter
from wepppy.nodb.core import Climate, ClimateMode, Watershed
from wepppy.nodb.redis_prep import RedisPrep, TaskEnum
from wepppy.query_engine.activate import update_catalog_entry

__all__ = [
    "OpenETNoDbLockedException",
    "OpenET_TS",
]

OPENET_DATASET_ID = "OPENET_CONUS"
OPENET_VARIABLES: Dict[str, str] = {
    "ensemble": "et_ensemble_mad",
    "eemetric": "et_eemetric",
}
OPENET_SOURCE = "climateengine"
OPENET_UNITS_DEFAULT = "mm"
OPENET_API_URL = "https://api.climateengine.org/timeseries/native/coordinates"
OPENET_MAX_WORKERS = 8
OPENET_RETRY_ATTEMPTS = 3
OPENET_RETRY_BACKOFF = 2

OPENET_ALLOWED_CLIMATE_MODES = {
    ClimateMode.Observed,
    ClimateMode.ObservedPRISM,
    ClimateMode.ObservedDb,
    ClimateMode.PRISM,
    ClimateMode.GridMetPRISM,
}


class OpenETNoDbLockedException(Exception):
    pass


def _find_env_file() -> Optional[Path]:
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


def _normalize_topaz_id(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return str(value)


def _matches_variable_key(key: str, variable: str) -> bool:
    return key == variable or key.startswith(variable)


def _extract_units(key: str) -> Optional[str]:
    if "(" not in key or not key.endswith(")"):
        return None
    return key.split("(", 1)[-1].rstrip(")")


def _select_variable_key(sample_row: Dict[str, Any], variable: str) -> Tuple[str, Optional[str]]:
    for key in sample_row:
        if key == "Date":
            continue
        if _matches_variable_key(key, variable):
            return key, _extract_units(key)
    raise KeyError(f"Variable '{variable}' not found in response keys: {list(sample_row.keys())}")


def _parse_timeseries_rows(
    rows: List[Dict[str, Any]],
    *,
    topaz_id: str,
    dataset_key: str,
    dataset_id: str,
    variable: str,
) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(
            columns=[
                "topaz_id",
                "year",
                "month",
                "dataset_key",
                "dataset_id",
                "value",
                "units",
                "source",
            ]
        )

    sample_row = rows[0]
    var_key, units = _select_variable_key(sample_row, variable)

    df = pd.DataFrame(rows)
    df = df.rename(columns={"Date": "date", var_key: "value"})
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df[df["value"].notna()]
    df = df[df["value"] != -9999]
    df["value"] = df["value"].round(4)

    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month
    df["topaz_id"] = str(topaz_id)
    df["dataset_key"] = dataset_key
    df["dataset_id"] = dataset_id
    df["units"] = units or OPENET_UNITS_DEFAULT
    df["source"] = OPENET_SOURCE

    return df[
        [
            "topaz_id",
            "year",
            "month",
            "dataset_key",
            "dataset_id",
            "value",
            "units",
            "source",
        ]
    ]


def _request_timeseries(
    *,
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

    last_exc: Optional[Exception] = None
    for attempt in range(1, OPENET_RETRY_ATTEMPTS + 1):
        try:
            response = requests.get(
                OPENET_API_URL, headers=headers, params=params, timeout=120
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            last_exc = exc
            if attempt < OPENET_RETRY_ATTEMPTS:
                time.sleep(OPENET_RETRY_BACKOFF ** (attempt - 1))
            else:
                raise
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("Unexpected OpenET request failure.")


def _load_subcatchments(path: str, *, skip_channels: bool = True) -> List[Tuple[str, Any]]:
    geojson = json.loads(Path(path).read_text(encoding="utf-8"))
    features = geojson.get("features", [])
    selections: List[Tuple[str, Any]] = []

    for feature in features:
        props = feature.get("properties", {})
        geometry = feature.get("geometry", {})
        coords = geometry.get("coordinates")
        if not coords:
            continue
        topaz_id = _normalize_topaz_id(
            props.get("TopazID", props.get("topaz_id", props.get("TOPAZ_ID")))
        )
        if not topaz_id:
            continue
        if skip_channels and topaz_id.endswith("4"):
            continue
        selections.append((topaz_id, coords))

    return selections


class OpenET_TS(NoDbBase):
    __name__: ClassVar[str] = "OpenET_TS"
    filename: ClassVar[str] = "openet_ts.nodb"

    def __init__(
        self,
        wd: str,
        cfg_fn: str,
        run_group: Optional[str] = None,
        group_name: Optional[str] = None,
    ) -> None:
        super().__init__(wd, cfg_fn, run_group=run_group, group_name=group_name)

        self.data: Optional[pd.DataFrame] = None
        self._openet_start_year: Optional[int] = None
        self._openet_end_year: Optional[int] = None

        with self.locked():
            os.makedirs(self.openet_dir, exist_ok=True)
            self.data = None
            self._openet_start_year = None
            self._openet_end_year = None

    def __getstate__(self) -> Dict[str, Any]:
        super().__getstate__()
        state = self.__dict__.copy()
        if _exists(self.openet_parquet_path):
            state.pop("data", None)
        return state

    @classmethod
    def _post_instance_loaded(cls, instance: "OpenET_TS") -> "OpenET_TS":
        instance = super()._post_instance_loaded(instance)
        if _exists(instance.openet_parquet_path):
            instance.data = pd.read_parquet(instance.openet_parquet_path)
        return instance

    @property
    def openet_start_year(self) -> Optional[int]:
        return self._openet_start_year

    @openet_start_year.setter
    @nodb_setter
    def openet_start_year(self, value: int) -> None:
        self._openet_start_year = value

    @property
    def openet_end_year(self) -> Optional[int]:
        return self._openet_end_year

    @openet_end_year.setter
    @nodb_setter
    def openet_end_year(self, value: int) -> None:
        self._openet_end_year = value

    @property
    def openet_dir(self) -> str:
        return _join(self.wd, "openet")

    @property
    def openet_parquet_path(self) -> str:
        return _join(self.openet_dir, "openet_ts.parquet")

    @property
    def openet_individual_dir(self) -> str:
        return _join(self.openet_dir, "individual")

    def _validate_climate(self, climate: Climate) -> Tuple[int, int]:
        if climate.climate_mode not in OPENET_ALLOWED_CLIMATE_MODES:
            raise ValueError(
                f"OpenET requires observed climate modes; got {climate.climate_mode}."
            )

        try:
            start_year = int(climate.observed_start_year)
            end_year = int(climate.observed_end_year)
        except Exception as exc:
            raise ValueError("Observed climate years are required for OpenET.") from exc

        if end_year < start_year:
            raise ValueError(
                f"Observed end year {end_year} precedes start year {start_year}."
            )

        return start_year, end_year

    def _purge_cache(self) -> None:
        base = Path(self.openet_individual_dir)
        if not base.exists():
            return
        for dataset_key in OPENET_VARIABLES:
            dataset_dir = base / dataset_key
            if not dataset_dir.exists():
                continue
            for parquet_path in dataset_dir.glob("*.parquet"):
                parquet_path.unlink()

    def acquire_timeseries(
        self,
        start_year: Optional[int] = None,
        end_year: Optional[int] = None,
        force_refresh: bool = False,
        max_workers: int = OPENET_MAX_WORKERS,
    ) -> None:
        climate = Climate.getInstance(self.wd)
        climate_start, climate_end = self._validate_climate(climate)
        start_year = climate_start if start_year is None else start_year
        end_year = climate_end if end_year is None else end_year

        if start_year != climate_start or end_year != climate_end:
            raise ValueError(
                f"OpenET years must match observed climate years: {climate_start}-{climate_end}."
            )

        subcatchments_path = Watershed.getInstance(self.wd).subwta_shp
        if not subcatchments_path or not _exists(subcatchments_path):
            raise FileNotFoundError("Subcatchments GeoJSON not found for OpenET.")

        api_key = _load_api_key()
        headers = {"Accept": "application/json", "Authorization": api_key}
        start_date = f"{start_year}-01-01"
        end_date = f"{end_year}-12-31"

        cache_is_current = (
            self._openet_start_year == start_year
            and self._openet_end_year == end_year
            and not force_refresh
        )

        features = _load_subcatchments(subcatchments_path, skip_channels=True)
        if not features:
            raise RuntimeError("No hillslope polygons found for OpenET.")

        with self.locked():
            self._openet_start_year = start_year
            self._openet_end_year = end_year

            if not cache_is_current:
                self._purge_cache()

            os.makedirs(self.openet_individual_dir, exist_ok=True)

            for dataset_key, variable in OPENET_VARIABLES.items():
                dataset_dir = Path(self.openet_individual_dir) / dataset_key
                dataset_dir.mkdir(parents=True, exist_ok=True)
                pending: List[Tuple[str, Any]] = []

                for topaz_id, coords in features:
                    cache_path = dataset_dir / f"{topaz_id}.parquet"
                    if cache_is_current and cache_path.exists():
                        continue
                    pending.append((topaz_id, coords))

                if not pending:
                    continue

                self.logger.info(
                    "OpenET: fetching %d hillslopes for %s", len(pending), dataset_key
                )

                failures: List[Tuple[str, str]] = []
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures: Dict[Future[pd.DataFrame], Tuple[str, Any]] = {}
                    for topaz_id, coords in pending:
                        future = executor.submit(
                            self._fetch_one,
                            headers,
                            dataset_key,
                            variable,
                            start_date,
                            end_date,
                            coords,
                            topaz_id,
                        )
                        futures[future] = (topaz_id, coords)

                    for future in as_completed(futures):
                        topaz_id, _coords = futures[future]
                        try:
                            df = future.result()
                            if df.empty:
                                failures.append((topaz_id, "empty response"))
                                continue
                            cache_path = dataset_dir / f"{topaz_id}.parquet"
                            df.to_parquet(
                                cache_path,
                                engine="pyarrow",
                                compression="snappy",
                                index=False,
                            )
                        except Exception as exc:
                            failures.append((topaz_id, str(exc)))

                if failures:
                    self.logger.warning(
                        "OpenET: %s had %d failures", dataset_key, len(failures)
                    )
                    for topaz_id, message in failures[:10]:
                        self.logger.warning("  %s failed: %s", topaz_id, message)

    def _fetch_one(
        self,
        headers: Dict[str, str],
        dataset_key: str,
        variable: str,
        start_date: str,
        end_date: str,
        coords: Any,
        topaz_id: str,
    ) -> pd.DataFrame:
        payload = _request_timeseries(
            headers=headers,
            dataset_id=OPENET_DATASET_ID,
            variable=variable,
            start_date=start_date,
            end_date=end_date,
            area_reducer="median",
            coordinates=coords,
        )

        data_list = payload.get("Data") if isinstance(payload, dict) else None
        if not data_list:
            raise RuntimeError("OpenET response missing Data list.")
        if not isinstance(data_list[0], dict):
            raise RuntimeError("OpenET response Data format unexpected.")
        rows = data_list[0].get("Data", [])
        return _parse_timeseries_rows(
            rows,
            topaz_id=topaz_id,
            dataset_key=dataset_key,
            dataset_id=OPENET_DATASET_ID,
            variable=variable,
        )

    def analyze(self) -> None:
        start_year = self._openet_start_year
        end_year = self._openet_end_year
        if start_year is None or end_year is None:
            raise ValueError("OpenET start/end years must be set before analysis.")

        frames: List[pd.DataFrame] = []
        base = Path(self.openet_individual_dir)
        for dataset_key in OPENET_VARIABLES:
            dataset_dir = base / dataset_key
            if not dataset_dir.exists():
                continue
            for parquet_path in dataset_dir.glob("*.parquet"):
                df = pd.read_parquet(parquet_path)
                df = df[
                    (df["year"] >= start_year) & (df["year"] <= end_year)
                ]
                if not df.empty:
                    frames.append(df)

        if not frames:
            raise RuntimeError("OpenET analysis found no cached parquet inputs.")

        combined = pd.concat(frames, ignore_index=True)
        combined = combined.sort_values(
            ["dataset_key", "topaz_id", "year", "month"]
        ).reset_index(drop=True)

        with self.locked():
            self.data = combined
            combined.to_parquet(
                self.openet_parquet_path,
                engine="pyarrow",
                compression="snappy",
                index=False,
            )
            update_catalog_entry(self.wd, "openet/openet_ts.parquet")
            prep = RedisPrep.getInstance(self.wd)
            prep.timestamp(TaskEnum.fetch_openet_ts)

    def on(self, evt: TriggerEvents) -> None:
        pass
