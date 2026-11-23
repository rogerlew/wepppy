"""Omni stream-order grouping, limits and rebuild tests."""

import logging
import os
import sys
import time
import types
from pathlib import Path

import numpy as np
import pytest
import rasterio

from tests.nodb.mods._omni_test_support import _noop_lock, omni_module as omni_module


pytestmark = pytest.mark.unit


@pytest.fixture
def stream_order_workspace(tmp_path):
    wbt_dir = tmp_path / "dem" / "wbt"
    wbt_dir.mkdir(parents=True)

    for stem in ("flovec", "netful", "relief", "chnjnt", "bound", "subwta"):
        (wbt_dir / f"{stem}.tif").write_text("", encoding="ascii")
    (wbt_dir / "outlet.geojson").write_text("{}", encoding="ascii")

    (wbt_dir / "netful.strahler.tif").write_text("", encoding="ascii")
    (wbt_dir / "netful.pruned_1.tif").write_text("", encoding="ascii")
    (wbt_dir / "netful.strahler_pruned_1.tif").write_text("", encoding="ascii")
    (wbt_dir / "chnjnt.strahler_pruned_1.tif").write_text("", encoding="ascii")
    (wbt_dir / "subwta.strahler_pruned_1.tif").write_text("", encoding="ascii")
    (wbt_dir / "netw.strahler_pruned_1.tsv").write_text("", encoding="ascii")
    return wbt_dir


def _stub_stream_order_rasters(monkeypatch, orders, mode_by_topaz):
    class DummyDataset:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self, *args, **kwargs):
            return np.ma.array(orders, mask=False)

    monkeypatch.setattr(rasterio, "open", lambda *args, **kwargs: DummyDataset())

    raster_characteristics = types.ModuleType("wepppyo3.raster_characteristics")
    raster_characteristics.identify_mode_single_raster_key = lambda **kwargs: mode_by_topaz
    raster_characteristics.count_intersecting_raster_key_pairs = lambda **kwargs: {}
    monkeypatch.setitem(sys.modules, "wepppyo3.raster_characteristics", raster_characteristics)


def test_stream_order_contrast_limit_enforced(tmp_path, omni_module, monkeypatch, stream_order_workspace):
    wbt_dir = stream_order_workspace
    _stub_stream_order_rasters(monkeypatch, [list(range(1, 226))], {"10": 1})

    class DummyTranslator:
        top2wepp = {"10": "1"}

    class DummyWatershed:
        delineation_backend_is_wbt = True
        wbt_wd = str(wbt_dir)

        def translator_factory(self):
            return DummyTranslator()

    monkeypatch.setattr(omni_module.Watershed, "getInstance", lambda wd: DummyWatershed())
    monkeypatch.setattr(
        omni_module.Omni,
        "base_scenario",
        property(lambda self: omni_module.OmniScenario.Undisturbed),
        raising=False,
    )
    monkeypatch.setattr(
        omni_module,
        "_resolve_base_scenario_key",
        lambda wd: str(omni_module.OmniScenario.Undisturbed),
    )

    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    omni.locked = _noop_lock
    omni.logger = logging.getLogger("tests.omni.stream_order_limit")
    omni._contrast_selection_mode = "stream_order"
    omni._contrast_pairs = [
        {"control_scenario": "uniform_low", "contrast_scenario": "mulch"},
    ]
    omni._contrast_order_reduction_passes = 1

    with pytest.raises(ValueError) as excinfo:
        omni._build_contrasts()

    assert "limited to 200" in str(excinfo.value)


def test_stream_order_contrasts_grouping_and_skip(tmp_path, omni_module, monkeypatch, stream_order_workspace):
    wbt_dir = stream_order_workspace
    _stub_stream_order_rasters(monkeypatch, [[1, 2, 3]], {"10": 2, "20": 1, "30": 1})

    class DummyTranslator:
        top2wepp = {"10": "1", "20": "2", "30": "3"}

    class DummyWatershed:
        delineation_backend_is_wbt = True
        wbt_wd = str(wbt_dir)

        def translator_factory(self):
            return DummyTranslator()

    monkeypatch.setattr(omni_module.Watershed, "getInstance", lambda wd: DummyWatershed())
    monkeypatch.setattr(
        omni_module.Omni,
        "base_scenario",
        property(lambda self: omni_module.OmniScenario.Undisturbed),
        raising=False,
    )
    monkeypatch.setattr(
        omni_module,
        "_resolve_base_scenario_key",
        lambda wd: str(omni_module.OmniScenario.Undisturbed),
    )

    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    omni.locked = _noop_lock
    omni.logger = logging.getLogger("tests.omni.stream_order")
    omni._contrast_selection_mode = "stream_order"
    omni._contrast_pairs = [
        {"control_scenario": "uniform_low", "contrast_scenario": "mulch"},
        {"control_scenario": "uniform_low", "contrast_scenario": "thinning"},
    ]
    omni._contrast_order_reduction_passes = 1

    omni._build_contrasts()

    assert omni.contrast_names[:4] == [
        "uniform_low,1__to__mulch",
        "uniform_low,2__to__thinning",
        "uniform_low,3__to__mulch",
        "uniform_low,4__to__thinning",
    ]
    assert omni.contrast_names[4:] == [None, None]

    sidecar_path = omni._contrast_sidecar_path(1)
    sidecar = {}
    with open(sidecar_path, "r", encoding="ascii") as handle:
        for line in handle:
            topaz_id, _, wepp_path = line.strip().partition("\t")
            sidecar[topaz_id] = wepp_path

    assert sidecar["20"].endswith("/_pups/omni/scenarios/mulch/wepp/output/H2")
    assert sidecar["30"].endswith("/_pups/omni/scenarios/mulch/wepp/output/H3")
    assert sidecar["10"].endswith("/_pups/omni/scenarios/uniform_low/wepp/output/H1")

    report = omni.contrast_status_report()
    report_index = {item["contrast_id"]: item for item in report["items"]}
    assert report_index[1]["subcatchments_group"] == 10
    assert report_index[3]["subcatchments_group"] == 20
    assert report_index[5]["subcatchments_group"] == 30
    skipped = next(item for item in report["items"] if item["contrast_id"] == 5)
    assert skipped["run_status"] == "skipped"
    assert skipped["skip_status"]["reason"] == "no_hillslopes"


