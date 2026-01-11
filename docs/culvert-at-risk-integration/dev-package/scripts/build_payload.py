#!/usr/bin/env python3
"""
Build a wepp.cloud-compatible payload.zip from a Culvert_web_app project.

This script is designed to be copied into Culvert_web_app with minimal changes.
It uses only Python stdlib + GDAL/OGR command-line tools (gdalinfo, ogrinfo, ogr2ogr).

Usage:
    # Basic usage (scans user directories for project)
    python build_payload.py "Santee_10m_no_hydroenforcement"

    # Specify user ID
    python build_payload.py "Santee_10m_no_hydroenforcement" --user-id 1

    # Custom output path
    python build_payload.py "Santee_10m_no_hydroenforcement" --output payload.zip

    # Dry run (validate without creating ZIP)
    python build_payload.py "Santee_10m_no_hydroenforcement" --dry-run

    # Extract to directory for inspection
    python build_payload.py "Santee_10m_no_hydroenforcement" --out-dir ./payload_contents

    # With model parameter overrides
    python build_payload.py "Santee_10m_no_hydroenforcement" \\
        --nlcd-db custom_nlcd.db \\
        --base-project-runid lt_wepp_template

Required files from Culvert_web_app project:
    outputs/{project}/WS_deln/breached_filled_DEM_UTM.tif  -> topo/hydro-enforced-dem.tif
    outputs/{project}/hydrogeo_vuln/main_stream_raster_UTM.tif -> topo/streams.tif
    outputs/{project}/WS_deln/pour_points_snapped_to_RSCS_UTM.shp -> culverts/culvert_points.geojson
    outputs/{project}/WS_deln/all_ws_polygon_UTM.shp -> culverts/watersheds.geojson

Note: We use RSCS-snapped pour points (snapped to Road-Stream Crossing Sites) rather than
the original Pour_Point_UTM.shp. This ensures culvert points are on the stream network.

Output payload.zip structure:
    topo/hydro-enforced-dem.tif
    topo/streams.tif
    culverts/culvert_points.geojson
    culverts/watersheds.geojson
    metadata.json
    model-parameters.json
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Schema versions for JSON files
METADATA_SCHEMA_VERSION = "culvert-metadata-v1"
MODEL_PARAMS_SCHEMA_VERSION = "culvert-model-params-v1"


class PayloadError(Exception):
    """Raised when payload building fails validation or processing."""
    pass


def sanitize_project_id(name: str) -> str:
    """Normalize a project name into a stable project_id."""
    sanitized = re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_")
    return sanitized or "project"


def extract_flow_accum_threshold(ws_deln_dir: Path) -> Optional[int]:
    """
    Extract flowAccumThreshold from user_ws_deln_responses.txt.

    This is the flow accumulation threshold used for stream extraction in
    Culvert_web_app. It's preserved in model-parameters.json for reference
    and potential future use.

    Returns the threshold value as an integer, or None if not found.
    """
    response_file = ws_deln_dir / "user_ws_deln_responses.txt"
    if not response_file.exists():
        return None

    try:
        with open(response_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                # Check for both hydro and no-hydro variants
                if line.startswith("flowAccumThreshold:") or line.startswith("flowAccumThreshold_nohydro:"):
                    value = line.split(":", 1)[1].strip()
                    try:
                        return int(float(value))
                    except ValueError:
                        pass
    except (IOError, UnicodeDecodeError):
        pass

    return None


def run_command(cmd: list[str], check: bool = False) -> tuple[int, str, str]:
    """
    Run a shell command and return (returncode, stdout, stderr).

    Args:
        cmd: Command and arguments as list
        check: If True, raise PayloadError on non-zero exit

    Returns:
        Tuple of (return_code, stdout, stderr)
    """
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120
        )
        if check and result.returncode != 0:
            raise PayloadError(f"Command failed: {' '.join(cmd)}\n{result.stderr}")
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        raise PayloadError(f"Command timed out: {' '.join(cmd)}")
    except FileNotFoundError:
        raise PayloadError(f"Command not found: {cmd[0]}")


def get_proj4(filepath: str) -> Optional[str]:
    """Return proj4 string for a dataset, if available."""
    code, proj4_out, _ = run_command(["gdalsrsinfo", "-o", "proj4", filepath])
    if code != 0:
        return None
    proj4 = proj4_out.strip().strip("'\"")
    return proj4 or None


def get_raster_metadata(filepath: str) -> dict:
    """
    Extract raster metadata using gdalinfo.

    Returns dict with: width, height, pixel_size_x, pixel_size_y, proj4, nodata
    """
    if not os.path.exists(filepath):
        raise PayloadError(f"Raster not found: {filepath}")

    code, stdout, stderr = run_command(["gdalinfo", "-json", filepath])
    if code != 0:
        raise PayloadError(f"gdalinfo failed for {filepath}: {stderr}")

    try:
        info = json.loads(stdout)
    except json.JSONDecodeError as e:
        raise PayloadError(f"Failed to parse gdalinfo JSON for {filepath}: {e}")

    metadata = {
        "path": filepath,
        "size_bytes": os.path.getsize(filepath),
    }

    # Extract size
    if "size" in info:
        metadata["width"] = info["size"][0]
        metadata["height"] = info["size"][1]

    # Extract pixel size from geoTransform [originX, pixelWidth, 0, originY, 0, pixelHeight]
    if "geoTransform" in info:
        gt = info["geoTransform"]
        metadata["pixel_size_x"] = abs(gt[1])
        metadata["pixel_size_y"] = abs(gt[5])

    # Extract proj4
    proj4 = get_proj4(filepath)
    if proj4:
        metadata["proj4"] = proj4

    # Extract nodata value
    if "bands" in info and len(info["bands"]) > 0:
        band = info["bands"][0]
        if "noDataValue" in band:
            metadata["nodata"] = band["noDataValue"]

    return metadata


def get_vector_metadata(filepath: str) -> dict:
    """
    Extract vector metadata using ogrinfo.

    Returns dict with: feature_count, geometry_type, proj4, has_point_id
    """
    if not os.path.exists(filepath):
        raise PayloadError(f"Vector file not found: {filepath}")

    layer_name = Path(filepath).stem

    # Get summary info
    code, stdout, stderr = run_command(["ogrinfo", "-so", "-json", filepath, layer_name])
    if code != 0:
        # Try without -json for older GDAL versions
        code, stdout, stderr = run_command(["ogrinfo", "-so", filepath, layer_name])
        if code != 0:
            raise PayloadError(f"ogrinfo failed for {filepath}: {stderr}")
        return _parse_ogrinfo_text(filepath, stdout)

    try:
        info = json.loads(stdout)
    except json.JSONDecodeError:
        # Fallback to text parsing
        code, stdout, _ = run_command(["ogrinfo", "-so", filepath, layer_name])
        return _parse_ogrinfo_text(filepath, stdout)

    metadata = {"path": filepath}

    # Get shapefile total size
    if filepath.lower().endswith(".shp"):
        metadata["size_bytes"] = _get_shapefile_size(filepath)
    else:
        metadata["size_bytes"] = os.path.getsize(filepath)

    # Parse JSON output
    if "layers" in info and len(info["layers"]) > 0:
        layer = info["layers"][0]
        metadata["feature_count"] = layer.get("featureCount", 0)
        metadata["geometry_type"] = layer.get("geometryType", "Unknown")

        # Check for Point_ID field
        if "fields" in layer:
            metadata["has_point_id"] = any(
                f.get("name") == "Point_ID" for f in layer["fields"]
            )
        else:
            metadata["has_point_id"] = False

        # Get proj4 from dataset
        proj4 = get_proj4(filepath)
        if proj4:
            metadata["proj4"] = proj4

    return metadata


def _parse_ogrinfo_text(filepath: str, output: str) -> dict:
    """Parse text output from ogrinfo (fallback for older GDAL)."""
    metadata = {
        "path": filepath,
        "has_point_id": False,
    }

    if filepath.lower().endswith(".shp"):
        metadata["size_bytes"] = _get_shapefile_size(filepath)
    else:
        metadata["size_bytes"] = os.path.getsize(filepath)

    for line in output.split("\n"):
        line = line.strip()
        if line.startswith("Feature Count:"):
            try:
                metadata["feature_count"] = int(line.split(":")[1].strip())
            except ValueError:
                pass
        elif line.startswith("Geometry:"):
            metadata["geometry_type"] = line.split(":")[1].strip()
        elif line.startswith("Point_ID:"):
            metadata["has_point_id"] = True

    # Get proj4 separately
    proj4 = get_proj4(filepath)
    if proj4:
        metadata["proj4"] = proj4

    return metadata


def _get_shapefile_size(filepath: str) -> int:
    """Get total size of shapefile including all component files."""
    base = Path(filepath).with_suffix("")
    extensions = [".shp", ".shx", ".dbf", ".prj", ".cpg", ".sbn", ".sbx"]
    total = 0
    for ext in extensions:
        component = base.with_suffix(ext)
        if component.exists():
            total += os.path.getsize(component)
    return total


def convert_to_geojson(input_shp: str, output_geojson: str) -> None:
    """Convert shapefile to GeoJSON using ogr2ogr."""
    if not os.path.exists(input_shp):
        raise PayloadError(f"Input shapefile not found: {input_shp}")

    # Remove output if exists (ogr2ogr won't overwrite by default)
    if os.path.exists(output_geojson):
        os.remove(output_geojson)

    code, stdout, stderr = run_command([
        "ogr2ogr",
        "-f", "GeoJSON",
        output_geojson,
        input_shp
    ], check=True)


def compute_file_sha256(filepath: str) -> str:
    """Compute SHA256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def validate_crs_alignment(files: dict[str, dict]) -> None:
    """
    Validate that all files have matching CRS.

    Args:
        files: Dict mapping file description to metadata dict with 'proj4' key

    Raises:
        PayloadError if CRS mismatch detected
    """
    proj4_values = {}
    missing = []
    for name, meta in files.items():
        if "proj4" in meta:
            proj4_values[name] = meta["proj4"]
        else:
            missing.append(name)

    if missing:
        raise PayloadError(
            "Missing CRS (proj4) for required files: "
            + ", ".join(sorted(missing))
        )

    # Normalize and compare proj4 strings
    # Remove whitespace variations for comparison
    def normalize_proj4(p: str) -> set[str]:
        return set(p.strip().split())

    reference_name = list(proj4_values.keys())[0]
    reference_proj4 = normalize_proj4(proj4_values[reference_name])

    for name, proj4 in proj4_values.items():
        if normalize_proj4(proj4) != reference_proj4:
            raise PayloadError(
                f"CRS mismatch between {reference_name} and {name}:\n"
                f"  {reference_name}: {proj4_values[reference_name]}\n"
                f"  {name}: {proj4}"
            )


