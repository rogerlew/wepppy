"""Canonical locale profile identities and composition rules.

This module classifies the complete shipped runtime-locale token boundary and
owns the closed dataset axes for every Builder-exposed profile.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
from types import MappingProxyType
from typing import Iterable, Mapping

from wepppy.nodb.locales.climate_catalog import (
    get_climate_dataset,
    get_climate_station_database,
)
from wepppy.nodb.locales.landuse_catalog import get_landcover_entry

__all__ = [
    "LocaleClassification",
    "LocaleComposition",
    "LocaleProfile",
    "LocaleProfileError",
    "LocaleSupportState",
    "get_locale_profile",
    "iter_locale_profiles",
    "locale_catalog_revision",
    "resolve_locale_composition",
    "DEM_SOURCE_RUNTIME",
    "SOIL_SOURCE_RUNTIME",
    "SHIPPED_MOD_IDS",
]


DEM_SOURCE_RUNTIME: Mapping[str, str] = MappingProxyType({
    "usgs-ned1-2024": "ned1/2024",
    "usgs-ned13-2022": "ned13/2022",
    "usgs-ned13-2016": "ned13/2016",
    "australia-srtm-1s": "au/srtm-1s-dem-h",
    "canada-cdem": "ca/ftp.maps.canada.ca/pub/nrcan_rncan/elevation/cdem_mnec",
    "copernicus-dem-30": "copernicus://dem_cop_30",
    "europe-eudem-v1-1": "eu/eu-dem-v1.1",
    "aragon-mdt": "idearagon://mdt",
    "chile-cayumanque-dem": "locales/ChileCayumanque/DEM",
    "hubbar-brook-dem": "locales/hubbar_brook/dem",
    "tenerife-mdt25": "tenerife/136_MDT25_TF",
    "tenerife-mdt05": "tenerife/MDT05_Tenerife",
})

SOIL_SOURCE_RUNTIME: Mapping[str, str | None] = MappingProxyType({
    "ssurgo-gnatsgso-2025": "ssurgo/gNATSGSO/2025",
    "alaska-gsmsoil": "alaska/gsmsoil",
    "hawaii-ssurgo": "hawaii/ssurgo",
    "usvi-soils": "locales/virgin_islands/soils",
    "isric-global": "isric",
    "esdac-europe": None,
    "asris-australia": None,
    "chile-soils": "chile",
    "portland-soils": "portland/soils",
    "chile-cayumanque-soils-map": "locales/ChileCayumanque/soils",
    "tenerife-soils-25m": "LOCALES_DIR/tenerife/soils/tf_soil_25.tif",
    "tenerife-soils-5m": "LOCALES_DIR/tenerife/soils/tf_soil_5.tif",
    "turkey-soils-map": "MODS_DIR/locations/turkey/data/soil_.asc",
    "none-soil-provider": None,
})

SHIPPED_MOD_IDS = frozenset({
    "ag_fields", "ash", "baer", "debris_flow", "disturbed", "general", "lt",
    "omni", "portland", "rangeland_cover", "rap", "rap_ts", "revegetation",
    "rhem", "rred", "seattle", "shrubland", "swat", "treatments", "treecanopy",
    "turkey",
})

_C3S_LANDUSE_IDS = tuple(f"c3s-landcover-{year}" for year in range(2020, 1991, -1))
_OYSTER_CREEK_LANDUSE_IDS = (
    "nlcd-2023", "nlcd-2020", "nlcd-2016", "nlcd-2010", "nlcd-2006",
    "nlcd-2001", "nlcd-1996", "oyster-creek-1993", "oyster-creek-1982",
    "oyster-creek-1975", "oyster-creek-1970", "oyster-creek-1964",
    "oyster-creek-1959",
)


class LocaleProfileError(ValueError):
    """Raised when runtime locale tokens do not identify one valid profile."""


class LocaleClassification(str, Enum):
    BASE = "base"
    OVERLAY = "overlay"
    NON_BUILDER_FAMILY = "non_builder_family"


class LocaleSupportState(str, Enum):
    BUILDER_EXPOSED = "builder_exposed"
    SUPPORTED_NON_BUILDER = "supported_non_builder"
    INVENTORY_ONLY = "inventory_only"
    NON_APPLICABLE = "non_applicable"


@dataclass(frozen=True, slots=True)
class LocaleProfile:
    profile_id: str
    label: str
    runtime_token: str
    classification: LocaleClassification
    support_state: LocaleSupportState
    source_revision: str
    base_profile_id: str | None = None
    overlay_precedence: int | None = None
    dem_sources: tuple[str, ...] = ()
    soil_sources: tuple[str, ...] = ()
    landuse_sources: tuple[str, ...] = ()
    climate_sources: tuple[str, ...] = ()
    climate_station_databases: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class LocaleComposition:
    base: LocaleProfile
    overlays: tuple[LocaleProfile, ...]

    @property
    def profiles(self) -> tuple[LocaleProfile, ...]:
        return self.base, *self.overlays

    @property
    def runtime_tokens(self) -> tuple[str, ...]:
        return tuple(profile.runtime_token for profile in self.profiles)


def _profile(
    profile_id: str,
    label: str,
    runtime_token: str,
    classification: LocaleClassification,
    support_state: LocaleSupportState,
    *,
    base_profile_id: str | None = None,
    overlay_precedence: int | None = None,
    dem_sources: tuple[str, ...] = (),
    soil_sources: tuple[str, ...] = (),
    landuse_sources: tuple[str, ...] = (),
    climate_sources: tuple[str, ...] = (),
    climate_station_databases: tuple[str, ...] = (),
    source_revision: str = "WP12C-1",
) -> LocaleProfile:
    return LocaleProfile(
        profile_id=profile_id,
        label=label,
        runtime_token=runtime_token,
        classification=classification,
        support_state=support_state,
        source_revision=source_revision,
        base_profile_id=base_profile_id,
        overlay_precedence=overlay_precedence,
        dem_sources=dem_sources,
        soil_sources=soil_sources,
        landuse_sources=landuse_sources,
        climate_sources=climate_sources,
        climate_station_databases=climate_station_databases,
    )


_PROFILES = (
    _profile(
        "continental-us", "Continental United States", "us",
        LocaleClassification.BASE, LocaleSupportState.BUILDER_EXPOSED,
        dem_sources=("usgs-ned1-2024", "usgs-ned13-2022"),
        soil_sources=("ssurgo-gnatsgso-2025",),
        landuse_sources=("nlcd-2019",),
        climate_sources=(
            "vanilla_cligen", "prism_stochastic", "observed_daymet", "observed_gridmet",
        ),
        climate_station_databases=(
            "cligen-stations-legacy", "cligen-stations-2015", "cligen-stations-ghcn",
        ),
    ),
    _profile(
        "alaska", "Alaska", "alaska", LocaleClassification.BASE,
        LocaleSupportState.SUPPORTED_NON_BUILDER,
        dem_sources=("usgs-ned1-2024",), soil_sources=("alaska-gsmsoil",),
        landuse_sources=("alaska-nlcd-2001", "alaska-nlcd-2011", "alaska-nlcd-2016"),
    ),
    _profile(
        "hawaii", "Hawaii", "hawaii", LocaleClassification.BASE,
        LocaleSupportState.SUPPORTED_NON_BUILDER,
        dem_sources=("usgs-ned1-2024",), soil_sources=("hawaii-ssurgo",),
        landuse_sources=("hawaii-nlcd-wepp-31131a7",),
    ),
    _profile(
        "us-virgin-islands", "United States Virgin Islands", "virgin_islands",
        LocaleClassification.BASE, LocaleSupportState.SUPPORTED_NON_BUILDER,
        dem_sources=("usgs-ned1-2024", "usgs-ned13-2022"),
        soil_sources=("usvi-soils",),
        landuse_sources=("usvi-landcover-2018", "usvi-landcover-2023"),
    ),
    _profile(
        "europe", "Europe", "eu", LocaleClassification.BASE,
        LocaleSupportState.BUILDER_EXPOSED,
        dem_sources=("europe-eudem-v1-1",),
        soil_sources=("esdac-europe",),
        landuse_sources=("corine-1990", "corine-2000", "corine-2006", "corine-2012", "corine-2018"),
        climate_sources=("vanilla_cligen", "eobs_modified"),
        climate_station_databases=("cligen-stations-ghcn",),
    ),
    _profile(
        "canada", "Canada", "canada", LocaleClassification.BASE,
        LocaleSupportState.BUILDER_EXPOSED,
        dem_sources=("copernicus-dem-30",), soil_sources=("isric-global",),
        landuse_sources=_C3S_LANDUSE_IDS,
        climate_sources=("vanilla_cligen", "observed_daymet"),
        climate_station_databases=("cligen-stations-ghcn",),
    ),
    _profile(
        "australia", "Australia", "au", LocaleClassification.BASE,
        LocaleSupportState.BUILDER_EXPOSED,
        dem_sources=("australia-srtm-1s",), soil_sources=("asris-australia",),
        landuse_sources=("australia-landuse-2010-2011",),
        climate_sources=("vanilla_cligen", "agdc"),
        climate_station_databases=("cligen-stations-ghcn",),
    ),
    _profile(
        "global-earth", "Global Earth", "earth", LocaleClassification.BASE,
        LocaleSupportState.BUILDER_EXPOSED,
        dem_sources=("copernicus-dem-30",), soil_sources=("isric-global",),
        landuse_sources=_C3S_LANDUSE_IDS,
        climate_sources=("vanilla_cligen",),
        climate_station_databases=("cligen-stations-ghcn",),
    ),
    _profile(
        "turkey", "Turkey", "turkey", LocaleClassification.BASE,
        LocaleSupportState.SUPPORTED_NON_BUILDER,
        source_revision="WP12D-1",
    ),
    _profile(
        "nigeria", "Nigeria", "nigeria", LocaleClassification.BASE,
        LocaleSupportState.SUPPORTED_NON_BUILDER,
        dem_sources=("copernicus-dem-30",), soil_sources=("isric-global",),
        landuse_sources=_C3S_LANDUSE_IDS,
    ),
    _profile(
        "british-columbia", "British Columbia", "bc-ca",
        LocaleClassification.BASE, LocaleSupportState.SUPPORTED_NON_BUILDER,
        dem_sources=("canada-cdem",),
        landuse_sources=("canada-landcover-2020",),
    ),
    _profile(
        "chile-cayumanque", "Chile Cayumanque", "ChileCayumanque",
        LocaleClassification.BASE, LocaleSupportState.SUPPORTED_NON_BUILDER,
        dem_sources=("chile-cayumanque-dem",), soil_sources=("chile-soils",),
        landuse_sources=("chile-cayumanque-landuse",),
    ),
    _profile(
        "oyster-creek", "Oyster Creek", "oyster-creek",
        LocaleClassification.BASE, LocaleSupportState.SUPPORTED_NON_BUILDER,
        dem_sources=("usgs-ned13-2016",),
        landuse_sources=_OYSTER_CREEK_LANDUSE_IDS,
    ),
    _profile(
        "lake-tahoe", "Lake Tahoe", "laketahoe", LocaleClassification.OVERLAY,
        LocaleSupportState.SUPPORTED_NON_BUILDER,
        base_profile_id="continental-us", overlay_precedence=10,
    ),
    _profile(
        "portland", "Portland", "portland", LocaleClassification.OVERLAY,
        LocaleSupportState.SUPPORTED_NON_BUILDER,
        base_profile_id="continental-us", overlay_precedence=20,
        soil_sources=("portland-soils",), landuse_sources=("portland-nlcd",),
    ),
    _profile(
        "seattle", "Seattle", "seattle", LocaleClassification.OVERLAY,
        LocaleSupportState.SUPPORTED_NON_BUILDER,
        base_profile_id="continental-us", overlay_precedence=30,
    ),
    _profile(
        "tenerife", "Tenerife", "tenerife", LocaleClassification.OVERLAY,
        LocaleSupportState.SUPPORTED_NON_BUILDER,
        base_profile_id="europe", overlay_precedence=10,
        dem_sources=("tenerife-mdt25", "tenerife-mdt05"),
        soil_sources=("tenerife-soils-25m", "tenerife-soils-5m"),
        landuse_sources=("corine-2018",),
    ),
    _profile(
        "rhem", "RHEM", "rhem", LocaleClassification.NON_BUILDER_FAMILY,
        LocaleSupportState.NON_APPLICABLE,
    ),
)

_BY_ID: Mapping[str, LocaleProfile] = MappingProxyType(
    {profile.profile_id: profile for profile in _PROFILES}
)
_BY_TOKEN: Mapping[str, LocaleProfile] = MappingProxyType(
    {profile.runtime_token.casefold(): profile for profile in _PROFILES}
)


def _validate_catalog() -> None:
    if len(_BY_ID) != len(_PROFILES) or len(_BY_TOKEN) != len(_PROFILES):
        raise RuntimeError("locale profile IDs and runtime tokens must be unique")
    overlay_precedence: set[tuple[str, int]] = set()
    for profile in _PROFILES:
        if profile.classification is LocaleClassification.OVERLAY:
            base = _BY_ID.get(profile.base_profile_id or "")
            if base is None or base.classification is not LocaleClassification.BASE:
                raise RuntimeError(f"overlay {profile.profile_id!r} has no canonical base")
            if profile.overlay_precedence is None:
                raise RuntimeError(f"overlay {profile.profile_id!r} has no precedence")
            precedence_key = (base.profile_id, profile.overlay_precedence)
            if precedence_key in overlay_precedence:
                raise RuntimeError(
                    f"overlay precedence {profile.overlay_precedence} is duplicated for "
                    f"base {base.profile_id!r}"
                )
            overlay_precedence.add(precedence_key)
        elif profile.base_profile_id is not None or profile.overlay_precedence is not None:
            raise RuntimeError(f"non-overlay {profile.profile_id!r} declares overlay fields")
        if (
            profile.classification is LocaleClassification.NON_BUILDER_FAMILY
            and profile.support_state is not LocaleSupportState.NON_APPLICABLE
        ):
            raise RuntimeError("non-Builder model families must be non-applicable")
        unknown_dem = set(profile.dem_sources).difference(DEM_SOURCE_RUNTIME)
        unknown_soil = set(profile.soil_sources).difference(SOIL_SOURCE_RUNTIME)
        unknown_landuse = {
            source for source in profile.landuse_sources
            if get_landcover_entry(source) is None
        }
        unknown_climate = {
            source for source in profile.climate_sources
            if get_climate_dataset(source) is None
        }
        unknown_station_databases = {
            source for source in profile.climate_station_databases
            if get_climate_station_database(source) is None
        }
        if (
            unknown_dem
            or unknown_soil
            or unknown_landuse
            or unknown_climate
            or unknown_station_databases
        ):
            raise RuntimeError(
                f"locale profile {profile.profile_id!r} references unknown data sources"
            )


_validate_catalog()


def iter_locale_profiles() -> tuple[LocaleProfile, ...]:
    """Return the complete canonical locale profile inventory."""

    return _PROFILES


def get_locale_profile(profile_id: str) -> LocaleProfile | None:
    """Return one canonical profile by stable ID."""

    return _BY_ID.get(profile_id)


def resolve_locale_composition(tokens: Iterable[str]) -> LocaleComposition:
    """Resolve runtime tokens to exactly one base and ordered overlays."""

    normalized = tuple(str(token).strip() for token in tokens)
    if not normalized:
        raise LocaleProfileError("locale composition is empty")
    profiles: list[LocaleProfile] = []
    seen: set[str] = set()
    for token in normalized:
        profile = _BY_TOKEN.get(token.casefold())
        if profile is None:
            raise LocaleProfileError(f"unknown runtime locale token: {token!r}")
        if profile.profile_id in seen:
            raise LocaleProfileError(f"duplicate runtime locale token: {token!r}")
        profiles.append(profile)
        seen.add(profile.profile_id)
    families = [
        profile for profile in profiles
        if profile.classification is LocaleClassification.NON_BUILDER_FAMILY
    ]
    if families:
        if len(profiles) != 1:
            raise LocaleProfileError("non-Builder families cannot compose with geographic profiles")
        raise LocaleProfileError(f"{families[0].profile_id!r} is not a geographic Builder profile")
    bases = [profile for profile in profiles if profile.classification is LocaleClassification.BASE]
    if len(bases) != 1:
        raise LocaleProfileError("locale composition must contain exactly one base")
    base = bases[0]
    overlays = [
        profile for profile in profiles
        if profile.classification is LocaleClassification.OVERLAY
    ]
    for overlay in overlays:
        if overlay.base_profile_id != base.profile_id:
            raise LocaleProfileError(
                f"overlay {overlay.profile_id!r} is incompatible with base {base.profile_id!r}"
            )
    overlays.sort(key=lambda item: (item.overlay_precedence or 0, item.profile_id))
    return LocaleComposition(base, tuple(overlays))


def locale_catalog_revision() -> str:
    """Return a deterministic identity for the canonical profile inventory."""

    payload = [
        {
            "id": item.profile_id,
            "label": item.label,
            "runtime_token": item.runtime_token,
            "classification": item.classification.value,
            "support_state": item.support_state.value,
            "source_revision": item.source_revision,
            "base_profile_id": item.base_profile_id,
            "overlay_precedence": item.overlay_precedence,
            "dem_sources": item.dem_sources,
            "soil_sources": item.soil_sources,
            "landuse_sources": item.landuse_sources,
            "climate_sources": item.climate_sources,
            "climate_station_databases": item.climate_station_databases,
        }
        for item in _PROFILES
    ]
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