@pytest.mark.parametrize(
    ("build_subcatchments_ts", "expect_prune", "expect_wbt"),
    [
        (10_000_000_000.0, True, True),
        (0.0, False, False),
    ],
)
def test_build_contrasts_stream_order_stale_rebuild_decisions(
    tmp_path,
    omni_module,
    monkeypatch,
    build_subcatchments_ts,
    expect_prune,
    expect_wbt,
    stream_order_workspace,
):
    wbt_dir = stream_order_workspace

    strahler_path = wbt_dir / "netful.strahler.tif"
    pruned_streams_path = wbt_dir / "netful.pruned_1.tif"
    order_pruned_path = wbt_dir / "netful.strahler_pruned_1.tif"
    chnjnt_pruned_path = wbt_dir / "chnjnt.strahler_pruned_1.tif"
    subwta_pruned_path = wbt_dir / "subwta.strahler_pruned_1.tif"
    netw_pruned_path = wbt_dir / "netw.strahler_pruned_1.tsv"
    now = time.time()
    for path in (
        strahler_path,
        pruned_streams_path,
        order_pruned_path,
        chnjnt_pruned_path,
        subwta_pruned_path,
        netw_pruned_path,
    ):
        os.utime(path, (now, now))

    _stub_stream_order_rasters(monkeypatch, [[1]], {"10": 1})

    class DummyTranslator:
        top2wepp = {"10": "1"}

    class DummyWatershed:
        delineation_backend_is_wbt = True
        wbt_wd = str(wbt_dir)

        def translator_factory(self):
            return DummyTranslator()

    monkeypatch.setattr(omni_module.Watershed, "getInstance", lambda wd: DummyWatershed())
    monkeypatch.setattr(
        omni_module.Omni,
        "base_scenario",
        property(lambda self: omni_module.OmniScenario.Undisturbed),
        raising=False,
    )
    monkeypatch.setattr(
        omni_module,
        "_resolve_base_scenario_key",
        lambda wd: str(omni_module.OmniScenario.Undisturbed),
    )

    prune_calls = []

    def _fake_prune(*args, **kwargs):
        prune_calls.append((args, kwargs))
        strahler_path.write_text("", encoding="ascii")
        pruned_streams_path.write_text("", encoding="ascii")
        os.utime(strahler_path, None)
        os.utime(pruned_streams_path, None)

    monkeypatch.setattr(omni_module, "_prune_stream_order", _fake_prune)

    wbt_calls = {"strahler_stream_order": 0, "stream_junction_identifier": 0, "hillslopes_topaz": 0}

    class DummyWhiteboxTools:
        def __init__(self, *args, **kwargs) -> None:
            self._working_dir = str(wbt_dir)

        def set_working_dir(self, working_dir: str) -> None:
            self._working_dir = working_dir

        def strahler_stream_order(self, **kwargs):
            wbt_calls["strahler_stream_order"] += 1
            Path(kwargs["output"]).write_text("", encoding="ascii")
            return 0

        def stream_junction_identifier(self, **kwargs):
            wbt_calls["stream_junction_identifier"] += 1
            Path(kwargs["output"]).write_text("", encoding="ascii")
            return 0

        def hillslopes_topaz(self, **kwargs):
            wbt_calls["hillslopes_topaz"] += 1
            Path(kwargs["subwta"]).write_text("", encoding="ascii")
            Path(kwargs["netw"]).write_text("", encoding="ascii")
            return 0

    whitebox_tools_stub = types.ModuleType("whitebox_tools")
    whitebox_tools_stub.WhiteboxTools = DummyWhiteboxTools
    whitebox_tools_stub.WhiteboxAppError = RuntimeError
    whitebox_tools_stub.WhiteboxToolsRunningError = RuntimeError
    monkeypatch.setitem(sys.modules, "whitebox_tools", whitebox_tools_stub)

    class DummyPrep:
        def __getitem__(self, key):
            return build_subcatchments_ts

    monkeypatch.setattr(omni_module.RedisPrep, "getInstance", lambda wd: DummyPrep())

    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    omni.locked = _noop_lock
    omni.logger = logging.getLogger("tests.omni.stream_order_rebuild")
    omni._contrast_selection_mode = "stream_order"
    omni._contrast_pairs = [{"control_scenario": "uniform_low", "contrast_scenario": "mulch"}]
    omni._contrast_order_reduction_passes = 1

    omni._build_contrasts()

    assert bool(prune_calls) is expect_prune
    assert bool(wbt_calls["hillslopes_topaz"]) is expect_wbt
    assert bool(wbt_calls["strahler_stream_order"]) is expect_wbt
    assert bool(wbt_calls["stream_junction_identifier"]) is expect_wbt