def validate_raster_alignment(dem_meta: dict, streams_meta: dict) -> None:
    """Validate DEM and streams rasters share dimensions and resolution."""
    required = ("width", "height", "pixel_size_x", "pixel_size_y")
    for key in required:
        if dem_meta.get(key) is None or streams_meta.get(key) is None:
            raise PayloadError(
                f"Missing raster metadata '{key}' for DEM or streams"
            )

    if dem_meta["width"] != streams_meta["width"] or dem_meta["height"] != streams_meta["height"]:
        raise PayloadError(
            "Raster dimension mismatch:\n"
            f"  DEM: {dem_meta['width']}x{dem_meta['height']}\n"
            f"  Streams: {streams_meta['width']}x{streams_meta['height']}"
        )

    tolerance = 1e-4
    if abs(dem_meta["pixel_size_x"] - streams_meta["pixel_size_x"]) > tolerance:
        raise PayloadError(
            "Raster resolution mismatch (pixel_size_x):\n"
            f"  DEM: {dem_meta['pixel_size_x']}\n"
            f"  Streams: {streams_meta['pixel_size_x']}"
        )
    if abs(dem_meta["pixel_size_y"] - streams_meta["pixel_size_y"]) > tolerance:
        raise PayloadError(
            "Raster resolution mismatch (pixel_size_y):\n"
            f"  DEM: {dem_meta['pixel_size_y']}\n"
            f"  Streams: {streams_meta['pixel_size_y']}"
        )


