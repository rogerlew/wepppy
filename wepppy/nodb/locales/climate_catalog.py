from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Iterable, Mapping, MutableMapping, Optional, Tuple, List


_GHCN_ONLY_LOCALES: Tuple[str, ...] = ("au", "alaska", "hawaii", "nigeria")


@dataclass(frozen=True)
class ClimateDataset:
    """Descriptor for a catalogued climate configuration."""

    catalog_id: str
    climate_mode: int
    label: str
    description: str = ""
    help_text: str = ""
    allowed_locales: Tuple[str, ...] = ()
    blocked_locales: Tuple[str, ...] = ()
    mods_required: Tuple[str, ...] = ()
    spatial_modes: Tuple[int, ...] = (0,)
    default_spatial_mode: int = 0
    station_modes: Tuple[int, ...] = (-1, 0, 1)
    inputs: Tuple[str, ...] = ()
    rap_compatible: bool = False
    dependencies: Tuple[str, ...] = ()
    upload_behaviour: str = "none"
    metadata: Mapping[str, object] = field(default_factory=dict)
    ui_exposed: bool = True

    def to_mapping(self) -> MutableMapping[str, object]:
        """Return a mutable representation suitable for JSON serialization."""
        return {
            "catalog_id": self.catalog_id,
            "climate_mode": self.climate_mode,
            "label": self.label,
            "description": self.description,
            "help_text": self.help_text,
            "allowed_locales": list(self.allowed_locales),
            "blocked_locales": list(self.blocked_locales),
            "mods_required": list(self.mods_required),
            "spatial_modes": list(self.spatial_modes),
            "default_spatial_mode": self.default_spatial_mode,
            "station_modes": list(self.station_modes),
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
        spatial_modes=(0, 1),
        default_spatial_mode=0,
        station_modes=(-1, 0, 1),
        inputs=("stochastic_years", "spatial_mode"),
        rap_compatible=True,
        blocked_locales=_GHCN_ONLY_LOCALES,
    ),
    ClimateDataset(
        catalog_id="observed_daymet",
        climate_mode=9,
        label='Observed DAYMET (GRIDMET wind)',
        description='Observed gridded DAYMET dataset (1980–latest release) with GRIDMET wind fallback.',
        help_text='Use when observed historical data is required (streamflow calibration, RAP).',
        spatial_modes=(0, 1, 2),
        default_spatial_mode=0,
        station_modes=(-1, 0, 1),
        inputs=("observed_years", "spatial_mode"),
        rap_compatible=True,
        metadata={"year_bounds": {"min": 1980, "max": 2023}},
        blocked_locales=_GHCN_ONLY_LOCALES,
    ),
    ClimateDataset(
        catalog_id="observed_gridmet",
        climate_mode=11,
        label='Observed GRIDMET',
        description='Observed gridded GRIDMET dataset (1980–present).',
        help_text='Recommended when real observed meteorology is available (e.g., RAP, streamflow studies).',
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
        spatial_modes=(0, 1),
        default_spatial_mode=0,
        station_modes=(4,),
        inputs=("upload", "spatial_mode"),
        upload_behaviour="upload",
    ),
    ClimateDataset(
        catalog_id="observed_db",
        climate_mode=6,
        label='Observed Climate Database',
        description='Pre-generated observed climate files packaged with the run configuration.',
        help_text='Select an observed `.cli` from the configured library.',
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
    """Return the full tuple of catalogued climate datasets."""
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


__all__ = [
    "ClimateDataset",
    "available_climate_datasets",
    "get_climate_dataset",
    "iter_climate_datasets",
]
