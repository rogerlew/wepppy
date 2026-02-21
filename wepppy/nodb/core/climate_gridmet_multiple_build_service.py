from __future__ import annotations

import os
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from os.path import join as _join
from typing import TYPE_CHECKING, Any, Callable

import numpy as np
import pandas as pd

from wepppy.climates.cligen import ClimateFile, Cligen, CligenStationsManager

if TYPE_CHECKING:
    from wepppy.nodb.core.climate import Climate


class ClimateGridmetMultipleBuildService:
    """Build observed GridMET climate files for watershed + hillslopes."""

    def build(
        self,
        climate: "Climate",
        *,
        build_observed_gridmet_interpolated_fn: Callable[..., str],
        ncpu: int,
    ) -> None:
        (
            measure_enum,
            retrieve_nc,
            read_nc,
            interpolate_daily_timeseries_for_location,
            read_nc_longlat,
        ) = self._load_gridmet_client_functions()

        measures = self._build_measures(measure_enum)
        interpolation_spec = self._build_interpolation_spec()

        watershed = climate.watershed_instance
        ws_lng, ws_lat = watershed.centroid
        cli_dir = climate.cli_dir
        start_year, end_year = climate._observed_start_year, climate._observed_end_year
        climate._input_years = end_year - start_year + 1

        station_manager = CligenStationsManager(version=climate.cligen_db)
        station_meta = station_manager.get_station_fromid(climate.climatestation)
        par_fn = station_meta.par
        cligen = Cligen(station_meta, wd=cli_dir)

        hillslope_locations = self._build_hillslope_locations(watershed, ws_lng, ws_lat)
        dates, bbox = self._build_dates_and_bbox(climate, start_year, end_year)
        ndates = len(dates)

        self._retrieve_gridmet_netcdfs(
            retrieve_nc=retrieve_nc,
            measures=measures,
            bbox=bbox,
            start_year=start_year,
            end_year=end_year,
            cli_dir=cli_dir,
            climate=climate,
            ncpu=ncpu,
        )

        raw_data, longitudes, latitudes = self._load_raw_gridmet_data(
            read_nc=read_nc,
            read_nc_longlat=read_nc_longlat,
            measures=measures,
            start_year=start_year,
            end_year=end_year,
            cli_dir=cli_dir,
            ndates=ndates,
        )

        self._interpolate_hillslope_timeseries(
            interpolate_daily_timeseries_for_location=interpolate_daily_timeseries_for_location,
            hillslope_locations=hillslope_locations,
            dates=dates,
            longitudes=longitudes,
            latitudes=latitudes,
            raw_data=raw_data,
            interpolation_spec=interpolation_spec,
            climate=climate,
            start_year=start_year,
            end_year=end_year,
            ncpu=ncpu,
        )

        sub_par_fns, sub_cli_fns, cli_fn = self._build_interpolated_cli_files(
            climate=climate,
            watershed=watershed,
            cligen=cligen,
            ws_lng=ws_lng,
            ws_lat=ws_lat,
            start_year=start_year,
            end_year=end_year,
            cli_dir=cli_dir,
            build_observed_gridmet_interpolated_fn=build_observed_gridmet_interpolated_fn,
            ncpu=ncpu,
        )

        climate_file = ClimateFile(_join(cli_dir, cli_fn))
        climate.monthlies = climate_file.calc_monthlies()
        climate.cli_fn = cli_fn
        climate.par_fn = par_fn
        climate.sub_par_fns = sub_par_fns
        climate.sub_cli_fns = sub_cli_fns

    @staticmethod
    def _load_gridmet_client_functions() -> tuple[Any, Any, Any, Any, Any]:
        from wepppy.climates.gridmet.client import (
            GridMetVariable,
            retrieve_nc,
            read_nc,
            interpolate_daily_timeseries_for_location,
            read_nc_longlat,
        )

        # Keep import behavior consistent with historical implementation.
        import xarray as _unused_xarray  # noqa: F401

        return (
            GridMetVariable,
            retrieve_nc,
            read_nc,
            interpolate_daily_timeseries_for_location,
            read_nc_longlat,
        )

    @staticmethod
    def _build_measures(gridmet_variable: Any) -> list[Any]:
        return [
            gridmet_variable.Precipitation,
            gridmet_variable.MinimumTemperature,
            gridmet_variable.MaximumTemperature,
            gridmet_variable.SurfaceRadiation,
            gridmet_variable.WindDirection,
            gridmet_variable.WindSpeed,
            gridmet_variable.MinimumRelativeHumidity,
            gridmet_variable.MaximumRelativeHumidity,
        ]

    @staticmethod
    def _build_interpolation_spec() -> dict[str, dict[str, Any]]:
        return {
            "pr(mm)": {"method": "cubic", "a_min": 0.0},
            "tmmx(degc)": {"method": "cubic"},
            "tmmn(degc)": {"method": "cubic"},
            "rmin(%)": {"method": "linear"},
            "rmax(%)": {"method": "linear"},
            "srad(Wm-2)": {"method": "linear", "a_min": 0.0},
            "vs(m/s)": {"method": "linear", "a_min": 0.0},
            "th(DegreesClockwisefromnorth)": {"method": "nearest"},
        }

    @staticmethod
    def _build_hillslope_locations(watershed: Any, ws_lng: float, ws_lat: float) -> dict[Any, dict[str, float]]:
        hillslope_locations = {"ws": {"longitude": ws_lng, "latitude": ws_lat}}
        for topaz_id, (_lng, _lat) in watershed.centroid_hillslope_iter():
            _lng, _lat = watershed.hillslope_centroid_lnglat(topaz_id)
            hillslope_locations[topaz_id] = {"longitude": _lng, "latitude": _lat}
        return hillslope_locations

    @staticmethod
    def _build_dates_and_bbox(climate: "Climate", start_year: int, end_year: int) -> tuple[pd.DatetimeIndex, list[float]]:
        extent = climate.ron_instance.extent
        cellsize = 0.04166601298087771
        pad = cellsize * 3
        extent = [extent[0] - pad, extent[1] - pad, extent[2] + pad, extent[3] + pad]
        dates = pd.date_range(f"{start_year}-01-01", f"{end_year}-12-31")
        # bbox = west, north, east, south
        bbox = [extent[0], extent[3], extent[2], extent[1]]
        return dates, bbox

    @staticmethod
    def _worker_count(default_workers: int, ncpu: int) -> int:
        if os.getenv("WEPPPY_NCPU"):
            return min(default_workers, ncpu)
        return default_workers

    def _retrieve_gridmet_netcdfs(
        self,
        *,
        retrieve_nc: Callable[..., Any],
        measures: list[Any],
        bbox: list[float],
        start_year: int,
        end_year: int,
        cli_dir: str,
        climate: "Climate",
        ncpu: int,
    ) -> None:
        workers = self._worker_count(default_workers=12, ncpu=ncpu)
        with ProcessPoolExecutor(max_workers=workers) as executor:
            futures = []
            for measure in measures:
                for year in range(start_year, end_year + 1):
                    futures.append(
                        executor.submit(
                            retrieve_nc,
                            measure,
                            bbox,
                            year,
                            cli_dir,
                            _id=f"{measure}_{year}",
                        )
                    )
            self._wait_for_futures(
                futures=futures,
                climate=climate,
                timeout=60,
                waiting_message="  GridMET retrieval still running after 60 seconds; continuing to wait.",
                executor=executor,
            )

    def _load_raw_gridmet_data(
        self,
        *,
        read_nc: Callable[..., tuple[np.ndarray, str, str]],
        read_nc_longlat: Callable[[str], tuple[np.ndarray, np.ndarray]],
        measures: list[Any],
        start_year: int,
        end_year: int,
        cli_dir: str,
        ndates: int,
    ) -> tuple[dict[str, np.ndarray], np.ndarray, np.ndarray]:
        raw_data: dict[Any, np.ndarray] = {}
        columns: dict[Any, str] = {}
        sample_nc = ""

        for measure in measures:
            date_offset = 0
            for year in range(start_year, end_year + 1):
                nc_path = _join(cli_dir, f"{measure}_{year}.nc")
                sample_nc = nc_path
                ts, abbrv, units = read_nc(nc_path, measure)
                ts = ts.transpose(2, 1, 0)  # reorder to longs, lats, dates
                ts_len = ts.shape[2]

                if year == start_year:
                    ncols = ts.shape[0]
                    nrows = ts.shape[1]
                    raw_data[measure] = np.zeros((ncols, nrows, ndates))
                    columns[measure] = f"{abbrv}({units})"

                raw_data[measure][:, :, date_offset : date_offset + ts_len] = ts
                date_offset += ts_len

        raw_data_with_columns = {columns[k]: v for k, v in raw_data.items()}

        longitudes, latitudes = read_nc_longlat(sample_nc)
        latitudes = latitudes[::-1]
        raw_data_with_columns = {k: v[:, ::-1, :] for k, v in raw_data_with_columns.items()}
        return raw_data_with_columns, longitudes, latitudes

    def _interpolate_hillslope_timeseries(
        self,
        *,
        interpolate_daily_timeseries_for_location: Callable[..., Any],
        hillslope_locations: dict[Any, dict[str, float]],
        dates: pd.DatetimeIndex,
        longitudes: np.ndarray,
        latitudes: np.ndarray,
        raw_data: dict[str, np.ndarray],
        interpolation_spec: dict[str, dict[str, Any]],
        climate: "Climate",
        start_year: int,
        end_year: int,
        ncpu: int,
    ) -> None:
        workers = self._worker_count(default_workers=28, ncpu=ncpu)
        with ProcessPoolExecutor(max_workers=workers) as executor:
            futures = []
            for topaz_id, loc in hillslope_locations.items():
                climate.logger.info(f"  interpolating topaz_id {topaz_id}...")
                futures.append(
                    executor.submit(
                        interpolate_daily_timeseries_for_location,
                        topaz_id,
                        loc,
                        dates,
                        longitudes,
                        latitudes,
                        raw_data,
                        interpolation_spec,
                        climate.cli_dir,
                        start_year,
                        end_year,
                    )
                )

            def _on_done(topaz_id: Any) -> None:
                climate.logger.info(f"  interpolated {topaz_id} done.")

            self._wait_for_futures(
                futures=futures,
                climate=climate,
                timeout=60,
                waiting_message="  GridMET interpolation still running after 60 seconds; continuing to wait.",
                on_done=_on_done,
                executor=executor,
            )

    def _build_interpolated_cli_files(
        self,
        *,
        climate: "Climate",
        watershed: Any,
        cligen: Cligen,
        ws_lng: float,
        ws_lat: float,
        start_year: int,
        end_year: int,
        cli_dir: str,
        build_observed_gridmet_interpolated_fn: Callable[..., str],
        ncpu: int,
    ) -> tuple[dict[Any, str], dict[Any, str], str]:
        sub_par_fns: dict[Any, str] = {}
        sub_cli_fns: dict[Any, str] = {}
        cli_fn = "wepp.cli"

        with ProcessPoolExecutor(max_workers=ncpu) as executor:
            futures = []
            for topaz_id, (_lng, _lat) in watershed.centroid_hillslope_iter():
                _lng, _lat = watershed.hillslope_centroid_lnglat(topaz_id)
                _prn_fn = f"gridmet_observed_{topaz_id}_{start_year}-{end_year}.prn"
                _cli_fn = f"gridmet_observed_{topaz_id}_{start_year}-{end_year}.cli"

                climate.logger.info(f"submitting climate build for {topaz_id} ...")
                futures.append(
                    executor.submit(
                        build_observed_gridmet_interpolated_fn,
                        cligen,
                        topaz_id,
                        _lng,
                        _lat,
                        start_year,
                        end_year,
                        cli_dir,
                        _cli_fn,
                        _prn_fn,
                        adjust_mx_pt5=climate.adjust_mx_pt5,
                    )
                )

                sub_par_fns[topaz_id] = _prn_fn
                sub_cli_fns[topaz_id] = _cli_fn

            ws_topaz_id = "ws"
            ws_prn_fn = f"gridmet_observed_{ws_topaz_id}_{start_year}-{end_year}.prn"
            futures.append(
                executor.submit(
                    build_observed_gridmet_interpolated_fn,
                    cligen,
                    ws_topaz_id,
                    ws_lng,
                    ws_lat,
                    start_year,
                    end_year,
                    cli_dir,
                    cli_fn,
                    ws_prn_fn,
                    adjust_mx_pt5=climate.adjust_mx_pt5,
                )
            )

            def _on_done(completed_topaz: Any) -> None:
                climate.logger.info(f"  climate for {completed_topaz} done.")

            self._wait_for_futures(
                futures=futures,
                climate=climate,
                timeout=60,
                waiting_message="  GridMET climate build still running after 60 seconds; continuing to wait.",
                on_done=_on_done,
                executor=executor,
            )

        return sub_par_fns, sub_cli_fns, cli_fn

    @staticmethod
    def _wait_for_futures(
        *,
        futures: list[Any],
        climate: "Climate",
        timeout: int,
        waiting_message: str,
        on_done: Callable[[Any], None] | None = None,
        executor: ProcessPoolExecutor | None = None,
    ) -> None:
        pending = set(futures)
        try:
            while pending:
                done, pending = wait(pending, timeout=timeout, return_when=FIRST_COMPLETED)
                if not done:
                    climate.logger.warning(waiting_message)
                    continue

                for future in done:
                    result = future.result()
                    if on_done is not None:
                        on_done(result)
        except Exception:
            # Worker-pool boundary: fail fast, cancel pending work, and stop dispatching new tasks.
            for future in futures:
                if not future.done():
                    future.cancel()
            if executor is not None:
                executor.shutdown(wait=False, cancel_futures=True)
            raise
