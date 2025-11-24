from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence, TYPE_CHECKING, Any

import logging
import duckdb
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from .schema_utils import pa_field
from .versioning import schema_with_version

if TYPE_CHECKING:
    from wepppy.nodb.core.wepp import BaseflowOpts
else:
    BaseflowOpts = Any  # type: ignore[assignment]

LOGGER = logging.getLogger(__name__)

DATE_COLUMNS = ("year", "sim_day_index", "julian", "month", "day_of_month", "water_year")
_SEDIMENT_CLASS_COUNT = 5
SEDIMENT_SPECIFIC_GRAVITY = (2.60, 2.65, 1.80, 1.60, 2.65)
SEDIMENT_DENSITY_KG_M3 = tuple(value * 1000.0 for value in SEDIMENT_SPECIFIC_GRAVITY)
SEDIMENT_MASS_COLUMNS = tuple(f"seddep_{idx}" for idx in range(1, _SEDIMENT_CLASS_COUNT + 1))
SEDIMENT_VOLUME_COLUMN = "sed_vol_conc"
ASH_VOLUME_COLUMN = "ash_vol_conc"
SED_ASH_VOLUME_COLUMN = "sed+ash_vol_conc"
ASH_BLACK_PCT_COLUMN = "ash_black_pct_by_vol"

PASS_METRIC_COLUMNS = (
    "runvol",
    "sbrunv",
    "tdet",
    "tdep",
    *SEDIMENT_MASS_COLUMNS,
    SEDIMENT_VOLUME_COLUMN,
)

# Ash columns are unitless in names; units live in schema metadata
ASH_TYPES = ("black", "white")
ASH_METRIC_BASES = ("wind_transport", "water_transport", "ash_transport", "transportable_ash")
ASH_TYPED_BASES = ("wind_transport", "water_transport", "ash_transport")
ASH_TONNE_COLUMNS = ASH_METRIC_BASES
ASH_PER_HA_COLUMNS = tuple(f"{name}_per_ha" for name in ASH_METRIC_BASES)
ASH_TYPED_TONNE_COLUMNS = tuple(f"{base}_{ash_type}" for ash_type in ASH_TYPES for base in ASH_TYPED_BASES)
ASH_TYPED_PER_HA_COLUMNS = tuple(f"{name}_per_ha" for name in ASH_TYPED_TONNE_COLUMNS)
ASH_METRIC_COLUMNS = ASH_TONNE_COLUMNS + ASH_PER_HA_COLUMNS + ASH_TYPED_TONNE_COLUMNS + ASH_TYPED_PER_HA_COLUMNS
ASH_TYPE_AREA_COLUMNS = tuple(f"area_{ash_type}_ha" for ash_type in ASH_TYPES)
ASH_VOLUME_HELPER_COLUMNS = ("ash_solids_volume", "ash_black_solids_volume", "ash_white_solids_volume")
ASH_JOIN_COLUMNS = ("year", "julian", "month", "day_of_month")

