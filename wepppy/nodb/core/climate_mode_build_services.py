from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from wepppy.nodb.core.climate import Climate


class ClimateModeBuildServices:
    """Route climate build requests to mode-specific builder methods."""

    def validate_mode_spatial_compatibility(self, climate: "Climate") -> None:
        from wepppy.nodb.core.climate import ClimateMode, ClimateSpatialMode

        validator = getattr(climate, "_validate_station_catalog_constraints", None)
        if callable(validator):
            validator(
                climate_mode=climate.climate_mode,
                climate_spatialmode=climate.climate_spatialmode,
            )

        if climate.climate_spatialmode == ClimateSpatialMode.MultipleInterpolated:
            if climate.climate_mode not in [ClimateMode.ObservedPRISM, ClimateMode.GridMetPRISM]:
                raise ValueError(
                    "climate_spatialmode is MultipleInterpolated but climate_mode is not "
                    "ObservedPRISM or GridMetPRISM"
                )

    def build_for_mode(
        self,
        climate: "Climate",
        *,
        verbose: bool = False,
        attrs: dict[str, Any] | None = None,
    ) -> None:
        from wepppy.nodb.core.climate import ClimateMode, ClimateSpatialMode, agdc_mod, eobs_mod

        climate_mode = climate.climate_mode

        if climate_mode == ClimateMode.Vanilla:
            climate._build_climate_vanilla(verbose=verbose, attrs=attrs)
            self._run_prism_revision_if_multiple(climate, verbose=verbose)

        elif climate_mode == ClimateMode.ObservedPRISM:
            if climate.climate_spatialmode == ClimateSpatialMode.MultipleInterpolated:
                # Maintains current compatibility behavior for legacy naming.
                climate._build_climate_observed_daymet_multiple(verbose=verbose, attrs=attrs)
            else:
                climate._build_climate_observed_daymet(verbose=verbose, attrs=attrs)
                self._run_prism_revision_if_multiple(climate, verbose=verbose)

        elif climate_mode == ClimateMode.Future:
            climate._build_climate_future(verbose=verbose, attrs=attrs)

        elif climate_mode == ClimateMode.SingleStorm:
            climate._build_climate_single_storm(verbose=verbose, attrs=attrs)

        elif climate_mode == ClimateMode.SingleStormBatch:
            climate._build_climate_single_storm_batch(verbose=verbose, attrs=attrs)

        elif climate_mode == ClimateMode.PRISM:
            climate._build_climate_prism(verbose=verbose, attrs=attrs)
            self._run_prism_revision_if_multiple(climate, verbose=verbose)

        elif climate_mode == ClimateMode.DepNexrad:
            climate._build_climate_depnexrad(verbose=verbose, attrs=attrs)

        elif climate_mode in [ClimateMode.ObservedDb, ClimateMode.FutureDb]:
            assert climate.orig_cli_fn is not None
            climate._post_defined_climate(verbose=verbose, attrs=attrs)
            self._run_prism_revision_if_multiple(climate, verbose=verbose)

        elif climate_mode == ClimateMode.EOBS:
            climate._build_climate_mod(mod_function=eobs_mod, verbose=verbose, attrs=attrs)

        elif climate_mode == ClimateMode.AGDC:
            climate._build_climate_mod(mod_function=agdc_mod, verbose=verbose, attrs=attrs)

        elif climate_mode == ClimateMode.GridMetPRISM:
            if climate.climate_spatialmode == ClimateSpatialMode.MultipleInterpolated:
                climate._build_climate_observed_gridmet_multiple(verbose=verbose, attrs=attrs)
            else:
                climate._build_climate_observed_gridmet(verbose=verbose, attrs=attrs)
                self._run_prism_revision_if_multiple(climate, verbose=verbose)

    @staticmethod
    def _run_prism_revision_if_multiple(climate: "Climate", *, verbose: bool) -> None:
        from wepppy.nodb.core.climate import ClimateSpatialMode

        if climate.climate_spatialmode == ClimateSpatialMode.Multiple:
            climate._prism_revision(verbose=verbose)
