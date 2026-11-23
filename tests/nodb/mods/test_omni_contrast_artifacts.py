"""Omni contrast sidecar, export and report readback tests."""

import json
import logging
import sys
import types
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import rasterio.features

from tests.nodb.mods._omni_test_support import (
    DummyGeoDataFrame,
    Rect,
    _noop_lock,
    omni_module as omni_module,
)


pytestmark = pytest.mark.unit


def test_contrast_sidecar_roundtrip(tmp_path, omni_module):
    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)

    contrast = {
        10: "/tmp/contrast/H10",
        "11": "/tmp/contrast/H11"
    }

    sidecar_path = omni._write_contrast_sidecar(1, contrast)
    with open(sidecar_path, "r", encoding="ascii") as fp:
        contents = fp.read()

    assert "\t" in contents

    loaded = omni._load_contrast_sidecar(1)
    assert loaded == {
        "10": "/tmp/contrast/H10",
        "11": "/tmp/contrast/H11"
    }


def test_write_contrast_id_definitions_psv_cumulative(tmp_path, monkeypatch, omni_module):
    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    omni.logger = logging.getLogger("tests.omni.contrast_ids_psv.cumulative")
    omni._contrast_selection_mode = "cumulative"
    omni._contrast_names = [
        "uniform_high,101__to__undisturbed",
        "uniform_high,102__to__undisturbed",
    ]
    omni._contrast_dependency_tree = {}
    omni.locked = _noop_lock

    monkeypatch.setattr(
        omni_module.Omni,
        "base_scenario",
        property(lambda self: omni_module.OmniScenario.Undisturbed),
        raising=False,
    )

    control_output = tmp_path / "_pups" / "omni" / "scenarios" / "uniform_high" / "wepp" / "output"
    contrast_output = tmp_path / "wepp" / "output"

    omni._write_contrast_sidecar(
        1,
        {
            "101": str(contrast_output / "H1"),
            "102": str(control_output / "H2"),
        },
    )
    omni._write_contrast_sidecar(
        2,
        {
            "101": str(control_output / "H1"),
            "102": str(contrast_output / "H2"),
        },
    )

    psv_path = Path(omni._write_contrast_id_definitions_psv())
    assert psv_path.exists()
    assert psv_path.read_text(encoding="ascii").splitlines() == [
        "1|101",
        "2|102",
    ]


def test_write_contrast_id_definitions_psv_user_defined_hillslope_groups(tmp_path, monkeypatch, omni_module):
    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    omni.logger = logging.getLogger("tests.omni.contrast_ids_psv.groups")
    omni._contrast_selection_mode = "user_defined_hillslope_groups"
    omni._contrast_names = [None, "uniform_low,2__to__mulch"]
    omni._contrast_dependency_tree = {}
    omni.locked = _noop_lock

    monkeypatch.setattr(
        omni_module.Omni,
        "base_scenario",
        property(lambda self: omni_module.OmniScenario.Undisturbed),
        raising=False,
    )

    control_output = tmp_path / "_pups" / "omni" / "scenarios" / "uniform_low" / "wepp" / "output"
    contrast_output = tmp_path / "_pups" / "omni" / "scenarios" / "mulch" / "wepp" / "output"

    omni._write_contrast_sidecar(
        2,
        {
            "10": str(contrast_output / "H1"),
            "11": str(contrast_output / "H2"),
            "12": str(control_output / "H3"),
        },
    )

    psv_path = Path(omni._write_contrast_id_definitions_psv())
    assert psv_path.exists()
    assert psv_path.read_text(encoding="ascii").splitlines() == ["2|10,11"]


