from __future__ import annotations

from os.path import exists as _exists
from typing import TYPE_CHECKING, Any

from wepppy.all_your_base import isfloat, isint

if TYPE_CHECKING:
    from wepppy.nodb.core.climate import Climate


class ClimateInputParsingService:
    """Parse and validate incoming climate payloads for the ``Climate`` facade."""

    def parse_inputs(self, climate: "Climate", kwds: dict[str, Any]) -> None:
        climate_mode = self._parse_core_inputs(climate, kwds)
        self._parse_mode_specific_inputs(climate, kwds, climate_mode)

    def _parse_core_inputs(self, climate: "Climate", kwds: dict[str, Any]) -> Any:
        from wepppy.nodb.core.climate import (
            CLIMATE_MAX_YEARS,
            ClimateMode,
            ClimatePrecipScalingMode,
            ClimateSpatialMode,
            _assert_supported_climate_mode,
        )

        with climate.locked():
            raw_climate_mode = kwds.get("climate_mode")
            catalog_id = kwds.get("climate_catalog_id") or kwds.get("catalog_id")
            catalog_dataset = None
            if catalog_id:
                catalog_dataset = climate._resolve_catalog_dataset(str(catalog_id))
                if catalog_dataset is None:
                    raise ValueError(f"Unknown or unavailable climate catalog id: {catalog_id}")
                climate_mode = ClimateMode(int(catalog_dataset.climate_mode))
                climate._catalog_id = catalog_dataset.catalog_id
            else:
                if raw_climate_mode is None:
                    raise ValueError("climate_mode not provided")
                climate_mode = ClimateMode(int(raw_climate_mode))
                climate._catalog_id = None
            _assert_supported_climate_mode(climate_mode)

            climate_spatialmode = kwds.get("climate_spatialmode", ClimateSpatialMode.Single)
            if catalog_dataset is not None:
                if climate_spatialmode in (None, "", "None"):
                    climate_spatialmode = catalog_dataset.default_spatial_mode
                spatialmode_value = int(climate_spatialmode)
                if catalog_dataset.spatial_modes and spatialmode_value not in catalog_dataset.spatial_modes:
                    raise ValueError(
                        f"Unsupported spatial mode {spatialmode_value} for catalog dataset {catalog_dataset.catalog_id}"
                    )
                climate_spatialmode = ClimateSpatialMode(spatialmode_value)
            else:
                climate_spatialmode = ClimateSpatialMode(int(climate_spatialmode))

            if climate_mode == ClimateMode.SingleStorm:
                climate_spatialmode = ClimateSpatialMode.Single

            input_years = kwds.get("input_years", None)
            if isint(input_years):
                input_years = int(input_years)

            if climate_mode in [ClimateMode.Vanilla]:
                assert isint(input_years)
                assert input_years > 0
                assert input_years <= CLIMATE_MAX_YEARS

            if climate_mode in [ClimateMode.ObservedDb, ClimateMode.FutureDb]:
                if climate_mode == ClimateMode.ObservedDb:
                    cli_path = kwds["climate_observed_selection"]
                else:
                    cli_path = kwds["climate_future_selection"]
                assert _exists(cli_path)
                climate._orig_cli_fn = cli_path

            validator = getattr(climate, "_validate_station_catalog_constraints", None)
            if callable(validator):
                validator(
                    climate_mode=climate_mode,
                    climate_spatialmode=climate_spatialmode,
                )

            climate._climate_mode = climate_mode
            climate._climate_spatialmode = climate_spatialmode
            climate._input_years = input_years

            climate._climate_daily_temp_ds = kwds.get("climate_daily_temp_ds", None)

            if kwds.get("precip_scaling_mode", None) is not None:
                climate._precip_scaling_mode = ClimatePrecipScalingMode(int(kwds["precip_scaling_mode"]))

            if kwds.get("precip_scale_factor", None) is not None:
                if isfloat(kwds["precip_scale_factor"]):
                    climate._precip_scale_factor = float(kwds["precip_scale_factor"])

            if kwds.get("precip_monthly_scale_factors_7", None) is not None:
                precip_monthly_scale_factors = []
                for i in range(12):
                    v = None
                    try:
                        v = float(kwds.get(f"precip_monthly_scale_factors_{i}"))
                        if v < 0.0:
                            v = 0.0
                    except ValueError:
                        pass
                    if v is not None:
                        precip_monthly_scale_factors.append(float(v))

                climate._precip_monthly_scale_factors = precip_monthly_scale_factors

            if kwds.get("precip_scale_reference", None) is not None:
                climate._precip_scaling_reference = kwds["precip_scale_reference"]

            if kwds.get("precip_scale_factor_map", None) is not None:
                climate._precip_scale_factor_map = kwds["precip_scale_factor_map"]

        return climate_mode

    def _parse_mode_specific_inputs(
        self,
        climate: "Climate",
        kwds: dict[str, Any],
        climate_mode: Any,
    ) -> None:
        from wepppy.nodb.core.climate import ClimateMode

        observed_required_modes = {
            ClimateMode.Observed,
            ClimateMode.ObservedPRISM,
            ClimateMode.GridMetPRISM,
            ClimateMode.DepNexrad,
        }
        future_required_modes = {
            ClimateMode.Future,
        }

        if climate_mode in future_required_modes:
            future_pars = self._resolve_year_bounds(
                kwds=kwds,
                start_key="future_start_year",
                end_key="future_end_year",
                required=True,
            )
            self._clear_year_bounds(
                climate=climate,
                start_attr="_observed_start_year",
                end_attr="_observed_end_year",
            )
            climate.set_future_pars(**future_pars)
        else:
            observed_pars = self._resolve_year_bounds(
                kwds=kwds,
                start_key="observed_start_year",
                end_key="observed_end_year",
                required=climate_mode in observed_required_modes,
            )
            if observed_pars is not None:
                climate.set_observed_pars(**observed_pars)
            else:
                self._clear_year_bounds(
                    climate=climate,
                    start_attr="_observed_start_year",
                    end_attr="_observed_end_year",
                )
            self._clear_year_bounds(
                climate=climate,
                start_attr="_future_start_year",
                end_attr="_future_end_year",
            )

        if climate_mode in (
            ClimateMode.SingleStorm,
            ClimateMode.SingleStormBatch,
            ClimateMode.UserDefinedSingleStorm,
        ):
            single_storm_required_fields = (
                "ss_storm_date",
                "ss_design_storm_amount_inches",
                "ss_duration_of_storm_in_hours",
                "ss_time_to_peak_intensity_pct",
                "ss_max_intensity_inches_per_hour",
            )
            missing = [
                field
                for field in single_storm_required_fields
                if kwds.get(field) in (None, "")
            ]
            if missing:
                raise ValueError(
                    f"Missing required climate field(s): {', '.join(missing)}"
                )
            single_storm_payload = dict(kwds)
            single_storm_payload.setdefault("ss_batch", "")
            climate.set_single_storm_pars(**single_storm_payload)

    @staticmethod
    def _resolve_year_bounds(
        *,
        kwds: dict[str, Any],
        start_key: str,
        end_key: str,
        required: bool,
    ) -> dict[str, Any] | None:
        start_value = kwds.get(start_key)
        end_value = kwds.get(end_key)

        missing = [
            key
            for key, value in ((start_key, start_value), (end_key, end_value))
            if value in (None, "")
        ]
        if missing:
            if required:
                raise ValueError(f"Missing required climate field(s): {', '.join(missing)}")
            if len(missing) == 1:
                raise ValueError(f"Missing required climate field(s): {', '.join(missing)}")
            return None

        return {
            "start_year": start_value,
            "end_year": end_value,
        }

    @staticmethod
    def _clear_year_bounds(
        *,
        climate: "Climate",
        start_attr: str,
        end_attr: str,
    ) -> None:
        with climate.locked():
            setattr(climate, start_attr, "")
            setattr(climate, end_attr, "")
