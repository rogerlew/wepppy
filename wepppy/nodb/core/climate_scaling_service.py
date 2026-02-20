from __future__ import annotations

import csv
import os
from os.path import exists as _exists
from os.path import join as _join
from typing import TYPE_CHECKING, Any

from wepppy.all_your_base import isfloat
from wepppy.all_your_base.geo import RasterDatasetInterpolator
from wepppyo3.climate import calculate_monthlies as pyo3_cli_calculate_monthlies
from wepppyo3.climate import calculate_p_annual_monthlies as pyo3_cli_calculate_annual_monthlies
from wepppyo3.climate import rust_cli_p_scale as pyo3_cli_p_scale
from wepppyo3.climate import rust_cli_p_scale_annual_monthlies as pyo3_cli_p_scale_annual_monthlies
from wepppyo3.climate import rust_cli_p_scale_monthlies as pyo3_cli_p_scale_monthlies

if TYPE_CHECKING:
    from wepppy.nodb.core.climate import Climate


class ClimateScalingService:
    """Validate and apply precipitation scaling operations for climate builds."""

    def validate_scaling_inputs(self, climate: "Climate") -> None:
        from wepppy.nodb.core.climate import ClimatePrecipScalingMode

        precip_scaling_mode = climate.precip_scaling_mode
        climate.logger.info(f"  precip_scaling_mode: {precip_scaling_mode}")

        if precip_scaling_mode == ClimatePrecipScalingMode.Scalar:
            climate.logger.info("  precip_scaling_mode is Scalar, validating")
            if climate.precip_scale_factor is None:
                raise ValueError("precip_scale_factor is None")

        elif precip_scaling_mode == ClimatePrecipScalingMode.Spatial:
            climate.logger.info("  precip_scaling_mode is Spatial, validating")
            if climate.precip_scale_factor_map is None:
                raise ValueError("precip_scale_factor_map is None")

        elif precip_scaling_mode == ClimatePrecipScalingMode.Monthlies:
            climate.logger.info("  precip_scaling_mode is Monthlies, validating")
            if climate.precip_monthly_scale_factors is None:
                raise ValueError("precip_monthly_scale_factors is None")

            if len(climate.precip_monthly_scale_factors) != 12:
                raise ValueError("precip_monthly_scale_factors length is not 12")

            for value in climate.precip_monthly_scale_factors:
                if not isfloat(value):
                    raise ValueError("precip_monthly_scale_factors contains non-floats")

        elif precip_scaling_mode == ClimatePrecipScalingMode.AnnualMonthlies:
            climate.logger.info("  precip_scaling_mode is AnnualMonthlies, validating")
            if climate.precip_scaling_reference is None:
                raise ValueError("precip_scaling_reference is None")

            if climate.precip_scaling_reference not in ["prism", "daymet", "gridmet"]:
                raise ValueError("precip_scaling_reference is not prism, daymet, or gridmet")

            if climate.precip_scaling_reference == "prism":
                climate.logger.info("  precip_scaling_reference is prism")
                if climate.observed_start_year < 1981:
                    raise ValueError("prism only available 1981 to present")

        climate.logger.info("  precip_scaling_mode validation passed")

    def apply_scaling(self, climate: "Climate") -> None:
        from wepppy.nodb.core.climate import ClimatePrecipScalingMode

        climate.logger.info("  routing by precip_scaling_mode...")

        if climate.precip_scaling_mode == ClimatePrecipScalingMode.Scalar:
            climate.logger.info("  precip_scaling_mode is Scalar, running _scale_precip")
            assert climate.precip_scale_factor is not None
            climate._scale_precip(climate.precip_scale_factor)

        elif climate.precip_scaling_mode == ClimatePrecipScalingMode.Spatial:
            climate.logger.info("  precip_scaling_mode is Spatial, running _spatial_scale_precip")
            assert climate.precip_scale_factor_map is not None
            climate._spatial_scale_precip(climate.precip_scale_factor_map)

        elif climate.precip_scaling_mode == ClimatePrecipScalingMode.Monthlies:
            climate.logger.info("  precip_scaling_mode is Monthlies, running _scale_precip_monthlies")
            assert climate.precip_monthly_scale_factors is not None
            climate._scale_precip_monthlies(climate.precip_monthly_scale_factors, pyo3_cli_p_scale_monthlies)

        elif climate.precip_scaling_mode == ClimatePrecipScalingMode.AnnualMonthlies:
            self._scale_precip_annual_monthlies(climate)

    def scale_precip(self, climate: "Climate", scale_factor: float) -> None:
        with climate.locked():
            climate.logger.info("  running _scale_precip... ")
            cli_dir = os.path.abspath(climate.cli_dir)

            pyo3_cli_p_scale(
                _join(cli_dir, climate.cli_fn),
                _join(cli_dir, f"scale_{climate.cli_fn}"),
                scale_factor,
            )
            climate.monthlies = pyo3_cli_calculate_monthlies(_join(cli_dir, f"scale_{climate.cli_fn}"))
            climate.cli_fn = f"scale_{climate.cli_fn}"

            if climate.sub_cli_fns is not None:
                sub_cli_fns = {}
                for topaz_id, sub_cli_fn in climate.sub_cli_fns.items():
                    pyo3_cli_p_scale(
                        _join(cli_dir, sub_cli_fn),
                        _join(cli_dir, f"scale_{sub_cli_fn}"),
                        scale_factor,
                    )
                    sub_cli_fns[topaz_id] = f"scale_{sub_cli_fn}"

                climate.sub_cli_fns = sub_cli_fns

    def scale_precip_monthlies(
        self,
        climate: "Climate",
        monthly_scale_factors: list[float],
        scale_func: Any,
    ) -> None:
        with climate.locked():
            climate.logger.info("  running _scale_precip... ")
            cli_dir = os.path.abspath(climate.cli_dir)

            scale_func(
                _join(cli_dir, climate.cli_fn),
                _join(cli_dir, f"scale_{climate.cli_fn}"),
                monthly_scale_factors,
            )
            climate.monthlies = pyo3_cli_calculate_monthlies(_join(cli_dir, f"scale_{climate.cli_fn}"))
            climate.cli_fn = f"scale_{climate.cli_fn}"

            if climate.sub_cli_fns is not None:
                sub_cli_fns = {}
                for topaz_id, sub_cli_fn in climate.sub_cli_fns.items():
                    scale_func(
                        _join(cli_dir, sub_cli_fn),
                        _join(cli_dir, f"scale_{sub_cli_fn}"),
                        monthly_scale_factors,
                    )
                    sub_cli_fns[topaz_id] = f"scale_{sub_cli_fn}"

                climate.sub_cli_fns = sub_cli_fns

    def spatial_scale_precip(self, climate: "Climate", scale_factor_map: str) -> None:
        climate.logger.info(f"  running _spatial_scale_precip with {scale_factor_map} ")

        with climate.locked():
            cli_dir = os.path.abspath(climate.cli_dir)

            assert _exists(scale_factor_map), scale_factor_map
            rdi = RasterDatasetInterpolator(scale_factor_map)

            watershed = climate.watershed_instance
            ws_lng, ws_lat = watershed.centroid
            scale_factor = rdi.get_location_info(ws_lng, ws_lat)

            climate.logger.info(f"    Scaling {climate.cli_fn}")
            climate.logger.info(
                f"      RasterDatasetInterpolator({scale_factor_map}).({ws_lng}, {ws_lat}) -> {scale_factor} "
            )
            if scale_factor is not None:
                if scale_factor > 0.1 and scale_factor < 10.0:
                    climate.logger.info("    pyo3_cli_p_scale() ")
                    pyo3_cli_p_scale(
                        _join(cli_dir, climate.cli_fn),
                        _join(cli_dir, f"scale_{climate.cli_fn}"),
                        scale_factor,
                    )
                    climate.monthlies = pyo3_cli_calculate_monthlies(_join(cli_dir, f"scale_{climate.cli_fn}"))
                    climate.cli_fn = f"scale_{climate.cli_fn}"
                else:
                    climate.logger.info(f"    scale factor {scale_factor} out of range, skipping for {climate.cli_fn}")

            if climate.sub_cli_fns is not None:
                sub_cli_fns = {}
                for topaz_id, sub_cli_fn in climate.sub_cli_fns.items():
                    lng, lat = watershed.hillslope_centroid_lnglat(topaz_id)
                    scale_factor = rdi.get_location_info(lng, lat)

                    climate.logger.info(
                        f"    RasterDatasetInterpolator({scale_factor_map}).({lng}, {lat}) -> {scale_factor} "
                    )
                    if scale_factor is not None:
                        climate.logger.info(f"    scaling {sub_cli_fn} ({lng}, {lat}) -> {scale_factor} ")
                        if scale_factor > 0.1 and scale_factor < 10.0:
                            climate.logger.info("    pyo3_cli_p_scale() ")
                            pyo3_cli_p_scale(
                                _join(cli_dir, sub_cli_fn),
                                _join(cli_dir, f"scale_{sub_cli_fn}"),
                                scale_factor,
                            )
                        else:
                            climate.logger.info(
                                f"    scale factor {scale_factor} out of range, skipping for {sub_cli_fn}"
                            )

                    if _exists(_join(cli_dir, f"scale_{sub_cli_fn}")):
                        sub_cli_fns[topaz_id] = f"scale_{sub_cli_fn}"
                    else:
                        sub_cli_fns[topaz_id] = sub_cli_fn

                climate.sub_cli_fns = sub_cli_fns

    def _scale_precip_annual_monthlies(self, climate: "Climate") -> None:
        from wepppy.nodb.core.climate import (
            get_daymet_p_annual_monthlies,
            get_gridmet_p_annual_monthlies,
            get_prism_p_annual_monthlies,
        )

        climate.logger.info("  precip_scaling_mode is AnnualMonthlies")
        assert climate.precip_scaling_reference in ["prism", "daymet", "gridmet"]

        watershed = climate.watershed_instance
        ws_lng, ws_lat = watershed.centroid
        start_year, end_year = climate.observed_start_year, climate.observed_end_year
        climate.logger.info(f"    reference: {climate.precip_scaling_reference}, years: {start_year}-{end_year}")

        cli_dir = climate.cli_dir
        og_annual_monthlies = pyo3_cli_calculate_annual_monthlies(_join(cli_dir, climate.cli_fn))
        if climate.precip_scaling_reference == "prism":
            climate.logger.info("    getting prism reference data")
            reference_annual_monthlies = get_prism_p_annual_monthlies(ws_lng, ws_lat, start_year, end_year)
        elif climate.precip_scaling_reference == "daymet":
            climate.logger.info("    getting daymet reference data")
            reference_annual_monthlies = get_daymet_p_annual_monthlies(ws_lng, ws_lat, start_year, end_year)
        else:
            climate.logger.info("    getting gridmet reference data")
            reference_annual_monthlies = get_gridmet_p_annual_monthlies(ws_lng, ws_lat, start_year, end_year)

        assert len(og_annual_monthlies) == len(reference_annual_monthlies), (
            len(og_annual_monthlies),
            len(reference_annual_monthlies),
        )

        monthly_scale_factors = []
        climate.logger.info("    calculating monthly scale factors")
        for ref, og in zip(reference_annual_monthlies, og_annual_monthlies):
            if og == 0:
                monthly_scale_factors.append(1.0)
            else:
                monthly_scale_factors.append(ref / og)

        climate.logger.info("    writing reference_annual_monthlies.csv")
        with open(_join(cli_dir, "reference_annual_monthlies.csv"), "w") as fp:
            writer = csv.writer(fp)
            writer.writerow(["Year", "Month", "Reference", "Scale_Factor"])
            year = start_year
            for index, (ref, og, scale) in enumerate(
                zip(reference_annual_monthlies, og_annual_monthlies, monthly_scale_factors)
            ):
                month = (index % 12) + 1
                if index > 0 and index % 12 == 0:
                    year += 1
                writer.writerow([year, month, ref, scale])

        climate.logger.info("    running _scale_precip_monthlies with annual factors")
        climate._scale_precip_monthlies(monthly_scale_factors, pyo3_cli_p_scale_annual_monthlies)
