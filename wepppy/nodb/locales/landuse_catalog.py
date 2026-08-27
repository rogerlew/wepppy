from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import hashlib
import json
import re
from typing import Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence, Tuple

from wepppy.wepp.management import load_map


_DEFAULT_LANDCOVER_DATASETS: List[Tuple[str, str]] = [
    (f"nlcd/ever_forest/{year}", f"nlcd/ever_forest/{year}") for year in range(2024, 1984, -1)
] + [
    (f"nlcd/{year}", f"nlcd/{year}") for year in range(2024, 1984, -1)
] + [
    (
        f"islay.ceoas.oregonstate.edu/v1/landcover/vote/{year}",
        f"emapr/v1/landcover/vote/{year}",
    )
    for year in range(2017, 1983, -1)
]


_STATIC_LANDCOVER_DATASETS: Dict[str, List[Tuple[str, str]]] = {
    "chilecayumanque": [
        ("locales/ChileCayumanque/landuse", "ChileCayumanque/landuse"),
    ],
    "alaska": [
        ("alaska/nlcd/2001", "NLCD/2001"),
        ("alaska/nlcd/2011", "NLCD/2011"),
        ("alaska/nlcd/2016", "NLCD/2016"),
    ],
    "oyster-creek": [
        ("nlcd/2023", "NLCD/2023"),
        ("nlcd/2020", "NLCD/2020"),
        ("nlcd/2016", "NLCD/2016"),
        ("nlcd/2010", "NLCD/2010"),
        ("nlcd/2006", "NLCD/2006"),
        ("nlcd/2001", "NLCD/2001"),
        ("nlcd/1996", "NLCD/1996"),
        ("locales/oyster-creek/landuse/1993", "Himmelstein/1993"),
        ("locales/oyster-creek/landuse/1982", "Himmelstein/1982"),
        ("locales/oyster-creek/landuse/1975", "Himmelstein/1975"),
        ("locales/oyster-creek/landuse/1970", "Himmelstein/1970"),
        ("locales/oyster-creek/landuse/1964", "Himmelstein/1964"),
        ("locales/oyster-creek/landuse/1959", "Himmelstein/1959"),
    ],
    "virgin_islands": [
        ("locales/virgin_islands/landcover", "USVI Landcover 2018"),
        ("locales/virgin_islands/landcover/2023", "USVI Landcover 2023"),
    ],
    "eu": [
        ("eu/CORINE_LandCover/1990", "CORINE 1990"),
        ("eu/CORINE_LandCover/2000", "CORINE 2000"),
        ("eu/CORINE_LandCover/2006", "CORINE 2006"),
        ("eu/CORINE_LandCover/2012", "CORINE 2012"),
        ("eu/CORINE_LandCover/2018", "CORINE 2018"),
    ],
    "au": [
        ("au/landuse_201011/lu10v5ua", "Australia Land Use 2010-2011"),
    ],
    "earth": [
        (f"locales/earth/C3Slandcover/{year}", f"C3Slandcover/{year}")
        for year in range(2020, 1991, -1)
    ],
    "_default": _DEFAULT_LANDCOVER_DATASETS,
}


_LANDCOVER_LOCALE_PRIORITY: Tuple[Tuple[str, ...], ...] = (
    ("chilecayumanque",),
    ("alaska",),
    ("oyster-creek",),
    ("virgin_islands",),
    ("eu",),
    ("au",),
    ("earth", "nigeria"),
)


_EXCLUDED_MANAGEMENT_FILES: Tuple[str, ...] = ("UnDisturbed/null.man",)

_CONFIG_ONLY_LANDCOVER_DATASETS: Tuple[Tuple[str, str], ...] = (
    ("hawaii/nlcd/wepp_31131a7", "Hawaii NLCD WEPP 31131a7"),
    ("ca/canadalandcover2020", "Canada Landcover 2020"),
    ("portland/nlcd", "Portland NLCD"),
)
_LANDCOVER_SPECIAL_IDS: Mapping[str, str] = {
    "locales/ChileCayumanque/landuse": "chile-cayumanque-landuse",
    "locales/virgin_islands/landcover": "usvi-landcover-2018",
    "locales/virgin_islands/landcover/2023": "usvi-landcover-2023",
    "hawaii/nlcd/wepp_31131a7": "hawaii-nlcd-wepp-31131a7",
    "ca/canadalandcover2020": "canada-landcover-2020",
    "portland/nlcd": "portland-nlcd",
    "au/landuse_201011/lu10v5ua": "australia-landuse-2010-2011",
}
LANDCOVER_PROVIDER_ADAPTER_REVISION = "landuse-catalog-adapter-v2"
_BUILDER_EXPOSED_LANDCOVER_IDS = frozenset(
    {
        "nlcd-2019",
        "corine-1990",
        "corine-2000",
        "corine-2006",
        "corine-2012",
        "corine-2018",
        "australia-landuse-2010-2011",
        *(f"c3s-landcover-{year}" for year in range(1992, 2021)),
    }
)


