#!/usr/bin/env python3
"""
Generate a synopsis document for Culvert-at-Risk projects.

Scans input/output directories to identify available files for wepp.cloud payload
and generates a markdown report.

Usage:
    # Run from user_data directory (scans all users)
    cd /workdir/culvert_app_instance_dir/user_data
    python /workdir/wepppy/docs/culvert-at-risk-integration/generate_project_synopsis.py

    # Scan specific user
    python generate_project_synopsis.py --user-id 1

    # Scan specific projects for a user
    python generate_project_synopsis.py --user-id 1 --projects "Hubbard Brook Experimental Forest" "Santee_10m_no_hydroenforcement"

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


def get_raster_info(filepath: str) -> Optional[dict]:
    """Extract raster metadata using gdalinfo."""
    if not os.path.exists(filepath):
        return None

    info = {"path": filepath, "exists": True}

    # Get basic info
    output = run_command(["gdalinfo", filepath])
    if not output:
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

    return info


def get_vector_info(filepath: str) -> Optional[dict]:
    """Extract vector metadata using ogrinfo."""
    if not os.path.exists(filepath):
        return None

    info = {"path": filepath, "exists": True}

    # Get layer name from filename
    layer_name = Path(filepath).stem

    output = run_command(["ogrinfo", "-so", filepath, layer_name])
    if not output:
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

    return info


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


def file_status(file_info: Optional[dict], key_attr: Optional[str] = None) -> str:
    """Return file status string."""
    if file_info is None:
        return "Missing"

    parts = ["Present"]
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


def generate_synopsis(projects: list[dict], output_file: Path) -> None:
    """Generate the markdown synopsis document."""

    # Check if we have multiple users
    user_ids = set(p.get("user_id", 0) for p in projects)
    multi_user = len(user_ids) > 1

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

    if multi_user:
        lines.extend([
            "| User | Project | WS Deln | Hydro-DEM | WS Raster | Streams | Culverts |",
            "|------|---------|---------|-----------|-----------|---------|----------|",
        ])
    else:
        lines.extend([
            "| Project | WS Deln | Hydro-DEM | WS Raster | Streams | Culverts |",
            "|---------|---------|-----------|-----------|---------|----------|",
        ])

    for p in projects:
        ws_status = "Yes" if p["ws_delineation_complete"] else "No"
        dem_status = "Yes" if p["files"].get("hydro_enforced_dem") else "No"
        ws_raster = "Yes" if p["files"].get("watersheds_raster") else ("Polygon" if p["files"].get("watersheds_polygon") else "No")
        streams = "Raster" if p["files"].get("streams_raster") else ("Vector" if p["files"].get("streams_vector") else ("FlowAcc" if p["files"].get("flow_accumulation") else "No"))
        culverts = "Yes" if p["files"].get("culvert_points") else "No"

        if multi_user:
            lines.append(f"| {p.get('user_id', '?')} | {p['name']} | {ws_status} | {dem_status} | {ws_raster} | {streams} | {culverts} |")
        else:
            lines.append(f"| {p['name']} | {ws_status} | {dem_status} | {ws_raster} | {streams} | {culverts} |")

    lines.extend([
        "",
        "**Legend:**",
        "- WS Deln: Watershed delineation completed",
        "- Hydro-DEM: Hydro-enforced DEM available",
        "- WS Raster: Watersheds as raster (Yes/Polygon/No)",
        "- Streams: Stream data format (Raster/Vector/FlowAcc/No)",
        "- Culverts: Culvert points shapefile available",
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

        # Viable project - show details
        lines.append("**Status: VIABLE** - Watershed delineation complete")
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
            lines.append("- Raster: **Missing** (needs generation from polygon)")

        if ws_polygon:
            has_pid = "has Point_ID" if ws_polygon.get("has_point_id") else "check for Point_ID"
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

        if ws_raster:
            ready_items.append("`topo/watersheds.tif` - Ready")
        elif ws_polygon:
            todo_items.append("`topo/watersheds.tif` - Generate by rasterizing all_ws_polygon_UTM.shp")
        else:
            todo_items.append("`topo/watersheds.tif` - Missing (no source available)")

        if stream_raster:
            ready_items.append("`topo/streams.tif` - Ready (copy main_stream_raster_UTM.tif)")
        elif flow_accum:
            todo_items.append("`topo/streams.tif` - Generate by thresholding flow accumulation")
        else:
            todo_items.append("`topo/streams.tif` - Missing (no source available)")

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
        "### Rasterize Watershed Polygons",
        "",
        "```bash",
        "# Replace values with project-specific extent and resolution",
        "gdal_rasterize -a Point_ID \\",
        "  -tr <pixel_size> <pixel_size> \\",
        "  -te <xmin> <ymin> <xmax> <ymax> \\",
        "  -ot Int32 -of GTiff \\",
        "  WS_deln/all_ws_polygon_UTM.shp \\",
        "  topo/watersheds.tif",
        "```",
        "",
        "### Derive Streams from Flow Accumulation",
        "",
        "```bash",
        "# Threshold value (e.g., 1000) determines stream density",
        "gdal_calc.py -A WS_deln/bD8Flow_accum_UTM.tif \\",
        "  --outfile=topo/streams.tif \\",
        "  --calc=\"(A>1000)*1\" \\",
        "  --type=Byte --NoDataValue=0",
        "```",
        "",
        "### Convert Shapefile to GeoJSON",
        "",
        "```bash",
        "ogr2ogr -f GeoJSON \\",
        "  culverts/culvert_points.geojson \\",
        "  WS_deln/Pour_Point_UTM.shp",
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
        help="Specific user ID to scan (e.g., 1 for 1_inputs/1_outputs)",
    )
    parser.add_argument(
        "--all-users",
        action="store_true",
        help="Scan all users in the directory",
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
        elif args.all_users:
            user_dirs = all_user_dirs
        else:
            # Default: scan user 1 or prompt
            user_dirs = [(uid, inp, out) for uid, inp, out in all_user_dirs if uid == 1]
            if not user_dirs:
                print("No default user (1) found. Use --user-id or --all-users", file=sys.stderr)
                print(f"Available users: {[uid for uid, _, _ in all_user_dirs]}", file=sys.stderr)
                sys.exit(1)

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
    viable = sum(1 for p in all_projects if p["ws_delineation_complete"])
    print(f"\nSummary: {viable}/{len(all_projects)} projects have completed WS delineation")


if __name__ == "__main__":
    main()
