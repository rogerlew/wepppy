from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from wepppy.nodb.mods.rap.rap import RAP, RAP_Band


class _DummyDataset:
    def __init__(self) -> None:
        self.requests = []

    def spatial_stats(self, band: RAP_Band, bound_fn: str):
        self.requests.append(band)
        if band.value >= 7:
            return None
        return {
            "num_pixels": 1,
            "valid_pixels": 1,
            "mean": float(band.value),
            "std": 0.0,
            "units": "%",
        }


def _write_bound(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "ncols        1",
                "nrows        1",
                "xllcorner    0",
                "yllcorner    0",
                "cellsize     1",
                "nodata_value -9999",
                "1",
            ]
        ),
        encoding="ascii",
    )


def test_rap_report_excludes_missing_bands(monkeypatch, tmp_path: Path) -> None:
    dataset = _DummyDataset()
    rap_mgr = SimpleNamespace(get_dataset=lambda year: dataset)

    bound = tmp_path / "bound.asc"
    _write_bound(bound)

    class _WatershedStub:
        def __init__(self, bound_fn: str) -> None:
            self.bound = bound_fn

    monkeypatch.setattr(
        "wepppy.nodb.mods.rap.rap.Watershed",
        SimpleNamespace(getInstance=lambda wd: _WatershedStub(str(bound))),
    )

    rap = object.__new__(RAP)
    rap.wd = str(tmp_path)
    rap.data = {}
    rap._rap_mgr = rap_mgr
    rap._rap_year = 2020

    report = rap.report
    assert report is not None
    assert "Tree uncertainty" not in report
    expected_titles = {
        "Annual Forb And Grass",
        "Bare Ground",
        "Litter",
        "Perennial Forb And Grass",
        "Shrub",
        "Tree",
    }
    assert expected_titles.issubset(report.keys())
