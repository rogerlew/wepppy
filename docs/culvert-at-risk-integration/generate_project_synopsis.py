#!/usr/bin/env python3
"""
Generate a synopsis document for Culvert-at-Risk projects.

Scans input/output directories to identify available files for wepp.cloud payload
and generates a markdown report.

Usage:
    # Run from user_data directory (scans all users by default)
    cd /path/to/culvert_app_instance_dir/user_data
    python /workdir/wepppy/docs/culvert-at-risk-integration/generate_project_synopsis.py

    # Scan specific user only
    python generate_project_synopsis.py --user-id 1

    # Scan specific projects for a user
    python generate_project_synopsis.py --user-id 1 --projects "Hubbard Brook Experimental Forest"

    # Legacy mode with explicit paths
    python generate_project_synopsis.py --inputs /path/to/inputs --outputs /path/to/outputs
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


def run_command(cmd: list[str], capture: bool = True) -> Optional[str]:
    """Run a shell command and return output."""
    try:
        result = subprocess.run(cmd, capture_output=capture, text=True, timeout=30)
        if result.returncode == 0:
            return result.stdout.strip() if capture else None
        return None
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def get_file_size(filepath: str) -> Optional[int]:
    """Get file size in bytes."""
    try:
        return os.path.getsize(filepath)
    except OSError:
        return None


def get_raster_info(filepath: str) -> Optional[dict]:
    """Extract raster metadata using gdalinfo."""
    if not os.path.exists(filepath):
        return None

    info = {"path": filepath, "exists": True}

    # Get file size
    size = get_file_size(filepath)
    if size is not None:
        info["size_bytes"] = size
        info["size_human"] = format_file_size(size)

    # Get basic info
    output = run_command(["gdalinfo", filepath])
    if not output:
        _update_raster_info_from_rasterio(info, filepath)
        return info

    for line in output.split("\n"):
        line = line.strip()
        if line.startswith("Size is"):
            parts = line.replace("Size is ", "").split(", ")
            if len(parts) == 2:
                info["width"] = int(parts[0])
                info["height"] = int(parts[1])
        elif "Pixel Size" in line:
            # Extract pixel size from line like "Pixel Size = (9.325770936052784,-9.325770936052784)"
            try:
                start = line.index("(") + 1
                end = line.index(")")
                parts = line[start:end].split(",")
                info["pixel_size_x"] = abs(float(parts[0]))
                info["pixel_size_y"] = abs(float(parts[1]))
                info["resolution"] = f"{info['pixel_size_x']:.2f}m"
            except (ValueError, IndexError):
                pass
        elif "EPSG" in line and "ID[" in line:
            try:
                start = line.index('ID["EPSG",') + 10
                end = line.index("]", start)
                info["epsg"] = int(line[start:end].rstrip("]"))
            except (ValueError, IndexError):
                pass
        elif line.startswith("PROJCRS["):
            try:
                start = line.index('["') + 2
                end = line.index('",', start)
                info["crs_name"] = line[start:end]
            except (ValueError, IndexError):
                pass

    if "resolution" not in info:
        _update_raster_info_from_rasterio(info, filepath)

    return info


def get_shapefile_size(filepath: str) -> Optional[int]:
    """Get total size of shapefile (all component files)."""
    base = Path(filepath).with_suffix("")
    extensions = [".shp", ".shx", ".dbf", ".prj", ".cpg", ".sbn", ".sbx", ".fbn", ".fbx", ".ain", ".aih", ".ixs", ".mxs", ".atx", ".xml"]
    total_size = 0
    found_any = False

    for ext in extensions:
        component = base.with_suffix(ext)
        if component.exists():
            found_any = True
            try:
                total_size += os.path.getsize(component)
            except OSError:
                pass

    return total_size if found_any else None


def get_vector_info(filepath: str) -> Optional[dict]:
    """Extract vector metadata using ogrinfo."""
    if not os.path.exists(filepath):
        return None

    info = {"path": filepath, "exists": True}

    # Get file size (for shapefiles, sum all components)
    if filepath.lower().endswith(".shp"):
        size = get_shapefile_size(filepath)
    else:
        size = get_file_size(filepath)

    if size is not None:
        info["size_bytes"] = size
        info["size_human"] = format_file_size(size)

    # Get layer name from filename
    layer_name = Path(filepath).stem

    output = run_command(["ogrinfo", "-so", "-al", filepath])
    if not output:
        output = run_command(["ogrinfo", "-so", filepath, layer_name])
    if not output:
        _update_vector_info_from_fiona(info, filepath)
        return info

    for line in output.split("\n"):
        line = line.strip()
        if line.startswith("Feature Count:"):
            try:
                info["feature_count"] = int(line.replace("Feature Count:", "").strip())
            except ValueError:
                pass
        elif line.startswith("Geometry:"):
            info["geometry_type"] = line.replace("Geometry:", "").strip()
        elif "EPSG" in line and "ID[" in line:
            try:
                start = line.index('ID["EPSG",') + 10
                end = line.index("]", start)
                info["epsg"] = int(line[start:end].rstrip("]"))
            except (ValueError, IndexError):
                pass
        # Check for Point_ID attribute
        elif line.startswith("Point_ID:"):
            info["has_point_id"] = True

    if "feature_count" not in info:
        _update_vector_info_from_fiona(info, filepath)

    return info


def _update_raster_info_from_rasterio(info: dict, filepath: str) -> None:
    try:
        import rasterio
    except Exception:
        return

    try:
        with rasterio.open(filepath) as dataset:
            if "width" not in info:
                info["width"] = dataset.width
            if "height" not in info:
                info["height"] = dataset.height
            if "pixel_size_x" not in info or "pixel_size_y" not in info:
                res_x, res_y = dataset.res
                info["pixel_size_x"] = abs(res_x)
                info["pixel_size_y"] = abs(res_y)
            if "resolution" not in info and "pixel_size_x" in info:
                info["resolution"] = f"{info['pixel_size_x']:.2f}m"
            if dataset.crs:
                epsg = dataset.crs.to_epsg()
                if epsg and "epsg" not in info:
                    info["epsg"] = epsg
                if "crs_name" not in info:
                    info["crs_name"] = dataset.crs.name or dataset.crs.to_string()
    except Exception:
        return


def _update_vector_info_from_fiona(info: dict, filepath: str) -> None:
    try:
        import fiona
    except Exception:
        return

    try:
        with fiona.open(filepath) as dataset:
            if "feature_count" not in info:
                info["feature_count"] = len(dataset)
            if "geometry_type" not in info:
                info["geometry_type"] = dataset.schema.get("geometry")
            if dataset.crs:
                epsg = dataset.crs.to_epsg()
                if epsg and "epsg" not in info:
                    info["epsg"] = epsg
            if "has_point_id" not in info:
                props = dataset.schema.get("properties") or {}
                info["has_point_id"] = "Point_ID" in props
    except Exception:
        return


def scan_project(project_name: str, inputs_dir: Path, outputs_dir: Path) -> dict:
    """Scan a single project for available files."""
    project = {
        "name": project_name,
        "has_inputs": False,
        "has_outputs": False,
        "ws_delineation_complete": False,
        "files": {
            "dem": None,
            "hydro_enforced_dem": None,
            "watersheds_raster": None,
            "watersheds_polygon": None,
            "streams_raster": None,
            "streams_vector": None,
            "culvert_points": None,
            "flow_accumulation": None,
        },
        "metadata": {},
    }

    input_path = inputs_dir / project_name
    output_path = outputs_dir / project_name

    # Check inputs
    if input_path.exists():
        project["has_inputs"] = True

        # Check for input DEM
        input_dem = input_path / "dem.tif"
        if input_dem.exists():
            project["files"]["input_dem"] = get_raster_info(str(input_dem))

        # Check for project metadata
        metadata_file = input_path / "project_metadata.json"
        if metadata_file.exists():
            try:
                with open(metadata_file) as f:
                    project["metadata"] = json.load(f)
            except (json.JSONDecodeError, IOError):
                pass

    # Check outputs
    if output_path.exists():
        project["has_outputs"] = True

        ws_deln = output_path / "WS_deln"
        hydrogeo = output_path / "hydrogeo_vuln"

        if ws_deln.exists() and any(ws_deln.iterdir()):
            project["ws_delineation_complete"] = True

            # DEM files
            dem_path = ws_deln / "DEM_UTM.tif"
            if dem_path.exists():
                project["files"]["dem"] = get_raster_info(str(dem_path))

            hydro_dem_path = ws_deln / "breached_filled_DEM_UTM.tif"
            if hydro_dem_path.exists():
                project["files"]["hydro_enforced_dem"] = get_raster_info(str(hydro_dem_path))

            # Watershed files
            ws_polygon = ws_deln / "all_ws_polygon_UTM.shp"
            if ws_polygon.exists():
                project["files"]["watersheds_polygon"] = get_vector_info(str(ws_polygon))

            # Check for watershed raster (various naming conventions)
            for ws_raster_name in ["ws_raster_UTM.tif", "watersheds.tif", "watershed_raster_UTM.tif"]:
                ws_raster = ws_deln / ws_raster_name
                if ws_raster.exists():
                    project["files"]["watersheds_raster"] = get_raster_info(str(ws_raster))
                    break

            # Stream files in WS_deln
            stream_vector = ws_deln / "stream_vector_UTM.shp"
            if stream_vector.exists():
                project["files"]["streams_vector"] = get_vector_info(str(stream_vector))

            # Flow accumulation
            flow_accum = ws_deln / "bD8Flow_accum_UTM.tif"
            if flow_accum.exists():
                project["files"]["flow_accumulation"] = get_raster_info(str(flow_accum))

            # Culvert points
            pour_point = ws_deln / "Pour_Point_UTM.shp"
            if pour_point.exists():
                project["files"]["culvert_points"] = get_vector_info(str(pour_point))

        # Check hydrogeo_vuln for stream raster
        if hydrogeo.exists():
            stream_raster = hydrogeo / "main_stream_raster_UTM.tif"
            if stream_raster.exists():
                project["files"]["streams_raster"] = get_raster_info(str(stream_raster))

    return project


def status_icon(value: bool) -> str:
    """Return status indicator."""
    return "Yes" if value else "No"


def file_status(file_info: Optional[dict], key_attr: Optional[str] = None, include_size: bool = True) -> str:
    """Return file status string."""
    if file_info is None:
        return "Missing"

    parts = ["Present"]
    if include_size and "size_human" in file_info:
        parts.append(file_info["size_human"])
    if "resolution" in file_info:
        parts.append(file_info["resolution"])
    if "feature_count" in file_info:
        parts.append(f"{file_info['feature_count']} features")
    if "epsg" in file_info:
        parts.append(f"EPSG:{file_info['epsg']}")
    if key_attr and file_info.get(key_attr):
        # Special case for common attributes
        if key_attr == "has_point_id":
            parts.append("has Point_ID")
        else:
            parts.append(f"has {key_attr}")

    return ", ".join(parts)


def has_hydro_dem(project: dict) -> bool:
    return project["files"].get("hydro_enforced_dem") is not None


def has_watersheds(project: dict) -> bool:
    return (
        project["files"].get("watersheds_raster") is not None
        or project["files"].get("watersheds_polygon") is not None
    )


def has_streams(project: dict) -> bool:
    return (
        project["files"].get("streams_raster") is not None
        or project["files"].get("streams_vector") is not None
        or project["files"].get("flow_accumulation") is not None
    )


def has_culverts(project: dict) -> bool:
    return project["files"].get("culvert_points") is not None


def is_viable(project: dict) -> bool:
    return (
        project["ws_delineation_complete"]
        and has_hydro_dem(project)
        and has_watersheds(project)
        and has_streams(project)
        and has_culverts(project)
    )


def missing_viable_fields(project: dict) -> list[str]:
    missing = []
    if not project["ws_delineation_complete"]:
        missing.append("WS Deln")
    if not has_hydro_dem(project):
        missing.append("Hydro-DEM")
    if not has_watersheds(project):
        missing.append("Watersheds")
    if not has_streams(project):
        missing.append("Streams")
    if not has_culverts(project):
        missing.append("Culverts")
    return missing


def generate_synopsis(projects: list[dict], output_file: Path) -> None:
    """Generate the markdown synopsis document."""

    # Check if we have multiple users and compute summary counts.
    user_ids = set(p.get("user_id", 0) for p in projects)
    multi_user = len(user_ids) > 1
    total_projects = len(projects)
    viable_projects = sum(1 for p in projects if is_viable(p))

    lines = [
        "# Culvert-at-Risk Projects Synopsis",
        "",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "This document provides an automated inventory of Culvert-at-Risk projects and their",
        "readiness for wepp.cloud payload generation.",
        "",
        "---",
        "",
        "## Quick Summary",
        "",
    ]

    lines.extend([
        f"- Total projects: {total_projects}",
        f"- Users scanned: {len(user_ids)}",
        f"- VIABLE projects (WS Deln + Hydro-DEM + Watersheds + Streams + Culverts): {viable_projects}",
        "",
    ])

    if multi_user:
        lines.extend([
            "| User | Project | WS Deln | Hydro-DEM | Hydro-DEM Res | Watersheds | Streams | Culverts | # Culverts |",
            "|------|---------|---------|-----------|---------------|------------|---------|----------|-----------|",
        ])
    else:
        lines.extend([
            "| Project | WS Deln | Hydro-DEM | Hydro-DEM Res | Watersheds | Streams | Culverts | # Culverts |",
            "|---------|---------|-----------|---------------|------------|---------|----------|-----------|",
        ])

    for p in projects:
        ws_status = "Yes" if p["ws_delineation_complete"] else "No"

        # Hydro-DEM with size
        hydro_dem = p["files"].get("hydro_enforced_dem")
        if hydro_dem:
            dem_size = hydro_dem.get("size_human", "")
            dem_resolution = hydro_dem.get("resolution") or "Unknown"
            dem_status = f"Yes ({dem_size})" if dem_size else "Yes"
        else:
            dem_resolution = "—"
            dem_status = "No"

        # Watersheds with size
        ws_raster_info = p["files"].get("watersheds_raster")
        ws_polygon_info = p["files"].get("watersheds_polygon")
        if ws_raster_info:
            ws_size = ws_raster_info.get("size_human", "")
            ws_raster = f"Yes ({ws_size})" if ws_size else "Yes"
        elif ws_polygon_info:
            ws_size = ws_polygon_info.get("size_human", "")
            ws_raster = f"Polygon ({ws_size})" if ws_size else "Polygon"
        else:
            ws_raster = "No"

        # Streams with size
        stream_raster = p["files"].get("streams_raster")
        stream_vector = p["files"].get("streams_vector")
        flow_accum = p["files"].get("flow_accumulation")
        if stream_raster:
            stream_size = stream_raster.get("size_human", "")
            streams = f"Raster ({stream_size})" if stream_size else "Raster"
        elif stream_vector:
            stream_size = stream_vector.get("size_human", "")
            streams = f"Vector ({stream_size})" if stream_size else "Vector"
        elif flow_accum:
            streams = "FlowAcc"
        else:
            streams = "No"

        # Culverts with count and size
        culvert_info = p["files"].get("culvert_points")
        if culvert_info:
            size = culvert_info.get("size_human", "")
            culverts = f"Yes ({size})" if size else "Yes"
            culvert_count = culvert_info.get("feature_count")
            culvert_count_str = str(culvert_count) if culvert_count is not None else "—"
        else:
            culverts = "No"
            culvert_count_str = "—"

        if multi_user:
            lines.append(
                f"| {p.get('user_id', '?')} | {p['name']} | {ws_status} | {dem_status} | {dem_resolution} | {ws_raster} | {streams} | {culverts} | {culvert_count_str} |"
            )
        else:
            lines.append(
                f"| {p['name']} | {ws_status} | {dem_status} | {dem_resolution} | {ws_raster} | {streams} | {culverts} | {culvert_count_str} |"
            )

    lines.extend([
        "",
        "**Legend:**",
        "- WS Deln: Watershed delineation completed",
        "- Hydro-DEM: Hydro-enforced DEM available",
        "- Hydro-DEM Res: Hydro-enforced DEM pixel resolution",
        "- Watersheds: Watershed polygons available (Polygon = shapefile, needs GeoJSON conversion; raster not required)",
        "- Streams: Stream raster available (Raster/Vector/FlowAcc/No)",
        "- Culverts: Culvert points available",
        "- # Culverts: Feature count from culvert points file",
        "",
        "---",
        "",
        "## Detailed Project Reports",
        "",
    ])

    for p in projects:
        if multi_user:
            lines.extend([
                f"### [User {p.get('user_id', '?')}] {p['name']}",
                "",
            ])
        else:
            lines.extend([
                f"### {p['name']}",
                "",
            ])

        # Status
        if not p["has_outputs"]:
            lines.extend([
                "**Status: NOT VIABLE** - No outputs exist. Watershed delineation has not been run.",
                "",
            ])
            if p["has_inputs"]:
                lines.append("**Inputs available:** Yes (dem.tif, pour_point.zip)")
            lines.extend(["", "---", ""])
            continue

        if not p["ws_delineation_complete"]:
            lines.extend([
                "**Status: INCOMPLETE** - Output folder exists but WS_deln is empty or missing.",
                "",
                "---",
                "",
            ])
            continue

        missing = missing_viable_fields(p)
        if missing:
            lines.extend([
                f"**Status: INCOMPLETE** - Missing: {', '.join(missing)}",
                "",
                "---",
                "",
            ])
            continue

        # Viable project - show details
        lines.append("**Status: VIABLE** - WS Deln, Hydro-DEM, Watersheds, Streams, Culverts available")
        lines.extend(["", "#### File Inventory", ""])

        # DEM section
        lines.append("**DEM Files:**")
        lines.append("")
        lines.append("| File | Status |")
        lines.append("|------|--------|")

        dem_info = p["files"].get("dem")
        if dem_info:
            lines.append(f"| DEM_UTM.tif | {file_status(dem_info)} |")

        hydro_info = p["files"].get("hydro_enforced_dem")
        if hydro_info:
            lines.append(f"| breached_filled_DEM_UTM.tif | {file_status(hydro_info)} |")
        else:
            lines.append("| breached_filled_DEM_UTM.tif | Missing |")

        lines.append("")

        # Watersheds section
        lines.append("**Watershed Files:**")
        lines.append("")

        ws_raster = p["files"].get("watersheds_raster")
        ws_polygon = p["files"].get("watersheds_polygon")

        if ws_raster:
            lines.append(f"- Raster: {file_status(ws_raster)}")
        else:
            lines.append("- Raster: Missing (not required; polygons are used for payload)")

        if ws_polygon:
            lines.append(f"- Polygon: {file_status(ws_polygon, 'has_point_id')}")
        else:
            lines.append("- Polygon: Missing")

        lines.append("")

        # Streams section
        lines.append("**Stream Files:**")
        lines.append("")

        stream_raster = p["files"].get("streams_raster")
        stream_vector = p["files"].get("streams_vector")
        flow_accum = p["files"].get("flow_accumulation")

        if stream_raster:
            lines.append(f"- Raster: {file_status(stream_raster)}")
        else:
            lines.append("- Raster: **Missing**")

        if stream_vector:
            lines.append(f"- Vector: {file_status(stream_vector)}")

        if flow_accum:
            lines.append(f"- Flow Accumulation: {file_status(flow_accum)} (can derive streams)")

        lines.append("")

        # Culvert points section
        lines.append("**Culvert Points:**")
        lines.append("")

        culverts = p["files"].get("culvert_points")
        if culverts:
            lines.append(f"- {file_status(culverts, 'has_point_id')}")
            lines.append("- Format: Shapefile (needs GeoJSON conversion for payload)")
        else:
            lines.append("- **Missing**")

        lines.append("")

        # Payload readiness
        lines.append("#### Payload Readiness")
        lines.append("")

        ready_items = []
        todo_items = []

        if hydro_info:
            ready_items.append("`topo/hydro-enforced-dem.tif` - Ready (copy breached_filled_DEM_UTM.tif)")
        else:
            todo_items.append("`topo/hydro-enforced-dem.tif` - Missing hydro-enforced DEM")

        if stream_raster:
            ready_items.append("`topo/streams.tif` - Ready (copy main_stream_raster_UTM.tif)")
        elif flow_accum:
            todo_items.append("`topo/streams.tif` - Generate by thresholding flow accumulation")
        else:
            todo_items.append("`topo/streams.tif` - Missing (no source available)")

        if ws_polygon:
            todo_items.append("`culverts/watersheds.geojson` - Convert from all_ws_polygon_UTM.shp")
        else:
            todo_items.append("`culverts/watersheds.geojson` - Missing (no watershed polygons)")

        if culverts:
            todo_items.append("`culverts/culvert_points.geojson` - Convert from shapefile")
        else:
            todo_items.append("`culverts/culvert_points.geojson` - Missing")

        if ready_items:
            lines.append("**Ready:**")
            for item in ready_items:
                lines.append(f"- {item}")
            lines.append("")

        if todo_items:
            lines.append("**Requires Processing:**")
            for item in todo_items:
                lines.append(f"- {item}")
            lines.append("")

        lines.extend(["---", ""])

    # Processing commands section
    lines.extend([
        "## Common Processing Commands",
        "",
        "### Convert Watershed Polygons to GeoJSON",
        "",
        "```bash",
        "ogr2ogr -f GeoJSON \\",
        "  culverts/watersheds.geojson \\",
        "  WS_deln/all_ws_polygon_UTM.shp",
        "```",
        "",
        "### Convert Culvert Points to GeoJSON",
        "",
        "```bash",
        "ogr2ogr -f GeoJSON \\",
        "  culverts/culvert_points.geojson \\",
        "  WS_deln/Pour_Point_UTM.shp",
        "```",
        "",
        "### Derive Streams from Flow Accumulation (if stream raster missing)",
        "",
        "```bash",
        "# Threshold value (e.g., 1000) determines stream density",
        "gdal_calc.py -A WS_deln/bD8Flow_accum_UTM.tif \\",
        "  --outfile=topo/streams.tif \\",
        "  --calc=\"(A>1000)*1\" \\",
        "  --type=Byte --NoDataValue=0",
        "```",
        "",
    ])

    # Write the file
    with open(output_file, "w") as f:
        f.write("\n".join(lines))

    print(f"Synopsis written to: {output_file}")


def discover_user_dirs(base_path: Path) -> list[tuple[int, Path, Path]]:
    """
    Discover user directories in the format {id}_inputs, {id}_outputs.
    Returns list of (user_id, inputs_path, outputs_path) tuples.
    """
    users = {}
    pattern = re.compile(r"^(\d+)_(inputs|outputs|logs|temp)$")

    for entry in base_path.iterdir():
        if entry.is_dir():
            match = pattern.match(entry.name)
            if match:
                user_id = int(match.group(1))
                dir_type = match.group(2)
                if user_id not in users:
                    users[user_id] = {}
                users[user_id][dir_type] = entry

    result = []
    for user_id in sorted(users.keys()):
        inputs = users[user_id].get("inputs")
        outputs = users[user_id].get("outputs")
        if inputs and outputs:
            result.append((user_id, inputs, outputs))

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Generate synopsis of Culvert-at-Risk projects"
    )
    parser.add_argument(
        "--user-id",
        type=int,
        help="Specific user ID to scan (e.g., 1 for 1_inputs/1_outputs). Default: all users",
    )
    parser.add_argument(
        "--inputs",
        type=Path,
        help="Path to inputs directory (legacy mode)",
    )
    parser.add_argument(
        "--outputs",
        type=Path,
        help="Path to outputs directory (legacy mode)",
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        default=Path("culvert-at-risk-projects-synopsis.md"),
        help="Output markdown file (default: culvert-at-risk-projects-synopsis.md)",
    )
    parser.add_argument(
        "--projects",
        nargs="*",
        help="Specific project names to scan (default: all projects)",
    )
    parser.add_argument(
        "--base-dir",
        type=Path,
        default=Path("."),
        help="Base user_data directory (default: current directory)",
    )

    args = parser.parse_args()

    # Check for required tools
    if not run_command(["gdalinfo", "--version"]):
        print("Warning: gdalinfo not found. Raster metadata will be limited.", file=sys.stderr)

    if not run_command(["ogrinfo", "--version"]):
        print("Warning: ogrinfo not found. Vector metadata will be limited.", file=sys.stderr)

    # Determine which directories to scan
    user_dirs = []

    if args.inputs and args.outputs:
        # Legacy mode: explicit paths
        if not args.inputs.exists():
            print(f"Error: Inputs directory not found: {args.inputs}", file=sys.stderr)
            sys.exit(1)
        if not args.outputs.exists():
            print(f"Error: Outputs directory not found: {args.outputs}", file=sys.stderr)
            sys.exit(1)
        user_dirs = [(0, args.inputs, args.outputs)]
    else:
        # Auto-discover user directories
        base = args.base_dir
        if not base.exists():
            print(f"Error: Base directory not found: {base}", file=sys.stderr)
            sys.exit(1)

        all_user_dirs = discover_user_dirs(base)

        if not all_user_dirs:
            # Maybe we're in wrong directory, try looking for {id}_inputs pattern
            print(f"No user directories found in {base}", file=sys.stderr)
            print("Expected format: 1_inputs, 1_outputs, 2_inputs, 2_outputs, ...", file=sys.stderr)
            sys.exit(1)

        if args.user_id is not None:
            # Filter to specific user
            user_dirs = [(uid, inp, out) for uid, inp, out in all_user_dirs if uid == args.user_id]
            if not user_dirs:
                print(f"Error: User ID {args.user_id} not found", file=sys.stderr)
                print(f"Available users: {[uid for uid, _, _ in all_user_dirs]}", file=sys.stderr)
                sys.exit(1)
        else:
            # Default: scan all users
            user_dirs = all_user_dirs
            print(f"Scanning all {len(user_dirs)} users (use --user-id N to scan specific user)")

    # Scan all specified user directories
    all_projects = []

    for user_id, inputs_dir, outputs_dir in user_dirs:
        print(f"\n=== Scanning User {user_id} ===")
        print(f"  Inputs:  {inputs_dir}")
        print(f"  Outputs: {outputs_dir}")

        # Discover projects for this user
        if args.projects:
            project_names = args.projects
        else:
            input_projects = {d.name for d in inputs_dir.iterdir() if d.is_dir()}
            output_projects = {d.name for d in outputs_dir.iterdir() if d.is_dir()}
            project_names = sorted(input_projects | output_projects)

        print(f"  Found {len(project_names)} projects")

        for name in project_names:
            print(f"    Scanning: {name}")
            project = scan_project(name, inputs_dir, outputs_dir)
            project["user_id"] = user_id
            all_projects.append(project)

    # Generate synopsis
    generate_synopsis(all_projects, args.output_file)

    # Print summary
    viable = sum(1 for p in all_projects if is_viable(p))
    print(
        f"\nSummary: {viable}/{len(all_projects)} projects meet viability criteria "
        "(WS Deln + Hydro-DEM + Watersheds + Streams + Culverts)"
    )


if __name__ == "__main__":
    main()