SCHEMA = schema_with_version(
    pa.schema(
        [
            pa_field("year", pa.int16()),
            pa_field("sim_day_index", pa.int32()),
            pa_field("julian", pa.int16()),
            pa_field("month", pa.int8()),
            pa_field("day_of_month", pa.int8()),
            pa_field("water_year", pa.int16()),
            pa_field("runvol", pa.float64(), units="m^3", description="Runoff volume"),
            pa_field("sbrunv", pa.float64(), units="m^3", description="Subsurface runoff volume"),
            pa_field("tdet", pa.float64(), units="kg", description="Total detachment"),
            pa_field("tdep", pa.float64(), units="kg", description="Total deposition"),
            pa_field("seddep_1", pa.float64(), units="kg", description="Sediment Class 1 deposition"),
            pa_field("seddep_2", pa.float64(), units="kg", description="Sediment Class 2 deposition"),
            pa_field("seddep_3", pa.float64(), units="kg", description="Sediment Class 3 deposition"),
            pa_field("seddep_4", pa.float64(), units="kg", description="Sediment Class 4 deposition"),
            pa_field("seddep_5", pa.float64(), units="kg", description="Sediment Class 5 deposition"),
            pa_field(
                "sed_vol_conc",
                pa.float64(),
                units="m^3/m^3",
                description="Total volumetric sediment concentration (solids volume divided by runoff volume)",
            ),
            pa_field("Area", pa.float64(), units="m^2", description="Area that depths apply over"),
            pa_field("P", pa.float64(), units="m^3", description="Precipitation volume"),
            pa_field("RM", pa.float64(), units="m^3", description="Rainfall+Irrigation+Snowmelt volume"),
            pa_field("Q", pa.float64(), units="m^3", description="Daily runoff over effective length volume"),
            pa_field("Dp", pa.float64(), units="m^3", description="Deep percolation volume"),
            pa_field("latqcc", pa.float64(), units="m^3", description="Lateral subsurface flow volume"),
            pa_field("QOFE", pa.float64(), units="m^3", description="Daily runoff scaled to single OFE volume"),
            pa_field("Ep", pa.float64(), units="m^3", description="Plant transpiration volume"),
            pa_field("Es", pa.float64(), units="m^3", description="Soil evaporation volume"),
            pa_field("Er", pa.float64(), units="m^3", description="Residue evaporation volume"),
            pa_field("UpStrmQ", pa.float64(), units="mm", description="Runon added to OFE depth"),
            pa_field("SubRIn", pa.float64(), units="mm", description="Subsurface runon added to OFE depth"),
            pa_field("Total-Soil Water", pa.float64(), units="mm", description="Unfrozen water in soil profile depth"),
            pa_field("frozwt", pa.float64(), units="mm", description="Frozen water in soil profile depth"),
            pa_field("Snow-Water", pa.float64(), units="mm", description="Water in surface snow depth"),
            pa_field("Tile", pa.float64(), units="mm", description="Tile drainage depth"),
            pa_field("Irr", pa.float64(), units="mm", description="Irrigation depth"),
            pa_field("Precipitation", pa.float64(), units="mm", description="Precipitation depth"),
            pa_field("Rain+Melt", pa.float64(), units="mm", description="Rainfall+Irrigation+Snowmelt depth"),
            pa_field("Percolation", pa.float64(), units="mm", description="Deep percolation depth"),
            pa_field("Lateral Flow", pa.float64(), units="mm", description="Lateral subsurface flow depth"),
            pa_field("Runoff", pa.float64(), units="mm", description="Daily runoff scaled to single OFE depth"),
            pa_field("Transpiration", pa.float64(), units="mm", description="Plant transpiration depth"),
            pa_field("Evaporation", pa.float64(), units="mm", description="Soil + residue evaporation depth"),
            pa_field("ET", pa.float64(), units="mm", description="Total evapotranspiration depth"),
            pa_field("Baseflow", pa.float64(), units="mm", description="Baseflow depth"),
            pa_field("Aquifer losses", pa.float64(), units="mm", description="Aquifer losses depth"),
            pa_field("Reservoir Volume", pa.float64(), units="mm", description="Groundwater storage depth"),
            pa_field("Streamflow", pa.float64(), units="mm", description="Streamflow depth"),
            pa_field("wind_transport", pa.float64(), units="tonne", description="Ash transported by wind (total mass)"),
            pa_field("wind_transport_per_ha", pa.float64(), units="tonne/ha", description="Ash transported by wind per unit area"),
            pa_field("wind_transport_black", pa.float64(), units="tonne", description="Black ash transported by wind (total mass)"),
            pa_field("wind_transport_black_per_ha", pa.float64(), units="tonne/ha", description="Black ash transported by wind per unit area over black ash hillslopes"),
            pa_field("wind_transport_white", pa.float64(), units="tonne", description="White ash transported by wind (total mass)"),
            pa_field("wind_transport_white_per_ha", pa.float64(), units="tonne/ha", description="White ash transported by wind per unit area over white ash hillslopes"),
            pa_field("water_transport", pa.float64(), units="tonne", description="Ash transported by water (total mass)"),
            pa_field("water_transport_per_ha", pa.float64(), units="tonne/ha", description="Ash transported by water per unit area"),
            pa_field("water_transport_black", pa.float64(), units="tonne", description="Black ash transported by water (total mass)"),
            pa_field("water_transport_black_per_ha", pa.float64(), units="tonne/ha", description="Black ash transported by water per unit area over black ash hillslopes"),
            pa_field("water_transport_white", pa.float64(), units="tonne", description="White ash transported by water (total mass)"),
            pa_field("water_transport_white_per_ha", pa.float64(), units="tonne/ha", description="White ash transported by water per unit area over white ash hillslopes"),
            pa_field("ash_transport", pa.float64(), units="tonne", description="Total ash transported (wind + water)"),
            pa_field("ash_transport_per_ha", pa.float64(), units="tonne/ha", description="Total ash transported per unit area"),
            pa_field("ash_transport_black", pa.float64(), units="tonne", description="Black ash transported by wind + water (total mass)"),
            pa_field("ash_transport_black_per_ha", pa.float64(), units="tonne/ha", description="Black ash transported per unit area over black ash hillslopes"),
            pa_field("ash_transport_white", pa.float64(), units="tonne", description="White ash transported by wind + water (total mass)"),
            pa_field("ash_transport_white_per_ha", pa.float64(), units="tonne/ha", description="White ash transported per unit area over white ash hillslopes"),
            pa_field("transportable_ash", pa.float64(), units="tonne", description="Ash mass still available for transport"),
            pa_field("transportable_ash_per_ha", pa.float64(), units="tonne/ha", description="Ash mass still available for transport per unit area"),
            pa_field(ASH_VOLUME_COLUMN, pa.float64(), units="m^3/m^3", description="Ash volumetric concentration (solids volume divided by runoff volume)"),
            pa_field(SED_ASH_VOLUME_COLUMN, pa.float64(), units="m^3/m^3", description="Sediment + ash volumetric concentration (total solids volume divided by runoff volume)"),
            pa_field(
                ASH_BLACK_PCT_COLUMN,
                pa.float64(),
                units="percent",
                description="Fraction of ash solids volume that is black ash (percent of total ash volume)",
            ),
        ]
    )
)

