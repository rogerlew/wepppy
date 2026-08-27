from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
import hashlib
import json
from configparser import ConfigParser
from pathlib import Path
from types import MappingProxyType
from typing import Iterable, Mapping, MutableMapping, Optional, Tuple, List


DAYMET_LAST_AVAILABLE_YEAR = 2024
_GHCN_ONLY_LOCALES: Tuple[str, ...] = ("au", "alaska", "hawaii", "nigeria")

CLIMATE_STATION_METHOD_RUNTIME: Mapping[str, int] = MappingProxyType(
    {
        "auto": -1,
        "distance": 0,
        "multi_factor": 1,
        "eu_heuristic": 2,
        "au_heuristic": 3,
        "user_defined": 4,
    }
)
CLIMATE_SPATIAL_METHOD_RUNTIME: Mapping[str, int] = MappingProxyType(
    {"single": 0, "multiple": 1, "interpolated": 2}
)
_STATION_METHOD_BY_RUNTIME = {value: key for key, value in CLIMATE_STATION_METHOD_RUNTIME.items()}
_SPATIAL_METHOD_BY_RUNTIME = {value: key for key, value in CLIMATE_SPATIAL_METHOD_RUNTIME.items()}
_BUILDER_EXPOSED_DATASETS = frozenset(
    {"vanilla_cligen", "prism_stochastic", "observed_daymet", "observed_gridmet"}
)
_SUPPORTED_NON_BUILDER_DATASETS = frozenset(
    {"dep_nexrad", "future_cmip5", "user_defined_cli", "eobs_modified"}
)


@dataclass(frozen=True)
class ClimateDataset:
    """Descriptor for a cataloged climate configuration."""

    catalog_id: str
    climate_mode: int
    label: str
    description: str = ""
    help_text: str = ""
    group: str = ""
    group_hint: str = ""
    allowed_locales: Tuple[str, ...] = ()
    blocked_locales: Tuple[str, ...] = ()
    mods_required: Tuple[str, ...] = ()
    spatial_modes: Tuple[int, ...] = (0,)
    default_spatial_mode: int = 0
    station_modes: Tuple[int, ...] = (-1, 0, 1)
    default_station_mode: int = -1
    inputs: Tuple[str, ...] = ()
    rap_compatible: bool = False
    dependencies: Tuple[str, ...] = ()
    upload_behaviour: str = "none"
    metadata: Mapping[str, object] = field(default_factory=dict)
    ui_exposed: bool = True

    @property
    def station_method_ids(self) -> Tuple[str, ...]:
        return tuple(_STATION_METHOD_BY_RUNTIME[mode] for mode in self.station_modes)

    @property
    def spatial_method_ids(self) -> Tuple[str, ...]:
        return tuple(_SPATIAL_METHOD_BY_RUNTIME[mode] for mode in self.spatial_modes)

    @property
    def default_station_method_id(self) -> str:
        return _STATION_METHOD_BY_RUNTIME[self.default_station_mode]

    @property
    def default_spatial_method_id(self) -> str:
        return _SPATIAL_METHOD_BY_RUNTIME[self.default_spatial_mode]

    @property
    def support_state(self) -> str:
        if self.catalog_id in _BUILDER_EXPOSED_DATASETS:
            return "builder_exposed"
        if self.catalog_id in _SUPPORTED_NON_BUILDER_DATASETS:
            return "supported_non_builder"
        return "inventory_only"

    def to_mapping(self) -> MutableMapping[str, object]:
        """Return a mutable representation suitable for JSON serialization."""
        return {
            "catalog_id": self.catalog_id,
            "climate_mode": self.climate_mode,
            "label": self.label,
            "description": self.description,
            "help_text": self.help_text,
            "group": self.group,
            "group_hint": self.group_hint,
            "allowed_locales": list(self.allowed_locales),
            "blocked_locales": list(self.blocked_locales),
            "mods_required": list(self.mods_required),
            "spatial_modes": list(self.spatial_modes),
            "default_spatial_mode": self.default_spatial_mode,
            "station_modes": list(self.station_modes),
            "station_method_ids": list(self.station_method_ids),
            "spatial_method_ids": list(self.spatial_method_ids),
            "default_station_method_id": self.default_station_method_id,
            "default_spatial_method_id": self.default_spatial_method_id,
            "support_state": self.support_state,
            "inputs": list(self.inputs),
            "rap_compatible": self.rap_compatible,
            "dependencies": list(self.dependencies),
            "upload_behaviour": self.upload_behaviour,
            "metadata": dict(self.metadata),
            "ui_exposed": self.ui_exposed,
        }

    def is_allowed_for(self, locales: Iterable[str], mods: Iterable[str], include_hidden: bool = False) -> bool:
        """Return True when dataset should be offered for the supplied context."""
        if not include_hidden and not self.ui_exposed:
            return False

        locale_set = {loc.lower() for loc in locales}
        mods_set = {mod.lower() for mod in mods}

        if self.allowed_locales:
            if not locale_set.intersection(l.lower() for l in self.allowed_locales):
                return False

        if self.blocked_locales:
            if locale_set.intersection(l.lower() for l in self.blocked_locales):
                return False

        if self.mods_required and not set(m.lower() for m in self.mods_required).issubset(mods_set):
            return False

        return True


