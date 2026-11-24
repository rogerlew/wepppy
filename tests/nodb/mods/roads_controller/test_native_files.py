from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
import wepppyo3.wepp_interchange as wepp_interchange_module

from wepppy.nodb.mods.roads.roads import Roads

pytestmark = [pytest.mark.unit, pytest.mark.nodb]


def test_roads_workspace_preserves_baseline_time_of_concentration(tmp_path):
    baseline = tmp_path / "baseline"
    baseline.mkdir()
    (baseline / "tc.txt").write_text("baseline input\n")
    (baseline / "tc_out.txt").write_text("baseline diagnostic\n")
    roads = tmp_path / "roads"
    controller = SimpleNamespace(
        wepp_instance=SimpleNamespace(runs_dir=str(baseline)),
        roads_runs_dir=str(roads),
        _safe_link_or_copy=Roads._safe_link_or_copy,
    )
    Roads._prepare_roads_runs_workspace(controller)
    assert (roads / "tc.txt").read_text() == "baseline input\n"
    # The native watershed creates this diagnostic in its working directory.
    (roads / "tc_out.txt").write_text("roads diagnostic\n")
    assert (baseline / "tc_out.txt").read_text() == "baseline diagnostic\n"


@pytest.mark.parametrize("marker", ["", "WEPP_PASS_COMPONENTS 3\r\n"])
def test_pass_climate_rewrite_preserves_version_and_payload(tmp_path, marker):
    path = tmp_path / "H1.pass.dat"
    tail = " 1 2000\r\n1000\r\nparticles\r\nphosphorus\r\nSRC3 2000 1 0\r\n"
    path.write_bytes((marker + "old.cli\r\n" + tail).encode())
    assert Roads._read_pass_header_climate_line(path) == "old.cli"
    Roads._rewrite_pass_header_climate_line(path, "new.cli")
    assert path.read_bytes() == (marker + "new.cli\r\n" + tail).encode()


@pytest.mark.parametrize("version", [1, 2, 4])
def test_pass_climate_rejects_unknown_component_version(tmp_path, version):
    path = tmp_path / "H1.pass.dat"
    path.write_text(f"WEPP_PASS_COMPONENTS {version}\np1.cli\n")
    with pytest.raises(ValueError, match="Unsupported PASS"):
        Roads._read_pass_header_climate_line(path)
    with pytest.raises(ValueError, match="Unsupported PASS"):
        Roads._rewrite_pass_header_climate_line(path, "new.cli")