def test_write_contrast_id_definitions_psv_user_defined_areas_merges_report_rows(
    tmp_path,
    monkeypatch,
    omni_module,
):
    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    omni.logger = logging.getLogger("tests.omni.contrast_ids_psv.user_defined_areas")
    omni._contrast_selection_mode = "user_defined_areas"
    omni._contrast_names = ["uniform_low,1__to__mulch"]
    omni._contrast_dependency_tree = {}
    omni.locked = _noop_lock

    monkeypatch.setattr(
        omni_module.Omni,
        "base_scenario",
        property(lambda self: omni_module.OmniScenario.Undisturbed),
        raising=False,
    )

    contrast_output = tmp_path / "_pups" / "omni" / "scenarios" / "mulch" / "wepp" / "output"
    omni._write_contrast_sidecar(
        1,
        {
            "10": str(contrast_output / "H1"),
            "11": str(contrast_output / "H2"),
            "12": str(contrast_output / "H3"),
        },
    )

    report_path = Path(omni._contrast_build_report_path())
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "contrast_id": 1,
                        "selection_mode": "user_defined_areas",
                        "topaz_ids": ["12", "10"],
                    }
                ),
                json.dumps(
                    {
                        "contrast_id": 1,
                        "selection_mode": "user_defined_areas",
                        "topaz_ids": ["11"],
                    }
                ),
            ]
        )
        + "\n",
        encoding="ascii",
    )

    assert Path(omni._write_contrast_id_definitions_psv()).read_text(encoding="ascii").splitlines() == [
        "1|10,11,12",
    ]


def test_write_contrast_id_definitions_psv_stream_order(tmp_path, monkeypatch, omni_module):
    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    omni.logger = logging.getLogger("tests.omni.contrast_ids_psv.stream_order")
    omni._contrast_selection_mode = "stream_order"
    omni._contrast_names = [None, "uniform_low,2__to__mulch"]
    omni._contrast_dependency_tree = {}
    omni.locked = _noop_lock

    monkeypatch.setattr(
        omni_module.Omni,
        "base_scenario",
        property(lambda self: omni_module.OmniScenario.Undisturbed),
        raising=False,
    )

    control_output = tmp_path / "_pups" / "omni" / "scenarios" / "uniform_low" / "wepp" / "output"
    contrast_output = tmp_path / "_pups" / "omni" / "scenarios" / "mulch" / "wepp" / "output"

    omni._write_contrast_sidecar(
        2,
        {
            "20": str(contrast_output / "H1"),
            "21": str(control_output / "H2"),
            "22": str(contrast_output / "H3"),
        },
    )

    psv_path = Path(omni._write_contrast_id_definitions_psv())
    assert psv_path.exists()
    assert psv_path.read_text(encoding="ascii").splitlines() == ["2|20,22"]


def test_load_contrast_id_definitions_psv_allows_empty_topaz_values(tmp_path, omni_module):
    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    omni.logger = logging.getLogger("tests.omni.contrast_ids_psv.load_empty")

    path = Path(omni._contrast_id_definitions_path())
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("1|\n2|10,20\n", encoding="ascii")

    assert omni._load_contrast_id_definitions_psv() == {1: [], 2: [10, 20]}


@pytest.mark.parametrize(
    ("payload", "error_fragment"),
    [
        ("1,10\n", "missing '|'"),
        ("0|10\n", "contrast_id must be a positive integer"),
        ("1|10,\n", "topaz_id must be a positive integer"),
        ("1|abc\n", "topaz_id must be a positive integer"),
        ("1|10\n1|11\n", "duplicate contrast_id"),
        ("1|10,10\n", "duplicate topaz_id"),
    ],
)
def test_load_contrast_id_definitions_psv_rejects_invalid_rows(
    tmp_path,
    omni_module,
    payload,
    error_fragment,
):
    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    omni.logger = logging.getLogger("tests.omni.contrast_ids_psv.load_invalid")

    path = Path(omni._contrast_id_definitions_path())
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="ascii")

    with pytest.raises(ValueError, match=error_fragment):
        omni._load_contrast_id_definitions_psv()


def test_write_contrast_id_definitions_psv_cumulative_falls_back_to_report_topaz_id(
    tmp_path,
    monkeypatch,
    omni_module,
):
    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    omni.logger = logging.getLogger("tests.omni.contrast_ids_psv.fallback")
    omni._contrast_selection_mode = "cumulative"
    omni._contrast_names = ["uniform_low,301__to__uniform_low"]
    omni._contrast_dependency_tree = {}
    omni.locked = _noop_lock

    monkeypatch.setattr(
        omni_module.Omni,
        "base_scenario",
        property(lambda self: omni_module.OmniScenario.Undisturbed),
        raising=False,
    )

    uniform_low_output = (
        tmp_path / "_pups" / "omni" / "scenarios" / "uniform_low" / "wepp" / "output"
    )
    omni._write_contrast_sidecar(
        1,
        {
            "301": str(uniform_low_output / "H1"),
            "302": str(uniform_low_output / "H2"),
        },
    )

    report_path = Path(omni._contrast_build_report_path())
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps({"contrast_id": 1, "topaz_id": 301, "selection_mode": "cumulative"}) + "\n",
        encoding="ascii",
    )

    assert Path(omni._write_contrast_id_definitions_psv()).read_text(encoding="ascii").splitlines() == [
        "1|301",
    ]


