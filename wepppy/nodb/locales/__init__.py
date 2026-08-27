"""
Locale-specific catalog helpers for NoDb controllers.
"""

from .landuse_catalog import (
    LandcoverCatalogEntry,
    LanduseDataset,
    available_landuse_datasets,
    get_landcover_entry,
    iter_landcover_catalog,
    landcover_catalog_id,
    landcover_catalog_revision,
)
from .climate_catalog import (
    CLIMATE_SPATIAL_METHOD_RUNTIME,
    CLIMATE_STATION_METHOD_RUNTIME,
    ClimateDataset,
    available_climate_datasets,
    climate_catalog_revision,
    get_climate_dataset,
    iter_climate_datasets,
)
from .locale_profiles import (
    LocaleClassification,
    LocaleComposition,
    LocaleProfile,
    LocaleProfileError,
    LocaleSupportState,
    get_locale_profile,
    iter_locale_profiles,
    locale_catalog_revision,
    resolve_locale_composition,
)
from .capability_graph import (
    CAPABILITY_SCHEMA_VERSION,
    CapabilityGraph,
    CapabilityGraphError,
    build_continental_us_capability_graph,
)

__all__ = [
    "LanduseDataset",
    "LandcoverCatalogEntry",
    "available_landuse_datasets",
    "get_landcover_entry",
    "iter_landcover_catalog",
    "landcover_catalog_id",
    "landcover_catalog_revision",
    "ClimateDataset",
    "CLIMATE_SPATIAL_METHOD_RUNTIME",
    "CLIMATE_STATION_METHOD_RUNTIME",
    "available_climate_datasets",
    "climate_catalog_revision",
    "get_climate_dataset",
    "iter_climate_datasets",
    "LocaleClassification",
    "LocaleComposition",
    "LocaleProfile",
    "LocaleProfileError",
    "LocaleSupportState",
    "get_locale_profile",
    "iter_locale_profiles",
    "locale_catalog_revision",
    "resolve_locale_composition",
    "CAPABILITY_SCHEMA_VERSION",
    "CapabilityGraph",
    "CapabilityGraphError",
    "build_continental_us_capability_graph",
]
