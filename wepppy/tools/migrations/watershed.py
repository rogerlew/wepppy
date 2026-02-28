"""Watershed-related migrations."""

from __future__ import annotations

import json
import pickle
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from wepppy.tools.migrations.parquet_paths import pick_existing_parquet_path

__all__ = [
    "migrate_watersheds",
    "migrate_watershed_nodb_slim",
    "migrate_wbt_geojson",
]


def _extract_py_tuple(value: Any) -> Optional[Tuple[Any, ...]]:
    if isinstance(value, dict) and "py/tuple" in value:
        tuple_value = value.get("py/tuple")
        if isinstance(tuple_value, list):
            return tuple(tuple_value)
        if isinstance(tuple_value, tuple):
            return tuple_value
        return None
    if isinstance(value, (list, tuple)):
        return tuple(value)
    return None


def _coerce_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        as_float = float(value)
    except (TypeError, ValueError):
        return None
    if not as_float.is_integer():
        return None
    return int(as_float)


def _coerce_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _extract_centroid_fields(centroid: Any) -> Tuple[Optional[int], Optional[int], Optional[float], Optional[float]]:
    if not isinstance(centroid, dict):
        return None, None, None, None
    px = _extract_py_tuple(centroid.get("px"))
    lnglat = _extract_py_tuple(centroid.get("lnglat"))
    centroid_px = _coerce_int(px[0]) if px and len(px) > 0 else None
    centroid_py = _coerce_int(px[1]) if px and len(px) > 1 else None
    centroid_lon = _coerce_float(lnglat[0]) if lnglat and len(lnglat) > 0 else None
    centroid_lat = _coerce_float(lnglat[1]) if lnglat and len(lnglat) > 1 else None
    return centroid_px, centroid_py, centroid_lon, centroid_lat


def _parse_flowpath_id(flow_key: Any) -> Optional[int]:
    if not isinstance(flow_key, str):
        return None
    parts = flow_key.split("_")
    if len(parts) >= 2:
        try:
            return int(parts[-1])
        except ValueError:
            return None
    return None


def _legacy_hillslope_rows(summaries: Any) -> List[Dict[str, Any]]:
    if not isinstance(summaries, dict):
        return []
    rows: List[Dict[str, Any]] = []
    for key, summary in summaries.items():
        if not isinstance(summary, dict):
            continue
        topaz_id = _coerce_int(summary.get("topaz_id", key))
        if topaz_id is None:
            continue
        centroid_px, centroid_py, centroid_lon, centroid_lat = _extract_centroid_fields(
            summary.get("centroid")
        )
        rows.append(
            {
                "topaz_id": topaz_id,
                "slope_scalar": _coerce_float(summary.get("slope_scalar")),
                "length": _coerce_float(summary.get("length")),
                "width": _coerce_float(summary.get("width")),
                "direction": _coerce_float(summary.get("direction")),
                "aspect": _coerce_float(summary.get("aspect")),
                "area": _coerce_float(summary.get("area")),
                "elevation": _coerce_float(summary.get("elevation")),
                "centroid_px": centroid_px,
                "centroid_py": centroid_py,
                "centroid_lon": centroid_lon,
                "centroid_lat": centroid_lat,
                "wepp_id": _coerce_int(summary.get("wepp_id")),
            }
        )
    return rows


def _legacy_channel_rows(summaries: Any) -> List[Dict[str, Any]]:
    if not isinstance(summaries, dict):
        return []
    rows: List[Dict[str, Any]] = []
    for key, summary in summaries.items():
        if not isinstance(summary, dict):
            continue
        topaz_id = _coerce_int(summary.get("topaz_id", key))
        if topaz_id is None:
            continue
        centroid_px, centroid_py, centroid_lon, centroid_lat = _extract_centroid_fields(
            summary.get("centroid")
        )
        rows.append(
            {
                "topaz_id": topaz_id,
                "slope_scalar": _coerce_float(summary.get("slope_scalar")),
                "length": _coerce_float(summary.get("length")),
                "width": _coerce_float(summary.get("width")),
                "direction": _coerce_float(summary.get("direction")),
                "order": _coerce_int(summary.get("order", summary.get("_order"))),
                "aspect": _coerce_float(summary.get("aspect")),
                "area": _coerce_float(summary.get("area")),
                "elevation": _coerce_float(summary.get("elevation")),
                "centroid_px": centroid_px,
                "centroid_py": centroid_py,
                "centroid_lon": centroid_lon,
                "centroid_lat": centroid_lat,
                "wepp_id": _coerce_int(summary.get("wepp_id")),
                "chn_enum": _coerce_int(summary.get("chn_enum")),
            }
        )
    return rows


