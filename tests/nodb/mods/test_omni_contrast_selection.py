"""Omni contrast selection and preview tests."""

import json
import logging
from collections import Counter
from pathlib import Path

import pytest

from tests.nodb.mods._omni_test_support import (
    Rect,
    _noop_lock,
    _stub_user_defined_geodata,
    omni_module as omni_module,
)


pytestmark = pytest.mark.unit


def test_user_defined_areas_contrast_builds_sidecars_with_overlap(tmp_path, omni_module, monkeypatch):
    hillslope_rows = [
        {"TopazID": "10", "geometry": Rect(0.0, 0.0, 10.0, 10.0)},
        {"TopazID": "20", "geometry": Rect(10.0, 0.0, 20.0, 10.0)},
    ]
    user_rows = [
        {"name": "Alpha", "geometry": Rect(0.0, 0.0, 6.0, 10.0)},
        {"name": None, "geometry": Rect(5.0, 0.0, 15.0, 10.0)},
        {"name": "Gamma", "geometry": Rect(30.0, 0.0, 40.0, 10.0)},
    ]
    user_geojson_path = _stub_user_defined_geodata(
        monkeypatch,
        omni_module,
        tmp_path,
        hillslope_rows=hillslope_rows,
        user_rows=user_rows,
    )

    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    omni.locked = _noop_lock
    omni.logger = logging.getLogger("tests.omni.user_defined")
    omni._contrast_selection_mode = "user_defined_areas"
    omni._contrast_geojson_path = str(user_geojson_path)
    omni._contrast_geojson_name_key = "name"
    omni._contrast_pairs = [
        {"control_scenario": "uniform_low", "contrast_scenario": "mulch"}
    ]
    omni._contrast_object_param = "Runoff_mm"
    omni._contrast_cumulative_obj_param_threshold_fraction = 0.8
    omni._contrast_hillslope_limit = None
    omni._contrast_hill_min_slope = None
    omni._contrast_hill_max_slope = None
    omni._contrast_select_burn_severities = None
    omni._contrast_select_topaz_ids = None
    omni._control_scenario = "uniform_low"
    omni._contrast_scenario = "mulch"

    omni._build_contrasts()

    assert omni.contrast_names == [
        "uniform_low,1__to__mulch",
        "uniform_low,2__to__mulch",
        None,
    ]
    assert omni._contrast_labels == {1: "Alpha", 2: "2", 3: "Gamma"}

    def _read_sidecar(path):
        contents = {}
        with open(path, "r", encoding="ascii") as fp:
            for line in fp:
                topaz_id, _, wepp_path = line.strip().partition("\t")
                contents[topaz_id] = wepp_path
        return contents

    contrast1 = _read_sidecar(omni._contrast_sidecar_path(1))
    contrast2 = _read_sidecar(omni._contrast_sidecar_path(2))

    assert contrast1["10"].endswith("/_pups/omni/scenarios/mulch/wepp/output/H1")
    assert contrast1["20"].endswith("/_pups/omni/scenarios/uniform_low/wepp/output/H2")
    assert contrast2["10"].endswith("/_pups/omni/scenarios/mulch/wepp/output/H1")
    assert contrast2["20"].endswith("/_pups/omni/scenarios/mulch/wepp/output/H2")
    assert not Path(omni._contrast_sidecar_path(3)).exists()


