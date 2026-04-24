from __future__ import annotations

from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from wepppy.nodb.core.landuse import Landuse

pytestmark = pytest.mark.unit


def test_build_managements_uses_watershed_hillslope_area_for_coverage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wd = tmp_path / "run"
    wd.mkdir(parents=True, exist_ok=True)

    landuse = Landuse.__new__(Landuse)
    landuse.wd = str(wd)
    landuse._mapping = "test-mapping"
    landuse.domlc_d = {"11": "forest", "12": "range"}
    landuse.managements = None
    landuse.locked = lambda: nullcontext()
    landuse.dump_landuse_parquet = lambda: None
    landuse.trigger = lambda *_args, **_kwargs: None

    map_stub = SimpleNamespace(cellsize=30.0)

    hillslope_area_calls: list[str] = []

    class _WatershedStub:
        subwta = str(wd / "watershed" / "subwta.tif")

        @staticmethod
        def hillslope_area(topaz_id: str) -> float:
            topaz_id = str(topaz_id)
            hillslope_area_calls.append(topaz_id)
            return {"11": 6.0, "12": 4.0}[topaz_id]

    monkeypatch.setattr(
        Landuse,
        "ron_instance",
        property(lambda _self: map_stub),
    )
    monkeypatch.setattr(
        Landuse,
        "watershed_instance",
        property(lambda _self: _WatershedStub()),
    )
    monkeypatch.setattr(
        Landuse,
        "wepp_instance",
        property(lambda _self: SimpleNamespace(_multi_ofe=False)),
    )

    def _fake_read_raster(_path: str, dtype: type[np.int32]):
        # Deliberately mismatched from hillslope_area() to ensure coverage no longer
        # comes from subwta pixel counts for this path.
        subwta = np.array([[11, 11, 11, 11, 11, 11, 11, 11, 11, 12]], dtype=dtype)
        return subwta, None, None

    monkeypatch.setattr("wepppy.nodb.core.landuse.read_raster", _fake_read_raster)

    class _ManagementSummaryStub:
        def __init__(self) -> None:
            self.area = 0.0
            self.pct_coverage = 0.0

    monkeypatch.setattr(
        "wepppy.nodb.core.landuse.get_management_summary",
        lambda *_args, **_kwargs: _ManagementSummaryStub(),
    )

    landuse.build_managements()

    assert hillslope_area_calls == ["11", "12"]
    assert landuse.managements["forest"].area == pytest.approx(6.0)
    assert landuse.managements["range"].area == pytest.approx(4.0)
    assert landuse.managements["forest"].pct_coverage == pytest.approx(60.0)
    assert landuse.managements["range"].pct_coverage == pytest.approx(40.0)


def test_build_managements_multi_ofe_uses_rust_pair_counts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wd = tmp_path / "run"
    wd.mkdir(parents=True, exist_ok=True)

    landuse = Landuse.__new__(Landuse)
    landuse.wd = str(wd)
    landuse._mapping = "test-mapping"
    landuse.domlc_d = {"11": "forest", "12": "range"}
    landuse.domlc_mofe_d = {
        "11": {"1": "forest", "2": "range"},
        "12": {"1": "range", "2": "forest"},
    }
    landuse.managements = None
    landuse.locked = lambda: nullcontext()
    landuse.dump_landuse_parquet = lambda: None
    landuse.trigger = lambda *_args, **_kwargs: None

    map_stub = SimpleNamespace(cellsize=30.0)

    class _WatershedStub:
        subwta = str(wd / "watershed" / "subwta.tif")
        mofe_map = str(wd / "watershed" / "mofe.tif")

        @staticmethod
        def hillslope_area(topaz_id: str) -> float:
            return {"11": 6.0, "12": 4.0}[str(topaz_id)]

    monkeypatch.setattr(
        Landuse,
        "ron_instance",
        property(lambda _self: map_stub),
    )
    monkeypatch.setattr(
        Landuse,
        "watershed_instance",
        property(lambda _self: _WatershedStub()),
    )
    monkeypatch.setattr(
        Landuse,
        "wepp_instance",
        property(lambda _self: SimpleNamespace(_multi_ofe=True)),
    )

    rust_calls: list[dict[str, object]] = []

    def _fake_pair_counts(**kwargs: object) -> dict[str, dict[str, int]]:
        rust_calls.append(kwargs)
        return {
            "11": {"1": 2, "2": 3},
            "12": {"1": 4},
        }

    monkeypatch.setattr(
        "wepppy.nodb.core.landuse.count_intersecting_raster_key_pairs",
        _fake_pair_counts,
    )

    class _ManagementSummaryStub:
        def __init__(self) -> None:
            self.area = 0.0
            self.pct_coverage = 0.0

    monkeypatch.setattr(
        "wepppy.nodb.core.landuse.get_management_summary",
        lambda *_args, **_kwargs: _ManagementSummaryStub(),
    )

    landuse.build_managements()

    assert rust_calls == [
        {
            "key_fn": _WatershedStub.subwta,
            "key2_fn": _WatershedStub.mofe_map,
            "ignore_channels": False,
            "ignore_keys": None,
            "ignore_keys2": None,
        }
    ]

    cell_area_ha = (30.0 ** 2) / 10000.0
    expected_forest_area = 2 * cell_area_ha  # (11,1); (12,2) absent => zero area
    expected_range_area = (3 + 4) * cell_area_ha
    expected_total = expected_forest_area + expected_range_area

    assert landuse.managements["forest"].area == pytest.approx(expected_forest_area)
    assert landuse.managements["range"].area == pytest.approx(expected_range_area)
    assert landuse.managements["forest"].pct_coverage == pytest.approx(
        100.0 * expected_forest_area / expected_total
    )
    assert landuse.managements["range"].pct_coverage == pytest.approx(
        100.0 * expected_range_area / expected_total
    )