def _load_point_ids(geojson_path: Path) -> tuple[set[str], int]:
    """Load Point_ID values from a GeoJSON file."""
    with open(geojson_path, "r") as f:
        data = json.load(f)

    missing = 0
    point_ids: set[str] = set()
    for feature in data.get("features", []):
        props = feature.get("properties") or {}
        if "Point_ID" not in props:
            missing += 1
            continue
        point_ids.add(str(props["Point_ID"]))
    return point_ids, missing


def validate_watershed_mapping(culvert_geojson: Path, watersheds_geojson: Path) -> None:
    """Ensure all watershed Point_ID values map to culvert Point_ID values."""
    culvert_ids, missing_culverts = _load_point_ids(culvert_geojson)
    watershed_ids, missing_watersheds = _load_point_ids(watersheds_geojson)

    if missing_culverts:
        raise PayloadError("Culvert points missing Point_ID values in GeoJSON")
    if missing_watersheds:
        raise PayloadError("Watersheds missing Point_ID values in GeoJSON")

    if not culvert_ids:
        raise PayloadError("No Point_ID values found in culvert_points.geojson")
    if not watershed_ids:
        raise PayloadError("No Point_ID values found in watersheds.geojson")

    missing = watershed_ids - culvert_ids
    if missing:
        sample = ", ".join(sorted(list(missing))[:5])
        raise PayloadError(
            "Watershed Point_ID values missing in culvert points. Sample: "
            + sample
        )