def test_clear_contrasts_removes_runs_and_sidecars(tmp_path, omni_module):
    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    omni.locked = _noop_lock
    omni._contrast_names = ["existing"]
    omni._contrasts = [{"1": "/tmp/H1"}]
    omni._contrast_dependency_tree = {"existing": {"signature": "sig"}}

    sidecar_dir = tmp_path / "omni" / "contrasts"
    sidecar_dir.mkdir(parents=True)
    (sidecar_dir / "contrast_00001.tsv").write_text("1\t/tmp/H1\n", encoding="ascii")

    contrasts_dir = tmp_path / "_pups" / "omni" / "contrasts"
    (contrasts_dir / "_uploads").mkdir(parents=True)
    (contrasts_dir / "1").mkdir(parents=True)
    (contrasts_dir / "2").mkdir(parents=True)
    report_path = contrasts_dir / "build_report.ndjson"
    report_path.write_text("{}", encoding="ascii")
    contrasts_report = tmp_path / "omni" / "contrasts.out.parquet"
    contrasts_report.parent.mkdir(parents=True, exist_ok=True)
    contrasts_report.write_text("placeholder", encoding="ascii")
    contrast_definitions = tmp_path / "omni" / "contrast_id_definitions.psv"
    contrast_definitions.write_text("1|10\n", encoding="ascii")

    omni.clear_contrasts()

    assert omni._contrasts is None
    assert omni._contrast_names is None
    assert omni._contrast_dependency_tree == {}
    assert not sidecar_dir.exists()
    assert not report_path.exists()
    assert not contrasts_report.exists()
    assert not contrast_definitions.exists()
    assert (contrasts_dir / "_uploads").exists()
    assert not (contrasts_dir / "1").exists()
    assert not (contrasts_dir / "2").exists()


def test_clear_contrasts_propagates_non_oserror_from_report_cleanup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    omni_module,
) -> None:
    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    omni.locked = _noop_lock
    omni._contrast_names = ["existing"]
    omni._contrasts = [{"1": "/tmp/H1"}]
    omni._contrast_dependency_tree = {}

    report_path = Path(omni._contrast_build_report_path())
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("{}", encoding="ascii")

    original_remove = omni_module.os.remove

    def _remove_with_non_oserror(path: str) -> None:
        if path == str(report_path):
            raise ValueError("simulated-remove-error")
        original_remove(path)

    monkeypatch.setattr(omni_module.os, "remove", _remove_with_non_oserror)

    with pytest.raises(ValueError, match="simulated-remove-error"):
        omni.clear_contrasts()


def _install_json_to_wgs_stub(monkeypatch):
    support_stub = types.ModuleType("wepppy.topo.watershed_abstraction.support")

    def _json_to_wgs(src_fn, s_srs=None):
        src_path = Path(src_fn)
        dst_path = src_path.with_suffix(".WGS.geojson")
        dst_path.write_text(src_path.read_text(encoding="ascii"), encoding="ascii")
        return str(dst_path)

    support_stub.json_to_wgs = _json_to_wgs

    wa_stub = types.ModuleType("wepppy.topo.watershed_abstraction")
    wa_stub.__path__ = []
    wa_stub.support = support_stub

    monkeypatch.setitem(sys.modules, "wepppy.topo.watershed_abstraction", wa_stub)
    monkeypatch.setitem(sys.modules, "wepppy.topo.watershed_abstraction.support", support_stub)


def _install_shapely_shape_stub(monkeypatch):
    shapely_stub = types.ModuleType("shapely")
    shapely_geometry_stub = types.ModuleType("shapely.geometry")
    shapely_ops_stub = types.ModuleType("shapely.ops")

    class DummyShape:
        def __init__(self, geom):
            self.__geo_interface__ = geom
            self.is_empty = False

    shapely_geometry_stub.shape = lambda geom: DummyShape(geom)
    shapely_ops_stub.unary_union = lambda geoms: geoms[0] if geoms else None

    monkeypatch.setitem(sys.modules, "shapely", shapely_stub)
    monkeypatch.setitem(sys.modules, "shapely.geometry", shapely_geometry_stub)
    monkeypatch.setitem(sys.modules, "shapely.ops", shapely_ops_stub)


