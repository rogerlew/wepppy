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

        climate.set_observed_pars(
            **dict(
                start_year=kwds["observed_start_year"],
                end_year=kwds["observed_end_year"],
            )
        )

        climate.set_future_pars(
            **dict(
                start_year=kwds["future_start_year"],
                end_year=kwds["future_end_year"],
            )
        )

        if climate_mode in (
            ClimateMode.SingleStorm,
            ClimateMode.SingleStormBatch,
            ClimateMode.UserDefinedSingleStorm,
        ):
            climate.set_single_storm_pars(**kwds)
