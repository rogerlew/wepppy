"""Generate reproducible coordinate manifests for EU invalid-soil searches.

The generated manifest is intentionally only a sampling frame. Source
screening and full ESDAC builds are separate steps so a large search does not
silently change production soil-building behavior.
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any

DEFAULT_ANCHOR_ATTRIBUTE = "fao90lev1"
DEFAULT_SEED = 20260819
DEFAULT_STRATA = (20, 20)


def _sample_pixel_indices(
    width: int,
    height: int,
    sample_count: int,
    *,
    seed: int,
    strata: tuple[int, int] = DEFAULT_STRATA,
) -> list[tuple[int, int]]:
    """Return deterministic, unique pixel indices distributed across strata."""
    if width < 1 or height < 1:
        raise ValueError(f"Raster dimensions must be positive, got {width}x{height}.")
    if sample_count < 1:
        raise ValueError(f"sample_count must be positive, got {sample_count}.")
    if sample_count > width * height:
        raise ValueError(
            f"Cannot draw {sample_count} unique pixels from {width * height} cells."
        )

    strata_rows, strata_cols = strata
    if not (1 <= strata_rows <= height and 1 <= strata_cols <= width):
        raise ValueError(
            f"Strata {strata_rows}x{strata_cols} do not fit raster {width}x{height}."
        )

    rng = random.Random(seed)
    stratum_count = strata_rows * strata_cols
    base_count, remainder = divmod(sample_count, stratum_count)
    samples: list[tuple[int, int]] = []

    for stratum_index in range(stratum_count):
        row_stratum, col_stratum = divmod(stratum_index, strata_cols)
        row_start = (row_stratum * height) // strata_rows
        row_stop = ((row_stratum + 1) * height) // strata_rows
        col_start = (col_stratum * width) // strata_cols
        col_stop = ((col_stratum + 1) * width) // strata_cols
        cells = [
            (row, col)
            for row in range(row_start, row_stop)
            for col in range(col_start, col_stop)
        ]
        draw_count = base_count + (stratum_index < remainder)
        if draw_count > len(cells):
            raise ValueError(
                f"Stratum {stratum_index} has {len(cells)} cells but needs {draw_count}."
            )
        samples.extend(rng.sample(cells, draw_count))

    return samples


def _manifest_path(output: Path) -> Path:
    return output if output.suffix.lower() == ".json" else output / "manifest.json"


def build_manifest(
    *,
    sample_count: int,
    seed: int,
    output: Path,
    anchor_attribute: str = DEFAULT_ANCHOR_ATTRIBUTE,
    strata: tuple[int, int] = DEFAULT_STRATA,
    force: bool = False,
) -> Path:
    """Build a coordinate manifest from the installed ESDAC anchor raster."""
    from wepppy.all_your_base.geo import RasterDatasetInterpolator
    from wepppy.eu.soils.esdac import ESDAC

    esdac = ESDAC()
    try:
        anchor_path = esdac.catalog[anchor_attribute]
    except KeyError as exc:
        raise FileNotFoundError(
            f"ESDAC anchor raster {anchor_attribute!r} is not catalogued. "
            "Install the matching ESDAC rasters before running this search."
        ) from exc

    raster = RasterDatasetInterpolator(anchor_path)
    pixel_indices = _sample_pixel_indices(
        raster.width,
        raster.height,
        sample_count,
        seed=seed,
        strata=strata,
    )

    samples: list[dict[str, Any]] = []
    for sample_id, (row, col) in enumerate(pixel_indices):
        easting, northing = raster.get_geo_coord(col + 0.5, row + 0.5)
        lng, lat = raster.proj2wgs_transformer.transform(easting, northing)
        samples.append(
            {
                "sample_id": sample_id,
                "row": row,
                "col": col,
                "lng": float(lng),
                "lat": float(lat),
            }
        )

    manifest = {
        "schema_version": 1,
        "campaign": "eu-invalid-soil-search",
        "sampling": {
            "seed": seed,
            "sample_count": sample_count,
            "strata": {"rows": strata[0], "cols": strata[1]},
            "unique_pixels": True,
        },
        "source": {
            "anchor_attribute": anchor_attribute,
            "anchor_raster": str(anchor_path),
            "width": raster.width,
            "height": raster.height,
            "projection": raster.wkt_text,
            "geotransform": list(raster.transform),
        },
        "samples": samples,
    }

    manifest_path = _manifest_path(output)
    if manifest_path.exists() and not force:
        raise FileExistsError(
            f"Refusing to overwrite {manifest_path}; pass --force to replace it."
        )
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return manifest_path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    count = parser.add_mutually_exclusive_group(required=True)
    count.add_argument("--pilot", type=int, help="Generate a pilot manifest.")
    count.add_argument("--samples", type=int, help="Generate a full manifest.")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--anchor-attribute", default=DEFAULT_ANCHOR_ATTRIBUTE)
    parser.add_argument("--strata-rows", type=int, default=DEFAULT_STRATA[0])
    parser.add_argument("--strata-cols", type=int, default=DEFAULT_STRATA[1])
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    sample_count = args.pilot if args.pilot is not None else args.samples
    assert sample_count is not None
    manifest_path = build_manifest(
        sample_count=sample_count,
        seed=args.seed,
        output=args.output,
        anchor_attribute=args.anchor_attribute,
        strata=(args.strata_rows, args.strata_cols),
        force=args.force,
    )
    print(f"Wrote {sample_count} samples to {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