@dataclass(frozen=True, slots=True)
class LandcoverCatalogEntry:
    """Stable landcover identity with one canonical runtime value."""

    catalog_id: str
    runtime_value: str
    label: str
    support_state: str


def landcover_catalog_id(runtime_value: str) -> str:
    """Map a closed runtime landcover token to its stable catalog ID."""

    value = str(runtime_value)
    special = _LANDCOVER_SPECIAL_IDS.get(value)
    if special is not None:
        return special
    match = re.fullmatch(r"nlcd/ever_forest/(\d{4})", value)
    if match:
        return f"nlcd-ever-forest-{match.group(1)}"
    match = re.fullmatch(r"nlcd/(\d{4})", value)
    if match:
        return f"nlcd-{match.group(1)}"
    match = re.fullmatch(
        r"islay\.ceoas\.oregonstate\.edu/v1/landcover/vote/(\d{4})", value
    )
    if match:
        return f"emapr-vote-{match.group(1)}"
    match = re.fullmatch(r"alaska/nlcd/(\d{4})", value)
    if match:
        return f"alaska-nlcd-{match.group(1)}"
    match = re.fullmatch(r"locales/oyster-creek/landuse/(\d{4})", value)
    if match:
        return f"oyster-creek-{match.group(1)}"
    match = re.fullmatch(r"eu/(?:CORINE_LandCover|corine_landcover)/(\d{4})", value)
    if match:
        return f"corine-{match.group(1)}"
    match = re.fullmatch(r"locales/earth/C3Slandcover/(\d{4})", value)
    if match:
        return f"c3s-landcover-{match.group(1)}"
    raise ValueError(f"unknown landcover runtime value: {value!r}")


@lru_cache(maxsize=1)
def iter_landcover_catalog() -> Tuple[LandcoverCatalogEntry, ...]:
    """Return the complete unique landcover catalog and shipped-config boundary."""

    values: dict[str, tuple[str, str]] = {}
    for group, entries in _STATIC_LANDCOVER_DATASETS.items():
        for runtime_value, label in entries:
            catalog_id = landcover_catalog_id(runtime_value)
            previous = values.get(catalog_id)
            if previous is not None and previous[0] != runtime_value:
                raise ValueError(f"landcover ID {catalog_id!r} maps to multiple runtime values")
            values[catalog_id] = (runtime_value, label)
    for runtime_value, label in _CONFIG_ONLY_LANDCOVER_DATASETS:
        catalog_id = landcover_catalog_id(runtime_value)
        values[catalog_id] = (runtime_value, label)
    return tuple(
        LandcoverCatalogEntry(
            catalog_id=catalog_id,
            runtime_value=runtime_value,
            label=label,
            support_state=(
                "builder_exposed"
                if catalog_id in _BUILDER_EXPOSED_LANDCOVER_IDS
                else "supported_non_builder"
            ),
        )
        for catalog_id, (runtime_value, label) in sorted(values.items())
    )


@lru_cache(maxsize=1)
def _landcover_by_id() -> Mapping[str, LandcoverCatalogEntry]:
    return {entry.catalog_id: entry for entry in iter_landcover_catalog()}


def get_landcover_entry(catalog_id: str) -> LandcoverCatalogEntry | None:
    """Return a landcover provider entry by stable ID."""

    return _landcover_by_id().get(catalog_id)


