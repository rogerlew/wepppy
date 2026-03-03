#!/usr/bin/env python3
"""Build merged WGS GeoJSON layers for St. Joe tributary runs.

The script reads run IDs from README.md entries like:
    - Run ID: `example-run-id`

For each run, it loads:
    /wc1/runs/<prefix>/<runid>/dem/wbt/bound.WGS.geojson
    /wc1/runs/<prefix>/<runid>/dem/wbt/channels.WGS.geojson
    /wc1/runs/<prefix>/<runid>/dem/wbt/subcatchments.WGS.geojson

It merges features per layer and injects `runid` into each feature's properties.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


RUN_ID_PATTERN = re.compile(r"^- Run ID: `([^`]+)`\s*$", re.MULTILINE)
LAYER_SOURCES = {
    "watersheds": "bound.WGS.geojson",
    "channels": "channels.WGS.geojson",
    "subcatchments": "subcatchments.WGS.geojson",
}


def parse_run_ids(readme_path: Path) -> list[str]:
    text = readme_path.read_text(encoding="utf-8")
    run_ids = RUN_ID_PATTERN.findall(text)
    if not run_ids:
        raise ValueError(f"No run IDs found in {readme_path}")

    # Preserve order while removing duplicates.
    unique_run_ids = list(dict.fromkeys(run_ids))
    return unique_run_ids


def find_run_directory(runs_root: Path, run_id: str) -> Path:
    matches = list(runs_root.glob(f"*/{run_id}"))
    if not matches:
        raise FileNotFoundError(f"Run directory not found for run ID '{run_id}' under {runs_root}")
    if len(matches) > 1:
        matched = ", ".join(str(path) for path in matches)
        raise RuntimeError(f"Multiple run directories found for run ID '{run_id}': {matched}")
    return matches[0]


def load_feature_collection(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("type") != "FeatureCollection":
        raise ValueError(f"Expected FeatureCollection in {path}, got type={data.get('type')!r}")
    features = data.get("features")
    if not isinstance(features, list):
        raise ValueError(f"'features' is not a list in {path}")
    return data


def build_collection(readme_path: Path, runs_root: Path, layer_filename: str, layer_name: str) -> dict:
    run_ids = parse_run_ids(readme_path)
    combined_features = []
    missing_paths: list[Path] = []

    for run_id in run_ids:
        run_dir = find_run_directory(runs_root, run_id)
        source_geojson = run_dir / "dem" / "wbt" / layer_filename
        if not source_geojson.exists():
            missing_paths.append(source_geojson)
            continue

        feature_collection = load_feature_collection(source_geojson)
        for feature in feature_collection["features"]:
            if not isinstance(feature, dict):
                raise ValueError(f"Feature is not an object in {source_geojson}")
            properties = feature.get("properties")
            if properties is None:
                properties = {}
            if not isinstance(properties, dict):
                raise ValueError(f"'properties' is not an object in {source_geojson}")
            properties["runid"] = run_id
            feature["properties"] = properties
            combined_features.append(feature)

    if missing_paths:
        missing = "\n".join(str(path) for path in missing_paths)
        raise FileNotFoundError(
            f"Missing WGS {layer_name} GeoJSON for one or more runs:\n"
            f"{missing}"
        )

    return {
        "type": "FeatureCollection",
        "name": f"st_joe_{layer_name}",
        "features": combined_features,
    }


def main() -> int:
    this_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--readme",
        type=Path,
        default=this_dir / "README.md",
        help="Path to README containing `Run ID` entries.",
    )
    parser.add_argument(
        "--runs-root",
        type=Path,
        default=Path("/wc1/runs"),
        help="Root directory containing run subdirectories.",
    )
    parser.add_argument(
        "--watersheds-output",
        type=Path,
        default=this_dir / "st-joe_watersheds.geojson",
        help="Output merged watersheds GeoJSON path.",
    )
    parser.add_argument(
        "--channels-output",
        type=Path,
        default=this_dir / "st-joe_channels.geojson",
        help="Output merged channels GeoJSON path.",
    )
    parser.add_argument(
        "--subcatchments-output",
        type=Path,
        default=this_dir / "st-joe_subcatchments.geojson",
        help="Output merged subcatchments GeoJSON path.",
    )
    args = parser.parse_args()

    run_ids = parse_run_ids(args.readme)
    outputs = {
        "watersheds": args.watersheds_output,
        "channels": args.channels_output,
        "subcatchments": args.subcatchments_output,
    }

    for layer_name, output_path in outputs.items():
        merged = build_collection(
            args.readme,
            args.runs_root,
            layer_filename=LAYER_SOURCES[layer_name],
            layer_name=layer_name,
        )
        output_path.write_text(json.dumps(merged, indent=2) + "\n", encoding="utf-8")
        print(
            f"Wrote {len(merged['features'])} {layer_name} features from {len(run_ids)} runs to {output_path}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
