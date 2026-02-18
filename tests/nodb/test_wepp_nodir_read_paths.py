from __future__ import annotations

import logging
from contextlib import contextmanager
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest

import wepppy.nodb.core.wepp as wepp_module
import wepppy.nodb.mods as nodb_mods
from wepppy.nodb.core.wepp import Wepp

pytestmark = pytest.mark.unit


class _Translator:
    def wepp(self, top: int) -> int:
        return int(top)


class _WatershedPeridotStub:
    def __init__(self) -> None:
        self._subs_summary = {"11": {}}


class _StopPath(Exception):
    """Sentinel exception used to stop methods after path assertions."""


class _DummySoilUtil:
    def __init__(self, _src_fn: str) -> None:
        pass

    def modify_initial_sat(self, _value: float) -> None:
        pass

    def modify_kslast(self, _value: float) -> None:
        pass

    def clip_soil_depth(self, _value: float) -> None:
        pass

    def write(self, dst_fn: str) -> None:
        Path(dst_fn).write_text("soil\n", encoding="utf-8")


class _DummyManagement:
    def __init__(self, **_kwargs: object) -> None:
        self.bdtill_values: list[float] = []
        self.rdmax_values: list[float] = []
        self.xmxlai_values: list[float] = []
        self.override_values: dict[str, object] = {}

    def set_bdtill(self, value: float) -> None:
        self.bdtill_values.append(float(value))

    def set_rdmax(self, value: float) -> None:
        self.rdmax_values.append(float(value))

    def set_xmxlai(self, value: float) -> None:
        self.xmxlai_values.append(float(value))

    def set_cancov(self, _value: float) -> None:
        pass

    def __setitem__(self, attr: str, value: object) -> None:
        self.override_values[attr] = value

    def build_multiple_year_man(self, _years: list[int]):
        return self

    def __str__(self) -> str:
        return "management\n"


class _DummyManagementSummary:
    man_fn = "dom1.man"
    key = "dom1"
    desc = "Domain 1"
    color = "#00ff00"
    disturbed_class = ""
    cancov_override = 0.42
    inrcov_override = 0.31
    rilcov_override = 0.27

    def __init__(self) -> None:
        self.get_management_calls = 0
        self.last_management: _DummyManagement | None = None

    def get_management(self) -> _DummyManagement:
        self.get_management_calls += 1
        self.last_management = _DummyManagement()
        return self.last_management


class _SoilsForPrepSoils:
    clip_soils = False
    clip_soils_depth = 0.0
    initial_sat = 0.2

    def sub_iter(self):
        return [("11", SimpleNamespace(fname="hill_11.sol"))]


