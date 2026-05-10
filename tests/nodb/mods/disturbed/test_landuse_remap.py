from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace

import pytest

import wepppy.nodb.mods.disturbed.disturbed as disturbed_module
from wepppy.nodb.mods.disturbed.disturbed import Disturbed

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
