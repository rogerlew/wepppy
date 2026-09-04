from pathlib import Path
from types import SimpleNamespace

import pytest

import wepppy.nodb.core.wepp as wepp_module

pytestmark = pytest.mark.unit


class _SoilStub:
    obj = {"ofes": []}

    def __init__(self, source: str, **_kwargs: object) -> None:
        self.source = Path(source)

    def modify_initial_sat(self, _value: float) -> None:
        return None

    def write(self, destination: str) -> None:
        Path(destination).write_text(self.source.read_text(encoding="ascii"), encoding="ascii")


class _ManagementStub:
    def __init__(self, *, ManagementFile: str, ManagementDir: str, **_kwargs: object) -> None:
        self.content = (Path(ManagementDir) / ManagementFile).read_text(encoding="ascii")

    def build_multiple_year_man(self, years: int) -> "_ManagementStub":
        self.content += f"years={years}\n"
        return self

    def __str__(self) -> str:
        return self.content


def test_prep_multi_ofe_hillslope_copies_treated_synthesized_management(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wd = tmp_path / "scenario"
    runs_dir = wd / "wepp" / "runs"
    runs_dir.mkdir(parents=True)
    slope = wd / "watershed" / "slope_files" / "hillslopes" / "hill_101.mofe.slp"
    slope.parent.mkdir(parents=True)
    slope.write_text("slope\n", encoding="ascii")
    soil = wd / "soils" / "hill_101.mofe.sol"
    soil.parent.mkdir(parents=True)
    soil.write_text("soil\n", encoding="ascii")
    management = wd / "landuse" / "hill_101.mofe.man"
    management.parent.mkdir(parents=True)
    management.write_text("treated-cancov=0.40\ntreated-ground-cover=0.75\n", encoding="ascii")

    monkeypatch.setattr(wepp_module, "WeppSoilUtil", _SoilStub)
    monkeypatch.setattr(wepp_module, "Management", _ManagementStub)
    monkeypatch.setattr(wepp_module, "_soil_has_symbolic_wepp_parameters", lambda _soil: False)

    wepp_module.prep_multi_ofe_hillslope(
        ("101", 7, str(wd), str(runs_dir), 3, None, 0.5, False, 60.0, False, 1.0, False, 1.0)
    )

    generated = (runs_dir / "p7.man").read_text(encoding="ascii")
    assert "treated-cancov=0.40" in generated
    assert "treated-ground-cover=0.75" in generated
    assert "years=3" in generated


def test_prep_multi_ofe_hillslope_clips_each_ofe_when_configured(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wd = tmp_path / "scenario"
    runs_dir = wd / "wepp" / "runs"
    runs_dir.mkdir(parents=True)
    slope = wd / "watershed" / "slope_files" / "hillslopes" / "hill_101.mofe.slp"
    slope.parent.mkdir(parents=True)
    slope.write_text(
        "97.5\n2\n311.995 80\n2 40\n0, 0.1 1, 0.2\n2 90\n0, 0.2 1, 0.3\n",
        encoding="ascii",
    )
    soil = wd / "soils" / "hill_101.mofe.sol"
    soil.parent.mkdir(parents=True)
    soil.write_text("soil\n", encoding="ascii")
    management = wd / "landuse" / "hill_101.mofe.man"
    management.parent.mkdir(parents=True)
    management.write_text("management\n", encoding="ascii")

    monkeypatch.setattr(wepp_module, "WeppSoilUtil", _SoilStub)
    monkeypatch.setattr(wepp_module, "Management", _ManagementStub)
    monkeypatch.setattr(wepp_module, "_soil_has_symbolic_wepp_parameters", lambda _soil: False)

    wepp_module.prep_multi_ofe_hillslope(
        ("101", 7, str(wd), str(runs_dir), 3, None, 0.5, True, 60.0, False, 1.0, False, 1.0)
    )

    lines = (runs_dir / "p7.slp").read_text(encoding="ascii").splitlines()
    assert [float(lines[index].split()[1]) for index in (3, 5)] == [40.0, 60.0]
    assert float(lines[2].split()[1]) * 100.0 == pytest.approx(80.0 * 130.0)


def test_prep_multi_ofe_hillslope_copies_slope_bytes_when_clipping_disabled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wd = tmp_path / "scenario"
    runs_dir = wd / "wepp" / "runs"
    runs_dir.mkdir(parents=True)
    slope = wd / "watershed" / "slope_files" / "hillslopes" / "hill_101.mofe.slp"
    slope.parent.mkdir(parents=True)
    slope_bytes = b"97.5\n2\n311.995 80\n2 40\n0, 0.1 1, 0.2\n2 90\n0, 0.2 1, 0.3\n"
    slope.write_bytes(slope_bytes)
    soil = wd / "soils" / "hill_101.mofe.sol"
    soil.parent.mkdir(parents=True)
    soil.write_text("soil\n", encoding="ascii")
    management = wd / "landuse" / "hill_101.mofe.man"
    management.parent.mkdir(parents=True)
    management.write_text("management\n", encoding="ascii")

    monkeypatch.setattr(wepp_module, "WeppSoilUtil", _SoilStub)
    monkeypatch.setattr(wepp_module, "Management", _ManagementStub)
    monkeypatch.setattr(wepp_module, "_soil_has_symbolic_wepp_parameters", lambda _soil: False)

    wepp_module.prep_multi_ofe_hillslope(
        ("101", 7, str(wd), str(runs_dir), 3, None, 0.5, False, 60.0, False, 1.0, False, 1.0)
    )

    assert (runs_dir / "p7.slp").read_bytes() == slope_bytes


def test_prep_multi_ofe_wires_configured_clip_value_and_length(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[tuple] = []
    monkeypatch.setattr(
        wepp_module,
        "prep_multi_ofe_hillslope",
        lambda args: (captured.append(args) or (args[0], 0.0)),
    )
    watershed = SimpleNamespace(
        clip_hillslopes_configured=True,
        clip_hillslope_length=60.0,
        subs_summary={"101": {}},
        hillslope_centroid_lnglat=lambda _topaz_id: (0.0, 0.0),
    )
    fake_wepp = SimpleNamespace(
        logger=SimpleNamespace(info=lambda *_args: None, warning=lambda *_args: None),
        wd=str(tmp_path),
        climate_instance=SimpleNamespace(input_years=3),
        watershed_instance=watershed,
        soils_instance=SimpleNamespace(
            clip_soils=False,
            clip_soils_depth=1.0,
            clip_soils_minimum=False,
            clip_soils_minimum_depth=1.0,
            initial_sat=0.5,
        ),
        runs_dir=str(tmp_path / "wepp" / "runs"),
        kslast=None,
        kslast_map=None,
    )
    translator = SimpleNamespace(wepp=lambda *, top: 7)

    wepp_module.Wepp._prep_multi_ofe(fake_wepp, translator, max_workers=1)

    assert len(captured) == 1
    assert captured[0][0:2] == ("101", 7)
    assert captured[0][7:9] == (True, 60.0)