def _write_zip(path: Path, entries: dict[str, bytes | str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, payload in entries.items():
            data = payload.encode("utf-8") if isinstance(payload, str) else payload
            zf.writestr(name, data)


def _wepp_stub(tmp_path: Path) -> Wepp:
    wepp = Wepp.__new__(Wepp)
    wepp.wd = str(tmp_path)
    wepp.logger = logging.getLogger("tests.nodb.wepp_nodir")
    wepp._mods = []
    return wepp


def test_prep_slopes_peridot_reads_archive_without_watershed_dir(tmp_path: Path) -> None:
    wd = tmp_path
    runs_dir = wd / "wepp" / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    _write_zip(
        wd / "watershed.nodir",
        {"slope_files/hillslopes/hill_11.slp": "99.1\n1\n10\n"},
    )

    wepp = _wepp_stub(wd)
    wepp._prep_slopes_peridot(_WatershedPeridotStub(), _Translator(), False, 100.0)

    out = runs_dir / "p11.slp"
    assert out.exists()
    assert out.read_text(encoding="utf-8") == "99.1\n1\n10\n"


def test_prep_slopes_peridot_falls_back_to_legacy_hill_path(tmp_path: Path) -> None:
    wd = tmp_path
    runs_dir = wd / "wepp" / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    _write_zip(
        wd / "watershed.nodir",
        {"hill_11.slp": "99.1\n1\n10\n"},
    )

    wepp = _wepp_stub(wd)
    wepp._prep_slopes_peridot(_WatershedPeridotStub(), _Translator(), False, 100.0)

    out = runs_dir / "p11.slp"
    assert out.exists()
    assert out.read_text(encoding="utf-8") == "99.1\n1\n10\n"


def test_prep_slopes_peridot_clip_prefers_native_path_in_mixed_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wd = tmp_path
    runs_dir = wd / "wepp" / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    src_fn = wd / "watershed" / "slope_files" / "hillslopes" / "hill_11.slp"
    src_fn.parent.mkdir(parents=True, exist_ok=True)
    src_fn.write_text("99.1\n1\n10\n", encoding="utf-8")
    (wd / "watershed.nodir").write_text("archive", encoding="utf-8")

    wepp = _wepp_stub(wd)

    clip_calls: list[tuple[str, str, float]] = []

    def _fake_clip(src_path: str, dst_path: str, clip_len: float) -> None:
        clip_calls.append((src_path, dst_path, clip_len))
        Path(dst_path).write_text("clipped\n", encoding="utf-8")

    def _fail_materialize(*_args: object, **_kwargs: object) -> str:
        raise AssertionError("materialize_input_file should not run when native slope exists")

    monkeypatch.setattr(wepp_module, "clip_slope_file_length", _fake_clip)
    monkeypatch.setattr(wepp_module, "materialize_input_file", _fail_materialize)

    wepp._prep_slopes_peridot(_WatershedPeridotStub(), _Translator(), True, 42.0)

    assert clip_calls == [(str(src_fn), str(runs_dir / "p11.slp"), 42.0)]


def test_prep_channel_slopes_reads_archive_without_watershed_dir(tmp_path: Path) -> None:
    wd = tmp_path
    runs_dir = wd / "wepp" / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    channels = "99.1\nlegacy-channel\n"
    _write_zip(
        wd / "watershed.nodir",
        {"slope_files/channels.slp": channels},
    )

    wepp = _wepp_stub(wd)
    wepp._prep_channel_slopes()

    out = runs_dir / "pw0.slp"
    assert out.exists()
    assert out.read_text(encoding="utf-8") == channels


def test_prep_channel_slopes_mixed_state_prefers_archive_stream(tmp_path: Path) -> None:
    wd = tmp_path
    runs_dir = wd / "wepp" / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    # Directory-form mixed content differs from archive content; prep should
    # deterministically read archive form when tolerate_mixed is enabled.
    dir_channels = wd / "watershed" / "slope_files" / "channels.slp"
    dir_channels.parent.mkdir(parents=True, exist_ok=True)
    dir_channels.write_text("99.1\ndir-form\n", encoding="utf-8")

    _write_zip(
        wd / "watershed.nodir",
        {"slope_files/channels.slp": "99.1\narchive-form\n"},
    )

    wepp = _wepp_stub(wd)
    wepp._prep_channel_slopes()

    out = runs_dir / "pw0.slp"
    assert out.exists()
    assert out.read_text(encoding="utf-8") == "99.1\narchive-form\n"


def test_prep_channel_slopes_2023_format_reads_archive_stream(tmp_path: Path) -> None:
    wd = tmp_path
    runs_dir = wd / "wepp" / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    _write_zip(
        wd / "watershed.nodir",
        {
            "slope_files/channels.slp": (
                "2023.1\n"
                "1\n"
                "10 0.1 100 1\n"
                "0 0\n"
                "1 1\n"
            )
        },
    )

    wepp = _wepp_stub(wd)
    wepp._prep_channel_slopes()

    out = runs_dir / "pw0.slp"
    lines = out.read_text(encoding="utf-8").splitlines()

    assert lines[0] == "99.1"
    assert lines[1] == "1"
    assert lines[2] == "10.0 0.305"


def test_prep_managements_prefers_management_summary_get_management(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wepp = _wepp_stub(tmp_path)
    Path(wepp.runs_dir).mkdir(parents=True, exist_ok=True)
    Path(wepp.fp_runs_dir).mkdir(parents=True, exist_ok=True)

    summary = _DummyManagementSummary()
    landuse = SimpleNamespace(
        hillslope_cancovs=None,
        domlc_d={"5": "dom1"},
        managements={"dom1": summary},
    )
    climate = SimpleNamespace(input_years=[2011], year0=2011)
    soils = SimpleNamespace(
        domsoil_d={"5": "mukey1"},
        bd_d={"mukey1": 1.2},
        soils={"mukey1": SimpleNamespace(clay=20.0, sand=40.0)},
    )

    monkeypatch.setattr(Wepp, "landuse_instance", property(lambda _self: landuse))
    monkeypatch.setattr(Wepp, "climate_instance", property(lambda _self: climate))
    monkeypatch.setattr(Wepp, "soils_instance", property(lambda _self: soils))
    monkeypatch.setattr(Wepp, "watershed_instance", property(lambda _self: SimpleNamespace()))

    monkeypatch.setattr(
        wepp_module,
        "Disturbed",
        type("DisturbedStub", (), {"tryGetInstance": staticmethod(lambda _wd: None)}),
    )
    monkeypatch.setattr(
        nodb_mods,
        "RAP_TS",
        type("RapTsStub", (), {"tryGetInstance": staticmethod(lambda _wd: None)}),
    )

    def _fail_management_load(*_args: object, **_kwargs: object):
        raise AssertionError("Management.load should not run when get_management is available")

    monkeypatch.setattr(wepp_module.Management, "load", staticmethod(_fail_management_load))

    wepp._prep_managements(_Translator())

    assert summary.get_management_calls == 1
    assert Path(wepp.runs_dir, "p5.man").exists()


def test_prep_managements_reads_texture_from_materialized_soil_when_soil_path_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wepp = _wepp_stub(tmp_path)
    Path(wepp.runs_dir).mkdir(parents=True, exist_ok=True)

    summary = _DummyManagementSummary()
    summary.disturbed_class = "forest"
    summary.cancov_override = None
    summary.inrcov_override = None
    summary.rilcov_override = None

    class _SoilPathFail:
        fname = "mukey1.sol"

        @property
        def clay(self) -> float:
            raise ValueError("Invalid run identifier: ")

        @property
        def sand(self) -> float:
            raise ValueError("Invalid run identifier: ")

    landuse = SimpleNamespace(
        hillslope_cancovs=None,
        domlc_d={"5": "dom1"},
        managements={"dom1": summary},
    )
    climate = SimpleNamespace(input_years=[2011], year0=2011)
    soils = SimpleNamespace(
        domsoil_d={"5": "mukey1"},
        bd_d={"mukey1": 1.2},
        soils={"mukey1": _SoilPathFail()},
    )

    monkeypatch.setattr(Wepp, "landuse_instance", property(lambda _self: landuse))
    monkeypatch.setattr(Wepp, "climate_instance", property(lambda _self: climate))
    monkeypatch.setattr(Wepp, "soils_instance", property(lambda _self: soils))
    monkeypatch.setattr(Wepp, "watershed_instance", property(lambda _self: SimpleNamespace()))

    disturbed_instance = SimpleNamespace(
        land_soil_replacements_d={
            ("loam", "forest"): {"rdmax": 2.1, "xmxlai": 3.4}
        }
    )
    monkeypatch.setattr(
        wepp_module,
        "Disturbed",
        type("DisturbedStub", (), {"tryGetInstance": staticmethod(lambda _wd: disturbed_instance)}),
    )
    monkeypatch.setattr(
        nodb_mods,
        "RAP_TS",
        type("RapTsStub", (), {"tryGetInstance": staticmethod(lambda _wd: None)}),
    )

    materialize_calls: list[tuple[str, str, str]] = []

    def _fake_materialize(wd: str, rel: str, *, purpose: str) -> str:
        materialize_calls.append((wd, rel, purpose))
        fn = Path(tmp_path) / rel.replace("/", "_")
        fn.parent.mkdir(parents=True, exist_ok=True)
        fn.write_text("soil\n", encoding="utf-8")
        return str(fn)

    class _TextureSoilUtil:
        def __init__(self, _src: str) -> None:
            self.clay = 20.0
            self.sand = 40.0

    monkeypatch.setattr(wepp_module, "materialize_input_file", _fake_materialize)
    monkeypatch.setattr(wepp_module, "WeppSoilUtil", _TextureSoilUtil)
    monkeypatch.setattr(wepp_module, "simple_texture", lambda clay, sand: "loam")
    monkeypatch.setattr(wepp_module, "apply_disturbed_management_overrides", lambda *_args, **_kwargs: None)

    wepp._prep_managements(_Translator())

    assert summary.last_management is not None
    assert summary.last_management.rdmax_values == [2.1]
    assert summary.last_management.xmxlai_values == [3.4]
    assert (wepp.wd, "soils/mukey1.sol", "wepp-prep-managements-soil-texture") in materialize_calls


def test_prep_structure_minimal_mode_checks_network_via_input_exists(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wepp = _wepp_stub(tmp_path)
    Path(wepp.runs_dir).mkdir(parents=True, exist_ok=True)

    watershed = SimpleNamespace(abstraction_backend="peridot", sub_n=1, chn_n=1)
    monkeypatch.setattr(Wepp, "watershed_instance", property(lambda _self: watershed))

    calls: list[tuple[str, str, bool, str]] = []

    def _fake_input_exists(
        wd: str,
        rel: str,
        *,
        tolerate_mixed: bool = False,
        mixed_prefer: str = "archive",
    ) -> bool:
        calls.append((wd, rel, tolerate_mixed, mixed_prefer))
        return False

    monkeypatch.setattr(wepp_module, "input_exists", _fake_input_exists)

    wepp._prep_structure(_Translator())

    assert calls == [(wepp.wd, "watershed/network.txt", True, "archive")]
    assert "94.301" in Path(wepp.runs_dir, "pw0.str").read_text(encoding="utf-8")


def test_prep_climates_reads_climate_inputs_via_copy_input_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wepp = _wepp_stub(tmp_path)
    Path(wepp.runs_dir).mkdir(parents=True, exist_ok=True)

    climate = SimpleNamespace(
        climate_mode="gridded",
        has_climate=True,
        sub_summary=lambda topaz_id: {"cli_fn": f"{topaz_id}.cli"},
    )
    watershed = SimpleNamespace(_subs_summary={"11": {}}, sub_n=1)

    monkeypatch.setattr(Wepp, "climate_instance", property(lambda _self: climate))
    monkeypatch.setattr(Wepp, "watershed_instance", property(lambda _self: watershed))

    calls: list[tuple[str, str, str]] = []

    def _fake_copy(wd: str, src_rel: str, dst_fn: str) -> str:
        calls.append((wd, src_rel, dst_fn))
        Path(dst_fn).write_text("cli\n", encoding="utf-8")
        return dst_fn

    monkeypatch.setattr(wepp_module, "copy_input_file", _fake_copy)

    wepp._prep_climates(_Translator())

    assert calls == [
        (
            wepp.wd,
            "climate/11.cli",
            str(Path(wepp.runs_dir) / "p11.cli"),
        )
    ]


def test_prep_channel_climate_reads_climate_input_via_copy_input_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wepp = _wepp_stub(tmp_path)
    Path(wepp.runs_dir).mkdir(parents=True, exist_ok=True)

    climate = SimpleNamespace(cli_fn="channel.cli")
    monkeypatch.setattr(Wepp, "climate_instance", property(lambda _self: climate))

    calls: list[tuple[str, str, str]] = []

    def _fake_copy(wd: str, src_rel: str, dst_fn: str) -> str:
        calls.append((wd, src_rel, dst_fn))
        return dst_fn

    monkeypatch.setattr(wepp_module, "copy_input_file", _fake_copy)

    wepp._prep_channel_climate(_Translator())

    assert calls == [
        (
            wepp.wd,
            "climate/channel.cli",
            str(Path(wepp.runs_dir) / "pw0.cli"),
        )
    ]


def test_prep_and_run_flowpaths_globs_archive_flowpath_slps(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wepp = _wepp_stub(tmp_path)

    calls: list[tuple[str, str, bool, str]] = []

    def _fake_glob(
        wd: str,
        pattern: str,
        *,
        tolerate_mixed: bool = False,
        mixed_prefer: str = "archive",
    ) -> list[str]:
        calls.append((wd, pattern, tolerate_mixed, mixed_prefer))
        raise _StopPath("stop after path check")

    monkeypatch.setattr(wepp_module, "glob_input_files", _fake_glob)

    with pytest.raises(_StopPath, match="stop after path check"):
        wepp.prep_and_run_flowpaths(clean_after_run=False)

    assert calls == [(wepp.wd, "watershed/slope_files/flowpaths/*.slps", True, "archive")]


def test_prep_multi_ofe_reads_watershed_soils_landuse_roots(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wepp = _wepp_stub(tmp_path)
    Path(wepp.runs_dir).mkdir(parents=True, exist_ok=True)

    climate = SimpleNamespace(input_years=[2015, 2016])
    watershed = SimpleNamespace(
        subs_summary={"11": SimpleNamespace()},
        hillslope_centroid_lnglat=lambda _topaz_id: (-116.1, 47.2),
    )
    soils = SimpleNamespace(clip_soils=False, clip_soils_depth=10.0, initial_sat=0.3)

    monkeypatch.setattr(Wepp, "landuse_instance", property(lambda _self: SimpleNamespace()))
    monkeypatch.setattr(Wepp, "climate_instance", property(lambda _self: climate))
    monkeypatch.setattr(Wepp, "watershed_instance", property(lambda _self: watershed))
    monkeypatch.setattr(Wepp, "soils_instance", property(lambda _self: soils))
    monkeypatch.setattr(Wepp, "kslast", property(lambda _self: None))
    monkeypatch.setattr(Wepp, "kslast_map", property(lambda _self: None))

    monkeypatch.setattr(
        wepp_module,
        "Disturbed",
        type("DisturbedStub", (), {"getInstance": staticmethod(lambda _wd: (_ for _ in ()).throw(RuntimeError()))}),
    )
    monkeypatch.setattr(wepp_module, "WeppSoilUtil", _DummySoilUtil)
    monkeypatch.setattr(wepp_module, "Management", _DummyManagement)

    copied: list[tuple[str, str, str]] = []
    path_contexts: list[tuple[str, str, str]] = []

    def _fake_copy(wd: str, src_rel: str, dst_fn: str) -> str:
        copied.append((wd, src_rel, dst_fn))
        Path(dst_fn).parent.mkdir(parents=True, exist_ok=True)
        Path(dst_fn).write_text("slope\n", encoding="utf-8")
        return dst_fn

    @contextmanager
    def _fake_with_input_file_path(
        wd: str,
        rel: str,
        *,
        purpose: str,
        tolerate_mixed: bool = False,
        mixed_prefer: str = "archive",
        use_projection: bool = True,
        allow_materialize_fallback: bool = False,
    ):
        path_contexts.append((wd, rel, purpose))
        fn = Path(tmp_path) / rel.replace("/", "_")
        fn.parent.mkdir(parents=True, exist_ok=True)
        fn.write_text("projected\n", encoding="utf-8")
        yield str(fn)

    monkeypatch.setattr(wepp_module, "copy_input_file", _fake_copy)
    monkeypatch.setattr(wepp_module, "with_input_file_path", _fake_with_input_file_path)

    wepp._prep_multi_ofe(_Translator())

    assert copied[0][1] == "watershed/slope_files/hillslopes/hill_11.mofe.slp"
    assert any(rel == "soils/hill_11.mofe.sol" for _, rel, _ in path_contexts)
    assert any(rel == "landuse/hill_11.mofe.man" for _, rel, _ in path_contexts)


def test_prep_soils_materializes_archive_input_before_worker_submit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wepp = _wepp_stub(tmp_path)

    soils = _SoilsForPrepSoils()
    watershed = SimpleNamespace(hillslope_centroid_lnglat=lambda _topaz_id: (-116.1, 47.2))

    monkeypatch.setattr(Wepp, "soils_instance", property(lambda _self: soils))
    monkeypatch.setattr(Wepp, "watershed_instance", property(lambda _self: watershed))
    monkeypatch.setattr(Wepp, "kslast", property(lambda _self: None))
    monkeypatch.setattr(Wepp, "kslast_map", property(lambda _self: None))

    calls: list[tuple[str, str, str]] = []

    def _fake_materialize(wd: str, rel: str, *, purpose: str) -> str:
        calls.append((wd, rel, purpose))
        raise _StopPath("stop after soils materialize")

    monkeypatch.setattr(wepp_module, "materialize_input_file", _fake_materialize)

    with pytest.raises(_StopPath, match="stop after soils materialize"):
        wepp._prep_soils(_Translator())

    assert calls == [(wepp.wd, "soils/hill_11.sol", "wepp-prep-soils")]