EMPTY_TABLE = pa.table({field.name: pa.array([], type=field.type) for field in SCHEMA}, schema=SCHEMA)


@dataclass(frozen=True)
class _QueryTargets:
    pass_path: Path
    wat_path: Path
    output_path: Path


def _normalize_wepp_ids(wepp_ids: Sequence[int] | None) -> list[int] | None:
    if wepp_ids is None:
        return None
    normalized = sorted({int(wepp_id) for wepp_id in wepp_ids})
    return normalized


def _resolve_run_root(interchange_dir: Path) -> Path | None:
    try:
        return interchange_dir.resolve().parents[2]
    except (IndexError, RuntimeError):
        return None


def _resolve_ash_dir(interchange_dir: Path, override: Path | str | None) -> Path | None:
    if override is not None:
        return Path(override)
    run_root = _resolve_run_root(interchange_dir)
    if run_root is None:
        return None
    return run_root / "ash"


def _default_ash_bulk_densities() -> dict[str, float]:
    try:
        from wepppy.nodb.mods.ash_transport.ash_multi_year_model import BLACK_ASH_BD, WHITE_ASH_BD
        return {"black": float(BLACK_ASH_BD) * 1000.0, "white": float(WHITE_ASH_BD) * 1000.0}
    except ModuleNotFoundError:
        # Fallback to baked-in defaults if ash module is unavailable
        return {"black": 0.22 * 1000.0, "white": 0.31 * 1000.0}


def _normalize_ash_type(value: Any) -> str | None:
    try:
        from wepppy.nodb.mods.ash_transport.ash_multi_year_model import AshType
    except ModuleNotFoundError:
        AshType = None  # type: ignore
    if value is None:
        return None
    if isinstance(value, str):
        lowered = value.lower()
        if lowered in ASH_TYPES:
            return lowered
        return None
    if AshType is not None:
        if value == AshType.BLACK:
            return "black"
        if value == AshType.WHITE:
            return "white"
    return None


def _available_wepp_ids(ash_dir: Path) -> list[int]:
    if not ash_dir.exists():
        return []
    candidates: set[int] = set()
    for path in ash_dir.glob("H*.parquet"):
        stem = path.stem  # e.g., H12_ash
        if not stem.startswith("H"):
            continue
        suffix = stem[1:]
        if suffix.endswith("_ash"):
            suffix = suffix[:-4]
        if not suffix.isdigit():
            continue
        candidates.add(int(suffix))
    return sorted(candidates)


def _select_wepp_ids(ash_dir: Path, wepp_ids: list[int] | None) -> list[int]:
    available = _available_wepp_ids(ash_dir)
    if wepp_ids is None:
        return available
    requested = {int(value) for value in wepp_ids}
    return [wepp_id for wepp_id in available if wepp_id in requested]


def _build_area_lookup_from_watershed(run_root: Path | None, wepp_ids: Iterable[int]) -> dict[int, float]:
    if run_root is None:
        return {}
    try:
        from wepppy.nodb.core import Watershed
    except ModuleNotFoundError:
        LOGGER.debug("Ash merge skipped; Watershed controller unavailable")
        return {}

    try:
        watershed = Watershed.getInstance(str(run_root))
    except Exception as exc:  # pragma: no cover - defensive
        LOGGER.debug("Ash merge skipped; unable to load Watershed at %s (%s)", run_root, exc)
        return {}

    translator = watershed.translator_factory()
    lookup: dict[int, float] = {}
    for wepp_id in wepp_ids:
        try:
            topaz_id = translator.top(wepp=int(wepp_id))
        except Exception:  # pragma: no cover - translator failures
            topaz_id = None
        if topaz_id is None:
            continue
        try:
            area_m2 = watershed.hillslope_area(topaz_id)
        except Exception:  # pragma: no cover - hillslope lookup failures
            continue
        if area_m2 is None:
            continue
        area_ha = float(area_m2) / 10_000.0
        if area_ha <= 0.0:
            continue
        lookup[int(wepp_id)] = area_ha
    return lookup