def _legacy_flowpath_rows(summaries: Any) -> List[Dict[str, Any]]:
    if not isinstance(summaries, dict):
        return []
    rows: List[Dict[str, Any]] = []
    for topaz_key, flowpaths in summaries.items():
        if not isinstance(flowpaths, dict):
            continue
        for flow_key, summary in flowpaths.items():
            if not isinstance(summary, dict):
                continue
            topaz_id = _coerce_int(summary.get("topaz_id", topaz_key))
            fp_id = _parse_flowpath_id(flow_key)
            if topaz_id is None or fp_id is None:
                continue
            centroid_px, centroid_py, centroid_lon, centroid_lat = _extract_centroid_fields(
                summary.get("centroid")
            )
            rows.append(
                {
                    "topaz_id": topaz_id,
                    "fp_id": fp_id,
                    "slope_scalar": _coerce_float(summary.get("slope_scalar")),
                    "length": _coerce_float(summary.get("length")),
                    "width": _coerce_float(summary.get("width")),
                    "direction": _coerce_float(summary.get("direction")),
                    "aspect": _coerce_float(summary.get("aspect")),
                    "area": _coerce_float(summary.get("area")),
                    "elevation": _coerce_float(summary.get("elevation")),
                    "order": None,
                    "centroid_px": centroid_px,
                    "centroid_py": centroid_py,
                    "centroid_lon": centroid_lon,
                    "centroid_lat": centroid_lat,
                }
            )
    return rows


def _write_legacy_parquet(
    rows: List[Dict[str, Any]],
    target: Path,
    columns: List[str],
    *,
    int32_columns: Tuple[str, ...] = (),
    int64_columns: Tuple[str, ...] = (),
    float_columns: Tuple[str, ...] = (),
    dry_run: bool = False,
) -> Tuple[bool, str]:
    if not rows:
        return True, ""
    if dry_run:
        return True, f"Would generate {target.name} from watershed.nodb summaries"

    try:
        import pandas as pd
        import pyarrow
    except ImportError:
        return False, "PyArrow/Pandas not available"

    df = pd.DataFrame(rows)
    for col in columns:
        if col not in df.columns:
            df[col] = pd.NA
    df = df[columns]

    for col in int32_columns:
        if col in df.columns:
            df[col] = pd.array(df[col], dtype="Int32")
    for col in int64_columns:
        if col in df.columns:
            df[col] = pd.array(df[col], dtype="Int64")
    for col in float_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df.to_parquet(target, index=False, engine="pyarrow")
    return True, f"Generated {target.name} from watershed.nodb summaries"