def test_user_defined_areas_duplicate_labels_merge_selected_topaz_ids(
    tmp_path,
    omni_module,
    monkeypatch,
):
    hillslope_rows = [
        {"TopazID": "10", "geometry": Rect(0.0, 0.0, 10.0, 10.0)},
        {"TopazID": "20", "geometry": Rect(10.0, 0.0, 20.0, 10.0)},
    ]
    user_rows = [
        {"name": "Alpha", "geometry": Rect(0.0, 0.0, 10.0, 10.0)},
        {"name": "Alpha", "geometry": Rect(10.0, 0.0, 20.0, 10.0)},
    ]
    user_geojson_path = _stub_user_defined_geodata(
        monkeypatch,
        omni_module,
        tmp_path,
        hillslope_rows=hillslope_rows,
        user_rows=user_rows,
    )

    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    omni.locked = _noop_lock
    omni.logger = logging.getLogger("tests.omni.user_defined_merge")
    omni._contrast_selection_mode = "user_defined_areas"
    omni._contrast_geojson_path = str(user_geojson_path)
    omni._contrast_geojson_name_key = "name"
    omni._contrast_pairs = [
        {"control_scenario": "uniform_low", "contrast_scenario": "mulch"}
    ]
    omni._contrast_object_param = "Runoff_mm"
    omni._contrast_cumulative_obj_param_threshold_fraction = 0.8
    omni._contrast_hillslope_limit = None
    omni._contrast_hill_min_slope = None
    omni._contrast_hill_max_slope = None
    omni._contrast_select_burn_severities = None
    omni._contrast_select_topaz_ids = None
    omni._control_scenario = "uniform_low"
    omni._contrast_scenario = "mulch"

    omni._build_contrasts()

    assert omni.contrast_names == ["uniform_low,1__to__mulch"]
    assert omni._contrast_labels == {1: "Alpha"}

    sidecar = omni._load_contrast_sidecar(1)
    mulch_root = "/_pups/omni/scenarios/mulch/wepp/output/"
    assert sidecar["10"].endswith(f"{mulch_root}H1")
    assert sidecar["20"].endswith(f"{mulch_root}H2")

    report_rows = omni._load_contrast_build_report()
    assert [row["contrast_id"] for row in report_rows] == [1, 1]
    assert report_rows[-1]["topaz_ids"] == ["10", "20"]


def test_user_defined_contrast_pairs_expand_and_skip_duplicates(tmp_path, omni_module, monkeypatch):
    hillslope_rows = [
        {"TopazID": "10", "geometry": Rect(0.0, 0.0, 10.0, 10.0)},
        {"TopazID": "20", "geometry": Rect(10.0, 0.0, 20.0, 10.0)},
    ]
    user_rows = [
        {"name": "Alpha", "geometry": Rect(0.0, 0.0, 10.0, 10.0)},
        {"name": "Beta", "geometry": Rect(10.0, 0.0, 20.0, 10.0)},
    ]
    user_geojson_path = _stub_user_defined_geodata(
        monkeypatch,
        omni_module,
        tmp_path,
        hillslope_rows=hillslope_rows,
        user_rows=user_rows,
    )

    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    omni.locked = _noop_lock
    omni.logger = logging.getLogger("tests.omni.user_defined_pairs")
    omni._contrast_selection_mode = "user_defined_areas"
    omni._contrast_geojson_path = str(user_geojson_path)
    omni._contrast_geojson_name_key = "name"
    omni._contrast_pairs = [
        {"control_scenario": "uniform_low", "contrast_scenario": "mulch"},
        {"control_scenario": "uniform_low", "contrast_scenario": "mulch"},
        {"control_scenario": "uniform_low", "contrast_scenario": "thinning"},
    ]
    omni._contrast_object_param = "Runoff_mm"
    omni._contrast_cumulative_obj_param_threshold_fraction = 0.8
    omni._contrast_hillslope_limit = None
    omni._contrast_hill_min_slope = None
    omni._contrast_hill_max_slope = None
    omni._contrast_select_burn_severities = None
    omni._contrast_select_topaz_ids = None
    omni._control_scenario = None
    omni._contrast_scenario = None

    omni._build_contrasts()

    names = [name for name in omni.contrast_names or [] if name]
    assert len(names) == 4
    assert Counter(omni._contrast_labels.values()) == Counter({"Alpha": 2, "Beta": 2})