_CLIMATE_DATASETS: Tuple[ClimateDataset, ...] = (
    ClimateDataset(
        catalog_id="vanilla_cligen",
        climate_mode=0,
        label='Vanilla CLIGEN',
        description='Baseline stochastic weather generator using nearest station.',
        help_text='Generates stochastic climates from CLIGEN station statistics.',
        group='Stochastic',
        group_hint='Long-term average conditions; probability risk assessment',
        spatial_modes=(0, 1),
        default_spatial_mode=0,
        station_modes=(-1, 0, 1),
        inputs=("stochastic_years", "spatial_mode"),
    ),
    ClimateDataset(
        catalog_id="prism_stochastic",
        climate_mode=5,
        label='Stochastic PRISM Modified',
        description='Applies PRISM precipitation/elevation adjustments to stochastic climates.',
        help_text='Recommended for BAER workflows when historic comparison is not required.',
        group='Stochastic',
        group_hint='Long-term average conditions; probability risk assessment',
        spatial_modes=(0, 1),
        default_spatial_mode=0,
        station_modes=(-1, 0, 1),
        inputs=("stochastic_years", "spatial_mode"),
        rap_compatible=False,
        blocked_locales=_GHCN_ONLY_LOCALES,
    ),
    ClimateDataset(
        catalog_id="observed_daymet",
        climate_mode=9,
        label='Observed DAYMET (GRIDMET wind)',
        description=(
            f'Observed gridded DAYMET dataset (1980–{DAYMET_LAST_AVAILABLE_YEAR}) '
            'with GRIDMET wind fallback.'
        ),
        help_text='Use when observed historical data is required (streamflow calibration, RAP).',
        group='Observed',
        group_hint='Model validation; historical disturbance analysis',
        spatial_modes=(0, 1, 2),
        default_spatial_mode=0,
        station_modes=(-1, 0, 1),
        inputs=("observed_years", "spatial_mode"),
        rap_compatible=True,
        metadata={"year_bounds": {"min": 1980, "max": DAYMET_LAST_AVAILABLE_YEAR}},
        blocked_locales=_GHCN_ONLY_LOCALES,
    ),
    ClimateDataset(
        catalog_id="observed_gridmet",
        climate_mode=11,
        label='Observed GRIDMET',
        description='Observed gridded GRIDMET dataset (1980–present).',
        help_text='Recommended when real observed meteorology is available (e.g., RAP, streamflow studies).',
        group='Observed',
        group_hint='Model validation; historical disturbance analysis',
        spatial_modes=(0, 1, 2),
        default_spatial_mode=0,
        station_modes=(-1, 0, 1),
        inputs=("observed_years", "spatial_mode"),
        rap_compatible=True,
        blocked_locales=_GHCN_ONLY_LOCALES,
    ),
    ClimateDataset(
        catalog_id="dep_nexrad",
        climate_mode=13,
        label='DEP NEXRAD Breakpoint',
        description='NEXRAD breakpoint files (0.01° grid) with optional temperature overrides.',
        help_text='Use for high-resolution breakpoint data (2007–present).',
        group='Observed',
        group_hint='Model validation; historical disturbance analysis',
        spatial_modes=(0, 1),
        default_spatial_mode=0,
        station_modes=(-1, 0, 1),
        inputs=("observed_years", "spatial_mode", "nexrad_overrides"),
        rap_compatible=False,
        blocked_locales=_GHCN_ONLY_LOCALES,
    ),
    ClimateDataset(
        catalog_id="future_cmip5",
        climate_mode=3,
        label='Future CMIP5',
        description='CMIP5-based future climate scenarios (2006–2099).',
        help_text='Experimental future projections; requires specifying start/end years.',
        group='Future',
        group_hint='Climate change impact analysis',
        spatial_modes=(0, 1),
        default_spatial_mode=0,
        station_modes=(-1, 0, 1),
        inputs=("future_years", "spatial_mode"),
        rap_compatible=False,
        blocked_locales=_GHCN_ONLY_LOCALES,
    ),
    ClimateDataset(
        catalog_id="single_storm",
        climate_mode=4,
        label='Single Storm (CLIGEN)',
        description='Designed single-storm event with CLIGEN-intensity curve.',
        help_text='Define date, precipitation amount, duration, and intensity profile for a single event.',
        group='Single Event',
        group_hint='Extreme-event analysis (note: Ignores subsurface and baseflow contribution to streamflow)',
        spatial_modes=(0,),
        default_spatial_mode=0,
        station_modes=(-1, 0, 1),
        inputs=("single_storm",),
    ),
    ClimateDataset(
        catalog_id="single_storm_batch",
        climate_mode=14,
        label='Single Storm Batch (CLIGEN)',
        description='Batch-run multiple designed storm events.',
        help_text='Provide multiple storm specifications (one per line) for batch execution.',
        group='Single Event',
        group_hint='Extreme-event analysis (note: Ignores subsurface and baseflow contribution to streamflow)',
        spatial_modes=(0,),
        default_spatial_mode=0,
        station_modes=(-1, 0, 1),
        inputs=("single_storm_batch",),
    ),
    ClimateDataset(
        catalog_id="user_defined_cli",
        climate_mode=12,
        label='User-Defined Climate (.cli)',
        description='Upload a custom CLIGEN-formatted `.cli` file.',
        help_text='Validates and installs a user-supplied climate file. Hillslope PRISM revision available when spatial mode allows.',
        group='User-Defined',
        group_hint='Research experiments/validation',
        spatial_modes=(0, 1),
        default_spatial_mode=0,
        station_modes=(4,),
        default_station_mode=4,
        inputs=("upload", "spatial_mode"),
        upload_behaviour="upload",
    ),
    ClimateDataset(
        catalog_id="observed_db",
        climate_mode=6,
        label='Observed Climate Database',
        description='Pre-generated observed climate files packaged with the run configuration.',
        help_text='Select an observed `.cli` from the configured library.',
        group='Observed',
        group_hint='Model validation; historical disturbance analysis',
        station_modes=(-1, 0),
        inputs=("observed_database",),
        ui_exposed=False,
    ),
    ClimateDataset(
        catalog_id="future_db",
        climate_mode=7,
        label='Future Climate Database',
        description='Pre-generated future climate files packaged with the run configuration.',
        help_text='Select a future `.cli` from the configured library.',
        group='Future',
        group_hint='Climate change impact analysis',
        station_modes=(-1, 0),
        inputs=("future_database",),
        ui_exposed=False,
    ),
    ClimateDataset(
        catalog_id="eobs_modified",
        climate_mode=8,
        label='E-OBS Modified (Europe)',
        description='E-OBS modified climates with spatial interpolation for European locales.',
        help_text='Recommended for European runs; performs spatial interpolation by default.',
        group='Observed',
        group_hint='Model validation; historical disturbance analysis',
        allowed_locales=("eu",),
        spatial_modes=(0, 1),
        default_spatial_mode=1,
        station_modes=(-1, 0, 1, 2),
        inputs=("stochastic_years", "spatial_mode"),
        rap_compatible=False,
    ),
    ClimateDataset(
        catalog_id="agdc",
        climate_mode=10,
        label='AGDC (Australia)',
        description='Australia Gridded Climate datasets.',
        help_text='Backend support only; UI exposure pending future requirements.',
        group='Observed',
        group_hint='Model validation; historical disturbance analysis',
        allowed_locales=("au",),
        spatial_modes=(0, 1),
        default_spatial_mode=0,
        station_modes=(-1, 0),
        ui_exposed=False,
    ),
)


