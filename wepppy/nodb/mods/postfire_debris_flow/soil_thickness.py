"""Offline M3 thickness study; no acquisition or NoDb mutations.

See docs/m3_soil_thickness.md and ADR-0053. Partial estimates are diagnostics,
not approval to substitute SSURGO in the calibrated model.
"""
from __future__ import annotations

from collections import defaultdict
import csv
import hashlib
import json
import math
from pathlib import Path
import re
import sqlite3
import typing

__all__ = ["derive_component", "derive_mapunits", "read_cache", "build_artifacts"]


def _number(value):
    if value is None or value == "":
        return None
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return result if math.isfinite(result) else None


def _reasons(values):
    return ";".join(sorted(set(values)))


def derive_component(horizons: typing.Iterable[typing.Mapping], *, policy="strict_soil") -> dict:
    """Derive cm thickness and audit interval alternatives for one component."""
    if policy not in {"strict_soil", "all_layers"}:
        raise ValueError("Unknown interval policy")
    rows, reasons = [], set()
    seen: dict[str, tuple] = {}
    fields = ("hzdept_r", "hzdepb_r", "hzthk_r", "desgnmaster", "hzname")
    for row in horizons:
        key = str(row.get("chkey", ""))
        signature = tuple(row.get(f) for f in fields)
        if not key or key == "None":
            reasons.add("duplicate_id_conflict")
        elif key in seen:
            if seen[key] != signature:
                reasons.add("duplicate_id_conflict")
            continue
        seen[key] = signature
        rows.append(row)
    intervals, soil = [], []
    for row in rows:
        top, bottom, reported = (_number(row.get(f)) for f in fields[:3])
        if top is None or bottom is None or top < 0 or bottom <= top:
            reasons.add("invalid_depth")
            continue
        intervals.append((top, bottom))
        if row.get("hzthk_r") not in (None, "") and (
            reported is None or not math.isclose(reported, bottom-top, abs_tol=1e-9, rel_tol=0)
        ):
            reasons.add("thickness_conflict")
        master = str(row.get("desgnmaster") or "").strip()
        name = str(row.get("hzname") or "").strip()
        if policy == "all_layers":
            soil.append((top, bottom))
        elif master == "R" and re.fullmatch(r"\d*R\d*", name):
            reasons.add("bedrock_excluded")
        elif (not master or not re.fullmatch(r"[OAEBC]+(?:/| and )?[OAEBC]*", master)
              or re.search(r"\d*C[^A-Z]*r", name) or "R" in name):
            reasons.add("ambiguous_material")
        else:
            soil.append((top, bottom))
    intervals.sort()
    union, end = 0.0, None
    for top, bottom in intervals:
        if end is None:
            if top != 0:
                reasons.add("nonzero_start")
        elif top < end:
            reasons.add("overlap")
        elif top > end:
            reasons.add("gap")
        union += max(0, bottom-max(top, end if end is not None else top))
        end = max(end or 0, bottom)
    # Excluded material cannot bridge two soil intervals or precede deeper soil.
    soil.sort()
    if soil and (soil[0][0] != 0 or any(a[1] != b[0] for a, b in zip(soil, soil[1:]))):
        reasons.add("gap")
    if not rows:
        reasons.add("missing_horizons")
    fatal = reasons - {"bedrock_excluded"}
    depth = None if fatal else sum(b-a for a, b in soil)
    if depth is not None and not math.isfinite(depth):
        raise ValueError("Nonfinite derived component thickness")
    status = "unavailable" if depth is None else "valid"
    if depth == 0:
        status = "nonsoil"
        reasons.add("nonsoil")
    return dict(thickness_cm=depth, status=status, reason_codes=_reasons(reasons),
                horizon_count=len(rows), interval_sum_cm=sum(b-a for a, b in intervals),
                interval_union_cm=union, deepest_bottom_cm=end)


def _key(value):
    text = str(value)
    if not re.fullmatch(r"[0-9]+", text) or int(text) <= 0:
        raise ValueError(f"Expected positive integer source key: {value!r}")
    return str(int(text))