def migrate_watersheds(wd: str, *, dry_run: bool = False, keep_csv: bool = False) -> Tuple[bool, str]:
    """
    Normalize watershed parquet schemas (Peridot tables).

    Converts legacy CSV files to Parquet and normalizes ID columns.
    Idempotent: safe to run multiple times.

    Args:
        wd: Working directory path
        dry_run: If True, report but don't modify
        keep_csv: If True, don't delete legacy CSV files

    Returns:
        (applied, message) tuple
    """
    run_path = Path(wd)
    watershed_dir = run_path / "watershed"
    watershed_nodb = run_path / "watershed.nodb"
    sidecar_parquets = [
        watershed_dir / "hillslopes.parquet",
        watershed_dir / "channels.parquet",
        watershed_dir / "flowpaths.parquet",
    ]
    sidecar_parquets = [path for path in sidecar_parquets if path.is_file()]
    if not watershed_dir.exists() and not watershed_nodb.exists() and not sidecar_parquets:
        return True, "No watershed data (nothing to migrate)"

    # Check if any parquet OR csv files exist (CSVs are converted to parquet)
    parquet_files = list(watershed_dir.glob("*.parquet"))
    csv_files = list(watershed_dir.glob("*.csv"))

    if not parquet_files and not csv_files and not sidecar_parquets:
        if not watershed_nodb.exists():
            return True, "No watershed data files (nothing to migrate)"
        try:
            with open(watershed_nodb, "r") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            return False, f"Failed to read watershed.nodb: {exc}"

        state = data.get("py/state", data)
        if not isinstance(state, dict):
            return True, "No watershed data files (nothing to migrate)"

        if not dry_run:
            watershed_dir.mkdir(parents=True, exist_ok=True)

        messages = []
        hillslope_rows = _legacy_hillslope_rows(state.get("_subs_summary"))
        applied, message = _write_legacy_parquet(
            hillslope_rows,
            watershed_dir / "hillslopes.parquet",
            [
                "topaz_id",
                "slope_scalar",
                "length",
                "width",
                "direction",
                "aspect",
                "area",
                "elevation",
                "centroid_px",
                "centroid_py",
                "centroid_lon",
                "centroid_lat",
                "wepp_id",
            ],
            int32_columns=("topaz_id", "wepp_id"),
            int64_columns=("centroid_px", "centroid_py"),
            float_columns=(
                "slope_scalar",
                "length",
                "width",
                "direction",
                "aspect",
                "area",
                "elevation",
                "centroid_lon",
                "centroid_lat",
            ),
            dry_run=dry_run,
        )
        if not applied:
            return False, message
        if message:
            messages.append(message)

        channel_rows = _legacy_channel_rows(state.get("_chns_summary"))
        applied, message = _write_legacy_parquet(
            channel_rows,
            watershed_dir / "channels.parquet",
            [
                "topaz_id",
                "slope_scalar",
                "length",
                "width",
                "direction",
                "order",
                "aspect",
                "area",
                "elevation",
                "centroid_px",
                "centroid_py",
                "centroid_lon",
                "centroid_lat",
                "wepp_id",
                "chn_enum",
            ],
            int32_columns=("topaz_id", "wepp_id", "chn_enum"),
            int64_columns=("centroid_px", "centroid_py", "order"),
            float_columns=(
                "slope_scalar",
                "length",
                "width",
                "direction",
                "aspect",
                "area",
                "elevation",
                "centroid_lon",
                "centroid_lat",
            ),
            dry_run=dry_run,
        )
        if not applied:
            return False, message
        if message:
            messages.append(message)

        flowpath_rows = _legacy_flowpath_rows(state.get("_fps_summary"))
        applied, message = _write_legacy_parquet(
            flowpath_rows,
            watershed_dir / "flowpaths.parquet",
            [
                "topaz_id",
                "fp_id",
                "slope_scalar",
                "length",
                "width",
                "direction",
                "aspect",
                "area",
                "elevation",
                "order",
                "centroid_px",
                "centroid_py",
                "centroid_lon",
                "centroid_lat",
            ],
            int32_columns=("topaz_id", "fp_id"),
            int64_columns=("centroid_px", "centroid_py", "order"),
            float_columns=(
                "slope_scalar",
                "length",
                "width",
                "direction",
                "aspect",
                "area",
                "elevation",
                "centroid_lon",
                "centroid_lat",
            ),
            dry_run=dry_run,
        )
        if not applied:
            return False, message
        if message:
            messages.append(message)

        if messages:
            return True, "; ".join(messages)
        return True, "No watershed data files (nothing to migrate)"

    # Check if CSV files need conversion
    needs_csv_conversion = bool(csv_files)

    # Check if parquet files need schema normalization
    parquet_scan_files = sidecar_parquets or parquet_files
    needs_normalization = False
    if parquet_scan_files and not needs_csv_conversion:
        try:
            import pyarrow.parquet as pq
            for pf in parquet_scan_files[:3]:  # Sample first few files
                try:
                    schema = pq.read_schema(pf)
                    col_names = [f.name for f in schema]
                    # Check for legacy uppercase ID columns
                    if any(
                        c in col_names
                        for c in [
                            "TOPAZ_ID",
                            "TopazID",
                            "Topaz_ID",
                            "WEPP_ID",
                            "WeppID",
                            "Wepp_ID",
                        ]
                    ):
                        needs_normalization = True
                        break
                except Exception:
                    continue
        except ImportError:
            # Can't check without pyarrow, assume normalization needed
            needs_normalization = True

    if dry_run:
        if needs_csv_conversion:
            return True, f"Would convert {len(csv_files)} CSV file(s) to Parquet"
        if needs_normalization:
            return True, f"Would normalize {len(parquet_scan_files)} watershed parquet file(s)"
        return True, "Watershed tables already normalized (nothing to migrate)"

    try:
        from wepppy.topo.peridot.peridot_runner import migrate_watershed_outputs
        changed = migrate_watershed_outputs(str(run_path), remove_csv=not keep_csv, verbose=False)
    except ImportError:
        return True, "Peridot migration not available (skipped)"
    except Exception as exc:
        return False, f"Watershed migration failed: {exc}"

    if changed:
        return True, "Normalized watershed tables (CSV to Parquet conversion)"
    return True, "Watershed tables already normalized"


