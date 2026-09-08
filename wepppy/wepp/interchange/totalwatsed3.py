from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence, TYPE_CHECKING, Any

import logging
import json
from importlib.metadata import version as distribution_version
import pyarrow as pa

from .schema_utils import pa_field
from .versioning import INTERCHANGE_VERSION, schema_with_version
from ._rust_interchange import call_wepppyo3_interchange

if TYPE_CHECKING:
    from wepppy.nodb.core.wepp import BaseflowOpts
else:
    BaseflowOpts = Any  # type: ignore[assignment]

LOGGER = logging.getLogger(__name__)

ASH_VOLUME_COLUMN = "ash_vol_conc"
SED_ASH_VOLUME_COLUMN = "sed+ash_vol_conc"
ASH_BLACK_PCT_COLUMN = "ash_black_pct_by_vol"

# Ash columns are unitless in names; units live in schema metadata
ASH_TYPES = ("black", "white")
ASH_METRIC_BASES = ("wind_transport", "water_transport", "ash_transport", "transportable_ash")
ASH_TYPED_BASES = ("wind_transport", "water_transport", "ash_transport")
ASH_TONNE_COLUMNS = ASH_METRIC_BASES
ASH_PER_HA_COLUMNS = tuple(f"{name}_per_ha" for name in ASH_METRIC_BASES)
ASH_TYPED_TONNE_COLUMNS = tuple(f"{base}_{ash_type}" for ash_type in ASH_TYPES for base in ASH_TYPED_BASES)
ASH_TYPED_PER_HA_COLUMNS = tuple(f"{name}_per_ha" for name in ASH_TYPED_TONNE_COLUMNS)
ASH_METRIC_COLUMNS = ASH_TONNE_COLUMNS + ASH_PER_HA_COLUMNS + ASH_TYPED_TONNE_COLUMNS + ASH_TYPED_PER_HA_COLUMNS

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
            pa_field("sed_del", pa.float64(), units="kg", description="Total sediment delivery (sum of class masses)"),
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
            pa_field("SoilWaterTotal", pa.float64(), units="mm", description="Area-weighted full-profile soil water depth (watcon + frozwt)"),
            pa_field("ProfileDepth", pa.float64(), units="mm", description="Area-weighted full soil profile depth (solthk(nsl))"),
            pa_field("ProfilePorosityCap", pa.float64(), units="mm", description="Area-weighted full-profile porosity storage capacity (sum(por * dg))"),
            pa_field("ProfileFCStore", pa.float64(), units="mm", description="Area-weighted full-profile field-capacity storage (sum(thetfc * dg))"),
            pa_field("ProfileWPStore", pa.float64(), units="mm", description="Area-weighted full-profile wilting-point storage (sum(thetdr * dg))"),
            pa_field("InterceptionStorage", pa.float64(), units="mm", description="Area-weighted plant/residue interception carryover storage depth (pintlv + resint)"),
            pa_field("TSMF", pa.float64(), units="frac", description="Area-weighted true soil moisture fraction (full profile)"),
            pa_field("frozwt", pa.float64(), units="mm", description="Frozen water in soil profile depth"),
            pa_field("Snow-Water", pa.float64(), units="mm", description="Water in surface snow depth"),
            pa_field("QRain", pa.float64(), units="mm", description="Area-weighted rain-generated runoff depth from element partitioning"),
            pa_field("QSnow", pa.float64(), units="mm", description="Area-weighted snow-generated runoff depth from element partitioning"),
            pa_field("Tile", pa.float64(), units="mm", description="Tile drainage depth"),
            pa_field("Irr", pa.float64(), units="mm", description="Irrigation depth"),
            pa_field("Precipitation", pa.float64(), units="mm", description="Precipitation depth"),
            pa_field("Rain+Melt", pa.float64(), units="mm", description="Rainfall+Irrigation+Snowmelt depth"),
            pa_field("Percolation", pa.float64(), units="mm", description="Deep percolation depth"),
            pa_field("Lateral Flow", pa.float64(), units="mm", description="Lateral subsurface flow depth"),
            pa_field("Runoff", pa.float64(), units="mm", description="Daily runoff depth from PASS runoff volume"),
            pa_field("Transpiration", pa.float64(), units="mm", description="Plant transpiration depth"),
            pa_field("Evaporation", pa.float64(), units="mm", description="Soil + residue evaporation depth"),
            pa_field("ET", pa.float64(), units="mm", description="Total evapotranspiration depth"),
            pa_field("Interception", pa.float64(), units="mm", description="Daily canopy/residue interception flux depth (optional producer-authoritative outflow)"),
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