def test_user_defined_areas_contrast_limit_enforced(tmp_path, omni_module, monkeypatch):
    hillslope_rows = [
        {"TopazID": "10", "geometry": Rect(0.0, 0.0, 10.0, 10.0)},
    ]
    user_rows = [
        {"name": f"Area {idx}", "geometry": Rect(0.0, 0.0, 10.0, 10.0)}
        for idx in range(101)
    ]
    user_geojson_path = _stub_user_defined_geodata(
        monkeypatch,
        omni_module,
        tmp_path,
        hillslope_rows=hillslope_rows,
        user_rows=user_rows,
    )

    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    omni.locked = _noop_lock
    omni.logger = logging.getLogger("tests.omni.user_defined_limit")
    omni._contrast_selection_mode = "user_defined_areas"
    omni._contrast_geojson_path = str(user_geojson_path)
    omni._contrast_geojson_name_key = "name"
    omni._contrast_pairs = [
        {"control_scenario": "uniform_low", "contrast_scenario": "mulch"},
        {"control_scenario": "uniform_low", "contrast_scenario": "thinning"},
    ]
    omni._contrast_hillslope_limit = None
    omni._contrast_hill_min_slope = None
    omni._contrast_hill_max_slope = None
    omni._contrast_select_burn_severities = None
    omni._contrast_select_topaz_ids = None

    with pytest.raises(ValueError) as excinfo:
        omni._build_contrasts()

    assert "limited to 200" in str(excinfo.value)


def test_user_defined_contrast_ids_stable_on_rebuild(tmp_path, omni_module, monkeypatch):
    hillslope_rows = [
        {"TopazID": "10", "geometry": Rect(0.0, 0.0, 10.0, 10.0)},
    ]
    user_rows = [
        {"name": "Alpha", "geometry": Rect(0.0, 0.0, 10.0, 10.0)},
    ]
    user_geojson_path = _stub_user_defined_geodata(
        monkeypatch,
        omni_module,
        tmp_path,
        hillslope_rows=hillslope_rows,
        user_rows=user_rows,
    )

    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    omni.locked = _noop_lock
    omni.logger = logging.getLogger("tests.omni.user_defined_ids")
    omni._contrast_selection_mode = "user_defined_areas"
    omni._contrast_geojson_path = str(user_geojson_path)
    omni._contrast_geojson_name_key = "name"
    omni._contrast_pairs = [
        {"control_scenario": "uniform_low", "contrast_scenario": "mulch"}
    ]
    omni._contrast_object_param = "Runoff_mm"
    omni._contrast_cumulative_obj_param_threshold_fraction = 0.8
    omni._contrast_hillslope_limit = None
    omni._contrast_hill_min_slope = None
    omni._contrast_hill_max_slope = None
    omni._contrast_select_burn_severities = None
    omni._contrast_select_topaz_ids = None
    omni._control_scenario = None
    omni._contrast_scenario = None

    omni._build_contrasts()
    first_names = list(omni.contrast_names or [])
    assert first_names == ["uniform_low,1__to__mulch"]

    omni._contrast_pairs = [
        {"control_scenario": "uniform_low", "contrast_scenario": "mulch"},
        {"control_scenario": "uniform_low", "contrast_scenario": "thinning"},
    ]
    omni._build_contrasts()

    assert omni.contrast_names[0] == first_names[0]
    assert omni.contrast_names[1] == "uniform_low,2__to__thinning"


