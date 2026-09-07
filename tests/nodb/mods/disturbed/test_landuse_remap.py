from __future__ import annotations

import json
from contextlib import contextmanager
from types import SimpleNamespace

import pytest

import wepppy.nodb.mods.disturbed.disturbed as disturbed_module
from wepppy.nodb.mods.disturbed.disturbed import Disturbed
from wepppy.nodb.core.landuse import Landuse, LanduseCustomMappingError, _write_mofe_management_file_task
from wepppy.wepp.management import get_management_summary, load_map
from wepppy.wepp.management.managements import Management

pytestmark = [pytest.mark.unit, pytest.mark.nodb]


class _NoopLogger:
    def info(self, *_args: object, **_kwargs: object) -> None:
        return

    def debug(self, *_args: object, **_kwargs: object) -> None:
        return

    def warning(self, *_args: object, **_kwargs: object) -> None:
        return


class _RecordingLogger(_NoopLogger):
    def __init__(self) -> None:
        self.info_messages: list[str] = []
        self.debug_messages: list[str] = []

    @staticmethod
    def _format(message: str, *args: object) -> str:
        if args:
            return message % args
        return str(message)

    def info(self, message: str, *args: object, **_kwargs: object) -> None:
        self.info_messages.append(self._format(message, *args))

    def debug(self, message: str, *args: object, **_kwargs: object) -> None:
        self.debug_messages.append(self._format(message, *args))


class _ManagementSummary:
    def __init__(self, disturbed_class: str) -> None:
        self.disturbed_class = disturbed_class


class _FakeLanduse:
    _instance: "_FakeLanduse | None" = None

    def __init__(self, domlc_d, managements, domlc_mofe_d=None, logger=None) -> None:
        self.domlc_d = domlc_d
        self.managements = managements
        self.domlc_mofe_d = domlc_mofe_d or {}
        self.logger = logger or _NoopLogger()
        self.build_managements_calls = 0

    @classmethod
    def getInstance(cls, _wd: str):
        assert cls._instance is not None
        return cls._instance

    @contextmanager
    def locked(self):
        yield

    def get_mapping_dict(self):
        return load_map('disturbed')

    def build_managements(self) -> None:
        self.build_managements_calls += 1