def _build_ash_type_and_density_lookup(run_root: Path | None, wepp_ids: Iterable[int]) -> tuple[dict[int, str], dict[int, float]]:
    if run_root is None:
        return {}, {}
    try:
        from wepppy.nodb.core import Watershed
        from wepppy.nodb.mods.ash_transport import Ash
    except ModuleNotFoundError:
        LOGGER.debug("Ash type lookup skipped; controllers unavailable")
        return {}, {}
    try:
        watershed = Watershed.getInstance(str(run_root))
        translator = watershed.translator_factory()
    except Exception as exc:  # pragma: no cover - defensive
        LOGGER.debug("Ash type lookup skipped; unable to load Watershed at %s (%s)", run_root, exc)
        return {}, {}
    try:
        ash = Ash.getInstance(str(run_root))
    except Exception as exc:  # pragma: no cover - defensive
        LOGGER.debug("Ash type lookup skipped; unable to load Ash at %s (%s)", run_root, exc)
        return {}, {}
    meta = ash.meta or {}
    defaults = _default_ash_bulk_densities()
    type_lookup: dict[int, str] = {}
    density_lookup: dict[int, float] = {}
    for wepp_id in wepp_ids:
        try:
            topaz_id = translator.top(wepp=int(wepp_id))
        except Exception:
            topaz_id = None
        meta_entry = None
        if topaz_id is not None:
            meta_entry = meta.get(topaz_id) or meta.get(str(topaz_id))
        if meta_entry is None:
            meta_entry = meta.get(str(wepp_id)) or meta.get(wepp_id)
        ash_type = _normalize_ash_type(meta_entry.get("ash_type") if isinstance(meta_entry, Mapping) else None)
        if ash_type:
            type_lookup[int(wepp_id)] = ash_type
        density_val: float | None = None
        if isinstance(meta_entry, Mapping):
            if "ash_bulkdensity" in meta_entry:
                try:
                    density_val = float(meta_entry["ash_bulkdensity"])
                except (TypeError, ValueError):
                    density_val = None
            elif "field_ash_bulkdensity" in meta_entry:
                try:
                    density_val = float(meta_entry["field_ash_bulkdensity"])
                except (TypeError, ValueError):
                    density_val = None
        if density_val is None and ash_type is not None:
            density_val = defaults.get(ash_type)
        if density_val is None:
            continue
        density_kg_m3 = density_val * 1000.0
        if density_kg_m3 > 0.0:
            density_lookup[int(wepp_id)] = density_kg_m3
    return type_lookup, density_lookup


def _locate_hillslope_path(ash_dir: Path, wepp_id: int) -> Path | None:
    candidates = [ash_dir / f"H{wepp_id}_ash.parquet", ash_dir / f"H{wepp_id}.parquet"]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _import_read_hillslope_out_fn():
    from wepppy.nodb.mods.ash_transport.ashpost import read_hillslope_out_fn

    return read_hillslope_out_fn


def _safe_mass_per_area(total: np.ndarray, area_ha: np.ndarray) -> np.ndarray:
    result = np.zeros_like(total, dtype=np.float64)
    np.divide(total, area_ha, out=result, where=area_ha > 0)
    return result


def _safe_volume_concentration(solids_volume: np.ndarray, runvol: np.ndarray) -> np.ndarray:
    result = np.zeros_like(runvol, dtype=np.float64)
    np.divide(solids_volume, runvol, out=result, where=runvol > 0.0)
    return result


def _compute_solids_volume(df: pd.DataFrame) -> np.ndarray:
    if df.empty:
        return np.zeros(0, dtype=np.float64)
    volumes = np.zeros(df.shape[0], dtype=np.float64)
    for column, density in zip(SEDIMENT_MASS_COLUMNS, SEDIMENT_DENSITY_KG_M3):
        masses = df[column].to_numpy(dtype=np.float64, copy=False)
        volumes += masses / density
    return volumes


def _compute_sediment_volumetric_concentration(df: pd.DataFrame) -> pd.Series:
    if df.empty:
        return pd.Series(dtype=np.float64, name=SEDIMENT_VOLUME_COLUMN)
    solids_volume = _compute_solids_volume(df)
    runvol = df["runvol"].to_numpy(dtype=np.float64, copy=False)
    concentration = np.zeros_like(solids_volume, dtype=np.float64)
    np.divide(solids_volume, runvol, out=concentration, where=runvol > 0.0)
    return pd.Series(concentration, index=df.index, name=SEDIMENT_VOLUME_COLUMN)