def derive_mapunits(components, horizons, *, policy="strict_soil", substituted_mukeys=()):
    """Return component and map-unit audit rows with explicit weight support."""
    by_component = defaultdict(list)
    owners = {}
    for h in horizons:
        ck, hk = _key(h["cokey"]), _key(h["chkey"])
        if hk in owners and owners[hk] != ck:
            raise ValueError("Horizon ID belongs to multiple components")
        owners[hk] = ck
        by_component[ck].append(dict(h, cokey=ck, chkey=hk))
    component_rows, groups, seen = [], defaultdict(list), set()
    for c in components:
        ck, mk = _key(c["cokey"]), _key(c["mukey"])
        if ck in seen:
            raise ValueError(f"Duplicate component ID: {ck}")
        seen.add(ck)
        row = dict(mukey=mk, cokey=ck, compname=c.get("compname"),
                   comppct_r=_number(c.get("comppct_r")),
                   **derive_component(by_component.get(ck, []), policy=policy))
        component_rows.append(row)
        groups[mk].append(row)
    if set(by_component)-seen:
        raise ValueError("Orphan horizon component IDs")
    substituted = {_key(k) for k in substituted_mukeys}
    mapunits = []
    for mk, rows in sorted(groups.items()):
        reasons = set()
        weights = [r["comppct_r"] for r in rows]
        if any(w is None or not 0 <= w <= 100 for w in weights):
            reasons.add("invalid_percentage")
        known = sum(w for w in weights if w is not None and 0 <= w <= 100)
        if known > 100:
            reasons.add("overfull_percentage")
        valid = sum(r["comppct_r"] for r in rows if r["status"] == "valid"
                    and r["comppct_r"] is not None and 0 <= r["comppct_r"] <= 100)
        nonsoil = sum(r["comppct_r"] for r in rows if r["status"] == "nonsoil"
                      and r["comppct_r"] is not None and 0 <= r["comppct_r"] <= 100)
        if mk in substituted:
            reasons.add("substituted_key")
        rejected = bool(reasons)
        numerator = sum(r["thickness_cm"]*r["comppct_r"] for r in rows
                        if r["status"] == "valid" and r["comppct_r"] is not None
                        and 0 <= r["comppct_r"] <= 100)
        if not math.isfinite(numerator):
            raise ValueError("Nonfinite derived weighted thickness")
        mean = numerator/valid if valid and not rejected else None
        support = valid/100 if not rejected else 0.0
        if support < 1:
            reasons.add("incomplete_components")
        for r in rows:
            if r["comppct_r"] != 0:
                reasons.update(filter(None, r["reason_codes"].split(";")))
        mapunits.append(dict(mukey=mk, mean_cm=mean, known_percentage=known,
                             valid_percentage=valid, nonsoil_percentage=nonsoil,
                             omitted_percentage=max(0, 100-valid-nonsoil),
                             valid_fraction=support,
                             status="complete" if support == 1 else "partial" if support else "unavailable",
                             reason_codes=_reasons(reasons)))
    return component_rows, mapunits


def _file(path, suffix=None):
    p = Path(path).resolve(strict=True)
    if not p.is_file() or (suffix and p.suffix.lower() != suffix):
        raise ValueError(f"Expected regular {suffix or ''} file: {p}")
    return p


