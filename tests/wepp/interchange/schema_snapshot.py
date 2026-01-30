from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

import pyarrow as pa
import pyarrow.parquet as pq

from wepppy.wepp.interchange.versioning import INTERCHANGE_VERSION, schema_with_version
REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SOURCE_DIR = (
    REPO_ROOT
    / "tests"
    / "wepp"
    / "interchange"
    / "fixtures"
    / "deductive-futurist"
    / "wepp"
    / "output"
    / "interchange"
)
SNAPSHOT_DIR = (
    REPO_ROOT / "tests" / "wepp" / "interchange" / "fixtures" / "schema_snapshots"
)

SNAPSHOT_TARGETS: dict[str, str] = {
    "pass_events": "pass_pw0.events.parquet",
    "pass_metadata": "pass_pw0.metadata.parquet",
    "soil": "soil_pw0.parquet",
    "loss_average_hill": "loss_pw0.hill.parquet",
    "loss_average_chn": "loss_pw0.chn.parquet",
    "loss_average_out": "loss_pw0.out.parquet",
    "loss_average_class": "loss_pw0.class_data.parquet",
    "loss_all_years_hill": "loss_pw0.all_years.hill.parquet",
    "loss_all_years_chn": "loss_pw0.all_years.chn.parquet",
    "loss_all_years_out": "loss_pw0.all_years.out.parquet",
    "loss_all_years_class": "loss_pw0.all_years.class_data.parquet",
    "chan_peak": "chan.out.parquet",
    "ebe": "ebe_pw0.parquet",
    "chanwb": "chanwb.parquet",
    "chnwb": "chnwb.parquet",
    "hill_pass": "H.pass.parquet",
    "hill_ebe": "H.ebe.parquet",
    "hill_element": "H.element.parquet",
    "hill_loss": "H.loss.parquet",
    "hill_soil": "H.soil.parquet",
    "hill_wat": "H.wat.parquet",
}

REQUIRED_SCHEMA_METADATA_KEYS = {
    "dataset_version",
    "dataset_version_major",
    "dataset_version_minor",
    "schema_version",
}


def _metadata_to_dict(metadata: Mapping[bytes, bytes] | None) -> dict[str, str]:
    if not metadata:
        return {}
    items = sorted(metadata.items(), key=lambda item: item[0])
    return {
        key.decode("utf-8", "replace"): value.decode("utf-8", "replace")
        for key, value in items
    }


def schema_to_dict(schema: pa.Schema) -> dict[str, Any]:
    return {
        "metadata": _metadata_to_dict(schema.metadata),
        "fields": [
            {
                "name": field.name,
                "type": str(field.type),
                "nullable": field.nullable,
                "metadata": _metadata_to_dict(field.metadata),
            }
            for field in schema
        ],
    }


def schema_from_parquet(parquet_path: Path) -> pa.Schema:
    return pq.read_schema(parquet_path)


def assert_schema_matches_snapshot(schema: pa.Schema, snapshot_name: str) -> None:
    expected = load_schema_snapshot(snapshot_name)
    actual = schema_to_dict(schema)
    assert actual == expected


def assert_version_metadata(schema: pa.Schema) -> None:
    metadata = _metadata_to_dict(schema.metadata)
    missing = REQUIRED_SCHEMA_METADATA_KEYS - set(metadata)
    assert not missing, f"Missing schema metadata keys: {sorted(missing)}"


def load_schema_snapshot(snapshot_name: str) -> dict[str, Any]:
    snapshot_path = SNAPSHOT_DIR / f"{snapshot_name}.json"
    if not snapshot_path.exists():
        raise FileNotFoundError(snapshot_path)
    return json.loads(snapshot_path.read_text(encoding="utf-8"))


def write_schema_snapshot(snapshot_name: str, schema: pa.Schema, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{snapshot_name}.json"
    payload = schema_to_dict(schema_with_version(schema, version=INTERCHANGE_VERSION))
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return output_path


def generate_snapshots(
    *,
    source_dir: Path = DEFAULT_SOURCE_DIR,
    output_dir: Path = SNAPSHOT_DIR,
) -> list[Path]:
    if not source_dir.exists():
        raise FileNotFoundError(source_dir)
    generated: list[Path] = []
    for name, filename in SNAPSHOT_TARGETS.items():
        parquet_path = source_dir / filename
        if not parquet_path.exists():
            raise FileNotFoundError(parquet_path)
        schema = schema_from_parquet(parquet_path)
        generated.append(write_schema_snapshot(name, schema, output_dir))
    return generated


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate interchange schema snapshots.")
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=DEFAULT_SOURCE_DIR,
        help="Directory containing interchange parquet outputs.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=SNAPSHOT_DIR,
        help="Directory to write schema snapshot JSON files.",
    )
    args = parser.parse_args()
    generated = generate_snapshots(source_dir=args.source_dir, output_dir=args.output_dir)
    print(f"Generated {len(generated)} schema snapshots in {args.output_dir}")


if __name__ == "__main__":
    main()