def test_user_defined_hillslope_group_ids_stable_on_rebuild(tmp_path, omni_module, monkeypatch):
    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    omni.locked = _noop_lock
    omni.logger = logging.getLogger("tests.omni.hillslope_groups_ids")
    omni._contrast_selection_mode = "user_defined_hillslope_groups"
    omni._contrast_hillslope_groups = "11 12\n13"
    omni._contrast_pairs = [
        {"control_scenario": "uniform_low", "contrast_scenario": "mulch"}
    ]
    omni._contrast_hillslope_limit = None
    omni._contrast_hill_min_slope = None
    omni._contrast_hill_max_slope = None
    omni._contrast_select_burn_severities = None
    omni._contrast_select_topaz_ids = None

    class DummyTranslator:
        top2wepp = {11: 1, 12: 2, 13: 3}

    class DummyWatershed:
        def translator_factory(self):
            return DummyTranslator()

    monkeypatch.setattr(
        omni_module.Omni,
        "base_scenario",
        property(lambda self: omni_module.OmniScenario.Undisturbed),
        raising=False,
    )
    monkeypatch.setattr(omni_module.Watershed, "getInstance", lambda wd: DummyWatershed())

    omni._build_contrasts()

    first_names = list(omni.contrast_names or [])
    assert first_names == ["uniform_low,1__to__mulch", "uniform_low,2__to__mulch"]

    omni._contrast_pairs = [
        {"control_scenario": "uniform_low", "contrast_scenario": "mulch"},
        {"control_scenario": "uniform_low", "contrast_scenario": "thinning"},
    ]
    omni._build_contrasts()

    assert omni.contrast_names[0] == first_names[0]
    assert omni.contrast_names[1] == first_names[1]
    assert omni.contrast_names[2] == "uniform_low,3__to__thinning"
    assert omni.contrast_names[3] == "uniform_low,4__to__thinning"


def test_user_defined_hillslope_groups_contrast_limit_enforced(tmp_path, omni_module):
    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    omni.locked = _noop_lock
    omni.logger = logging.getLogger("tests.omni.hillslope_group_limit")
    omni._contrast_selection_mode = "user_defined_hillslope_groups"
    omni._contrast_hillslope_groups = "\n".join(["11"] * 101)
    omni._contrast_pairs = [
        {"control_scenario": "uniform_low", "contrast_scenario": "mulch"},
        {"control_scenario": "uniform_low", "contrast_scenario": "thinning"},
    ]
    omni._contrast_hillslope_limit = None
    omni._contrast_hill_min_slope = None
    omni._contrast_hill_max_slope = None
    omni._contrast_select_burn_severities = None
    omni._contrast_select_topaz_ids = None

    with pytest.raises(ValueError) as excinfo:
        omni._build_contrasts()

    assert "limited to 200" in str(excinfo.value)


def test_build_contrasts_report_normalizes_control_scenario(tmp_path, monkeypatch, omni_module):
    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    omni.logger = logging.getLogger("tests.omni.build_contrasts")
    omni._contrast_object_param = "Runoff_mm"
    omni._contrast_cumulative_obj_param_threshold_fraction = 1.0
    omni._contrast_hillslope_limit = None
    omni._contrast_hill_min_slope = None
    omni._contrast_hill_max_slope = None
    omni._contrast_select_burn_severities = None
    omni._contrast_select_topaz_ids = None
    omni._contrast_scenario = None
    omni._control_scenario = None
    omni._contrast_names = []
    omni._contrasts = None
    omni._contrast_dependency_tree = {}
    omni.locked = _noop_lock

    class DummyTranslator:
        top2wepp = {10: 20}

    class DummyWatershed:
        def translator_factory(self):
            return DummyTranslator()

    monkeypatch.setattr(
        omni_module.Omni,
        "base_scenario",
        property(lambda self: omni_module.OmniScenario.Undisturbed),
        raising=False
    )
    monkeypatch.setattr(omni_module.Watershed, "getInstance", lambda wd: DummyWatershed())
    monkeypatch.setattr(
        omni_module.Omni,
        "get_objective_parameter_from_gpkg",
        lambda self, objective_parameter, scenario=None: (
            [omni_module.ObjectiveParameter("10", "20", 5.0)],
            5.0,
        ),
    )

    omni._build_contrasts()

    report_path = tmp_path / "_pups" / "omni" / "contrasts" / "build_report.ndjson"
    assert report_path.exists()

    payload = json.loads(report_path.read_text().splitlines()[0])
    assert payload["control_scenario"] == str(omni_module.OmniScenario.Undisturbed)
    assert payload["contrast_id"] == 1


