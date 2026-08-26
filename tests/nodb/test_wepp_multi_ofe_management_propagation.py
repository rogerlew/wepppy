from pathlib import Path

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
        ("101", 7, str(wd), str(runs_dir), 3, None, 0.5, False, 1.0, False, 1.0)
    )

    generated = (runs_dir / "p7.man").read_text(encoding="ascii")
    assert "treated-cancov=0.40" in generated
    assert "treated-ground-cover=0.75" in generated
    assert "years=3" in generated