def _hash(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read_cache(path):
    """Read canonical core columns from SQLite without creating/writing a DB."""
    p = _file(path)
    required = {"component": ("mukey", "cokey", "compname", "comppct_r"),
                "chorizon": ("cokey", "chkey", "hzname", "hzdept_r", "hzdepb_r", "hzthk_r", "desgnmaster")}
    conn = sqlite3.connect(p.as_uri()+"?mode=ro", uri=True)
    try:
        conn.execute("PRAGMA query_only=ON")
        conn.execute("PRAGMA trusted_schema=OFF")
        conn.enable_load_extension(False)
        conn.row_factory = sqlite3.Row
        result = []
        for table, columns in required.items():
            schema = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
            kind = conn.execute("SELECT type FROM sqlite_master WHERE name=?", (table,)).fetchone()
            if not kind or kind[0] != "table" or not set(columns) <= schema:
                raise ValueError(f"Incompatible {table} source schema")
            rows = [dict(r) for r in conn.execute(f"SELECT {','.join(columns)} FROM {table}")]
            if not rows:
                raise ValueError(f"Empty {table} source")
            result.append(rows)
        return tuple(result)
    finally:
        conn.close()


def _csv(path, rows):
    with Path(path).open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _grid(ds):
    t = ds.transform
    if (ds.driver != "GTiff" or ds.count != 1 or not ds.crs or not ds.crs.is_projected
            or ds.crs.linear_units != "metre" or t.b != 0 or t.d != 0
            or t.a <= 0 or t.e >= 0 or not math.isclose(t.a, -t.e)):
        raise ValueError("Expected single-band projected square meter grid")
    return ds.shape, ds.crs, ds.transform


def build_artifacts(cache_path, mukey_raster, catchments, output_dir, *, source_id,
                    policy="strict_soil", substituted_mukeys=()):
    """Build new offline rasters/tables using owned Rust intersection counts."""
    import numpy as np
    import rasterio  # type: ignore[import-untyped]
    from wepppyo3.raster_characteristics import count_intersecting_raster_key_pairs  # type: ignore[import-untyped]

    if not source_id or not catchments:
        raise ValueError("Explicit source ID and catchments required")
    cache = _file(cache_path)
    raster = _file(mukey_raster, ".tif")
    masks = {str(k): _file(v, ".tif") for k, v in catchments.items()}
    paths = [cache, raster, *masks.values()]
    hashes = {str(p): _hash(p) for p in paths}
    components, units = derive_mapunits(*read_cache(cache), policy=policy,
                                        substituted_mukeys=substituted_mukeys)
    lookup = {int(r["mukey"]): r for r in units}
    with rasterio.open(raster, driver="GTiff") as ds:
        grid, profile, keys = _grid(ds), ds.profile, ds.read(1)
        if not np.issubdtype(keys.dtype, np.integer) or ds.nodata != 0 or np.any(keys < 0):
            raise ValueError("MUKEY grid must contain nonnegative integer keys and nodata=0")
    for path in masks.values():
        with rasterio.open(path, driver="GTiff") as ds:
            if _grid(ds) != grid:
                raise ValueError("Catchment grid mismatch")
            mask = ds.read(1)
            if not np.any(mask == 1):
                raise ValueError("Empty catchment mask")
            # WBT masks contain 1 inside and nodata outside.
            outside = mask != 1
            valid_outside = (mask == 0) | (mask == ds.nodata) | np.isnan(mask)
            if np.any(outside & ~valid_outside):
                raise ValueError("Catchment masks must use 1 for included cells")
    if any(r["mean_cm"] is not None and r["mean_cm"] > np.finfo("float32").max for r in units):
        raise ValueError("Thickness cannot be represented by Float32 output")
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=False)
    thickness = np.full(keys.shape, np.nan, dtype="float32")
    fraction = np.zeros(keys.shape, dtype="float32")
    for key, row in lookup.items():
        if row["mean_cm"] is not None:
            selected = keys == key
            thickness[selected] = row["mean_cm"]
            fraction[selected] = row["valid_fraction"]
    for name, array, nodata in [("thickness_cm.tif", thickness, float("nan")),
                                ("valid_fraction.tif", fraction, None)]:
        with rasterio.open(out/name, "w", **dict(profile, dtype="float32", nodata=nodata,
                                                compress="deflate")) as dst:
            dst.write(array, 1)
    # Treat 0 as a category for denominator accounting, not GDAL nodata.
    count_keys = out/"count_keys.tif"
    with rasterio.open(count_keys, "w", **dict(profile, nodata=None)) as dst:
        dst.write(keys, 1)
    results = []
    for cid, mask in masks.items():
        pairs = count_intersecting_raster_key_pairs(str(mask), str(count_keys),
                                                   ignore_channels=False)
        counts = pairs.get("1", {})
        total = sum(counts.values())
        with rasterio.open(mask, driver="GTiff") as ds:
            expected = int(np.count_nonzero(ds.read(1) == 1))
        if total != expected:
            raise ValueError("Owned intersection counts lost catchment support")
        numerator, support, reasons = 0.0, 0.0, set()
        for key, n in counts.items():
            unit = lookup.get(int(key))
            if int(key) == 0:
                reasons.add("outside_survey")
            elif unit is None:
                reasons.add("unknown_mukey")
            else:
                fraction = unit["valid_fraction"]
                support += n*fraction
                if fraction:
                    numerator += n*fraction*unit["mean_cm"]
                reasons.update(filter(None, unit["reason_codes"].split(";")))
        coverage = support/total
        complete = math.isclose(coverage, 1, rel_tol=0, abs_tol=1e-12)
        mean = numerator/support if support else None
        if not complete:
            reasons.add("partial_support")
        results.append(dict(catchment_id=cid, source_id=source_id, policy=policy,
                            full_area_m2=total*abs(grid[2].a*grid[2].e), full_cells=total,
                            valid_equivalent_cells=support, valid_fraction=coverage,
                            known_mean_cm=mean, known_S=mean/254 if mean is not None else None,
                            full_mean_cm=mean if complete else None,
                            full_S=mean/254 if complete else None,
                            status="complete" if complete else "partial" if support else "unavailable",
                            reason_codes=_reasons(reasons), source_sha256=hashes[str(cache)],
                            spatial_sha256=hashes[str(raster)], mask_sha256=hashes[str(mask)]))
    count_keys.unlink()
    _csv(out/"components.csv", components)
    _csv(out/"mapunits.csv", units)
    _csv(out/"catchments.csv", results)
    if any(_hash(p) != h for p, h in hashes.items()):
        raise RuntimeError("Input changed during offline build")
    (out/"manifest.json").write_text(json.dumps(dict(schema_version=1, source_id=source_id,
        policy=policy, thickness_unit="cm", S_scale="cm/254", inputs=hashes), indent=2)+"\n")
    return results