def test_build_contrasts_applies_advanced_filters(tmp_path, monkeypatch, omni_module):
    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    omni.logger = logging.getLogger("tests.omni.contrast_filters")
    omni._contrast_object_param = "Runoff_mm"
    omni._contrast_cumulative_obj_param_threshold_fraction = 1.0
    omni._contrast_hillslope_limit = 1
    omni._contrast_hill_min_slope = 30.0
    omni._contrast_hill_max_slope = None
    omni._contrast_select_burn_severities = [2, 3]
    omni._contrast_select_topaz_ids = [102, 103]
    omni._contrast_selection_mode = "cumulative"
    omni._contrast_scenario = None
    omni._control_scenario = "uniform_high"
    omni._contrast_names = []
    omni._contrasts = None
    omni._contrast_dependency_tree = {}
    omni.locked = _noop_lock

    class DummyTranslator:
        top2wepp = {101: 201, 102: 202, 103: 203}

    class DummyWatershed:
        def translator_factory(self):
            return DummyTranslator()

        def hillslope_slope(self, topaz_id):
            return {"101": 0.2, "102": 0.4, "103": 0.6}[str(topaz_id)]

    class DummyLanduse:
        def identify_burn_class(self, topaz_id):
            return {"101": "Low", "102": "Moderate", "103": "High"}[str(topaz_id)]

    monkeypatch.setattr(
        omni_module.Omni,
        "base_scenario",
        property(lambda self: omni_module.OmniScenario.Undisturbed),
        raising=False,
    )
    monkeypatch.setattr(omni_module.Watershed, "getInstance", lambda wd: DummyWatershed())
    import wepppy.nodb.core as nodb_core
    monkeypatch.setattr(nodb_core.Landuse, "getInstance", lambda wd: DummyLanduse())
    monkeypatch.setattr(
        omni_module.Omni,
        "get_objective_parameter_from_gpkg",
        lambda self, objective_parameter, scenario=None: (
            [
                omni_module.ObjectiveParameter("101", "201", 10.0),
                omni_module.ObjectiveParameter("102", "202", 9.0),
                omni_module.ObjectiveParameter("103", "203", 8.0),
            ],
            27.0,
        ),
    )

    omni._build_contrasts()

    assert omni._contrast_names == ["uniform_high,102__to__undisturbed"]


def test_build_contrasts_ignores_filters_when_not_cumulative(tmp_path, monkeypatch, omni_module):
    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    omni.logger = logging.getLogger("tests.omni.contrast_filters")
    omni._contrast_object_param = "Runoff_mm"
    omni._contrast_cumulative_obj_param_threshold_fraction = 1.0
    omni._contrast_hillslope_limit = None
    omni._contrast_hill_min_slope = 0.3
    omni._contrast_hill_max_slope = 0.5
    omni._contrast_select_burn_severities = [3]
    omni._contrast_select_topaz_ids = [101]
    omni._contrast_selection_mode = "objective"
    omni._contrast_scenario = None
    omni._control_scenario = "uniform_high"
    omni._contrast_names = []
    omni._contrasts = None
    omni._contrast_dependency_tree = {}
    omni.locked = _noop_lock

    class DummyTranslator:
        top2wepp = {101: 201, 102: 202}

    class DummyWatershed:
        def translator_factory(self):
            return DummyTranslator()

    monkeypatch.setattr(
        omni_module.Omni,
        "base_scenario",
        property(lambda self: omni_module.OmniScenario.Undisturbed),
        raising=False,
    )
    monkeypatch.setattr(omni_module.Watershed, "getInstance", lambda wd: DummyWatershed())
    monkeypatch.setattr(
        omni_module.Omni,
        "get_objective_parameter_from_gpkg",
        lambda self, objective_parameter, scenario=None: (
            [
                omni_module.ObjectiveParameter("101", "201", 6.0),
                omni_module.ObjectiveParameter("102", "202", 4.0),
            ],
            10.0,
        ),
    )

    omni._build_contrasts()

    assert omni._contrast_names == [
        "uniform_high,101__to__undisturbed",
        "uniform_high,102__to__undisturbed",
    ]