def _aggregate_ash_metrics(
    interchange_dir: Path,
    wepp_ids: list[int] | None,
    ash_dir_override: Path | str | None,
    ash_area_lookup: Mapping[int, float] | None,
) -> pd.DataFrame | None:
    ash_dir = _resolve_ash_dir(interchange_dir, ash_dir_override)
    if ash_dir is None or not ash_dir.exists():
        return None

    candidate_wepp_ids = _select_wepp_ids(ash_dir, wepp_ids)
    if not candidate_wepp_ids:
        return None

    area_lookup = {int(k): float(v) for k, v in (ash_area_lookup or {}).items()}
    run_root = _resolve_run_root(interchange_dir)
    if not area_lookup:
        area_lookup = _build_area_lookup_from_watershed(run_root, candidate_wepp_ids)

    if not area_lookup:
        return None

    ash_type_lookup, ash_density_lookup = _build_ash_type_and_density_lookup(run_root, candidate_wepp_ids)

    read_hillslope_out_fn = _import_read_hillslope_out_fn()

    frames: list[pd.DataFrame] = []
    for wepp_id in candidate_wepp_ids:
        area_ha = area_lookup.get(int(wepp_id))
        if area_ha is None or area_ha <= 0.0:
            LOGGER.debug("Ash merge skipping wepp_id=%s due to missing area", wepp_id)
            continue
        hillslope_path = _locate_hillslope_path(ash_dir, int(wepp_id))
        if hillslope_path is None:
            LOGGER.debug("Ash merge skipping wepp_id=%s; file not found", wepp_id)
            continue
        df = read_hillslope_out_fn(
            str(hillslope_path),
            meta_data={"area (ha)": area_ha},
            meta_data_types={"area (ha)": "float64"},
        )
        if df.empty:
            continue
        if "year0" in df.columns:
            df = df[df["year0"] == df["year"]]
        elif "days_from_fire (days)" in df.columns:
            df = df[df["days_from_fire (days)"] <= 365]
        if df.empty:
            continue
        df = df.rename(columns={"mo": "month", "da": "day_of_month"})
        if "month" not in df.columns or "day_of_month" not in df.columns:
            try:
                if {"year", "julian"}.issubset(df.columns):
                    ordinal = (
                        df["year"].to_numpy(dtype=np.int32, copy=False) * 1000
                        + df["julian"].to_numpy(dtype=np.int32, copy=False)
                    )
                elif "date_int" in df.columns:
                    ordinal = df["date_int"].to_numpy(dtype=np.int64, copy=False)
                else:
                    raise KeyError("missing year/julian for calendar resolution")
                dates = pd.to_datetime(ordinal.astype(str), format="%Y%j", errors="coerce")
                if dates.isna().any():
                    raise ValueError("unable to parse ordinal dates")
                if "month" not in df.columns:
                    df["month"] = dates.month.astype(np.int16)
                if "day_of_month" not in df.columns:
                    df["day_of_month"] = dates.day.astype(np.int16)
            except Exception as exc:  # pragma: no cover - defensive
                LOGGER.debug("Ash merge skipped; unable to derive calendar fields for %s (%s)", hillslope_path, exc)
                continue
        rename_map = {
            "wind_transport (tonne)": "wind_transport",
            "water_transport (tonne)": "water_transport",
            "ash_transport (tonne)": "ash_transport",
            "transportable_ash (tonne)": "transportable_ash",
            "wind_transport (tonne/ha)": "wind_transport_per_ha",
            "water_transport (tonne/ha)": "water_transport_per_ha",
            "ash_transport (tonne/ha)": "ash_transport_per_ha",
            "transportable_ash (tonne/ha)": "transportable_ash_per_ha",
        }
        df = df.rename(columns=rename_map)
        base_subset_columns = [
            "year",
            "month",
            "day_of_month",
            "julian",
            "area (ha)",
            *ASH_TONNE_COLUMNS,
        ]
        missing = [col for col in base_subset_columns if col not in df.columns]
        if missing:
            LOGGER.debug("Ash merge skipping %s; missing columns %s", hillslope_path, missing)
            continue
        ash_type = ash_type_lookup.get(int(wepp_id))
        ash_density = ash_density_lookup.get(int(wepp_id))
        ash_volume = np.zeros(df.shape[0], dtype=np.float64)
        if ash_density is not None and ash_density > 0.0:
            ash_volume = df["ash_transport"].to_numpy(dtype=np.float64, copy=False) * 1000.0 / float(ash_density)
        df["ash_solids_volume"] = ash_volume
        df["ash_black_solids_volume"] = ash_volume if ash_type == "black" else 0.0
        df["ash_white_solids_volume"] = ash_volume if ash_type == "white" else 0.0
        for ash_type_name in ASH_TYPES:
            df[f"area_{ash_type_name}_ha"] = area_ha if ash_type == ash_type_name else 0.0
        for base in ASH_TYPED_BASES:
            for ash_type_name in ASH_TYPES:
                col = f"{base}_{ash_type_name}"
                df[col] = df[base] if ash_type == ash_type_name else 0.0
        subset_columns = [
            *base_subset_columns,
            *ASH_TYPE_AREA_COLUMNS,
            *ASH_TYPED_TONNE_COLUMNS,
            *ASH_VOLUME_HELPER_COLUMNS,
        ]
        frames.append(df[subset_columns])

    if not frames:
        return None

    combined = pd.concat(frames, ignore_index=True)
    aggregations: dict[str, str] = {"area (ha)": "sum"}
    aggregations.update({name: "sum" for name in ASH_TONNE_COLUMNS})
    aggregations.update({name: "sum" for name in ASH_TYPE_AREA_COLUMNS})
    aggregations.update({name: "sum" for name in ASH_TYPED_TONNE_COLUMNS})
    aggregations.update({name: "sum" for name in ASH_VOLUME_HELPER_COLUMNS})
    grouped = combined.groupby(list(ASH_JOIN_COLUMNS), as_index=False).agg(aggregations)
    area = grouped["area (ha)"].to_numpy(dtype=np.float64, copy=False)
    for base in ASH_METRIC_BASES:
        total_col = base
        per_ha_col = f"{base}_per_ha"
        grouped[per_ha_col] = _safe_mass_per_area(
            grouped[total_col].to_numpy(dtype=np.float64, copy=False),
            area,
        )
    for ash_type_name in ASH_TYPES:
        area_col = f"area_{ash_type_name}_ha"
        area_by_type = grouped[area_col].to_numpy(dtype=np.float64, copy=False)
        for base in ASH_TYPED_BASES:
            total_col = f"{base}_{ash_type_name}"
            per_ha_col = f"{total_col}_per_ha"
            grouped[per_ha_col] = _safe_mass_per_area(
                grouped[total_col].to_numpy(dtype=np.float64, copy=False),
                area_by_type,
            )
    grouped.drop(columns=["area (ha)", *ASH_TYPE_AREA_COLUMNS], inplace=True)
    return grouped