def test_build_contrast_ids_geojson_cumulative(tmp_path, monkeypatch, omni_module):
    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    omni.logger = logging.getLogger("tests.omni.contrast_ids")
    omni.locked = _noop_lock
    omni._contrast_selection_mode = "cumulative"

    report_path = Path(omni._contrast_build_report_path())
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps({"topaz_id": 101}) + "\n", encoding="ascii")

    hillslope_path = tmp_path / "subwta.wgs.geojson"
    hillslope_path.write_text("{}", encoding="ascii")
    hillslope_rows = [{"TopazID": "101", "geometry": Rect(0.0, 0.0, 1.0, 1.0)}]
    hillslope_gdf = DummyGeoDataFrame(hillslope_rows, crs="EPSG:4326")

    geopandas_stub = types.ModuleType("geopandas")
    geopandas_stub.read_file = lambda path: hillslope_gdf
    monkeypatch.setitem(sys.modules, "geopandas", geopandas_stub)

    shapely_stub = types.ModuleType("shapely")
    shapely_geometry_stub = types.ModuleType("shapely.geometry")
    shapely_ops_stub = types.ModuleType("shapely.ops")
    shapely_geometry_stub.mapping = lambda geom: {
        "type": "Polygon",
        "coordinates": [[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0], [0.0, 0.0]]],
    }
    shapely_ops_stub.unary_union = lambda geoms: geoms[0] if geoms else None
    monkeypatch.setitem(sys.modules, "shapely", shapely_stub)
    monkeypatch.setitem(sys.modules, "shapely.geometry", shapely_geometry_stub)
    monkeypatch.setitem(sys.modules, "shapely.ops", shapely_ops_stub)

    class DummyWatershed:
        subwta_shp = str(hillslope_path)

    monkeypatch.setattr(omni_module.Watershed, "getInstance", lambda wd: DummyWatershed())

    output_path = omni._build_contrast_ids_geojson()

    payload = json.loads(Path(output_path).read_text(encoding="ascii"))
    assert payload["type"] == "FeatureCollection"
    assert payload["features"]
    assert payload["features"][0]["properties"]["contrast_label"] == "101"


def test_build_contrast_ids_geojson_user_defined_areas(tmp_path, monkeypatch, omni_module):
    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    omni.logger = logging.getLogger("tests.omni.contrast_ids.user_defined")
    omni.locked = _noop_lock
    omni._contrast_selection_mode = "user_defined_areas"

    report_path = Path(omni._contrast_build_report_path())
    report_path.parent.mkdir(parents=True, exist_ok=True)
    entries = [
        {
            "selection_mode": "user_defined_areas",
            "feature_index": 1,
            "topaz_ids": ["8122", "8123"],
        },
        {
            "selection_mode": "user_defined_areas",
            "feature_index": 1,
            "topaz_ids": ["8122", "8123"],
        },
        {
            "selection_mode": "user_defined_areas",
            "feature_index": 2,
            "topaz_ids": ["8201", "8202"],
        },
    ]
    report_path.write_text(
        "\n".join(json.dumps(entry) for entry in entries) + "\n",
        encoding="ascii",
    )

    subwta_path = tmp_path / "dem" / "wbt" / "subwta.tif"
    subwta_path.parent.mkdir(parents=True, exist_ok=True)
    subwta_path.write_text("", encoding="ascii")

    class DummyWatershed:
        subwta = str(subwta_path)

    monkeypatch.setattr(omni_module.Watershed, "getInstance", lambda wd: DummyWatershed())

    data = np.ma.array([[8122, 8201], [8123, 8202]], mask=False)

    class DummyDataset:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self, *args, **kwargs):
            return data

        @property
        def transform(self):
            return "transform"

        @property
        def crs(self):
            return "EPSG:32611"

    def _shapes(*args, **kwargs):
        return [
            (
                {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [0.0, 0.0],
                            [1.0, 0.0],
                            [1.0, 1.0],
                            [0.0, 1.0],
                            [0.0, 0.0],
                        ]
                    ],
                },
                1,
            )
        ]

    monkeypatch.setattr(rasterio, "open", lambda *args, **kwargs: DummyDataset())
    monkeypatch.setattr(rasterio.features, "shapes", _shapes)

    _install_shapely_shape_stub(monkeypatch)
    _install_json_to_wgs_stub(monkeypatch)

    output_path = omni._build_contrast_ids_geojson()

    utm_path = output_path.replace(".wgs.geojson", ".utm.geojson")
    assert Path(utm_path).exists()

    payload = json.loads(Path(output_path).read_text(encoding="ascii"))
    labels = [feature["properties"]["contrast_label"] for feature in payload["features"]]
    assert labels == ["1", "2"]
    for feature in payload["features"]:
        assert feature["properties"]["label"] == feature["properties"]["contrast_label"]
        assert feature["properties"]["selection_mode"] == "user_defined_areas"