def validate_point_id(vector_meta: dict, file_desc: str) -> None:
    """Validate that vector file has Point_ID attribute."""
    if not vector_meta.get("has_point_id", False):
        raise PayloadError(
            f"{file_desc} is missing required 'Point_ID' attribute.\n"
            f"File: {vector_meta.get('path', 'unknown')}"
        )


def discover_project(
    project_name: str,
    base_dir: Path,
    user_id: Optional[int] = None
) -> tuple[int, Path, Path]:
    """
    Discover project inputs and outputs directories.

    Returns:
        Tuple of (user_id, inputs_dir, outputs_dir) for the project
    """
    # Look for user directories
    pattern = re.compile(r"^(\d+)_(inputs|outputs)$")
    user_dirs = {}

    for entry in base_dir.iterdir():
        if entry.is_dir():
            match = pattern.match(entry.name)
            if match:
                uid = int(match.group(1))
                dir_type = match.group(2)
                if uid not in user_dirs:
                    user_dirs[uid] = {}
                user_dirs[uid][dir_type] = entry

    if not user_dirs:
        raise PayloadError(
            f"No user directories found in {base_dir}\n"
            "Expected format: 1_inputs, 1_outputs, ..."
        )

    # Find project
    candidates = []
    for uid, dirs in sorted(user_dirs.items()):
        if user_id is not None and uid != user_id:
            continue

        inputs = dirs.get("inputs")
        outputs = dirs.get("outputs")
        if inputs and outputs:
            project_outputs = outputs / project_name
            if project_outputs.exists():
                candidates.append((uid, inputs / project_name, project_outputs))

    if not candidates:
        if user_id is not None:
            raise PayloadError(
                f"Project '{project_name}' not found for user {user_id}"
            )
        raise PayloadError(
            f"Project '{project_name}' not found in any user directory"
        )

    if len(candidates) > 1:
        user_list = ", ".join(str(c[0]) for c in candidates)
        raise PayloadError(
            f"Project '{project_name}' found in multiple user directories: {user_list}\n"
            "Use --user-id to specify which one to use."
        )

    uid, inputs_dir, outputs_dir = candidates[0]
    print(f"Found project in user {uid}")
    return uid, inputs_dir, outputs_dir