def _build_where_clause(wepp_ids: list[int] | None) -> str:
    if wepp_ids is None:
        return ""
    if not wepp_ids:
        return "WHERE FALSE"
    id_list = ",".join(str(wepp_id) for wepp_id in wepp_ids)
    return f"WHERE wepp_id IN ({id_list})"


def _resolve_sim_day_column(path: Path) -> str:
    schema = pq.read_schema(path)
    if "sim_day_index" in schema.names:
        return "sim_day_index"
    if "day" in schema.names:
        return "day"
    raise KeyError(f"Neither 'sim_day_index' nor 'day' column present in {path}")


def _aggregate_pass(con: duckdb.DuckDBPyConnection, pass_path: Path, where_clause: str) -> pd.DataFrame:
    day_column = _resolve_sim_day_column(pass_path)
    query = f"""
        SELECT
            year,
            "{day_column}" AS sim_day_index,
            julian,
            month,
            day_of_month,
            water_year,
            SUM(runvol) AS runvol,
            SUM(sbrunv) AS sbrunv,
            SUM(tdet) AS tdet,
            SUM(tdep) AS tdep,
            SUM(sedcon_1 * runvol) AS seddep_1,
            SUM(sedcon_2 * runvol) AS seddep_2,
            SUM(sedcon_3 * runvol) AS seddep_3,
            SUM(sedcon_4 * runvol) AS seddep_4,
            SUM(sedcon_5 * runvol) AS seddep_5
        FROM read_parquet('{pass_path.as_posix()}')
        {where_clause}
        GROUP BY year, "{day_column}", julian, month, day_of_month, water_year
        ORDER BY year, julian, "{day_column}"
    """
    df = con.execute(query).df()
    df[SEDIMENT_VOLUME_COLUMN] = _compute_sediment_volumetric_concentration(df)
    return df


def _aggregate_wat(con: duckdb.DuckDBPyConnection, wat_path: Path, where_clause: str) -> pd.DataFrame:
    day_column = _resolve_sim_day_column(wat_path)
    query = f"""
        SELECT
            year,
            "{day_column}" AS sim_day_index,
            julian,
            month,
            day_of_month,
            water_year,
            SUM(Area) AS Area,
            SUM(P * 0.001 * Area) AS P,
            SUM(RM * 0.001 * Area) AS RM,
            SUM(Q * 0.001 * Area) AS Q,
            SUM(Dp * 0.001 * Area) AS Dp,
            SUM(latqcc * 0.001 * Area) AS latqcc,
            SUM(QOFE * 0.001 * Area) AS QOFE,
            SUM(Ep * 0.001 * Area) AS Ep,
            SUM(Es * 0.001 * Area) AS Es,
            SUM(Er * 0.001 * Area) AS Er,
            SUM(UpStrmQ * 0.001 * Area) AS UpStrmQ_volume,
            SUM(SubRIn * 0.001 * Area) AS SubRIn_volume,
            SUM("Total-Soil Water" * 0.001 * Area) AS Total_Soil_Water_volume,
            SUM(frozwt * 0.001 * Area) AS frozwt_volume,
            SUM("Snow-Water" * 0.001 * Area) AS Snow_Water_volume,
            SUM(Tile * 0.001 * Area) AS Tile_volume,
            SUM(Irr * 0.001 * Area) AS Irr_volume
        FROM read_parquet('{wat_path.as_posix()}')
        {where_clause}
        GROUP BY year, "{day_column}", julian, month, day_of_month, water_year
        ORDER BY year, julian, "{day_column}"
    """
    return con.execute(query).df()


