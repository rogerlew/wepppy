"""Convert ESDAC STU rasters (``.rst``) into GeoTIFFs and JSON metadata."""

from __future__ import annotations

from glob import glob
import json
from pathlib import Path
from subprocess import check_output, run

DEFAULT_RST_GLOB = "/geodata/eu/ESDAC_STU_EU_Layers/*.rst"


def convert_rst_directory(
    raster_glob: str = DEFAULT_RST_GLOB,
) -> None:
    """Iterate over ``.rst`` rasters and emit ``.tif`` + ``.json`` companions."""
    for src in glob(raster_glob):
        src_path = Path(src)
        dst_path = src_path.with_suffix(".tif")
        json_path = src_path.with_suffix(".json")

        cmd = ["gdal_translate", str(src_path), str(dst_path), "-a_srs", "epsg:3035"]
        print(" ".join(cmd))
        run(cmd, check=True)

        info = json.loads(check_output(["gdalinfo", "-json", str(src_path)], text=True))
        with open(json_path, "w", encoding="utf-8") as fp:
            json.dump(info, fp, indent=4, sort_keys=True, allow_nan=False)


if __name__ == "__main__":
    convert_rst_directory()