def test_build_managements_multi_ofe_propagates_pair_count_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wd = tmp_path / "run"
    wd.mkdir(parents=True, exist_ok=True)

    landuse = Landuse.__new__(Landuse)
    landuse.wd = str(wd)
    landuse._mapping = "test-mapping"
    landuse.domlc_d = {"11": "forest"}
    landuse.domlc_mofe_d = {"11": {"1": "forest"}}
    landuse.managements = None
    landuse.locked = lambda: nullcontext()
    landuse.dump_landuse_parquet = lambda: None
    landuse.trigger = lambda *_args, **_kwargs: None

    monkeypatch.setattr(
        Landuse,
        "ron_instance",
        property(lambda _self: SimpleNamespace(cellsize=30.0)),
    )
    monkeypatch.setattr(
        Landuse,
        "watershed_instance",
        property(
            lambda _self: SimpleNamespace(
                subwta=str(wd / "watershed" / "subwta.tif"),
                mofe_map=str(wd / "watershed" / "mofe.tif"),
                hillslope_area=lambda _topaz_id: 1.0,
            )
        ),
    )
    monkeypatch.setattr(
        Landuse,
        "wepp_instance",
        property(lambda _self: SimpleNamespace(_multi_ofe=True)),
    )

    class _ManagementSummaryStub:
        def __init__(self) -> None:
            self.area = 0.0
            self.pct_coverage = 0.0

    monkeypatch.setattr(
        "wepppy.nodb.core.landuse.get_management_summary",
        lambda *_args, **_kwargs: _ManagementSummaryStub(),
    )
    monkeypatch.setattr(
        "wepppy.nodb.core.landuse.count_intersecting_raster_key_pairs",
        lambda **_kwargs: (_ for _ in ()).throw(ValueError("Raster shape mismatch")),
    )

    with pytest.raises(ValueError, match="Raster shape mismatch"):
        landuse.build_managements()


def test_build_managements_multi_ofe_skips_pair_counts_without_domlc_assignments(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wd = tmp_path / "run"
    wd.mkdir(parents=True, exist_ok=True)

    landuse = Landuse.__new__(Landuse)
    landuse.wd = str(wd)
    landuse._mapping = "test-mapping"
    landuse.domlc_d = {"11": "forest", "12": "range"}
    landuse.domlc_mofe_d = None
    landuse.managements = None
    landuse.locked = lambda: nullcontext()
    landuse.dump_landuse_parquet = lambda: None
    landuse.trigger = lambda *_args, **_kwargs: None

    monkeypatch.setattr(
        Landuse,
        "ron_instance",
        property(lambda _self: SimpleNamespace(cellsize=30.0)),
    )
    monkeypatch.setattr(
        Landuse,
        "watershed_instance",
        property(
            lambda _self: SimpleNamespace(
                subwta=str(wd / "watershed" / "subwta.tif"),
                mofe_map=str(wd / "watershed" / "mofe.tif"),
                hillslope_area=lambda topaz_id: {"11": 6.0, "12": 4.0}[str(topaz_id)],
            )
        ),
    )
    monkeypatch.setattr(
        Landuse,
        "wepp_instance",
        property(lambda _self: SimpleNamespace(_multi_ofe=True)),
    )

    class _ManagementSummaryStub:
        def __init__(self) -> None:
            self.area = 0.0
            self.pct_coverage = 0.0

    monkeypatch.setattr(
        "wepppy.nodb.core.landuse.get_management_summary",
        lambda *_args, **_kwargs: _ManagementSummaryStub(),
    )
    monkeypatch.setattr(
        "wepppy.nodb.core.landuse.count_intersecting_raster_key_pairs",
        lambda **_kwargs: (_ for _ in ()).throw(
            AssertionError("pair counts should not run before domlc_mofe_d is populated")
        ),
    )

    landuse.build_managements()

    assert landuse.managements["forest"].area == pytest.approx(0.0)
    assert landuse.managements["range"].area == pytest.approx(0.0)
    assert landuse.managements["forest"].pct_coverage == pytest.approx(0.0)
    assert landuse.managements["range"].pct_coverage == pytest.approx(0.0)
