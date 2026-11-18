"""Generate trusted exact/+1 GeoParquet controls and invoke the Rust CLI."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile
import time

from shapely.geometry import Point
from shapely.wkb import dumps

from red_fixtures.generate_fixtures import arrow_file, geo_metadata

ROOT = Path(__file__).resolve().parents[4]
CLI = (
    ROOT
    / "wepppy/microservices/shape_converter/rust/geoparquet_parser_cli/target/release/geoparquet_parser_cli"
)


def invoke(root: Path, source: Path, *, max_features: int = 100_000) -> dict[str, object]:
    output = root / "output.json"
    started = time.perf_counter()
    result = subprocess.run(
        [
            CLI,
            "--request-root", root,
            "--input-path", source,
            "--output-path", output,
            "--max-payload-bytes", "16777216",
            "--max-input-bytes", "104857600",
            "--max-features", str(max_features),
            "--max-vertices-per-feature", "250000",
            "--max-memory-bytes", "402653184",
            "--max-cpu-seconds", "60",
            "--max-open-files", "32",
        ],
        check=False,
        capture_output=True,
        text=True,
        env={"LC_ALL": "C", "LANG": "C"},
    )
    count = 0
    output_bytes = 0
    if output.exists():
        output_bytes = output.stat().st_size
        count = json.loads(output.read_text())["feature_count"]
        output.unlink()
    return {
        "exit": result.returncode,
        "stderr": result.stderr.strip(),
        "features": count,
        "input_bytes": source.stat().st_size,
        "output_bytes": output_bytes,
        "elapsed_seconds": round(time.perf_counter() - started, 6),
    }


def main() -> None:
    point = dumps(Point(0, 0))
    results: dict[str, object] = {}
    with tempfile.TemporaryDirectory(prefix="geoparquet-thresholds-") as raw:
        root = Path(raw)
        for rows in (100_000, 100_001):
            source = root / f"rows-{rows}.parquet"
            source.write_bytes(
                arrow_file(
                    [point] * rows,
                    metadata=geo_metadata(geometry_types=["Point"]),
                    properties={"field_id": list(range(rows))},
                    codec="snappy",
                )
            )
            results[f"rows_{rows}"] = invoke(root, source)
            source.unlink()

        for columns in (64, 65):
            source = root / f"columns-{columns}.parquet"
            properties = {f"c{index}": [index] for index in range(columns - 1)}
            source.write_bytes(
                arrow_file(
                    [point],
                    metadata=geo_metadata(geometry_types=["Point"]),
                    properties=properties,
                    codec="snappy",
                )
            )
            results[f"columns_{columns}"] = invoke(root, source)
            source.unlink()

    assert results["rows_100000"]["exit"] == 0
    assert results["rows_100000"]["features"] == 100_000
    assert results["rows_100001"]["stderr"] == "geoparquet_parser_error:row_limit"
    assert results["columns_64"]["exit"] == 0
    assert results["columns_64"]["features"] == 1
    assert results["columns_65"]["stderr"] == "geoparquet_parser_error:footer_structure_limit"
    print(json.dumps(results, sort_keys=True))


if __name__ == "__main__":
    main()