def migrate_watershed_nodb_slim(wd: str, *, dry_run: bool = False) -> Tuple[bool, str]:
    """
    Remove legacy summary dictionaries from watershed.nodb and externalize structure.

    After parquet files exist (hillslopes.parquet, flowpaths.parquet, channels.parquet),
    the _subs_summary, _fps_summary, and _chns_summary dictionaries are no longer needed
    in watershed.nodb. Removing them reduces file size dramatically for large watersheds.

    Also migrates inline _structure data to structure.json file if not already externalized.

    Idempotent: safe to run multiple times.

    Args:
        wd: Working directory path
        dry_run: If True, report but don't modify

    Returns:
        (applied, message) tuple
    """
    run_path = Path(wd)
    watershed_nodb = run_path / "watershed.nodb"
    watershed_dir = run_path / "watershed"

    if not watershed_nodb.exists():
        return True, "No watershed.nodb (nothing to migrate)"

    # Check that required parquet files exist
    required_parquets = [
        "watershed/hillslopes.parquet",
        "watershed/flowpaths.parquet",
        "watershed/channels.parquet",
    ]
    missing_parquets = [
        logical for logical in required_parquets if pick_existing_parquet_path(run_path, logical) is None
    ]

    if missing_parquets:
        return True, f"Missing parquet files: {', '.join(missing_parquets)} (skipped)"

    # Load watershed.nodb
    try:
        with open(watershed_nodb, "r") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        return False, f"Failed to read watershed.nodb: {exc}"

    # The nodb format stores state under py/state for jsonpickle serialization
    state = data.get("py/state", data)

    # Track what we're changing
    changes = []

    # Check for legacy summary dictionaries that contain actual summary objects
    # After migration, these will be dicts like {str(id): None} which don't need migration
    def needs_slimming(key: str) -> bool:
        val = state.get(key)
        if val is None:
            return False
        if not isinstance(val, dict):
            return True  # Unexpected format, try to migrate
        # Check if any values are non-None (actual summary objects)
        return any(v is not None for v in val.values())

    legacy_keys = ["_subs_summary", "_fps_summary", "_chns_summary"]
    found_keys = [k for k in legacy_keys if needs_slimming(k)]

    # Check for inline _structure that needs to be externalized
    structure_json_path = watershed_dir / "structure.json"
    structure_data = state.get("_structure")
    legacy_pickle_path = None
    needs_structure_migration = False

    if structure_json_path.exists():
        needs_structure_migration = False
    elif isinstance(structure_data, str):
        structure_path = Path(structure_data)
        if structure_path.suffix == ".pkl" and structure_path.exists():
            legacy_pickle_path = structure_path
            needs_structure_migration = True
        elif structure_path.suffix == ".json" and structure_path.exists():
            needs_structure_migration = False
    elif structure_data is not None:
        needs_structure_migration = True
    else:
        fallback_pickle = watershed_dir / "structure.pkl"
        if fallback_pickle.exists():
            legacy_pickle_path = fallback_pickle
            needs_structure_migration = True

    if not found_keys and not needs_structure_migration:
        return True, "No legacy summaries or inline structure in watershed.nodb"

    # Calculate size savings
    original_size = len(json.dumps(data))

    if dry_run:
        msgs = []
        if found_keys:
            msgs.append(f"slim {len(found_keys)} legacy summary dict(s)")
        if needs_structure_migration:
            msgs.append("externalize _structure to structure.json")
        return True, f"Would {' and '.join(msgs)}"

    # Load topaz_ids from parquet files to create placeholder dicts
    # This maintains backward compatibility with code that iterates over _subs_summary/_chns_summary
    try:
        import duckdb
        con = duckdb.connect()

        hillslopes_path = pick_existing_parquet_path(run_path, "watershed/hillslopes.parquet")
        channels_path = pick_existing_parquet_path(run_path, "watershed/channels.parquet")
        if hillslopes_path is None or channels_path is None:
            raise FileNotFoundError("Missing required watershed parquet files")
        hillslopes_parquet = str(hillslopes_path)
        channels_parquet = str(channels_path)

        sub_ids = [
            row[0]
            for row in con.execute(
                f"SELECT topaz_id FROM read_parquet('{hillslopes_parquet}')"
            ).fetchall()
        ]
        chn_ids = [
            row[0]
            for row in con.execute(
                f"SELECT topaz_id FROM read_parquet('{channels_parquet}')"
            ).fetchall()
        ]
        con.close()
    except Exception as exc:
        return False, f"Failed to read topaz_ids from parquet: {exc}"

    # Replace legacy dictionaries with placeholder dicts containing just the IDs
    # This maintains iteration compatibility while dropping the actual summary objects
    if "_subs_summary" in found_keys:
        state["_subs_summary"] = {str(topaz_id): None for topaz_id in sub_ids}
        changes.append("slimmed _subs_summary")
    if "_chns_summary" in found_keys:
        state["_chns_summary"] = {str(topaz_id): None for topaz_id in chn_ids}
        changes.append("slimmed _chns_summary")
    if "_fps_summary" in found_keys:
        state["_fps_summary"] = None  # flowpaths don't need iteration compatibility
        changes.append("removed _fps_summary")

    # Externalize _structure to JSON file if needed
    if needs_structure_migration:
        try:
            structure_obj = None

            if legacy_pickle_path is not None:
                with open(legacy_pickle_path, "rb") as f:
                    structure_obj = pickle.load(f)
            elif structure_data is not None and not isinstance(structure_data, str):
                # The structure data from JSON needs to be decoded via jsonpickle
                import jsonpickle
                structure_json = json.dumps(structure_data)
                structure_obj = jsonpickle.decode(structure_json)

            if structure_obj is None:
                raise ValueError("structure data unavailable for migration")

            normalized_structure = [
                [int(value) for value in row] for row in structure_obj
            ]

            with open(structure_json_path, "w", encoding="utf-8") as f:
                json.dump(normalized_structure, f)

            # Update _structure to be the path string
            state["_structure"] = str(structure_json_path)
            changes.append("externalized _structure to structure.json")
        except Exception as exc:
            # Non-fatal - structure migration can be skipped
            changes.append(f"_structure migration skipped: {exc}")

    # Write updated watershed.nodb
    try:
        with open(watershed_nodb, "w") as f:
            json.dump(data, f, indent=2)
    except OSError as exc:
        return False, f"Failed to write watershed.nodb: {exc}"

    # Calculate new size
    new_size = len(json.dumps(data))
    saved_mb = (original_size - new_size) / (1024 * 1024)

    return True, f"{', '.join(changes)}, saved {saved_mb:.1f} MB"


