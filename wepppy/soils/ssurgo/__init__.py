from __future__ import annotations

"""Public SSURGO/STATSGO helpers used throughout the WEPP stack."""

from .ssurgo import (
    SoilSummary,
    SSURGO_PROJECT_CACHE_FILENAME,
    STATSGO_PROJECT_CACHE_FILENAME,
    SsurgoRequestError,
    SurgoSoilCollection,
    query_mukeys_in_extent,
    surgo_cache_metadata_path,
)
from .fallback import (
    canonical_full_ssurgo_mukey_raster,
    candidate_raster_mukeys,
    categorical_candidate_support,
    categorical_candidate_support_wgs84,
    categorical_value_centroid_wgs84,
    direct_shallow_profile,
    full_ssurgo_candidate_support,
    full_ssurgo_mukey_raster_path,
    load_active_candidate_raster,
    prepare_padded_candidate_raster,
    raw_mukey_source_locations_wgs84,
    select_vector_donor,
)
from .statsgo_spatial import StatsgoSpatial
from .spatializer import SurgoSpatializer, spatial_vars
from .surgo_map import NoValidSoilsException, SurgoMap

__all__ = [
    "canonical_full_ssurgo_mukey_raster",
    "candidate_raster_mukeys",
    "categorical_candidate_support",
    "categorical_candidate_support_wgs84",
    "categorical_value_centroid_wgs84",
    "direct_shallow_profile",
    "NoValidSoilsException",
    "SoilSummary",
    "SSURGO_PROJECT_CACHE_FILENAME",
    "STATSGO_PROJECT_CACHE_FILENAME",
    "SsurgoRequestError",
    "full_ssurgo_candidate_support",
    "full_ssurgo_mukey_raster_path",
    "load_active_candidate_raster",
    "prepare_padded_candidate_raster",
    "raw_mukey_source_locations_wgs84",
    "select_vector_donor",
    "SurgoMap",
    "SurgoSoilCollection",
    "SurgoSpatializer",
    "StatsgoSpatial",
    "query_mukeys_in_extent",
    "spatial_vars",
    "surgo_cache_metadata_path",
]