def test_build_contrasts_raises_value_error_when_no_soil_data(tmp_path, monkeypatch, omni_module):
    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    omni.logger = logging.getLogger("tests.omni.no_soil_data")
    omni._contrast_object_param = "Runoff_mm"
    omni._contrast_cumulative_obj_param_threshold_fraction = 1.0
    omni._contrast_hillslope_limit = None
    omni._contrast_hill_min_slope = None
    omni._contrast_hill_max_slope = None
    omni._contrast_select_burn_severities = None
    omni._contrast_select_topaz_ids = None
    omni._contrast_selection_mode = "cumulative"
    omni._control_scenario = "uniform_high"
    omni._contrast_scenario = None
    omni._contrast_names = []
    omni._contrasts = None
    omni._contrast_dependency_tree = {}
    omni.locked = _noop_lock

    class DummyTranslator:
        top2wepp = {101: 201}

    class DummyWatershed:
        def translator_factory(self):
            return DummyTranslator()

    monkeypatch.setattr(
        omni_module.Omni,
        "base_scenario",
        property(lambda self: omni_module.OmniScenario.Undisturbed),
        raising=False,
    )
    monkeypatch.setattr(omni_module.Watershed, "getInstance", lambda wd: DummyWatershed())
    monkeypatch.setattr(
        omni_module.Omni,
        "get_objective_parameter_from_gpkg",
        lambda self, objective_parameter, scenario=None: ([], 0.0),
    )

    with pytest.raises(ValueError, match="No soil erosion data found!"):
        omni._build_contrasts()


def test_build_contrasts_clamps_hillslope_limit(tmp_path, monkeypatch, omni_module, caplog):
    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    omni.logger = logging.getLogger("tests.omni.contrast_cap")
    omni.locked = _noop_lock
    omni._contrast_object_param = "Runoff_mm"
    omni._contrast_cumulative_obj_param_threshold_fraction = 1.0
    omni._contrast_hillslope_limit = 150
    omni._contrast_hill_min_slope = None
    omni._contrast_hill_max_slope = None
    omni._contrast_select_burn_severities = None
    omni._contrast_select_topaz_ids = None
    omni._contrast_selection_mode = "cumulative"
    omni._contrast_scenario = None
    omni._control_scenario = None
    omni._contrast_names = []
    omni._contrasts = None
    omni._contrast_dependency_tree = {}

    class DummyTranslator:
        top2wepp = {i: i for i in range(1, 121)}

    class DummyWatershed:
        def translator_factory(self):
            return DummyTranslator()

    monkeypatch.setattr(
        omni_module.Omni,
        "base_scenario",
        property(lambda self: omni_module.OmniScenario.Undisturbed),
        raising=False,
    )
    monkeypatch.setattr(omni_module.Watershed, "getInstance", lambda wd: DummyWatershed())

    obj_params = [
        omni_module.ObjectiveParameter(str(i), str(i), 1.0) for i in range(1, 121)
    ]
    monkeypatch.setattr(
        omni_module.Omni,
        "get_objective_parameter_from_gpkg",
        lambda self, objective_parameter, scenario=None: (obj_params, 120.0),
    )

    with caplog.at_level(logging.WARNING, logger=omni.logger.name):
        omni._build_contrasts()

    assert len(omni._contrast_names) == 100
    assert "capped at 100" in caplog.text


