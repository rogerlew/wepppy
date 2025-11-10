"""Download helper for the EU SoilHydroGrids archive."""

from __future__ import annotations

from pathlib import Path
from urllib.request import urlopen

DEFAULT_DATASETS = ("THS", "KS", "WP", "FC")
DEFAULT_DEPTHS = ("sl1", "sl2", "sl3", "sl4", "sl5", "sl6", "sl7")
URL_TEMPLATE = (
    "https://eusoilhydrogrids.rissac.hu/dl1k.php?"
    "nev=Roger+Lew&email=rogerlew%40uidaho.edu&dataset={dataset}&depth={depth}"
)


def download_soilhydrogrids_archives(
    datasets: tuple[str, ...] = DEFAULT_DATASETS,
    depths: tuple[str, ...] = DEFAULT_DEPTHS,
    destination: str | Path = ".",
    url_template: str = URL_TEMPLATE,
) -> None:
    """Download all depth slices for the requested SoilHydroGrids datasets."""
    dest_path = Path(destination).expanduser().resolve()
    dest_path.mkdir(parents=True, exist_ok=True)

    for dataset in datasets:
        for depth in depths:
            url = url_template.format(dataset=dataset, depth=depth)
            output_path = dest_path / f"{dataset}_{depth}.zip"
            print(f"Downloading {url} -> {output_path}")
            with urlopen(url) as response, open(output_path, "wb") as fp:
                fp.write(response.read())


if __name__ == "__main__":
    download_soilhydrogrids_archives()