def _safe_depth(volume: np.ndarray, area: np.ndarray) -> np.ndarray:
    result = np.zeros_like(volume, dtype=np.float64)
    np.divide(volume, area, out=result, where=area > 0)
    result *= 1000.0
    return result


def _compute_baseflow(percolation_mm: np.ndarray, baseflow_opts: BaseflowOpts) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    n = percolation_mm.size
    if n == 0:
        return (
            np.zeros(0, dtype=np.float64),
            np.zeros(0, dtype=np.float64),
            np.zeros(0, dtype=np.float64),
        )
    reservoir = np.zeros(n, dtype=np.float64)
    baseflow = np.zeros(n, dtype=np.float64)
    aquifer_losses = np.zeros(n, dtype=np.float64)
    reservoir[0] = baseflow_opts.gwstorage
    for idx in range(n):
        if idx == 0:
            continue
        aquifer_losses[idx - 1] = reservoir[idx - 1] * baseflow_opts.dscoeff
        reservoir[idx] = reservoir[idx - 1] - baseflow[idx - 1] + percolation_mm[idx] - aquifer_losses[idx - 1]
        baseflow[idx] = reservoir[idx] * baseflow_opts.bfcoeff
    return reservoir, baseflow, aquifer_losses


def _prepare_paths(interchange_dir: Path | str) -> _QueryTargets:
    base = Path(interchange_dir)
    pass_path = base / "H.pass.parquet"
    wat_path = base / "H.wat.parquet"
    output_path = base / "totalwatsed3.parquet"
    if not pass_path.exists():
        raise FileNotFoundError(pass_path)
    if not wat_path.exists():
        raise FileNotFoundError(wat_path)
    base.mkdir(parents=True, exist_ok=True)
    return _QueryTargets(pass_path=pass_path, wat_path=wat_path, output_path=output_path)


def _finalise_table(df: pd.DataFrame) -> pa.Table:
    if df.empty:
        return EMPTY_TABLE
    int16_cols = ["year", "julian", "water_year"]
    int32_cols = ["sim_day_index"]
    int8_cols = ["month", "day_of_month"]
    for col in int16_cols:
        df[col] = df[col].astype(np.int16, copy=False)
    for col in int32_cols:
        df[col] = df[col].astype(np.int32, copy=False)
    for col in int8_cols:
        df[col] = df[col].astype(np.int8, copy=False)
    float_cols = [name for name in SCHEMA.names if name not in int16_cols + int8_cols + int32_cols]
    for col in float_cols:
        df[col] = df[col].astype(np.float64, copy=False)
    df = df[SCHEMA.names]
    return pa.Table.from_pandas(df, schema=SCHEMA, preserve_index=False)