def build_payload(
    project_name: str,
    base_dir: Path,
    output_path: Path,
    user_id: Optional[int] = None,
    out_dir: Optional[Path] = None,
    dry_run: bool = False,
    nlcd_db: Optional[str] = None,
    base_project_runid: Optional[str] = None,
) -> None:
    """
    Build a wepp.cloud payload.zip from a Culvert_web_app project.

    Args:
        project_name: Name of the project to package
        base_dir: Base user_data directory
        output_path: Path for output ZIP file
        user_id: Optional user ID to disambiguate projects
        out_dir: Optional directory to extract payload for inspection
        dry_run: If True, validate and print info without creating files
        nlcd_db: Optional NLCD database override for model-parameters.json
        base_project_runid: Optional base project runid for model-parameters.json
    """
    print(f"Building payload for project: {project_name}")
    print(f"Base directory: {base_dir}")

    # Discover project directories
    resolved_user_id, inputs_dir, outputs_dir = discover_project(project_name, base_dir, user_id)
    print(f"Inputs: {inputs_dir}")
    print(f"Outputs: {outputs_dir}")
    project_id = sanitize_project_id(project_name)

    # Define source file paths
    ws_deln = outputs_dir / "WS_deln"
    hydrogeo = outputs_dir / "hydrogeo_vuln"

    source_files = {
        "hydro_dem": ws_deln / "breached_filled_DEM_UTM.tif",
        "streams": hydrogeo / "main_stream_raster_UTM.tif",
        "culvert_points": ws_deln / "pour_points_snapped_to_RSCS_UTM.shp",
        "watersheds": ws_deln / "all_ws_polygon_UTM.shp",
    }

    # Check all required files exist
    print("\nValidating required files...")
    missing = []
    for name, path in source_files.items():
        if not path.exists():
            missing.append(f"  {name}: {path}")
        else:
            print(f"  [OK] {name}: {path}")

    if missing:
        raise PayloadError(
            "Missing required files:\n" + "\n".join(missing)
        )

    # Extract metadata
    print("\nExtracting metadata...")

    dem_meta = get_raster_metadata(str(source_files["hydro_dem"]))
    print(f"  DEM: {dem_meta.get('width')}x{dem_meta.get('height')}, "
          f"{dem_meta.get('pixel_size_x', 0):.2f}m resolution")

    streams_meta = get_raster_metadata(str(source_files["streams"]))
    print(f"  Streams: {streams_meta.get('width')}x{streams_meta.get('height')}")

    culverts_meta = get_vector_metadata(str(source_files["culvert_points"]))
    print(f"  Culverts: {culverts_meta.get('feature_count', 0)} features")

    watersheds_meta = get_vector_metadata(str(source_files["watersheds"]))
    print(f"  Watersheds: {watersheds_meta.get('feature_count', 0)} features")

    # Validate Point_ID attribute
    print("\nValidating Point_ID attributes...")
    validate_point_id(culverts_meta, "Culvert points")
    print("  [OK] culvert_points has Point_ID")
    validate_point_id(watersheds_meta, "Watersheds")
    print("  [OK] watersheds has Point_ID")

    # Validate CRS alignment
    print("\nValidating CRS alignment...")
    all_files = {
        "hydro_dem": dem_meta,
        "streams": streams_meta,
        "culvert_points": culverts_meta,
        "watersheds": watersheds_meta,
    }
    validate_crs_alignment(all_files)
    print(f"  [OK] All files use: {dem_meta.get('proj4', 'unknown')[:60]}...")

    print("\nValidating raster alignment...")
    validate_raster_alignment(dem_meta, streams_meta)
    print("  [OK] DEM and streams dimensions/resolution match")

    # Extract flow accumulation threshold from project settings
    flow_accum_threshold = extract_flow_accum_threshold(ws_deln)
    if flow_accum_threshold is not None:
        print(f"\nFlow accumulation threshold: {flow_accum_threshold}")
    else:
        print("\nFlow accumulation threshold: not found (will omit from model-parameters.json)")

    # Build payload in temp directory (used for dry-run validation too)
    print("\nBuilding payload...")

    with tempfile.TemporaryDirectory(prefix="culvert_payload_") as tmpdir:
        tmp_path = Path(tmpdir)

        # Create directory structure
        (tmp_path / "culverts").mkdir()
        (tmp_path / "topo").mkdir()

        # Convert vectors to GeoJSON
        print("  Converting culvert points to GeoJSON...")
        culvert_geojson = tmp_path / "culverts" / "culvert_points.geojson"
        convert_to_geojson(
            str(source_files["culvert_points"]),
            str(culvert_geojson)
        )

        print("  Converting watersheds to GeoJSON...")
        watersheds_geojson = tmp_path / "culverts" / "watersheds.geojson"
        convert_to_geojson(
            str(source_files["watersheds"]),
            str(watersheds_geojson)
        )

        print("  Validating watershed-to-culvert mapping...")
        validate_watershed_mapping(culvert_geojson, watersheds_geojson)
        print("  [OK] Watershed Point_ID values map to culvert points")

        if dry_run:
            print("\n[DRY RUN] Validation complete. No files created.")
            print("\nPayload would contain:")
            print(f"  topo/hydro-enforced-dem.tif ({dem_meta.get('size_bytes', 0) / 1024 / 1024:.1f} MB)")
            print(f"  topo/streams.tif ({streams_meta.get('size_bytes', 0) / 1024 / 1024:.1f} MB)")
            print(f"  culverts/culvert_points.geojson (from {culverts_meta.get('feature_count', 0)} features)")
            print(f"  culverts/watersheds.geojson (from {watersheds_meta.get('feature_count', 0)} features)")
            print("  metadata.json")
            print("  model-parameters.json")
            return

        # Copy rasters to topo directory
        print("  Copying hydro-enforced DEM...")
        shutil.copy2(source_files["hydro_dem"], tmp_path / "topo" / "hydro-enforced-dem.tif")

        print("  Copying streams raster...")
        shutil.copy2(source_files["streams"], tmp_path / "topo" / "streams.tif")

        # Build metadata.json
        print("  Writing metadata.json...")
        metadata = {
            "schema_version": METADATA_SCHEMA_VERSION,
            "source": {
                "system": "Culvert_web_app",
                "project_id": project_id,
                "user_id": str(resolved_user_id),
            },
            "created_at": datetime.now(timezone.utc).isoformat(),
            "culvert_count": culverts_meta.get("feature_count", 0),
            "crs": {
                "proj4": dem_meta.get("proj4", ""),
            },
            "dem": {
                "path": "topo/hydro-enforced-dem.tif",
                "width": dem_meta.get("width"),
                "height": dem_meta.get("height"),
                "resolution_m": dem_meta.get("pixel_size_x"),
                "nodata": dem_meta.get("nodata"),
            },
            "streams": {
                "path": "topo/streams.tif",
                "nodata": streams_meta.get("nodata"),
                "value_semantics": "binary",
            },
            "culvert_points": {
                "path": "culverts/culvert_points.geojson",
                "feature_count": culverts_meta.get("feature_count", 0),
                "point_id_field": "Point_ID",
            },
            "watersheds": {
                "path": "culverts/watersheds.geojson",
                "feature_count": watersheds_meta.get("feature_count", 0),
                "point_id_field": "Point_ID",
                "simplified": True,
                "simplification_tolerance_m": 1.0,
                "note": "Simplified polygons from Culvert_web_app (1.0m tolerance)",
            },
        }

        with open(tmp_path / "metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)

        # Build model-parameters.json
        print("  Writing model-parameters.json...")
        model_params = {
            "schema_version": MODEL_PARAMS_SCHEMA_VERSION,
        }
        if base_project_runid:
            model_params["base_project_runid"] = base_project_runid
        if nlcd_db:
            model_params["nlcd_db"] = nlcd_db
        if flow_accum_threshold is not None:
            model_params["flow_accum_threshold"] = flow_accum_threshold

        with open(tmp_path / "model-parameters.json", "w") as f:
            json.dump(model_params, f, indent=2)

        # Copy to out_dir if requested
        if out_dir:
            print(f"  Copying to output directory: {out_dir}")
            if out_dir.exists():
                shutil.rmtree(out_dir)
            shutil.copytree(tmp_path, out_dir)

        # Create ZIP file
        print(f"  Creating ZIP: {output_path}")
        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(tmp_path):
                for file in files:
                    file_path = Path(root) / file
                    arcname = file_path.relative_to(tmp_path)
                    zf.write(file_path, arcname)

        # Compute ZIP hash
        zip_hash = compute_file_sha256(str(output_path))
        zip_size = os.path.getsize(output_path)

    print(f"\nPayload created successfully!")
    print(f"  Path: {output_path}")
    print(f"  Size: {zip_size / 1024 / 1024:.1f} MB")
    print(f"  SHA256: {zip_hash}")


def main():
    parser = argparse.ArgumentParser(
        description="Build wepp.cloud payload.zip from Culvert_web_app project",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Basic usage
    python build_payload.py "Santee_10m_no_hydroenforcement"

    # Specify user ID (if project exists in multiple user directories)
    python build_payload.py "Santee_10m_no_hydroenforcement" --user-id 1

    # Dry run (validate only)
    python build_payload.py "Santee_10m_no_hydroenforcement" --dry-run

    # Extract to directory for inspection
    python build_payload.py "Santee_10m_no_hydroenforcement" --out-dir ./inspect

    # With model parameter overrides
    python build_payload.py "Santee_10m_no_hydroenforcement" \\
        --nlcd-db custom_nlcd.db \\
        --base-project-runid lt_wepp_template
        """
    )

    parser.add_argument(
        "project",
        help="Project name (e.g., 'Santee_10m_no_hydroenforcement')"
    )
    parser.add_argument(
        "--base-dir",
        type=Path,
        default=Path("/wc1/culvert_app_instance_dir/user_data"),
        help="Base user_data directory (default: /wc1/culvert_app_instance_dir/user_data)"
    )
    parser.add_argument(
        "--user-id",
        type=int,
        help="User ID to disambiguate if project exists in multiple user directories"
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=Path("payload.zip"),
        help="Output ZIP file path (default: payload.zip)"
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        help="Also extract payload to this directory for inspection"
    )
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Validate and print info without creating files"
    )
    parser.add_argument(
        "--nlcd-db",
        help="NLCD database path override for model-parameters.json"
    )
    parser.add_argument(
        "--base-project-runid",
        help="Base project runid for model-parameters.json"
    )

    args = parser.parse_args()

    # Validate base directory exists
    if not args.base_dir.exists():
        print(f"Error: Base directory not found: {args.base_dir}", file=sys.stderr)
        sys.exit(1)

    try:
        build_payload(
            project_name=args.project,
            base_dir=args.base_dir,
            output_path=args.output,
            user_id=args.user_id,
            out_dir=args.out_dir,
            dry_run=args.dry_run,
            nlcd_db=args.nlcd_db,
            base_project_runid=args.base_project_runid,
        )
    except PayloadError as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nAborted.", file=sys.stderr)
        sys.exit(130)


if __name__ == "__main__":
    main()