def migrate_wbt_geojson(wd: str, *, dry_run: bool = False) -> Tuple[bool, str]:
    """
    Normalize TopazID/WeppID in WhiteboxTools GeoJSON files.

    Idempotent: safe to run multiple times.

    Args:
        wd: Working directory path
        dry_run: If True, report but don't modify

    Returns:
        (applied, message) tuple
    """
    run_path = Path(wd)
    wbt_dir = run_path / "dem" / "wbt"

    if not wbt_dir.exists():
        return True, "No WBT directory (nothing to migrate)"

    target_files = [
        "channels.geojson",
        "channels.WGS.geojson",
        "subcatchments.geojson",
        "subcatchments.WGS.geojson",
    ]

    existing_files = [wbt_dir / f for f in target_files if (wbt_dir / f).exists()]
    if not existing_files:
        return True, "No WBT GeoJSON files (nothing to migrate)"

    def _coerce_int(value) -> Tuple[bool, Any]:
        try:
            ivalue = int(value)
        except (TypeError, ValueError):
            try:
                ivalue = int(str(value))
            except (TypeError, ValueError):
                return False, value
        return (ivalue != value), ivalue

    def _normalize_feature(props: Dict[str, Any]) -> bool:
        changed = False
        for key in ("TopazID", "WeppID", "Order"):
            if key in props:
                delta, coerced = _coerce_int(props[key])
                if delta:
                    props[key] = coerced
                    changed = True
        return changed

    total_changed = 0
    files_modified = 0

    for geojson_path in existing_files:
        try:
            with open(geojson_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue

        features = data.get("features", [])
        file_changed = False

        for feature in features:
            props = feature.get("properties") if isinstance(feature, dict) else None
            if isinstance(props, dict) and _normalize_feature(props):
                total_changed += 1
                file_changed = True

        if file_changed:
            files_modified += 1
            if not dry_run:
                with open(geojson_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, allow_nan=False)

    if total_changed == 0:
        return True, "WBT GeoJSON already normalized"

    action = "Would normalize" if dry_run else "Normalized"
    return True, f"{action} {total_changed} feature(s) in {files_modified} file(s)"
