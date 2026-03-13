from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from wepppy.all_your_base.geo import RasterDatasetInterpolator
from wepppy.climates.cligen import CligenStationsManager

if TYPE_CHECKING:
    from wepppy.nodb.core.climate import Climate


class ClimateStationCatalogService:
    """Resolve climate catalog selections and station metadata/search results."""

    @staticmethod
    def _apply_runtime_constraints(climate: "Climate", dataset: Any) -> Optional[Any]:
        """Apply run-specific dataset constraints before exposing catalog options."""
        if not climate.uses_tenerife_station_catalog:
            return dataset

        # Tenerife is intentionally limited to:
        # - Vanilla station-catalog mode (Single + Auto/Closest)
        # - User-defined CLI uploads (Single only)
        if dataset.catalog_id == "vanilla_cligen":
            return replace(
                dataset,
                spatial_modes=(0,),
                default_spatial_mode=0,
                station_modes=(-1, 0),
            )

        if dataset.catalog_id == "user_defined_cli":
            return replace(
                dataset,
                spatial_modes=(0,),
                default_spatial_mode=0,
                station_modes=(4,),
            )

        return None

    def available_catalog_datasets(self, climate: "Climate", include_hidden: bool = False) -> List[Any]:
        from wepppy.nodb.locales import available_climate_datasets

        locales = climate.locales or ()
        mods = climate.ron_instance.mods or []
        datasets = available_climate_datasets(locales, mods, include_hidden=include_hidden)

        constrained: List[Any] = []
        for dataset in datasets:
            constrained_dataset = self._apply_runtime_constraints(climate, dataset)
            if constrained_dataset is not None:
                constrained.append(constrained_dataset)
        return constrained

    def resolve_catalog_dataset(
        self,
        climate: "Climate",
        catalog_id: str,
        include_hidden: bool = False,
    ) -> Optional[Any]:
        from wepppy.nodb.locales import get_climate_dataset

        if catalog_id is None:
            return None

        dataset = get_climate_dataset(catalog_id)
        if dataset is None:
            return None

        locales = climate.locales or ()
        mods = climate.ron_instance.mods or []
        if not dataset.is_allowed_for(locales, mods, include_hidden=include_hidden):
            return None

        return self._apply_runtime_constraints(climate, dataset)

    def climatestation_meta(self, climate: "Climate") -> Any:
        from wepppy.nodb.core.climate import ClimateMode

        user_station_meta = getattr(climate, "_user_station_meta", None)
        if user_station_meta is not None and (
            climate.catalog_id == "user_defined_cli"
            or climate._climate_mode in (ClimateMode.UserDefined, ClimateMode.UserDefinedSingleStorm)
        ):
            return user_station_meta

        climatestation = climate.climatestation
        if climatestation is None:
            return None

        station_manager = CligenStationsManager(version=climate.cligen_db)
        station_meta = station_manager.get_station_fromid(climatestation)
        assert station_meta is not None
        return station_meta

    def find_closest_stations(
        self,
        climate: "Climate",
        num_stations: int = 10,
    ) -> Optional[List[Dict[str, Any]]]:
        from wepppy.nodb.core.climate import ClimateStationMode

        if climate.islocked() and climate._closest_stations is not None:
            return climate.closest_stations

        with climate.locked():
            watershed = climate.watershed_instance
            centroid = watershed.centroid

            if centroid is None:
                climate.logger.warning("Cannot find closest stations: watershed centroid is not set")
                return None

            lng, lat = centroid
            station_manager = CligenStationsManager(version=climate.cligen_db)
            results = station_manager.get_closest_stations((lng, lat), num_stations)
            climate._closest_stations = results
            climate._climatestation_mode = ClimateStationMode.Closest
            climate._climatestation = results[0].id
            return climate.closest_stations

    def find_heuristic_stations(
        self,
        climate: "Climate",
        num_stations: int = 10,
    ) -> Optional[List[Dict[str, Any]]]:
        if climate.islocked() and climate._heuristic_stations is not None:
            return climate.heuristic_stations

        if "eu" in climate.locales:
            return self.find_eu_heuristic_stations(climate, num_stations=num_stations)
        if "au" in climate.locales:
            return self.find_au_heuristic_stations(climate, num_stations=num_stations)

        with climate.locked():
            watershed = climate.watershed_instance
            lng, lat = watershed.centroid
            station_manager = CligenStationsManager(version=climate.cligen_db)
            results = station_manager.get_stations_heuristic_search((lng, lat), num_stations)
            climate._heuristic_stations = results
            climate._climatestation = results[0].id
            return climate.heuristic_stations

    def find_eu_heuristic_stations(
        self,
        climate: "Climate",
        num_stations: int = 10,
    ) -> Optional[List[Dict[str, Any]]]:
        with climate.locked():
            watershed = climate.watershed_instance
            lng, lat = watershed.centroid
            ron = climate.ron_instance

            rdi = RasterDatasetInterpolator(ron.dem_fn)
            elev = rdi.get_location_info(lng, lat, method="near")

            station_manager = CligenStationsManager(version=climate.cligen_db)
            results = station_manager.get_stations_eu_heuristic_search((lng, lat), elev, num_stations)
            climate._heuristic_stations = results
            climate._climatestation = results[0].id
            return climate.heuristic_stations

    def find_au_heuristic_stations(
        self,
        climate: "Climate",
        num_stations: Optional[int] = None,
    ) -> Optional[List[Dict[str, Any]]]:
        with climate.locked():
            watershed = climate.watershed_instance
            lng, lat = watershed.centroid
            ron = climate.ron_instance

            rdi = RasterDatasetInterpolator(ron.dem_fn)
            elev = rdi.get_location_info(lng, lat, method="near")

            station_manager = CligenStationsManager(version=climate.cligen_db)
            results = station_manager.get_stations_au_heuristic_search((lng, lat), elev, num_stations)
            climate._heuristic_stations = results
            climate._climatestation = results[0].id
            return climate.heuristic_stations