@lru_cache(maxsize=None)
def _catalog_by_id() -> Mapping[str, ClimateDataset]:
    return {dataset.catalog_id: dataset for dataset in _CLIMATE_DATASETS}


def iter_climate_datasets() -> Tuple[ClimateDataset, ...]:
    """Return the full tuple of cataloged climate datasets."""
    return _CLIMATE_DATASETS


def available_climate_datasets(
    locales: Iterable[str],
    mods: Iterable[str],
    include_hidden: bool = False,
) -> List[ClimateDataset]:
    """Return climate datasets filtered for the given locales/mod combinations."""
    locales = tuple(locales or ())
    mods = tuple(mods or ())

    datasets: List[ClimateDataset] = []
    for dataset in _CLIMATE_DATASETS:
        if dataset.is_allowed_for(locales, mods, include_hidden=include_hidden):
            datasets.append(dataset)

    if not datasets:
        # Fall back to vanilla dataset to ensure at least one option is available.
        vanilla = _catalog_by_id().get("vanilla_cligen")
        if vanilla is not None:
            datasets.append(vanilla)

    return datasets


def get_climate_dataset(catalog_id: str) -> Optional[ClimateDataset]:
    """Return the dataset for the provided catalog identifier."""
    return _catalog_by_id().get(catalog_id)