def test_build_contrast_ids_geojson_user_defined_hillslope_groups(tmp_path, monkeypatch, omni_module):
    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    omni.logger = logging.getLogger("tests.omni.contrast_ids.hillslope_groups")
    omni.locked = _noop_lock
    omni._contrast_selection_mode = "user_defined_hillslope_groups"

    report_path = Path(omni._contrast_build_report_path())
    report_path.parent.mkdir(parents=True, exist_ok=True)
    entries = [
        {
            "selection_mode": "user_defined_hillslope_groups",
            "group_index": 2,
            "topaz_ids": ["101", "102"],
        },
        {
            "selection_mode": "user_defined_hillslope_groups",
            "group_index": 1,
            "topaz_ids": ["103"],
        },
    ]
    report_path.write_text(
        "\n".join(json.dumps(entry) for entry in entries) + "\n",
        encoding="ascii",
    )

    hillslope_path = tmp_path / "subwta.wgs.geojson"
    hillslope_path.write_text("{}", encoding="ascii")
    hillslope_rows = [
        {"TopazID": "101", "geometry": Rect(0.0, 0.0, 1.0, 1.0)},
        {"TopazID": "102", "geometry": Rect(1.0, 0.0, 2.0, 1.0)},
        {"TopazID": "103", "geometry": Rect(2.0, 0.0, 3.0, 1.0)},
    ]
    hillslope_gdf = DummyGeoDataFrame(hillslope_rows, crs="EPSG:4326")

    geopandas_stub = types.ModuleType("geopandas")
    geopandas_stub.read_file = lambda path: hillslope_gdf
    monkeypatch.setitem(sys.modules, "geopandas", geopandas_stub)

    shapely_stub = types.ModuleType("shapely")
    shapely_geometry_stub = types.ModuleType("shapely.geometry")
    shapely_ops_stub = types.ModuleType("shapely.ops")
    shapely_geometry_stub.mapping = lambda geom: {
        "type": "Polygon",
        "coordinates": [[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0], [0.0, 0.0]]],
    }
    shapely_ops_stub.unary_union = lambda geoms: geoms[0] if geoms else None
    monkeypatch.setitem(sys.modules, "shapely", shapely_stub)
    monkeypatch.setitem(sys.modules, "shapely.geometry", shapely_geometry_stub)
    monkeypatch.setitem(sys.modules, "shapely.ops", shapely_ops_stub)

    class DummyWatershed:
        subwta_shp = str(hillslope_path)

    monkeypatch.setattr(omni_module.Watershed, "getInstance", lambda wd: DummyWatershed())

    output_path = omni._build_contrast_ids_geojson()

    payload = json.loads(Path(output_path).read_text(encoding="ascii"))
    labels = [feature["properties"]["contrast_label"] for feature in payload["features"]]
    assert labels == ["1", "2"]
    for feature in payload["features"]:
        assert feature["properties"]["selection_mode"] == "user_defined_hillslope_groups"
        assert feature["properties"]["label"] == feature["properties"]["contrast_label"]
        assert "group_index" in feature["properties"]


