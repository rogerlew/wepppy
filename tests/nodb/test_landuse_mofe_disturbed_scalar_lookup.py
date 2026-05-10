from __future__ import annotations

from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace

import pytest

import wepppy.nodb.core.landuse as landuse_module
from wepppy.nodb.core.landuse import Landuse

pytestmark = pytest.mark.unit


class _LoggerStub:
    def info(self, *_args, **_kwargs) -> None:
        return None

    def debug(self, *_args, **_kwargs) -> None:
        return None

    def warning(self, *_args, **_kwargs) -> None:
        return None

    def error(self, *_args, **_kwargs) -> None:
        return None


class _ManagementStub:
    def __init__(self) -> None:
        self.rdmax_values: list[float] = []
        self.xmxlai_values: list[float] = []
        self.cancov_values: list[float] = []
        self.overrides: dict[str, float] = {}

    def set_rdmax(self, value: float) -> None:
        self.rdmax_values.append(value)

    def set_xmxlai(self, value: float) -> None:
        self.xmxlai_values.append(value)

    def set_cancov(self, value: float) -> None:
        self.cancov_values.append(value)
        self.overrides["ini.data.cancov"] = float(value)

    def __setitem__(self, attr: str, value: str | float | int) -> None:
        self.overrides[attr] = float(value)

    def __str__(self) -> str:
        return "management-stub\n"


class _ManagementSummaryStub:
    def __init__(self, management: _ManagementStub, disturbed_class: str) -> None:
        self._management = management
        self.disturbed_class = disturbed_class

    def get_management(self) -> _ManagementStub:
        return self._management


class _RecordingLogger:
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

    def warning(self, *_args: object, **_kwargs: object) -> None:
        return None

    def error(self, *_args: object, **_kwargs: object) -> None:
        return None


