"""Lookup loading and normalization helpers for RUSLE C modes."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from wepppy.nodb.mods.disturbed import lookup_disturbed_class

from .c_formula import compute_c_from_ground_cover_fraction


DEFAULT_LOOKUP_PATH = str(Path(__file__).resolve().parent / "data" / "rusle_c_lookup.csv")

BURNABLE_FAMILIES: tuple[str, str, str] = ("forest", "shrub", "tall_grass")
REQUIRED_BURNABLE_SBS_CLASSES: tuple[str, str, str, str] = ("unburned", "low", "moderate", "high")
REQUIRED_STATIC_ROWS: tuple[tuple[str, str], ...] = (
    ("bare", "unburned"),
    ("short_grass", "unburned"),
)

MASKED_FAMILY_NAMES = frozenset({"water", "developed", "wetlands", "ice_snow"})
BASE_DISTURBED_CLASS_RASTER_CODES: dict[str, int] = {
    "forest": 1,
    "shrub": 2,
    "tall_grass": 3,
    "bare": 4,
    "short_grass": 5,
    "agriculture_crops": 6,
    "water": 7,
    "developed": 8,
    "wetlands": 9,
    "ice_snow": 10,
}
DISTURBED_CLASS_RASTER_NODATA = 0


__all__ = [
    "BASE_DISTURBED_CLASS_RASTER_CODES",
    "BURNABLE_FAMILIES",
    "DEFAULT_LOOKUP_PATH",
    "DISTURBED_CLASS_RASTER_NODATA",
    "MASKED_FAMILY_NAMES",
    "REQUIRED_BURNABLE_SBS_CLASSES",
    "RusleCLookupRow",
    "canonicalize_sbs_class",
    "disturbed_family_from_nlcd_class",
    "load_rusle_c_lookup",
    "normalize_disturbed_family",
    "resolve_lookup_row",
]


@dataclass(frozen=True)
class RusleCLookupRow:
    disturbed_class: str
    sbs_class: str
    nlcd_class: str | None
    canopy_cover: float | None
    ground_cover: float | None
    litter_cover: float | None
    rock_cover: float | None
    effective_fall_height: float | None
    c_override: float | None
    notes: str | None

    def resolved_c(self) -> float:
        """Return the effective `C` value for this lookup row."""

        if self.c_override is not None:
            return float(self.c_override)
        if self.ground_cover is None:
            raise ValueError(
                f"Lookup row ({self.disturbed_class}, {self.sbs_class}) requires either ground_cover or c_override"
            )
        return float(compute_c_from_ground_cover_fraction(self.ground_cover))


def _normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    return text or None


def _parse_optional_float(value: str | None, *, field_name: str, key: tuple[str, str]) -> float | None:
    text = _normalize_text(value)
    if text is None:
        return None
    try:
        return float(text)
    except ValueError as exc:
        raise ValueError(f"Lookup row {key} has invalid {field_name} value: {value!r}") from exc


def canonicalize_sbs_class(value: object) -> str:
    """Normalize severity labels into the canonical lookup key set."""

    token = _normalize_text(None if value is None else str(value))
    if token is None:
        raise ValueError("sbs_class is required")

    normalized = token.lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "0": "unburned",
        "130": "unburned",
        "unburned": "unburned",
        "no_burn": "unburned",
        "noburn": "unburned",
        "1": "low",
        "131": "low",
        "low": "low",
        "low_severity": "low",
        "2": "moderate",
        "132": "moderate",
        "moderate": "moderate",
        "moderate_severity": "moderate",
        "3": "high",
        "133": "high",
        "high": "high",
        "high_severity": "high",
    }

    result = aliases.get(normalized)
    if result is None:
        raise ValueError(f"Unsupported SBS class value: {value!r}")
    return result


def normalize_disturbed_family(disturbed_class: str | None) -> str | None:
    """Normalize raw disturbed classes into canonical scenario families."""

    raw = _normalize_text(None if disturbed_class is None else str(disturbed_class).lower())
    if raw is None:
        return None

    base = lookup_disturbed_class(raw) or raw
    text = base.replace("_", " ").strip()

    if text in {"forest", "young forest"} or text.startswith("forest ") or text.startswith("young forest "):
        return "forest"
    if text == "shrub" or text.startswith("shrub "):
        return "shrub"
    if text in {"tall grass", "grass"} or text.startswith("grass ") or text.startswith("tall grass "):
        return "tall_grass"
    if text == "short grass" or text.startswith("short grass "):
        return "short_grass"
    if text == "bare" or text.startswith("bare "):
        return "bare"
    if text == "agriculture crops" or text.startswith("agriculture crops "):
        return "agriculture_crops"
    if text.startswith("developed "):
        return "developed"

    return text.replace(" ", "_").replace("-", "_")


def disturbed_family_from_nlcd_class(nlcd_class: int, disturbed_class: str | None) -> str | None:
    """Apply the specification's NLCD policy before family lookup."""

    if nlcd_class == 0:
        return None
    if nlcd_class == 11:
        return "water"
    if nlcd_class in {21, 22, 23, 24}:
        return "developed"
    if nlcd_class in {90, 95}:
        return "wetlands"
    if nlcd_class == 12:
        return "ice_snow"
    return normalize_disturbed_family(disturbed_class)


