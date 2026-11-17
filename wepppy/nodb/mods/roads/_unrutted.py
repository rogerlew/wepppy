"""RUPC-01 crossing normalization and emitted-profile area checks.

These are abstract parallel strips, not inferred drainage partitions.
"""
from __future__ import annotations

import hashlib
import math
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

from shapely.geometry import LineString, MultiLineString
from shapely.ops import linemerge, unary_union
from shapely.strtree import STRtree

POLICY = "unrutted_strips_v1"
PLACEMENT_POLICY = "unrutted_top_placement_v1"
LIMITATION = "Simplified parallel strips; switchbacks and shared contributing-area connectivity are not resolved."
AREA_EPSILON_M2 = 1e-6


def line_parts(geometry):
    if isinstance(geometry, LineString):
        if not geometry.is_empty:
            yield geometry
    elif hasattr(geometry, "geoms"):
        for child in geometry.geoms:
            yield from line_parts(child)


def geometry_key(geometry):
    lines = list(line_parts(geometry))
    merged = linemerge(lines) if len(lines) > 1 else lines[0]
    return hashlib.sha256(merged.simplify(0).normalize().wkb).hexdigest()


def crossings(rows):
    """Union equal-input connected pieces before eligibility; reject conflicts."""
    for row in rows:
        if (not row["geometry"].is_valid or any(
            not math.isfinite(v) for line in line_parts(row["geometry"])
            for xy in line.coords for v in xy[:2]
        )):
            raise ValueError("Unrutted crossing geometry must be valid and finite.")
    tree = STRtree([row["geometry"] for row in rows])
    for i, row in enumerate(rows):
        for j in tree.query(row["geometry"], predicate="intersects"):
            if j <= i:
                continue
            other = rows[j]
            if row["signature"] != other["signature"]:
                intersection = row["geometry"].intersection(other["geometry"])
                if sum(part.length for part in line_parts(intersection)) > 0:
                    raise ValueError("Unrutted overlapping roads have conflicting model inputs; resolve the duplicate geometry.")
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["signature"]].append(row)
    result = []
    for signature, members in sorted(grouped.items()):
        union = unary_union([row["geometry"] for row in members])
        # unary_union nodes every intersection. Connectivity is therefore an
        # endpoint graph; avoid repeated all-pairs GEOS scans on dense linework.
        parts = list(line_parts(union))
        endpoints = defaultdict(list)
        for i, part in enumerate(parts):
            endpoints[tuple(part.coords[0][:2])].append(i)
            endpoints[tuple(part.coords[-1][:2])].append(i)
        unseen = set(range(len(parts)))
        member_tree = STRtree([row["geometry"] for row in members])
        while unseen:
            stack = [unseen.pop()]
            component = []
            while stack:
                index = stack.pop()
                part = parts[index]
                component.append(part)
                for point in (tuple(part.coords[0][:2]), tuple(part.coords[-1][:2])):
                    for neighbor in endpoints.pop(point, []):
                        if neighbor in unseen:
                            unseen.remove(neighbor)
                            stack.append(neighbor)
            geometry = unary_union(component)
            sources = sorted({members[j]["source"] for j in member_tree.query(geometry, predicate="intersects")
                              if members[j]["geometry"].intersection(geometry).length > 0})
            result.append({"geometry": geometry, "signature": signature,
                           "sources": sources, "key": geometry_key(geometry)})
    return sorted(result, key=lambda row: (row["key"], row["signature"]))


def road_geometry(overlap_length_m, road_width_m):
    if (not all(math.isfinite(v) and v > 0 for v in (overlap_length_m, road_width_m))
            or not 0.3 <= road_width_m <= 100):
        raise ValueError("Unrutted road geometry requires finite positive overlap and valid physical width.")
    if not math.isfinite(overlap_length_m * road_width_m):
        raise ValueError("Unrutted target road area must be finite.")
    return {"sim_length_m": road_width_m, "sim_width_m": overlap_length_m,
            "road_slope_fraction": 0.04, "road_slope_pct": 4.0,
            "geometry_scale": 1.0, "geometry_policy": POLICY,
            "road_target_area_m2": overlap_length_m * road_width_m}