def run_totalwatsed3(
    interchange_dir: Path | str,
    baseflow_opts: BaseflowOpts,
    wepp_ids: Sequence[int] | None = None,
    *,
    ash_dir: Path | str | None = None,
    ash_area_lookup: Mapping[int, float] | None = None,
) -> Path:
    """Create ``totalwatsed3.parquet`` by fusing hydrology and ash transport outputs.

    Args:
        interchange_dir: Directory containing ``H.pass.parquet`` and ``H.wat.parquet``.
        baseflow_opts: Baseflow configuration applied to aggregated percolation depths.
        wepp_ids: Optional subset of hillslope WEPP identifiers to include.
        ash_dir: Optional override pointing at the ``ash`` directory. Defaults to
            ``<run>/ash`` derived from ``interchange_dir``.
        ash_area_lookup: Optional mapping of ``wepp_id`` → ``area_ha``. Supplying this
            skips Watershed lookups (useful for tests or bespoke batch jobs).
    """
    targets = _prepare_paths(interchange_dir)
    wepp_ids_normalized = _normalize_wepp_ids(wepp_ids)
    where_clause = _build_where_clause(wepp_ids_normalized)

    with duckdb.connect() as con:
        pass_df = _aggregate_pass(con, targets.pass_path, where_clause)
        wat_df = _aggregate_wat(con, targets.wat_path, where_clause)

    if wat_df.empty:
        table = EMPTY_TABLE
        pq.write_table(table, targets.output_path, compression="snappy", use_dictionary=True)
        return targets.output_path

    merged = wat_df.merge(pass_df, on=list(DATE_COLUMNS), how="left", suffixes=("", "_pass"))
    if pass_df.empty:
        merged[list(PASS_METRIC_COLUMNS)] = 0.0
    else:
        merged[list(PASS_METRIC_COLUMNS)] = merged[list(PASS_METRIC_COLUMNS)].fillna(0.0)

    ash_df = _aggregate_ash_metrics(Path(interchange_dir), wepp_ids_normalized, ash_dir, ash_area_lookup)
    if ash_df is None:
        for col in ASH_METRIC_COLUMNS:
            merged[col] = 0.0
        for col in ASH_VOLUME_HELPER_COLUMNS:
            merged[col] = 0.0
    else:
        merged = merged.merge(ash_df, on=list(ASH_JOIN_COLUMNS), how="left", validate="many_to_one")
        merged[list(ASH_METRIC_COLUMNS)] = merged[list(ASH_METRIC_COLUMNS)].fillna(0.0)
        for col in ASH_VOLUME_HELPER_COLUMNS:
            if col in merged:
                merged[col] = merged[col].fillna(0.0)
            else:
                merged[col] = 0.0

    area = merged["Area"].to_numpy(dtype=np.float64, copy=False)

    merged["UpStrmQ"] = _safe_depth(merged.pop("UpStrmQ_volume").to_numpy(dtype=np.float64, copy=False), area)
    merged["SubRIn"] = _safe_depth(merged.pop("SubRIn_volume").to_numpy(dtype=np.float64, copy=False), area)
    merged["Total-Soil Water"] = _safe_depth(merged.pop("Total_Soil_Water_volume").to_numpy(dtype=np.float64, copy=False), area)
    merged["frozwt"] = _safe_depth(merged.pop("frozwt_volume").to_numpy(dtype=np.float64, copy=False), area)
    merged["Snow-Water"] = _safe_depth(merged.pop("Snow_Water_volume").to_numpy(dtype=np.float64, copy=False), area)
    merged["Tile"] = _safe_depth(merged.pop("Tile_volume").to_numpy(dtype=np.float64, copy=False), area)
    merged["Irr"] = _safe_depth(merged.pop("Irr_volume").to_numpy(dtype=np.float64, copy=False), area)

    merged["Precipitation"] = _safe_depth(merged["P"].to_numpy(dtype=np.float64, copy=False), area)
    merged["Rain+Melt"] = _safe_depth(merged["RM"].to_numpy(dtype=np.float64, copy=False), area)
    merged["Percolation"] = _safe_depth(merged["Dp"].to_numpy(dtype=np.float64, copy=False), area)
    merged["Lateral Flow"] = _safe_depth(merged["latqcc"].to_numpy(dtype=np.float64, copy=False), area)
    merged["Runoff"] = _safe_depth(merged["QOFE"].to_numpy(dtype=np.float64, copy=False), area)

    merged["Transpiration"] = _safe_depth(merged["Ep"].to_numpy(dtype=np.float64, copy=False), area)
    evaporation_volume = merged["Es"].to_numpy(dtype=np.float64, copy=False) + merged["Er"].to_numpy(dtype=np.float64, copy=False)
    merged["Evaporation"] = _safe_depth(evaporation_volume, area)
    merged["ET"] = _safe_depth(
        merged["Ep"].to_numpy(dtype=np.float64, copy=False)
        + merged["Es"].to_numpy(dtype=np.float64, copy=False)
        + merged["Er"].to_numpy(dtype=np.float64, copy=False),
        area,
    )

    percolation_mm = merged["Percolation"].to_numpy(dtype=np.float64, copy=False)
    reservoir, baseflow, aquifer_losses = _compute_baseflow(percolation_mm, baseflow_opts)
    merged["Reservoir Volume"] = reservoir
    merged["Baseflow"] = baseflow
    merged["Aquifer losses"] = aquifer_losses
    merged["Streamflow"] = merged["Runoff"] + merged["Lateral Flow"] + merged["Baseflow"]

    runvol_volume = merged["runvol"].to_numpy(dtype=np.float64, copy=False)
    ash_solids_volume = merged["ash_solids_volume"].to_numpy(dtype=np.float64, copy=False)
    ash_black_volume = merged["ash_black_solids_volume"].to_numpy(dtype=np.float64, copy=False)
    merged[ASH_VOLUME_COLUMN] = _safe_volume_concentration(ash_solids_volume, runvol_volume)
    ash_black_pct = np.zeros_like(ash_solids_volume, dtype=np.float64)
    np.divide(ash_black_volume, ash_solids_volume, out=ash_black_pct, where=ash_solids_volume > 0.0)
    ash_black_pct *= 100.0
    merged[ASH_BLACK_PCT_COLUMN] = ash_black_pct
    sed_solids_volume = merged[SEDIMENT_VOLUME_COLUMN].to_numpy(dtype=np.float64, copy=False) * runvol_volume
    merged[SED_ASH_VOLUME_COLUMN] = _safe_volume_concentration(sed_solids_volume + ash_solids_volume, runvol_volume)
    merged.drop(columns=list(ASH_VOLUME_HELPER_COLUMNS), inplace=True, errors="ignore")

    merged = merged.sort_values(["year", "julian", "sim_day_index"], kind="mergesort").reset_index(drop=True)
    table = _finalise_table(merged)
    pq.write_table(table.combine_chunks(), targets.output_path, compression="snappy", use_dictionary=True)
    return targets.output_path


__all__ = ["run_totalwatsed3"]