def load_rusle_c_lookup(path: str = DEFAULT_LOOKUP_PATH) -> dict[tuple[str, str], RusleCLookupRow]:
    """Load and validate the runtime RUSLE C lookup table."""

    lookup_path = Path(path)
    if not lookup_path.exists():
        raise FileNotFoundError(f"RUSLE C lookup not found: {path}")

    rows: dict[tuple[str, str], RusleCLookupRow] = {}

    with lookup_path.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        for raw_row in reader:
            raw_disturbed_class = _normalize_text(raw_row.get("disturbed_class"))
            disturbed_class = normalize_disturbed_family(raw_disturbed_class)
            if disturbed_class is None:
                raise ValueError(f"Lookup row is missing disturbed_class: {raw_row}")

            sbs_class = canonicalize_sbs_class(raw_row.get("sbs_class"))
            key = (disturbed_class, sbs_class)
            if key in rows:
                raise ValueError(f"Duplicate RUSLE C lookup row: {key}")

            row = RusleCLookupRow(
                disturbed_class=disturbed_class,
                sbs_class=sbs_class,
                nlcd_class=_normalize_text(raw_row.get("nlcd_class")),
                canopy_cover=_parse_optional_float(raw_row.get("canopy_cover"), field_name="canopy_cover", key=key),
                ground_cover=_parse_optional_float(raw_row.get("ground_cover"), field_name="ground_cover", key=key),
                litter_cover=_parse_optional_float(raw_row.get("litter_cover"), field_name="litter_cover", key=key),
                rock_cover=_parse_optional_float(raw_row.get("rock_cover"), field_name="rock_cover", key=key),
                effective_fall_height=_parse_optional_float(
                    raw_row.get("effective_fall_height"),
                    field_name="effective_fall_height",
                    key=key,
                ),
                c_override=_parse_optional_float(raw_row.get("c_override"), field_name="c_override", key=key),
                notes=_normalize_text(raw_row.get("notes")),
            )
            row.resolved_c()
            rows[key] = row

    missing: list[tuple[str, str]] = []
    for family in BURNABLE_FAMILIES:
        for sbs_class in REQUIRED_BURNABLE_SBS_CLASSES:
            if (family, sbs_class) not in rows:
                missing.append((family, sbs_class))
    for key in REQUIRED_STATIC_ROWS:
        if key not in rows:
            missing.append(key)
    if missing:
        raise ValueError(f"RUSLE C lookup is missing required rows: {missing}")

    return rows


def resolve_lookup_row(
    lookup: dict[tuple[str, str], RusleCLookupRow],
    disturbed_class: str,
    sbs_class: str,
) -> RusleCLookupRow:
    """Return a lookup row or raise an explicit missing-row error."""

    key = (normalize_disturbed_family(disturbed_class) or "", canonicalize_sbs_class(sbs_class))
    row = lookup.get(key)
    if row is None:
        raise ValueError(
            f"Missing RUSLE C lookup row for disturbed_class={key[0]!r}, sbs_class={key[1]!r}"
        )
    return row