def test_build_contrasts_caps_when_no_limit(tmp_path, monkeypatch, omni_module, caplog):
    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    omni.logger = logging.getLogger("tests.omni.contrast_cap_default")
    omni.locked = _noop_lock
    omni._contrast_object_param = "Runoff_mm"
    omni._contrast_cumulative_obj_param_threshold_fraction = 1.0
    omni._contrast_hillslope_limit = None
    omni._contrast_hill_min_slope = None
    omni._contrast_hill_max_slope = None
    omni._contrast_select_burn_severities = None
    omni._contrast_select_topaz_ids = None
    omni._contrast_selection_mode = "cumulative"
    omni._contrast_scenario = None
    omni._control_scenario = None
    omni._contrast_names = []
    omni._contrasts = None
    omni._contrast_dependency_tree = {}

    class DummyTranslator:
        top2wepp = {i: i for i in range(1, 151)}

    class DummyWatershed:
        def translator_factory(self):
            return DummyTranslator()

    monkeypatch.setattr(
        omni_module.Omni,
        "base_scenario",
        property(lambda self: omni_module.OmniScenario.Undisturbed),
        raising=False,
    )
    monkeypatch.setattr(omni_module.Watershed, "getInstance", lambda wd: DummyWatershed())

    obj_params = [
        omni_module.ObjectiveParameter(str(i), str(i), 1.0) for i in range(1, 151)
    ]
    monkeypatch.setattr(
        omni_module.Omni,
        "get_objective_parameter_from_gpkg",
        lambda self, objective_parameter, scenario=None: (obj_params, 150.0),
    )

    with caplog.at_level(logging.WARNING, logger=omni.logger.name):
        omni._build_contrasts()

    assert len(omni._contrast_names) == 100
    assert "Contrast selection reached cap of 100 hillslopes" in caplog.text


def test_build_contrasts_stream_order_delegates_to_contrast_build_service(tmp_path, monkeypatch, omni_module):
    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    captured: dict[str, object] = {}

    def _fake_build(instance):
        captured["instance"] = instance

    monkeypatch.setattr(
        omni_module._OMNI_CONTRAST_BUILD_SERVICE,
        "build_contrasts_stream_order",
        _fake_build,
    )

    omni._build_contrasts_stream_order()

    assert captured["instance"] is omni


def test_build_contrasts_user_defined_areas_delegates_to_contrast_build_service(
    tmp_path,
    monkeypatch,
    omni_module,
):
    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    captured: dict[str, object] = {}

    def _fake_build(instance):
        captured["instance"] = instance

    monkeypatch.setattr(
        omni_module._OMNI_CONTRAST_BUILD_SERVICE,
        "build_contrasts_user_defined_areas",
        _fake_build,
    )

    omni._build_contrasts_user_defined_areas()

    assert captured["instance"] is omni


def test_build_contrasts_dry_run_report_cumulative_statuses(tmp_path, monkeypatch, omni_module):
    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    omni.logger = logging.getLogger("tests.omni.dry_run_cumulative")
    omni.locked = _noop_lock
    monkeypatch.setattr(omni, "_contrast_landuse_skip_reason", lambda *args, **kwargs: None)

    monkeypatch.setattr(
        omni_module.Omni,
        "base_scenario",
        property(lambda self: omni_module.OmniScenario.Undisturbed),
        raising=False,
    )

    def fake_build_contrasts(*args, **kwargs):
        omni._contrast_selection_mode = "cumulative"
        omni._contrast_names = [
            "None,10__to__undisturbed",
            "None,20__to__undisturbed",
        ]
        sidecar1 = Path(omni._contrast_sidecar_path(1))
        sidecar1.parent.mkdir(parents=True, exist_ok=True)
        sidecar1.write_text("10\t/tmp/H10\n", encoding="ascii")
        sidecar2 = Path(omni._contrast_sidecar_path(2))
        sidecar2.write_text("20\t/tmp/H20\n", encoding="ascii")

        snapshot = {"timestamps:run_wepp_watershed": 123}
        (tmp_path / "redisprep.dump").write_text(json.dumps(snapshot), encoding="ascii")

        readme_path = Path(omni._contrast_run_readme_path(1))
        readme_path.parent.mkdir(parents=True, exist_ok=True)
        readme_path.write_text("ok", encoding="ascii")

        omni._contrast_dependency_tree = {
            "None,10__to__undisturbed": {
                "dependencies": {},
                "sidecar_sha1": omni_module._hash_file_sha1(str(sidecar1)),
                "control_redisprep": snapshot,
                "contrast_redisprep": snapshot,
                "last_run": 1.0,
            }
        }

    monkeypatch.setattr(omni, "build_contrasts", fake_build_contrasts)

    report = omni.build_contrasts_dry_run_report(
        control_scenario_def={"type": "uniform_low"},
        contrast_scenario_def={"type": "mulch"},
        contrast_pairs=[{"control_scenario": "uniform_low", "contrast_scenario": "mulch"}],
    )

    assert report["selection_mode"] == "cumulative"
    assert report["items"][0]["run_status"] == "up_to_date"
    assert report["items"][1]["run_status"] == "needs_run"
    assert report["items"][0]["topaz_id"] == "10"
    assert report["items"][1]["topaz_id"] == "20"