def test_build_multiple_ofe_accepts_extended_rdmax_xmxlai_keys(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir = tmp_path / "run"
    (run_dir / "landuse").mkdir(parents=True, exist_ok=True)

    management = _ManagementStub()
    landuse = Landuse.__new__(Landuse)
    landuse.wd = str(run_dir)
    landuse._mods = []
    landuse.managements = {
        "forest-dom": _ManagementSummaryStub(
            management=management,
            disturbed_class="forest moderate sev fire",
        )
    }
    landuse.locked = lambda: nullcontext()
    landuse.logger = _LoggerStub()

    watershed = SimpleNamespace(
        _subs_summary={"101": {}},
        mofe_nsegments={"101": "1"},
        mofe_buffer=False,
        subwta=str(run_dir / "watershed" / "subwta.tif"),
        mofe_map=str(run_dir / "watershed" / "mofe_map.tif"),
    )
    monkeypatch.setattr(
        Landuse,
        "watershed_instance",
        property(lambda _self: watershed),
    )

    class _LandcoverMapStub:
        def __init__(self, _lc_fn: str) -> None:
            pass

        def build_lcgrid(self, _subwta: str, _mofe_map: str) -> dict[str, dict[str, str]]:
            return {"101": {"1": "forest-dom"}}

    monkeypatch.setattr(landuse_module, "LandcoverMap", _LandcoverMapStub)
    monkeypatch.setattr(landuse_module, "wepppyo3", None)

    class _DisturbedStub:
        burn_shrubs = False
        burn_grass = False
        land_soil_replacements_d = {
            ("sand loam", "forest moderate sev fire"): {
                "plant.data.rdmax": "0.33",
                "plant.data.xmxlai": "5.7",
                "plant.data.decfct": "1.0",
            }
        }

        def get_disturbed_key_lookup(self) -> dict[str, str]:
            return {}

        def get_sbs(self) -> None:
            return None

    disturbed = _DisturbedStub()
    monkeypatch.setattr(
        "wepppy.nodb.mods.disturbed.Disturbed.tryGetInstance",
        lambda _wd: disturbed,
    )

    landuse._build_multiple_ofe()

    assert management.rdmax_values == [0.33]
    assert management.xmxlai_values == [5.7]
    assert management.overrides["plant.data.decfct"] == pytest.approx(1.0)
    assert (run_dir / "landuse" / "hill_101.mofe.man").exists()


def test_build_multiple_ofe_rap_cancov_overrides_lookup_ini_cancov(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir = tmp_path / "run"
    (run_dir / "landuse").mkdir(parents=True, exist_ok=True)

    management = _ManagementStub()
    landuse = Landuse.__new__(Landuse)
    landuse.wd = str(run_dir)
    landuse._mods = ["rap"]
    landuse.managements = {
        "forest-dom": _ManagementSummaryStub(
            management=management,
            disturbed_class="forest moderate sev fire",
        )
    }
    landuse.locked = lambda: nullcontext()
    landuse.logger = _LoggerStub()

    watershed = SimpleNamespace(
        _subs_summary={"101": {}},
        mofe_nsegments={"101": "1"},
        mofe_buffer=False,
        subwta=str(run_dir / "watershed" / "subwta.tif"),
        mofe_map=str(run_dir / "watershed" / "mofe_map.tif"),
    )
    monkeypatch.setattr(
        Landuse,
        "watershed_instance",
        property(lambda _self: watershed),
    )

    class _LandcoverMapStub:
        def __init__(self, _lc_fn: str) -> None:
            pass

        def build_lcgrid(self, _subwta: str, _mofe_map: str) -> dict[str, dict[str, str]]:
            return {"101": {"1": "forest-dom"}}

    monkeypatch.setattr(landuse_module, "LandcoverMap", _LandcoverMapStub)
    monkeypatch.setattr(landuse_module, "wepppyo3", None)

    class _DisturbedStub:
        burn_shrubs = False
        burn_grass = False
        land_soil_replacements_d = {
            ("sand loam", "forest moderate sev fire"): {
                "ini.data.cancov": "0.11",
                "plant.data.rdmax": "0.33",
                "plant.data.xmxlai": "5.7",
            }
        }

        def get_disturbed_key_lookup(self) -> dict[str, str]:
            return {}

        def get_sbs(self) -> None:
            return None

    class _RapStub:
        mofe_data = {
            landuse_module.RAP_Band.TREE: {"101": {"1": 70.0}},
            landuse_module.RAP_Band.SHRUB: {"101": {"1": 20.0}},
            landuse_module.RAP_Band.ANNUAL_FORB_AND_GRASS: {"101": {"1": 5.0}},
            landuse_module.RAP_Band.PERENNIAL_FORB_AND_GRASS: {"101": {"1": 5.0}},
        }

    disturbed = _DisturbedStub()
    monkeypatch.setattr(
        "wepppy.nodb.mods.disturbed.Disturbed.tryGetInstance",
        lambda _wd: disturbed,
    )
    monkeypatch.setattr(
        "wepppy.nodb.mods.rap.RAP.getInstance",
        lambda _wd: _RapStub(),
    )

    landuse._build_multiple_ofe()

    assert management.cancov_values == [pytest.approx(1.0)]
    assert management.overrides["ini.data.cancov"] == pytest.approx(1.0)
    assert management.rdmax_values == [0.33]
    assert management.xmxlai_values == [5.7]


def test_build_multiple_ofe_sbs_remap_reuses_existing_management_summaries(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir = tmp_path / "run"
    (run_dir / "landuse").mkdir(parents=True, exist_ok=True)

    landuse = Landuse.__new__(Landuse)
    landuse.wd = str(run_dir)
    landuse._mods = []
    landuse._mapping = "mock-map"
    landuse.locked = lambda: nullcontext()
    logger = _RecordingLogger()
    landuse.logger = logger

    landuse.managements = {
        "forest-dom": _ManagementSummaryStub(_ManagementStub(), "forest"),
        "forest-low": _ManagementSummaryStub(_ManagementStub(), "forest low sev fire"),
        "forest-mod": _ManagementSummaryStub(_ManagementStub(), "forest moderate sev fire"),
    }

    watershed = SimpleNamespace(
        _subs_summary={"101": {}, "102": {}},
        mofe_nsegments={"101": "1", "102": "1"},
        mofe_buffer=False,
        subwta=str(run_dir / "watershed" / "subwta.tif"),
        mofe_map=str(run_dir / "watershed" / "mofe_map.tif"),
    )
    monkeypatch.setattr(
        Landuse,
        "watershed_instance",
        property(lambda _self: watershed),
    )
    monkeypatch.setattr(landuse_module, "wepppyo3", None)

    class _LandcoverMapStub:
        def __init__(self, _lc_fn: str) -> None:
            pass

        def build_lcgrid(self, _subwta: str, _mofe_map: str) -> dict[str, dict[str, str]]:
            return {"101": {"1": "forest-dom"}, "102": {"1": "forest-dom"}}

    monkeypatch.setattr(landuse_module, "LandcoverMap", _LandcoverMapStub)
    monkeypatch.setattr(
        landuse_module,
        "_wait_for_gdal_openable_raster",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(landuse_module.os, "cpu_count", lambda: 1)

    class _SbsStub:
        class_pixel_map = {"11": "131", "12": "132"}

        @staticmethod
        def build_lcgrid(_subwta: str, _mofe_map: str) -> dict[str, dict[str, str]]:
            return {"101": {"1": "11"}, "102": {"1": "12"}}

    class _DisturbedStub:
        burn_shrubs = False
        burn_grass = False
        land_soil_replacements_d = None
        disturbed_cropped = str(run_dir / "disturbed" / "disturbed_cropped.tif")

        def get_disturbed_key_lookup(self) -> dict[str, str]:
            return {
                "forest_low_sev_fire": "forest-low",
                "forest_moderate_sev_fire": "forest-mod",
                "forest_high_sev_fire": "forest-high",
                "shrub_low_sev_fire": "shrub-low",
                "shrub_moderate_sev_fire": "shrub-mod",
                "shrub_high_sev_fire": "shrub-high",
                "grass_low_sev_fire": "grass-low",
                "grass_moderate_sev_fire": "grass-mod",
                "grass_high_sev_fire": "grass-high",
            }

        def get_sbs(self) -> _SbsStub:
            return _SbsStub()

    monkeypatch.setattr(
        "wepppy.nodb.mods.disturbed.Disturbed.tryGetInstance",
        lambda _wd: _DisturbedStub(),
    )

    summary_lookup_calls: list[str] = []
    monkeypatch.setattr(
        landuse_module,
        "get_management_summary",
        lambda dom, _map=None: summary_lookup_calls.append(str(dom)),
    )

    landuse._build_multiple_ofe()

    assert summary_lookup_calls == []
    assert landuse.domlc_mofe_d == {
        "101": {"1": "forest-low"},
        "102": {"1": "forest-mod"},
    }
    assert any(
        message.startswith("Prepared multi-OFE landuse assignments")
        for message in logger.info_messages
    )
    assert all("domlc_d =" not in message for message in logger.info_messages)
    assert any("domlc_d =" in message for message in logger.debug_messages)

@pytest.mark.unit
def test_build_multiple_ofe_sbs_nodata_segment_stays_unburned(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir = tmp_path / "run"
    (run_dir / "landuse").mkdir(parents=True, exist_ok=True)

    landuse = Landuse.__new__(Landuse)
    landuse.wd = str(run_dir)
    landuse._mods = []
    landuse._mapping = "mock-map"
    landuse.locked = lambda: nullcontext()
    landuse.logger = _LoggerStub()

    landuse.managements = {
        "forest-dom": _ManagementSummaryStub(_ManagementStub(), "forest"),
        "forest-low": _ManagementSummaryStub(_ManagementStub(), "forest low sev fire"),
    }

    watershed = SimpleNamespace(
        _subs_summary={"101": {}},
        mofe_nsegments={"101": "1"},
        mofe_buffer=False,
        subwta=str(run_dir / "watershed" / "subwta.tif"),
        mofe_map=str(run_dir / "watershed" / "mofe_map.tif"),
    )
    monkeypatch.setattr(
        Landuse,
        "watershed_instance",
        property(lambda _self: watershed),
    )
    monkeypatch.setattr(landuse_module, "wepppyo3", None)

    class _LandcoverMapStub:
        def __init__(self, _lc_fn: str) -> None:
            pass

        def build_lcgrid(self, _subwta: str, _mofe_map: str) -> dict[str, dict[str, str]]:
            return {"101": {"1": "forest-dom"}}

    monkeypatch.setattr(landuse_module, "LandcoverMap", _LandcoverMapStub)
    monkeypatch.setattr(
        landuse_module,
        "_wait_for_gdal_openable_raster",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(landuse_module.os, "cpu_count", lambda: 1)

    class _SbsStub:
        class_pixel_map = {"255": "130"}

        @staticmethod
        def build_lcgrid(_subwta: str, _mofe_map: str) -> dict[str, dict[str, str]]:
            # Nodata-only segment from SBS crop/off-footprint.
            return {"101": {"1": "255"}}

    class _DisturbedStub:
        burn_shrubs = False
        burn_grass = False
        land_soil_replacements_d = None
        disturbed_cropped = str(run_dir / "disturbed" / "disturbed_cropped.tif")

        def get_disturbed_key_lookup(self) -> dict[str, str]:
            return {
                "forest_low_sev_fire": "forest-low",
                "forest_moderate_sev_fire": "forest-mod",
                "forest_high_sev_fire": "forest-high",
                "shrub_low_sev_fire": "shrub-low",
                "shrub_moderate_sev_fire": "shrub-mod",
                "shrub_high_sev_fire": "shrub-high",
                "grass_low_sev_fire": "grass-low",
                "grass_moderate_sev_fire": "grass-mod",
                "grass_high_sev_fire": "grass-high",
            }

        def get_sbs(self) -> _SbsStub:
            return _SbsStub()

    monkeypatch.setattr(
        "wepppy.nodb.mods.disturbed.Disturbed.tryGetInstance",
        lambda _wd: _DisturbedStub(),
    )

    landuse._build_multiple_ofe()

    # Nodata/off-map MOFE segment must stay baseline (unburned), not remap via global mode.
    assert landuse.domlc_mofe_d == {"101": {"1": "forest-dom"}}


def test_build_multiple_ofe_sbs_unknown_class_pixel_falls_back_to_unburned(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir = tmp_path / "run"
    (run_dir / "landuse").mkdir(parents=True, exist_ok=True)

    landuse = Landuse.__new__(Landuse)
    landuse.wd = str(run_dir)
    landuse._mods = []
    landuse._mapping = "mock-map"
    landuse.locked = lambda: nullcontext()
    landuse.logger = _LoggerStub()

    landuse.managements = {
        "forest-dom": _ManagementSummaryStub(_ManagementStub(), "forest"),
        "forest-low": _ManagementSummaryStub(_ManagementStub(), "forest low sev fire"),
    }

    watershed = SimpleNamespace(
        _subs_summary={"101": {}},
        mofe_nsegments={"101": "1"},
        mofe_buffer=False,
        subwta=str(run_dir / "watershed" / "subwta.tif"),
        mofe_map=str(run_dir / "watershed" / "mofe_map.tif"),
    )
    monkeypatch.setattr(
        Landuse,
        "watershed_instance",
        property(lambda _self: watershed),
    )
    monkeypatch.setattr(landuse_module, "wepppyo3", None)

    class _LandcoverMapStub:
        def __init__(self, _lc_fn: str) -> None:
            pass

        def build_lcgrid(self, _subwta: str, _mofe_map: str) -> dict[str, dict[str, str]]:
            return {"101": {"1": "forest-dom"}}

    monkeypatch.setattr(landuse_module, "LandcoverMap", _LandcoverMapStub)
    monkeypatch.setattr(
        landuse_module,
        "_wait_for_gdal_openable_raster",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(landuse_module.os, "cpu_count", lambda: 1)

    class _SbsStub:
        class_pixel_map: dict[str, str] = {}

        @staticmethod
        def build_lcgrid(_subwta: str, _mofe_map: str) -> dict[str, dict[str, str]]:
            # Unknown/unmapped class from SBS.
            return {"101": {"1": "999"}}

    class _DisturbedStub:
        burn_shrubs = False
        burn_grass = False
        land_soil_replacements_d = None
        disturbed_cropped = str(run_dir / "disturbed" / "disturbed_cropped.tif")

        def get_disturbed_key_lookup(self) -> dict[str, str]:
            return {
                "forest_low_sev_fire": "forest-low",
                "forest_moderate_sev_fire": "forest-mod",
                "forest_high_sev_fire": "forest-high",
                "shrub_low_sev_fire": "shrub-low",
                "shrub_moderate_sev_fire": "shrub-mod",
                "shrub_high_sev_fire": "shrub-high",
                "grass_low_sev_fire": "grass-low",
                "grass_moderate_sev_fire": "grass-mod",
                "grass_high_sev_fire": "grass-high",
            }

        def get_sbs(self) -> _SbsStub:
            return _SbsStub()

    monkeypatch.setattr(
        "wepppy.nodb.mods.disturbed.Disturbed.tryGetInstance",
        lambda _wd: _DisturbedStub(),
    )

    landuse._build_multiple_ofe()

    # Unknown SBS class must default to unburned behavior (no burn remap).
    assert landuse.domlc_mofe_d == {"101": {"1": "forest-dom"}}