def test_remap_landuse_applies_burn_classes_and_respects_flags(
    disturbed_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    disturbed, _ = disturbed_factory("remap-landuse")
    disturbed._burn_shrubs = True
    disturbed._burn_grass = False

    landuse = _FakeLanduse(
        domlc_d={"101": "forest-dom", "102": "shrub-dom", "103": "grass-dom", "104": "channel-dom"},
        managements={
            "forest-dom": _ManagementSummary("forest"),
            "shrub-dom": _ManagementSummary("shrub"),
            "grass-dom": _ManagementSummary("tall grass"),
            "channel-dom": _ManagementSummary("forest"),
        },
    )
    _FakeLanduse._instance = landuse

    monkeypatch.setattr(Disturbed, "landuse_instance", property(lambda self: landuse))
    monkeypatch.setattr(
        Disturbed,
        "get_disturbed_key_lookup",
        lambda self: {
            "forest_low_sev_fire": "forest-low",
            "forest_moderate_sev_fire": "forest-mod",
            "forest_high_sev_fire": "forest-high",
            "shrub_low_sev_fire": "shrub-low",
            "shrub_moderate_sev_fire": "shrub-mod",
            "shrub_high_sev_fire": "shrub-high",
            "grass_low_sev_fire": "grass-low",
            "grass_moderate_sev_fire": "grass-mod",
            "grass_high_sev_fire": "grass-high",
        },
    )
    monkeypatch.setattr(
        disturbed_module,
        "count_intersecting_raster_key_pairs",
        lambda **_kwargs: {
            "101": {"1": 10},
            "102": {"2": 10},
            "103": {"3": 10},
            "104": {"1": 10},
        },
    )
    monkeypatch.setattr(
        disturbed_module,
        "Watershed",
        SimpleNamespace(getInstance=lambda _wd: SimpleNamespace(subwta="subwta.tif")),
    )
    monkeypatch.setattr(Disturbed, "_calc_sbs_coverage", lambda self, _sbs: None)
    monkeypatch.setattr(
        Disturbed,
        "get_sbs",
        lambda self: SimpleNamespace(class_pixel_map={"1": "131", "2": "132", "3": "133"}),
    )

    disturbed.remap_landuse()

    assert landuse.domlc_d["101"] == "forest-low"
    assert landuse.domlc_d["102"] == "shrub-mod"
    assert landuse.domlc_d["103"] == "grass-dom"
    assert landuse.domlc_d["104"] == "channel-dom"
    assert landuse.build_managements_calls == 1


def test_remap_landuse_defers_rebuild_when_requested_and_compacts_info_logging(
    disturbed_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    disturbed, _ = disturbed_factory("remap-landuse-deferred")
    disturbed._burn_shrubs = True
    disturbed._burn_grass = False
    logger = _RecordingLogger()

    landuse = _FakeLanduse(
        domlc_d={"101": "forest-dom", "102": "shrub-dom", "103": "grass-dom"},
        managements={
            "forest-dom": _ManagementSummary("forest"),
            "shrub-dom": _ManagementSummary("shrub"),
            "grass-dom": _ManagementSummary("tall grass"),
        },
        logger=logger,
    )
    _FakeLanduse._instance = landuse

    monkeypatch.setattr(Disturbed, "landuse_instance", property(lambda self: landuse))
    monkeypatch.setattr(
        Disturbed,
        "get_disturbed_key_lookup",
        lambda self: {
            "forest_low_sev_fire": "forest-low",
            "forest_moderate_sev_fire": "forest-mod",
            "forest_high_sev_fire": "forest-high",
            "shrub_low_sev_fire": "shrub-low",
            "shrub_moderate_sev_fire": "shrub-mod",
            "shrub_high_sev_fire": "shrub-high",
            "grass_low_sev_fire": "grass-low",
            "grass_moderate_sev_fire": "grass-mod",
            "grass_high_sev_fire": "grass-high",
        },
    )
    monkeypatch.setattr(
        disturbed_module,
        "count_intersecting_raster_key_pairs",
        lambda **_kwargs: {
            "101": {"1": 12},
            "102": {"2": 9},
            "103": {"3": 7},
        },
    )
    monkeypatch.setattr(
        disturbed_module,
        "Watershed",
        SimpleNamespace(getInstance=lambda _wd: SimpleNamespace(subwta="subwta.tif")),
    )
    monkeypatch.setattr(Disturbed, "_calc_sbs_coverage", lambda self, _sbs: None)
    monkeypatch.setattr(
        Disturbed,
        "get_sbs",
        lambda self: SimpleNamespace(class_pixel_map={"1": "131", "2": "132", "3": "133"}),
    )

    disturbed.remap_landuse(rebuild_managements=False)

    assert landuse.build_managements_calls == 0
    assert any("Disturbed remap summary:" in message for message in logger.info_messages)
    assert not any("topaz_id=" in message for message in logger.info_messages)
    assert any("topaz_id=" in message for message in logger.debug_messages)


def test_remap_landuse_treats_nodata_only_hillslopes_as_no_burn(
    disturbed_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    disturbed, _ = disturbed_factory("remap-landuse-nodata-fallback")
    disturbed._burn_shrubs = True
    disturbed._burn_grass = False

    landuse = _FakeLanduse(
        domlc_d={"101": "forest-dom", "102": "shrub-dom"},
        managements={
            "forest-dom": _ManagementSummary("forest"),
            "shrub-dom": _ManagementSummary("shrub"),
        },
    )
    _FakeLanduse._instance = landuse

    monkeypatch.setattr(Disturbed, "landuse_instance", property(lambda self: landuse))
    monkeypatch.setattr(
        Disturbed,
        "get_disturbed_key_lookup",
        lambda self: {
            "forest_low_sev_fire": "forest-low",
            "forest_moderate_sev_fire": "forest-mod",
            "forest_high_sev_fire": "forest-high",
            "shrub_low_sev_fire": "shrub-low",
            "shrub_moderate_sev_fire": "shrub-mod",
            "shrub_high_sev_fire": "shrub-high",
            "grass_low_sev_fire": "grass-low",
            "grass_moderate_sev_fire": "grass-mod",
            "grass_high_sev_fire": "grass-high",
        },
    )
    monkeypatch.setattr(
        disturbed_module,
        "count_intersecting_raster_key_pairs",
        lambda **_kwargs: {"101": {"3": 4}},
    )
    monkeypatch.setattr(
        disturbed_module,
        "Watershed",
        SimpleNamespace(getInstance=lambda _wd: SimpleNamespace(subwta="subwta.tif")),
    )
    monkeypatch.setattr(Disturbed, "_calc_sbs_coverage", lambda self, _sbs: None)
    monkeypatch.setattr(
        Disturbed,
        "get_sbs",
        lambda self: SimpleNamespace(class_pixel_map={"3": "132"}),
    )

    disturbed.remap_landuse()

    assert landuse.domlc_d["101"] == "forest-mod"
    # Key 102 has no valid SBS cells; it must remain unburned instead of inheriting global mode.
    assert landuse.domlc_d["102"] == "shrub-dom"
    assert disturbed.meta["102"]["burn_class"] == "130"


def test_color_maps_do_not_depend_on_builtin_map_symbol(
    disturbed_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    disturbed, _ = disturbed_factory("color-map-builtin-shadow")
    disturbed._ct = object()
    disturbed._color_map = {"1_2_3": "low", "10_11_12": "high"}
    disturbed._color_coverage_pcts = {"1_2_3": "25.0", "10_11_12": "75.0"}

    # Simulate namespace collision (e.g., imported `map` module shadowing builtin map()).
    monkeypatch.setattr(disturbed_module, "map", disturbed_module, raising=False)

    assert disturbed.color_to_severity_map == {(1, 2, 3): "low", (10, 11, 12): "high"}
    assert disturbed.color_coverage_pcts == {(1, 2, 3): 25.0, (10, 11, 12): 75.0}


def test_remap_mofe_landuse_maps_burned_classes(
    disturbed_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    disturbed, _ = disturbed_factory("remap-mofe")

    landuse = _FakeLanduse(
        domlc_d={},
        managements={
            "forest-dom": _ManagementSummary("forest"),
            "shrub-dom": _ManagementSummary("shrub"),
            "grass-dom": _ManagementSummary("tall grass"),
        },
        domlc_mofe_d={"101": {"1": "forest-dom", "2": "shrub-dom", "3": "grass-dom"}},
    )
    _FakeLanduse._instance = landuse

    monkeypatch.setattr(Disturbed, "landuse_instance", property(lambda self: landuse))
    monkeypatch.setattr(
        disturbed_module,
        "Watershed",
        SimpleNamespace(
            getInstance=lambda _wd: SimpleNamespace(subwta="subwta.tif", mofe_map="mofe.map")
        ),
    )
    monkeypatch.setattr(Disturbed, "_calc_sbs_coverage", lambda self, _sbs: None)
    monkeypatch.setattr(
        Disturbed,
        "get_sbs",
        lambda self: SimpleNamespace(
            build_lcgrid=lambda _subwta, _mofe_map: {"101": {"1": "131", "2": "132", "3": "133"}}
        ),
    )

    disturbed.remap_mofe_landuse()

    assert landuse.domlc_mofe_d["101"]["1"] == "106"
    assert landuse.domlc_mofe_d["101"]["2"] == "120"
    assert landuse.domlc_mofe_d["101"]["3"] == "129"
    assert landuse.build_managements_calls == 1


def test_remap_mofe_landuse_defers_rebuild_when_requested(
    disturbed_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    disturbed, _ = disturbed_factory("remap-mofe-deferred")
    logger = _RecordingLogger()

    landuse = _FakeLanduse(
        domlc_d={},
        managements={
            "forest-dom": _ManagementSummary("forest"),
            "shrub-dom": _ManagementSummary("shrub"),
            "grass-dom": _ManagementSummary("tall grass"),
        },
        domlc_mofe_d={"101": {"1": "forest-dom", "2": "shrub-dom", "3": "grass-dom"}},
        logger=logger,
    )
    _FakeLanduse._instance = landuse

    monkeypatch.setattr(Disturbed, "landuse_instance", property(lambda self: landuse))
    monkeypatch.setattr(
        disturbed_module,
        "Watershed",
        SimpleNamespace(
            getInstance=lambda _wd: SimpleNamespace(subwta="subwta.tif", mofe_map="mofe.map")
        ),
    )
    monkeypatch.setattr(Disturbed, "_calc_sbs_coverage", lambda self, _sbs: None)
    monkeypatch.setattr(
        Disturbed,
        "get_sbs",
        lambda self: SimpleNamespace(
            build_lcgrid=lambda _subwta, _mofe_map: {"101": {"1": "131", "2": "132", "3": "133"}}
        ),
    )

    disturbed.remap_mofe_landuse(rebuild_managements=False)

    assert landuse.build_managements_calls == 0
    assert any("Disturbed MOFE remap summary:" in message for message in logger.info_messages)
    assert any("mofe topaz_id=" in message for message in logger.debug_messages)


def test_remap_landuse_returns_early_without_sbs(
    disturbed_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    disturbed, _ = disturbed_factory("remap-no-sbs")

    landuse = _FakeLanduse(
        domlc_d={"101": "forest-dom"},
        managements={"forest-dom": _ManagementSummary("forest")},
    )
    _FakeLanduse._instance = landuse

    monkeypatch.setattr(Disturbed, "landuse_instance", property(lambda self: landuse))
    monkeypatch.setattr(Disturbed, "get_disturbed_key_lookup", lambda self: {})
    monkeypatch.setattr(Disturbed, "get_sbs", lambda self: None)
    monkeypatch.setattr(
        disturbed_module,
        "Watershed",
        SimpleNamespace(getInstance=lambda _wd: SimpleNamespace(subwta="subwta.tif")),
    )

    disturbed.remap_landuse()

    assert landuse.domlc_d["101"] == "forest-dom"
    assert landuse.build_managements_calls == 0


@pytest.fixture
def mofe_mapping_case(disturbed_factory, monkeypatch):
    """Use actual effective-map loading; isolate only raster analysis and locks."""
    def make(mapping="c3s-disturbed", custom_state=None):
        disturbed, run_dir = disturbed_factory("mofe-mapping")
        source = Landuse.__new__(Landuse)
        source.wd = str(run_dir)
        source._mapping = mapping
        source._custom_mapping_relpath = None
        if custom_state is not None:
            source._custom_mapping_relpath = "landuse/custom.json"
            custom_path = run_dir / source._custom_mapping_relpath
            custom_path.parent.mkdir(exist_ok=True)
            data = load_map("c3s-disturbed")
            if custom_state == "complete":
                data = {f"custom-{key}": dict(value, Key=f"custom-{key}")
                        for key, value in data.items()}
            elif custom_state == "incomplete":
                del data["406"]
            if custom_state == "malformed":
                custom_path.write_text("{broken")
            elif custom_state != "missing":
                custom_path.write_text(json.dumps(data))
        landuse = _FakeLanduse({}, {}, {})
        landuse.get_mapping_dict = source.get_mapping_dict
        _FakeLanduse._instance = landuse
        monkeypatch.setattr(Disturbed, "landuse_instance", property(lambda self: landuse))
        monkeypatch.setattr(
            disturbed_module, "Watershed",
            SimpleNamespace(getInstance=lambda _wd:
                            SimpleNamespace(subwta="subwta.tif", mofe_map="mofe.map")),
        )
        monkeypatch.setattr(Disturbed, "_calc_sbs_coverage", lambda self, sbs: None)
        severity = {}
        monkeypatch.setattr(
            Disturbed, "get_sbs",
            lambda self: SimpleNamespace(build_lcgrid=lambda *_args: severity),
        )
        return disturbed, landuse, source, severity, run_dir
    return make


@pytest.mark.parametrize("mapping,custom_state", [
    ("disturbed", None), ("c3s-disturbed", None), ("c3s-disturbed", "complete"),
])
@pytest.mark.parametrize("rebuild", [True, False])
def test_mofe_effective_mapping_and_generated_managements(
    mofe_mapping_case, mapping, custom_state, rebuild,
):
    disturbed, landuse, source, severity, run_dir = mofe_mapping_case(mapping, custom_state)
    # Preserve MOFE's current eligibility even with both flags false.
    disturbed._burn_shrubs = False
    disturbed._burn_grass = False
    data = source.get_mapping_dict()
    expected = []
    assignments = {}
    burns = {}
    for vegetation in ("forest", "shrub", "short grass", "tall grass"):
        base = next(key for key, row in data.items() if row["DisturbedClass"] == vegetation)
        landuse.managements[base] = get_management_summary(
            base, source._resolve_effective_mapping_reference(source.mapping))
        for severity_code, severity_name in zip(("131", "132", "133"), ("low", "moderate", "high")):
            segment = str(len(assignments) + 1)
            assignments[segment] = base
            burns[segment] = severity_code
            bucket = "grass" if vegetation.endswith("grass") else vegetation
            expected.append(f"{bucket} {severity_name} sev fire")
    # Non-burned and ineligible segments remain unchanged.
    forest = next(key for key, row in data.items() if row["DisturbedClass"] == "forest")
    ineligible = next(key for key, row in data.items() if row["DisturbedClass"] == "")
    landuse.managements[ineligible] = get_management_summary(
        ineligible, source._resolve_effective_mapping_reference(source.mapping))
    assignments["13"], assignments["14"] = forest, ineligible
    burns["13"], burns["14"] = "130", "133"
    landuse.domlc_mofe_d = {"101": assignments}
    severity["101"] = burns

    disturbed.remap_mofe_landuse(rebuild_managements=rebuild)

    result = landuse.domlc_mofe_d["101"]
    assert [data[result[str(i)]]["DisturbedClass"] for i in range(1, 13)] == expected
    forest_targets = [result[str(i)] for i in (1, 2, 3)]
    prefix = "custom-" if custom_state else ""
    assert forest_targets == [prefix + k for k in (
        ("106", "118", "105") if mapping == "disturbed" else ("406", "418", "405"))]
    assert (result["13"], result["14"]) == (forest, ineligible)
    assert landuse.build_managements_calls == int(rebuild)

    # Resolve actual summaries and run the production MOFE synthesis writer.
    reference = source._resolve_effective_mapping_reference(source.mapping)
    summaries = [get_management_summary(result[str(i)], reference) for i in range(1, 13)]
    plans = [dict(key=m.key, man_fn=m.man_fn, man_dir=m.man_dir,
                  desc=m.desc, color=m.color) for m in summaries]
    output = run_dir / "landuse" / "hill_101.mofe.man"
    output.parent.mkdir(exist_ok=True)
    _write_mofe_management_file_task(("101", str(output), 12, plans))
    generated = Management(Key="hill_101", ManagementFile=output.name,
                           ManagementDir=str(output.parent), Description="MOFE", Color=(0, 0, 0, 255))
    # Exercise the real multi-year expansion used by WEPP preparation.
    run_output = run_dir / "wepp" / "runs" / "p1.man"
    run_output.write_text(str(generated.build_multiple_year_man(2)))
    reread = Management(Key="p1", ManagementFile=run_output.name,
                        ManagementDir=str(run_output.parent), Description="MOFE", Color=(0, 0, 0, 255))
    assert len(reread.inis) == 12
    for actual, summary in zip(reread.inis, summaries):
        expected_ini = summary.get_management().inis[0]
        for attribute in ("cancov", "inrcov", "rilcov"):
            assert getattr(actual.data, attribute) == pytest.approx(
                getattr(expected_ini.data, attribute))
    assert run_output.stat().st_size > 0


@pytest.mark.parametrize("custom_state,error", [
    ("incomplete", AssertionError), ("malformed", LanduseCustomMappingError),
    ("missing", LanduseCustomMappingError),
])
def test_mofe_invalid_mapping_fails_before_assignment_mutation(mofe_mapping_case, custom_state, error):
    disturbed, landuse, _source, severity, _run_dir = mofe_mapping_case(custom_state=custom_state)
    landuse.managements = {"base": _ManagementSummary("forest")}
    landuse.domlc_mofe_d = {"101": {"1": "base"}}
    severity["101"] = {"1": "131"}
    with pytest.raises(error):
        disturbed.remap_mofe_landuse()
    assert landuse.domlc_mofe_d == {"101": {"1": "base"}}
    assert landuse.build_managements_calls == 0


def test_mofe_no_sbs_does_not_load_missing_map(mofe_mapping_case, monkeypatch):
    disturbed, landuse, _source, _severity, _run_dir = mofe_mapping_case(custom_state="missing")
    landuse.domlc_mofe_d = {"101": {"1": "base"}}
    monkeypatch.setattr(Disturbed, "get_sbs", lambda self: None)
    disturbed.remap_mofe_landuse()
    assert landuse.domlc_mofe_d == {"101": {"1": "base"}}
    assert landuse.build_managements_calls == 0


def test_mofe_empty_assignments_remain_empty(mofe_mapping_case):
    disturbed, landuse, _source, _severity, _run_dir = mofe_mapping_case()
    disturbed.remap_mofe_landuse()
    assert landuse.domlc_mofe_d == {}
    assert landuse.build_managements_calls == 1