def test_build_contrast_ids_geojson_stream_order(tmp_path, monkeypatch, omni_module):
    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    omni.logger = logging.getLogger("tests.omni.contrast_ids.stream_order")
    omni.locked = _noop_lock
    omni._contrast_selection_mode = "stream_order"
    omni._contrast_order_reduction_passes = 1

    report_path = Path(omni._contrast_build_report_path())
    report_path.parent.mkdir(parents=True, exist_ok=True)
    entries = [
        {
            "selection_mode": "stream_order",
            "subcatchments_group": 220,
            "n_hillslopes": 8,
        },
        {
            "selection_mode": "stream_order",
            "subcatchments_group": 220,
            "n_hillslopes": 8,
        },
        {
            "selection_mode": "stream_order",
            "subcatchments_group": 230,
            "n_hillslopes": 6,
        },
        {
            "selection_mode": "stream_order",
            "subcatchments_group": 240,
            "n_hillslopes": 0,
            "status": "skipped",
        },
    ]
    report_path.write_text(
        "\n".join(json.dumps(entry) for entry in entries) + "\n",
        encoding="ascii",
    )

    wbt_dir = tmp_path / "dem" / "wbt"
    wbt_dir.mkdir(parents=True, exist_ok=True)
    subwta_pruned_path = wbt_dir / "subwta.strahler_pruned_1.tif"
    subwta_pruned_path.write_text("", encoding="ascii")

    class DummyWatershed:
        wbt_wd = str(wbt_dir)

    monkeypatch.setattr(omni_module.Watershed, "getInstance", lambda wd: DummyWatershed())

    data = np.ma.array([[22, 23], [0, 0]], mask=False)

    class DummyDataset:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self, *args, **kwargs):
            return data

        @property
        def transform(self):
            return "transform"

        @property
        def crs(self):
            return "EPSG:32611"

    def _shapes(*args, **kwargs):
        return [
            (
                {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [0.0, 0.0],
                            [1.0, 0.0],
                            [1.0, 1.0],
                            [0.0, 1.0],
                            [0.0, 0.0],
                        ]
                    ],
                },
                22,
            ),
            (
                {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [2.0, 2.0],
                            [3.0, 2.0],
                            [3.0, 3.0],
                            [2.0, 3.0],
                            [2.0, 2.0],
                        ]
                    ],
                },
                23,
            ),
        ]

    monkeypatch.setattr(rasterio, "open", lambda *args, **kwargs: DummyDataset())
    monkeypatch.setattr(rasterio.features, "shapes", _shapes)

    _install_shapely_shape_stub(monkeypatch)
    _install_json_to_wgs_stub(monkeypatch)

    output_path = omni._build_contrast_ids_geojson()

    utm_path = output_path.replace(".wgs.geojson", ".utm.geojson")
    assert Path(utm_path).exists()

    payload = json.loads(Path(output_path).read_text(encoding="ascii"))
    labels = [feature["properties"]["contrast_label"] for feature in payload["features"]]
    assert labels == ["220", "230"]
    for feature in payload["features"]:
        assert feature["properties"]["selection_mode"] == "stream_order"
        assert "subcatchments_group" in feature["properties"]


def test_contrasts_report_reads_contrast_outputs_from_pups(tmp_path, monkeypatch, omni_module):
    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    omni.logger = logging.getLogger("tests.omni.contrasts_report")
    omni._contrast_names = ["None,10__to__undisturbed"]
    omni._contrast_selection_mode = "cumulative"

    monkeypatch.setattr(
        omni_module.Omni,
        "base_scenario",
        property(lambda self: omni_module.OmniScenario.Undisturbed),
        raising=False
    )

    contrast_path = tmp_path / "_pups" / "omni" / "contrasts" / "1" / "wepp" / "output" / "interchange" / "loss_pw0.out.parquet"
    contrast_path.parent.mkdir(parents=True, exist_ok=True)
    contrast_path.touch()

    control_path = tmp_path / "wepp" / "output" / "interchange" / "loss_pw0.out.parquet"
    control_path.parent.mkdir(parents=True, exist_ok=True)
    control_path.touch()

    read_calls = []

    def fake_read_parquet(path, *args, **kwargs):
        read_calls.append(str(path))
        if str(path) == str(contrast_path):
            return pd.DataFrame({
                "key": ["Avg. Ann. water discharge from outlet"],
                "value": [1.0],
                "units": ["m^3/yr"]
            })
        return pd.DataFrame({
            "key": ["Avg. Ann. water discharge from outlet"],
            "value": [2.0],
            "units": ["m^3/yr"]
        })

    monkeypatch.setattr(omni_module.pd, "read_parquet", fake_read_parquet)
    monkeypatch.setattr(
        omni_module.pd.DataFrame,
        "to_parquet",
        lambda self, *args, **kwargs: None
    )

    df = omni.contrasts_report()

    assert str(contrast_path) in read_calls
    assert str(control_path) in read_calls
    assert df["control-contrast_v"].iloc[0] == 1.0