def _write_minimal_pass(path: Path, *, climate_token: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                climate_token,
                "   16      2000",
                ".44409E+04",
                "  5    0.20000E-05 0.10000E-04 0.30000E-04 0.30600E-03 0.20000E-03",
                "    0.00     0.00     0.00     0.00",
                "NO EVENT   2000     1      0.64000E-01 0.00000E+00",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def test_build_single_ofe_soil_file_keeps_only_road_ofe(tmp_path: Path) -> None:
    controller = Roads(str(tmp_path), "disturbed9002-wbt-mofe.cfg")
    template_path = Path(controller.roads_legacy_soils_dir) / "3gloam2.sol"
    output_path = tmp_path / "roads" / "single_ofe.sol"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    controller._build_single_ofe_soil_file(
        template_path=template_path,
        output_path=output_path,
        traffic="low",
        surface="gravel",
        rfg_pct=20.0,
    )

    text = output_path.read_text(encoding="utf-8")
    assert "1 0" in text
    assert "'Road'" in text
    assert "'Fill'" not in text
    assert "'Forest'" not in text
    assert "urr" not in text
    assert "ufr" not in text
    assert "ubr" not in text


@pytest.mark.parametrize("template_name", ["3inslope.man", "3inslopen.man"])
def test_build_single_ofe_management_file_keeps_only_ofe_1(tmp_path: Path, template_name: str) -> None:
    controller = Roads(str(tmp_path), "disturbed9002-wbt-mofe.cfg")
    template_path = Path(controller.roads_legacy_managements_dir) / template_name
    output_path = tmp_path / "roads" / "single_ofe.man"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    controller._build_single_ofe_management_file(
        template_path=template_path,
        output_path=output_path,
    )

    text = output_path.read_text(encoding="utf-8")
    if template_name == "3inslopen.man":
        assert "2       # `iresd' - <FILL>" in text
    assert "3       # looper; number of Plant scenarios" in text
    assert "# number of OFEs" in text
    assert "Plant scenario 2" in text
    assert "Initial Conditions scenario 2" not in text
    assert "Yearly scenario 2" not in text
    assert "OFE : 2" not in text
    assert "OFE : 3" not in text


def test_build_routed_two_ofe_soil_file_keeps_road_and_buffer_ofes(tmp_path: Path) -> None:
    controller = Roads(str(tmp_path), "disturbed9002-wbt-mofe.cfg")
    template_path = Path(controller.roads_legacy_soils_dir) / "3gloam2.sol"
    output_path = tmp_path / "roads" / "routed_two_ofe.sol"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    controller._build_routed_two_ofe_soil_file(
        template_path=template_path,
        output_path=output_path,
        traffic="low",
        surface="gravel",
        rfg_pct=20.0,
    )

    text = output_path.read_text(encoding="utf-8")
    assert "2 0" in text
    assert "'Road'" in text
    assert "'Forest'" in text
    assert "'Fill'" not in text
    assert "urr" not in text
    assert "ufr" not in text
    assert "ubr" not in text


def test_build_routed_three_ofe_soil_file_keeps_road_fill_and_buffer_ofes(tmp_path: Path) -> None:
    controller = Roads(str(tmp_path), "disturbed9002-wbt-mofe.cfg")
    template_path = Path(controller.roads_legacy_soils_dir) / "3gloam2.sol"
    output_path = tmp_path / "roads" / "routed_three_ofe.sol"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    controller._build_routed_three_ofe_soil_file(
        template_path=template_path,
        output_path=output_path,
        traffic="low",
        surface="gravel",
        rfg_pct=20.0,
    )

    text = output_path.read_text(encoding="utf-8")
    assert "3 0" in text
    assert "'Road'" in text
    assert "'Fill'" in text
    assert "'Forest'" in text
    assert "urr" not in text
    assert "ufr" not in text
    assert "ubr" not in text


def test_write_routed_three_ofe_slope_file_writes_three_ofes(tmp_path: Path) -> None:
    controller = Roads(str(tmp_path), "disturbed9002-wbt-mofe.cfg")
    output_path = tmp_path / "roads" / "routed_three_ofe.slp"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    controller._write_routed_three_ofe_slope_file(
        output_path,
        width_m=4.0,
        road_length_m=120.0,
        road_slope_pct=8.0,
        fill_length_m=18.0,
        fill_slope_pct=12.0,
        buffer_length_m=30.0,
        buffer_slope_pct=6.0,
    )

    text = output_path.read_text(encoding="utf-8")
    lines = text.splitlines()

    assert lines[0] == "97.3"
    assert lines[1] == "3"
    assert lines[3] == "2 120.000"
    assert lines[5] == "3 18.000"
    assert lines[7] == "3 30.000"
    assert lines[4].count(",") == 2
    assert lines[6].count(",") == 3
    assert lines[8].count(",") == 3


@pytest.mark.parametrize("template_name", ["3inslope.man", "3inslopen.man"])
def test_build_routed_two_ofe_management_file_keeps_road_and_buffer(tmp_path: Path, template_name: str) -> None:
    controller = Roads(str(tmp_path), "disturbed9002-wbt-mofe.cfg")
    template_path = Path(controller.roads_legacy_managements_dir) / template_name
    output_path = tmp_path / "roads" / "routed_two_ofe.man"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    controller._build_routed_two_ofe_management_file(
        template_path=template_path,
        output_path=output_path,
    )

    text = output_path.read_text(encoding="utf-8")
    if template_name == "3inslopen.man":
        assert "2       # `iresd' - <FILL>" in text
    assert "3       # looper; number of Plant scenarios" in text
    assert "3\t# number of OFEs" not in text
    assert "2\t# number of OFEs" in text
    assert "Plant scenario 2 of 3" in text
    assert "Initial Conditions scenario 2 of 3" not in text
    assert "Yearly scenario 2 of 3" not in text
    assert "OFE : 3" not in text
    assert "OFE : 2" in text
    assert "Initial Conditions indx' - <FILL>" not in text
    assert "3       # `itype' - <FOREST>" in text
    assert "2       # `itype' - <FOREST>" not in text


def test_combine_target_hillslope_pass_normalizes_alias_climate_tokens(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller = Roads(str(tmp_path), "disturbed9002-wbt-mofe.cfg")

    base_pass_path = tmp_path / "wepp" / "output" / "H15.pass.dat"
    road_pass_path = tmp_path / "wepp" / "roads" / "output" / "H900003.pass.dat"
    out_pass_path = tmp_path / "wepp" / "roads" / "output" / "H15.combined.pass.dat"
    base_cli_path = tmp_path / "wepp" / "runs" / "p15.cli"
    road_cli_path = tmp_path / "wepp" / "roads" / "runs" / "p900003.cli"

    base_cli_path.parent.mkdir(parents=True, exist_ok=True)
    road_cli_path.parent.mkdir(parents=True, exist_ok=True)
    base_cli_path.write_text("shared-climate", encoding="utf-8")
    road_cli_path.symlink_to(base_cli_path)

    _write_minimal_pass(base_pass_path, climate_token="p15.cli")
    _write_minimal_pass(road_pass_path, climate_token="p900003.cli")

    captured: dict[str, object] = {}

    def _fake_combine(**kwargs) -> None:
        captured.update(kwargs)
        Path(kwargs["out_pass"]).write_text("combined", encoding="utf-8")

    monkeypatch.setattr(wepp_interchange_module, "combine_hillslope_pass_files", _fake_combine)

    controller._combine_target_hillslope_pass(
        base_pass_path=str(base_pass_path),
        road_pass_paths=[str(road_pass_path)],
        output_pass_path=str(out_pass_path),
    )

    assert captured["base_pass"] == str(base_pass_path)
    assert captured["road_passes"] == [str(road_pass_path)]
    assert captured["strategy"] == "phase1"
    assert road_pass_path.read_text(encoding="utf-8").splitlines()[0] == "p15.cli"
    assert out_pass_path.read_text(encoding="utf-8") == "combined"


def test_combine_target_hillslope_pass_rejects_distinct_climate_tokens(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller = Roads(str(tmp_path), "disturbed9002-wbt-mofe.cfg")

    base_pass_path = tmp_path / "wepp" / "output" / "H15.pass.dat"
    road_pass_path = tmp_path / "wepp" / "roads" / "output" / "H900003.pass.dat"
    out_pass_path = tmp_path / "wepp" / "roads" / "output" / "H15.combined.pass.dat"
    base_cli_path = tmp_path / "wepp" / "runs" / "p15.cli"
    road_cli_path = tmp_path / "wepp" / "roads" / "runs" / "p900003.cli"

    base_cli_path.parent.mkdir(parents=True, exist_ok=True)
    road_cli_path.parent.mkdir(parents=True, exist_ok=True)
    base_cli_path.write_text("base-climate", encoding="utf-8")
    road_cli_path.write_text("different-climate", encoding="utf-8")

    _write_minimal_pass(base_pass_path, climate_token="p15.cli")
    _write_minimal_pass(road_pass_path, climate_token="p900003.cli")

    monkeypatch.setattr(
        wepp_interchange_module,
        "combine_hillslope_pass_files",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("combine should not be called")),
    )

    with pytest.raises(ValueError, match="could not be normalized"):
        controller._combine_target_hillslope_pass(
            base_pass_path=str(base_pass_path),
            road_pass_paths=[str(road_pass_path)],
            output_pass_path=str(out_pass_path),
        )

    assert road_pass_path.read_text(encoding="utf-8").splitlines()[0] == "p900003.cli"