@dataclass(frozen=True)
class _QueryTargets:
    pass_path: Path
    wat_path: Path
    soil_path: Path | None
    element_path: Path | None
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


def _native_ash_inputs(
    interchange_dir: Path,
    wepp_ids: list[int] | None,
    ash_dir_override: Path | str | None,
    ash_area_lookup: Mapping[int, float] | None,
) -> list[tuple[str, float, str | None, float | None]]:
    """Resolve files and controller metadata; native code reads all ash rows."""
    ash_dir = _resolve_ash_dir(interchange_dir, ash_dir_override)
    if ash_dir is None or not ash_dir.exists():
        return []
    ids = _select_wepp_ids(ash_dir, wepp_ids)
    if not ids:
        return []
    areas = {int(k): float(v) for k, v in (ash_area_lookup or {}).items()}
    run_root = _resolve_run_root(interchange_dir)
    if not areas:
        areas = _build_area_lookup_from_watershed(run_root, ids)
    if not areas:
        return []
    types, densities = _build_ash_type_and_density_lookup(run_root, ids)
    inputs = []
    for wepp_id in ids:
        area = areas.get(wepp_id)
        path = _locate_hillslope_path(ash_dir, wepp_id)
        if area is None or area <= 0.0 or path is None:
            continue
        inputs.append((str(path), area, types.get(wepp_id), densities.get(wepp_id)))
    return inputs


def _pandas_schema_metadata() -> str:
    """Preserve legacy Arrow metadata without importing pandas or building frames."""
    columns = []
    for field in SCHEMA:
        dtype = "float64" if pa.types.is_floating(field.type) else str(field.type)
        columns.append({"name": field.name, "field_name": field.name,
                        "pandas_type": dtype, "numpy_type": dtype, "metadata": None})
    return json.dumps({"index_columns": [], "column_indexes": [], "columns": columns,
                       "attributes": {}, "creator": {"library": "pyarrow", "version": pa.__version__},
                       "pandas_version": distribution_version("pandas")})


def _prepare_paths(interchange_dir: Path | str) -> _QueryTargets:
    base = Path(interchange_dir)
    pass_path = base / "H.pass.parquet"
    wat_path = base / "H.wat.parquet"
    soil_path = base / "H.soil.parquet"
    element_path = base / "H.element.parquet"
    output_path = base / "totalwatsed3.parquet"
    if not pass_path.exists():
        raise FileNotFoundError(pass_path)
    if not wat_path.exists():
        raise FileNotFoundError(wat_path)
    base.mkdir(parents=True, exist_ok=True)
    return _QueryTargets(
        pass_path=pass_path,
        wat_path=wat_path,
        soil_path=soil_path if soil_path.exists() else None,
        element_path=element_path if element_path.exists() else None,
        output_path=output_path,
    )


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
    call_wepppyo3_interchange(
        "totalwatsed3", "totalwatsed3_to_parquet",
        str(targets.pass_path), str(targets.wat_path), str(targets.output_path),
        float(baseflow_opts.gwstorage), float(baseflow_opts.bfcoeff), float(baseflow_opts.dscoeff),
        INTERCHANGE_VERSION.major, INTERCHANGE_VERSION.minor,
        soil_path=str(targets.soil_path) if targets.soil_path is not None else None,
        element_path=str(targets.element_path) if targets.element_path is not None else None,
        wepp_ids=wepp_ids_normalized,
        ash_inputs=_native_ash_inputs(Path(interchange_dir), wepp_ids_normalized, ash_dir, ash_area_lookup),
        pandas_metadata=_pandas_schema_metadata(),
    )
    return targets.output_path


__all__ = ["run_totalwatsed3"]