CLIMATE_PROVIDER_ADAPTER_REVISION = "climate-input-parser-v1"
_CLIMATE_PROVIDER_OPTIONS = (
    "cligen_db",
    "daymet_observed",
    "use_gridmet_wind_when_applicable",
)


def default_climate_provider_tokens() -> Mapping[str, str]:
    """Return configured non-secret climate database/version tokens."""

    defaults_path = Path(__file__).parents[1] / "configs" / "_defaults.cfg"
    parser = ConfigParser(interpolation=None)
    if not parser.read(defaults_path, encoding="utf-8") or not parser.has_section("climate"):
        raise ValueError(f"unable to read climate provider defaults from {defaults_path}")
    values = {
        option: parser.get("climate", option)
        for option in _CLIMATE_PROVIDER_OPTIONS
        if parser.has_option("climate", option)
    }
    if set(values) != set(_CLIMATE_PROVIDER_OPTIONS) or any(not value for value in values.values()):
        raise ValueError("climate provider defaults are incomplete")
    return values


def climate_catalog_revision(
    configured_tokens: Mapping[str, str],
    adapter_revision: str = CLIMATE_PROVIDER_ADAPTER_REVISION,
) -> str:
    """Return identity for descriptors, configured tokens, methods, and adapter."""

    payload = {
        "datasets": [dataset.to_mapping() for dataset in _CLIMATE_DATASETS],
        "station_runtime": dict(CLIMATE_STATION_METHOD_RUNTIME),
        "spatial_runtime": dict(CLIMATE_SPATIAL_METHOD_RUNTIME),
        "configured_tokens": dict(configured_tokens),
        "adapter_revision": adapter_revision,
    }
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


__all__ = [
    "ClimateDataset",
    "CLIMATE_SPATIAL_METHOD_RUNTIME",
    "CLIMATE_STATION_METHOD_RUNTIME",
    "CLIMATE_PROVIDER_ADAPTER_REVISION",
    "available_climate_datasets",
    "climate_catalog_revision",
    "default_climate_provider_tokens",
    "get_climate_dataset",
    "iter_climate_datasets",
]
