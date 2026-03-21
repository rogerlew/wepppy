from __future__ import annotations

import json
from pathlib import Path

import pytest

import wepppy.nodb.mods.rusle.ls_integration as ls_integration


pytestmark = pytest.mark.unit


class _FakeWhiteboxTools:
    def __init__(self, *, verbose: bool, raise_on_error: bool) -> None:
        self.verbose = verbose
        self.raise_on_error = raise_on_error
        self.working_dir: str | None = None
        self.calls: list[dict] = []

    def set_working_dir(self, wd: str) -> None:
        self.working_dir = wd

    def rusle_ls_factor(self, **kwargs):
        self.calls.append(kwargs)
        for key in (
            "output",
            "l_output",
            "s_output",
            "sca_output",
            "effective_slope_length_output",
        ):
            Path(kwargs[key]).write_text(f"fake:{key}", encoding="utf-8")
        return 0


def test_run_rusle_ls_factor_writes_outputs_and_manifest(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dem_path = tmp_path / "dem.tif"
    dem_path.write_text("fake-dem", encoding="utf-8")

    fake_instances: list[_FakeWhiteboxTools] = []

    def _factory(*, verbose: bool, raise_on_error: bool) -> _FakeWhiteboxTools:
        inst = _FakeWhiteboxTools(verbose=verbose, raise_on_error=raise_on_error)
        fake_instances.append(inst)
        return inst

    monkeypatch.setattr(ls_integration, "WhiteboxTools", _factory)

    result = ls_integration.run_rusle_ls_factor(
        wd=str(tmp_path),
        dem=str(dem_path),
        routing_mode="dinf",
        m_regime="moderate",
        max_slope_length_m=304.8,
        channel_mask=str(tmp_path / "channel_mask.tif"),
        blocking_mask=str(tmp_path / "blocking_mask.tif"),
    )

    assert result.ls.endswith("rusle/ls.tif")
    assert Path(result.ls).exists()
    assert Path(result.l).exists()
    assert Path(result.s).exists()
    assert Path(result.sca).exists()
    assert Path(result.effective_slope_length).exists()
    assert Path(result.manifest).exists()

    assert len(fake_instances) == 1
    call = fake_instances[0].calls[0]
    assert call["routing"] == "dinf"
    assert call["m_regime"] == "moderate"
    assert call["max_slope_length_m"] == 304.8

    with open(result.manifest, "r", encoding="utf-8") as stream:
        manifest = json.load(stream)

    ls_payload = manifest["ls"]
    assert ls_payload["tool"] == "RusleLsFactor"
    assert ls_payload["routing_mode"] == "dinf"
    assert ls_payload["max_slope_length_m"] == 304.8
    assert ls_payload["max_slope_length_basis"] == "rusle2_handbook_1000ft"
    assert ls_payload["blocking_mask_source"] == "input_raster"
    assert ls_payload["sca_source"] == "derived"
    assert ls_payload["slope_source"] == "derived"
    assert set(ls_payload["stop_mask_components"]) == {"channel_mask", "blocking_mask"}


def test_run_rusle_ls_factor_fails_for_missing_dem(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="DEM path does not exist"):
        ls_integration.run_rusle_ls_factor(wd=str(tmp_path), dem=str(tmp_path / "missing_dem.tif"))


def test_run_rusle_ls_factor_raises_when_wbt_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dem_path = tmp_path / "dem.tif"
    dem_path.write_text("fake-dem", encoding="utf-8")

    class _FailingWhiteboxTools(_FakeWhiteboxTools):
        def rusle_ls_factor(self, **kwargs):
            self.calls.append(kwargs)
            return 1

    monkeypatch.setattr(
        ls_integration,
        "WhiteboxTools",
        lambda *, verbose, raise_on_error: _FailingWhiteboxTools(
            verbose=verbose,
            raise_on_error=raise_on_error,
        ),
    )

    with pytest.raises(RuntimeError, match="return code: 1"):
        ls_integration.run_rusle_ls_factor(wd=str(tmp_path), dem=str(dem_path))
