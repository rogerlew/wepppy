from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
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
    "au": [],
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

    for record in records.values():
        if record.get("IsTreatment"):
            continue

        key = str(record.get("Key"))
        description = record.get("Description", "") or ""
        management_file = record.get("ManagementFile", "") or ""
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
        )
        for value, label in landcover_entries
    ]

    return datasets + landcover_datasets


__all__ = ["LanduseDataset", "available_landuse_datasets"]
