from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from wepppy.all_your_base.geo import RasterDatasetInterpolator
from wepppy.climates.cligen import CligenStationsManager
from wepppy.nodb.locales.climate_catalog import (
    CLIMATE_SPATIAL_METHOD_RUNTIME,
    CLIMATE_STATION_METHOD_RUNTIME,
)

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
        from wepppy.nodb.locales import available_climate_datasets, iter_climate_datasets
        from wepppy.nodb.project_config_capabilities import (
            resolve_run_capability_authority,
        )

        run_authority = resolve_run_capability_authority(climate)
        authority = run_authority.graph
        if authority is None:
            locales = run_authority.runtime_tokens or tuple(climate.locales or ())
            mods = climate.ron_instance.mods or []
            datasets = available_climate_datasets(locales, mods, include_hidden=include_hidden)
            from wepppy.nodb.project_config_capabilities import capability_ids

            allowed = capability_ids(climate, "climate_datasets")
            if allowed is not None:
                datasets = [dataset for dataset in datasets if dataset.catalog_id in allowed]
        else:
            allowed = set(authority.climate_datasets)
            datasets = [
                dataset
                for dataset in iter_climate_datasets()
                if dataset.catalog_id in allowed
                and (include_hidden or dataset.ui_exposed)
            ]
            datasets = [
                replace(
                    dataset,
                    station_modes=tuple(
                        CLIMATE_STATION_METHOD_RUNTIME[item]
                        for item in authority.climate_station_methods_by_dataset[dataset.catalog_id]
                    ),
                    default_station_mode=CLIMATE_STATION_METHOD_RUNTIME[
                        authority.climate_station_defaults[dataset.catalog_id]
                    ],
                    spatial_modes=tuple(
                        CLIMATE_SPATIAL_METHOD_RUNTIME[item]
                        for item in authority.climate_spatial_methods_by_dataset[dataset.catalog_id]
                    ),
                    default_spatial_mode=CLIMATE_SPATIAL_METHOD_RUNTIME[
                        authority.climate_spatial_defaults[dataset.catalog_id]
                    ],
                )
                for dataset in datasets
            ]

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
        from wepppy.nodb.project_config_capabilities import (
            resolve_run_capability_authority,
        )

        if catalog_id is None:
            return None

        dataset = get_climate_dataset(catalog_id)
        if dataset is None:
            return None

        run_authority = resolve_run_capability_authority(climate)
        authority = run_authority.graph
        if authority is not None:
            if dataset.catalog_id not in authority.climate_datasets:
                # Compatibility carveout: an ordinary build may consume the
                # exact persisted selection even after authority stops
                # advertising it. Presentation still uses
                # available_catalog_datasets(), so this does not make the
                # omitted dataset selectable again.
                if dataset.catalog_id != climate.catalog_id:
                    return None
                return self._apply_runtime_constraints(climate, dataset)
            return next(
                (
                    item
                    for item in self.available_catalog_datasets(
                        climate, include_hidden=True
                    )
                    if item.catalog_id == dataset.catalog_id
                ),
                None,
            )

        locales = run_authority.runtime_tokens or tuple(climate.locales or ())
        mods = climate.ron_instance.mods or []
        if not dataset.is_allowed_for(locales, mods, include_hidden=include_hidden):
            return None
        from wepppy.nodb.project_config_capabilities import capability_ids

        allowed = capability_ids(climate, "climate_datasets")
        if allowed is not None and dataset.catalog_id not in allowed:
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
            lng, lat = watershed.require_centroid()
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

        from wepppy.nodb.project_config_capabilities import (
            resolve_run_capability_authority,
        )

        run_authority = resolve_run_capability_authority(climate)
        effective_locales = run_authority.runtime_tokens or tuple(climate.locales or ())
        if "eu" in effective_locales:
            return self.find_eu_heuristic_stations(climate, num_stations=num_stations)
        if "au" in effective_locales:
            return self.find_au_heuristic_stations(climate, num_stations=num_stations)

        with climate.locked():
            watershed = climate.watershed_instance
            lng, lat = watershed.require_centroid()
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
            lng, lat = watershed.require_centroid()
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
            lng, lat = watershed.require_centroid()
            ron = climate.ron_instance

            rdi = RasterDatasetInterpolator(ron.dem_fn)
            elev = rdi.get_location_info(lng, lat, method="near")

            station_manager = CligenStationsManager(version=climate.cligen_db)
            results = station_manager.get_stations_au_heuristic_search((lng, lat), elev, num_stations)
            climate._heuristic_stations = results
            climate._climatestation = results[0].id
            return climate.heuristic_stations