def write_slope(path, width, lengths, slopes):
    """Write only unrutted profiles; preserve the existing OFE slope transitions."""
    if len(lengths) != len(slopes) or not lengths:
        raise ValueError("Unrutted slope profile dimensions do not match.")
    if not all(math.isfinite(v) and v > 0 for v in (width, *lengths, *slopes)):
        raise ValueError("Unrutted profile dimensions and slopes must be finite and positive.")
    lines = ["97.3", str(len(lengths)), f"180.0 {width:.12f}"]
    for i, (length, slope) in enumerate(zip(lengths, slopes)):
        if i == 0:
            lines.extend([f"2 {length:.12f}", f"0.00, {slope:.6f} 1.00, {slope:.6f}"])
        else:
            lines.extend([f"3 {length:.12f}",
                          f"0.00, {slopes[i-1]:.6f} 0.05, {slope:.6f} 1.00, {slope:.6f}"])
    Path(path).write_text("\n".join(lines) + "\n")
    return slope_area(path)


def slope_area(path):
    lines = Path(path).read_text().splitlines()
    count = int(lines[1])
    width = float(lines[2].split()[1])
    lengths = [float(lines[3 + 2*i].split()[1]) for i in range(count)]
    if count < 1 or not all(math.isfinite(v) and v > 0 for v in [width, *lengths]):
        raise ValueError("Emitted unrutted profile dimensions must be finite and positive.")
    area = width * math.fsum(lengths)
    if not math.isfinite(area) or area <= 0:
        raise ValueError("Emitted unrutted profile area must be finite and positive.")
    return area


def placement(hillslope_length, road_length, fill_length, distance, landuse_min):
    """RUPC-02: omit upstream landuse if the terrain anchor exceeds the profile."""
    if not all(math.isfinite(v) and v > 0 for v in (hillslope_length, road_length, fill_length, landuse_min)):
        raise ValueError("Unrutted profile lengths must be finite and positive.")
    if not math.isfinite(distance) or distance < 0:
        raise ValueError("Unrutted distance to channel must be finite and nonnegative.")
    bottom = max(0.0, distance - fill_length)
    if bottom < landuse_min:
        bottom = 0.0
    # Compare the supplied decimal dimensions, avoiding a spurious sub-native
    # landuse OFE from binary cancellation (e.g. 24.3 - 4.1 - 20.2).
    remaining = float(Decimal(str(hillslope_length)) - Decimal(str(road_length)) - Decimal(str(fill_length)))
    original_top = remaining - bottom
    adjusted = original_top <= 0
    fits = remaining >= 0
    if adjusted and fits:
        bottom = remaining
    return {
        "fits": fits,
        "placement_policy": PLACEMENT_POLICY,
        "placement_adjustment": "top_of_hillslope" if adjusted else "none",
        "placement_adjustment_reason": "non_positive_upstream_length" if adjusted else None,
        "original_top_landuse_length_m": original_top,
        "hillslope_length_m": hillslope_length,
        "upslope_runon_assumed_zero": adjusted,
        "top_landuse_length_m": 0.0 if adjusted else original_top,
        "bottom_landuse_length_m": bottom,
    }


def compensate(plan, length):
    """Put area corrections downhill for top placement, never on the road/fill."""
    side = "bottom" if plan["placement_adjustment"] == "top_of_hillslope" else "top"
    key = f"{side}_landuse_length_m"
    adjusted = plan[key] + length
    if not math.isfinite(adjusted) or adjusted < 0 or (side == "top" and adjusted == 0):
        return False
    plan[key] = adjusted
    plan[f"{side}_ofe_compensation_m"] += length
    plan["has_downslope_landuse"] = plan["bottom_landuse_length_m"] > 0
    return True


def profile_parts(plan):
    """Return aligned native lengths/slopes/template roles, omitting absent landuse."""
    lengths = [plan["parity_profile"]["sim_length_m"], plan["fill_profile"]["fill_length_m"]]
    slopes = [0.04, plan["fill_profile"]["fill_slope_pct"] / 100]
    roles = [1, 2]
    if plan["top_landuse_length_m"] > 0:
        lengths.insert(0, plan["top_landuse_length_m"])
        slopes.insert(0, plan["top_landuse_slope_pct"] / 100)
        roles.insert(0, 3)
    if plan["bottom_landuse_length_m"] > 0:
        lengths.append(plan["bottom_landuse_length_m"])
        slopes.append(plan["bottom_landuse_slope_pct"] / 100)
        roles.append(3)
    return lengths, slopes, tuple(roles)