def landcover_catalog_revision(
    adapter_revision: str = LANDCOVER_PROVIDER_ADAPTER_REVISION,
) -> str:
    """Return identity over entries, ordered locale groups, and adapter."""

    payload = {
        "entries": [
            {
                "id": entry.catalog_id,
                "runtime": entry.runtime_value,
                "label": entry.label,
                "support_state": entry.support_state,
            }
            for entry in iter_landcover_catalog()
        ],
        "locale_groups": [
            {
                "group": group,
                "catalog_ids": [landcover_catalog_id(runtime) for runtime, _label in entries],
            }
            for group, entries in _STATIC_LANDCOVER_DATASETS.items()
        ],
        "locale_priority": _LANDCOVER_LOCALE_PRIORITY,
        "config_only_catalog_ids": [
            landcover_catalog_id(runtime) for runtime, _label in _CONFIG_ONLY_LANDCOVER_DATASETS
        ],
        "adapter_revision": adapter_revision,
    }
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _resolve_landcover_datasets(locales: Iterable[str]) -> List[Tuple[str, str]]:
    """Return the landcover dataset list for the provided locales."""
    locales_lower = {str(locale).lower() for locale in locales}

    for candidates in _LANDCOVER_LOCALE_PRIORITY:
        if any(candidate in locales_lower for candidate in candidates):
            key = candidates[0]
            return list(_STATIC_LANDCOVER_DATASETS.get(key, []))

    return list(_STATIC_LANDCOVER_DATASETS["_default"])


@dataclass(frozen=True)
class LanduseDataset:
    """Descriptor for an available landuse management dataset."""

    key: str
    description: str
    management_file: str
    metadata: Mapping[str, object]
    kind: str = "mapping"
    catalog_id: str | None = None
    support_state: str | None = None

    def to_mapping(self) -> MutableMapping[str, object]:
        """Return a mutable copy of the underlying metadata, keyed like legacy dicts."""
        return dict(self.metadata)

    @property
    def label(self) -> str:
        """Return a human-readable label for UI use."""
        if self.description:
            return self.description
        if self.management_file:
            return self.management_file
        return self.key


@lru_cache(maxsize=None)
def _load_catalog(mapping: Optional[str]) -> Tuple[LanduseDataset, ...]:
    """Load and cache the underlying management map as dataset descriptors."""
    records = load_map(mapping)
    datasets: List[LanduseDataset] = []
    seen_description_management_pairs = set()

    for record in records.values():
        management_file = record.get("ManagementFile", "") or ""
        if management_file in _EXCLUDED_MANAGEMENT_FILES:
            continue

        key = str(record.get("Key"))
        description = record.get("Description", "") or ""
        description_management_pair = (description, management_file)
        if description_management_pair in seen_description_management_pairs:
            continue
        seen_description_management_pairs.add(description_management_pair)
        datasets.append(
            LanduseDataset(
                key=key,
                description=description,
                management_file=management_file,
                metadata=dict(record),
            )
        )

    datasets.sort(key=lambda item: item.key)
    return tuple(datasets)


def available_landuse_datasets(
    mapping: Optional[str],
    mods: Iterable[str],
    locales: Iterable[str] | None = None,
) -> List[LanduseDataset]:
    """Return filtered dataset descriptors for the supplied mapping and mods."""
    mods_lower = {str(mod).lower() for mod in mods}
    datasets = list(_load_catalog(mapping))

    if "baer" in mods_lower:
        datasets = [
            dataset
            for dataset in datasets
            if "Agriculture" not in dataset.management_file
        ]

    if {"lt", "portland", "seattle"} & mods_lower:
        datasets = [
            dataset
            for dataset in datasets
            if "Tahoe" in dataset.management_file
        ]

    locales = locales or ()
    landcover_entries = _resolve_landcover_datasets(locales)
    landcover_datasets = [
        LanduseDataset(
            key=value,
            description=label,
            management_file="",
            metadata={
                "Key": value,
                "Description": label,
                "ManagementFile": "",
                "kind": "landcover",
            },
            kind="landcover",
            catalog_id=landcover_catalog_id(value),
            support_state=(
                "builder_exposed"
                if landcover_catalog_id(value) in _BUILDER_EXPOSED_LANDCOVER_IDS
                else "supported_non_builder"
            ),
        )
        for value, label in landcover_entries
    ]

    return datasets + landcover_datasets


__all__ = [
    "LandcoverCatalogEntry",
    "LanduseDataset",
    "available_landuse_datasets",
    "get_landcover_entry",
    "iter_landcover_catalog",
    "landcover_catalog_id",
    "landcover_catalog_revision",
]