def test_build_contrasts_dry_run_report_user_defined(tmp_path, monkeypatch, omni_module):
    omni = omni_module.Omni.__new__(omni_module.Omni)
    omni.wd = str(tmp_path)
    omni.logger = logging.getLogger("tests.omni.dry_run_user_defined")
    omni.locked = _noop_lock
    monkeypatch.setattr(omni, "_contrast_landuse_skip_reason", lambda *args, **kwargs: None)

    monkeypatch.setattr(
        omni_module.Omni,
        "base_scenario",
        property(lambda self: omni_module.OmniScenario.Undisturbed),
        raising=False,
    )

    def fake_build_contrasts(*args, **kwargs):
        omni._contrast_selection_mode = "user_defined_areas"
        omni._control_scenario = None
        omni._contrast_scenario = None
        omni._contrast_names = [
            None,
            "None,2__to__undisturbed",
        ]
        omni._contrast_labels = {1: "A1", 2: "A2"}

        report_path = Path(omni._contrast_build_report_path())
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_lines = [
            {
                "contrast_id": 1,
                "control_scenario": "undisturbed",
                "contrast_scenario": "undisturbed",
                "selection_mode": "user_defined_areas",
                "area_label": "A1",
                "n_hillslopes": 0,
                "topaz_ids": [],
                "status": "skipped",
            },
            {
                "contrast_id": 2,
                "control_scenario": "undisturbed",
                "contrast_scenario": "undisturbed",
                "selection_mode": "user_defined_areas",
                "area_label": "A2",
                "n_hillslopes": 2,
                "topaz_ids": ["10", "11"],
            },
        ]
        report_path.write_text(
            "\n".join(json.dumps(line) for line in report_lines) + "\n",
            encoding="ascii",
        )

        sidecar2 = Path(omni._contrast_sidecar_path(2))
        sidecar2.parent.mkdir(parents=True, exist_ok=True)
        sidecar2.write_text("10\t/tmp/H10\n", encoding="ascii")

        snapshot = {"timestamps:run_wepp_watershed": 456}
        (tmp_path / "redisprep.dump").write_text(json.dumps(snapshot), encoding="ascii")

        readme_path = Path(omni._contrast_run_readme_path(2))
        readme_path.parent.mkdir(parents=True, exist_ok=True)
        readme_path.write_text("ok", encoding="ascii")

        omni._contrast_dependency_tree = {
            "None,2__to__undisturbed": {
                "dependencies": {},
                "sidecar_sha1": omni_module._hash_file_sha1(str(sidecar2)),
                "control_redisprep": snapshot,
                "contrast_redisprep": snapshot,
                "last_run": 1.0,
            }
        }

    monkeypatch.setattr(omni, "build_contrasts", fake_build_contrasts)

    report = omni.build_contrasts_dry_run_report(
        control_scenario_def={"type": "uniform_low"},
        contrast_scenario_def={"type": "mulch"},
    )

    assert report["selection_mode"] == "user_defined_areas"
    assert report["items"][0]["run_status"] == "skipped"
    assert report["items"][0]["skip_status"]["reason"] == "no_hillslopes"
    assert report["items"][1]["run_status"] == "up_to_date"
    assert report["items"][1]["skip_status"]["skipped"] is False
