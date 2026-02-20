from __future__ import annotations

import logging
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest

from wepppy.nodb.core.climate import ClimatePrecipScalingMode
from wepppy.nodb.core.climate_scaling_service import (
    ClimateScalingService,
    pyo3_cli_p_scale_annual_monthlies,
)

pytestmark = pytest.mark.unit


class _ScalingClimate:
    def __init__(self, tmp_path: Path) -> None:
        self.logger = logging.getLogger("tests.nodb.climate.scaling")
        self._locked = False
        self.cli_dir = str(tmp_path)
        self.cli_fn = "main.cli"
        self.sub_cli_fns = None
        self.monthlies = None

        self.precip_scaling_mode = ClimatePrecipScalingMode.NoScaling
        self.precip_scale_factor = None
        self.precip_scale_factor_map = None
        self.precip_monthly_scale_factors = None
        self.precip_scaling_reference = None

        self.observed_start_year = 1981
        self.observed_end_year = 1982
        self.watershed_instance = SimpleNamespace(
            centroid=(-116.0, 43.0),
            hillslope_centroid_lnglat=lambda _topaz_id: (-115.0, 43.0),
        )

    def _scale_precip(self, scale_factor: float) -> None:
        self._scaled = ("scalar", scale_factor)

    def _spatial_scale_precip(self, map_fn: str) -> None:
        self._scaled = ("spatial", map_fn)

    def _scale_precip_monthlies(self, factors, scale_func) -> None:
        self._scaled = ("monthlies", tuple(factors), scale_func)

    @contextmanager
    def locked(self):
        assert not self._locked
        self._locked = True
        yield
        self._locked = False


def test_validate_scaling_rejects_missing_scalar_factor(tmp_path: Path) -> None:
    service = ClimateScalingService()
    climate = _ScalingClimate(tmp_path)
    climate.precip_scaling_mode = ClimatePrecipScalingMode.Scalar

    with pytest.raises(ValueError, match="precip_scale_factor is None"):
        service.validate_scaling_inputs(climate)


def test_validate_scaling_rejects_invalid_monthlies(tmp_path: Path) -> None:
    service = ClimateScalingService()
    climate = _ScalingClimate(tmp_path)
    climate.precip_scaling_mode = ClimatePrecipScalingMode.Monthlies
    climate.precip_monthly_scale_factors = [1.0] * 11

    with pytest.raises(ValueError, match="length is not 12"):
        service.validate_scaling_inputs(climate)


def test_validate_scaling_rejects_prism_reference_before_1981(tmp_path: Path) -> None:
    service = ClimateScalingService()
    climate = _ScalingClimate(tmp_path)
    climate.precip_scaling_mode = ClimatePrecipScalingMode.AnnualMonthlies
    climate.precip_scaling_reference = "prism"
    climate.observed_start_year = 1979

    with pytest.raises(ValueError, match="prism only available 1981 to present"):
        service.validate_scaling_inputs(climate)


def test_apply_scaling_dispatches_modes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    service = ClimateScalingService()
    climate = _ScalingClimate(tmp_path)

    climate.precip_scaling_mode = ClimatePrecipScalingMode.Scalar
    climate.precip_scale_factor = 1.25
    service.apply_scaling(climate)
    assert climate._scaled == ("scalar", 1.25)

    climate.precip_scaling_mode = ClimatePrecipScalingMode.Spatial
    climate.precip_scale_factor_map = "map.tif"
    service.apply_scaling(climate)
    assert climate._scaled == ("spatial", "map.tif")

    climate.precip_scaling_mode = ClimatePrecipScalingMode.Monthlies
    climate.precip_monthly_scale_factors = [1.0] * 12
    service.apply_scaling(climate)
    assert climate._scaled[0] == "monthlies"

    climate.precip_scaling_mode = ClimatePrecipScalingMode.AnnualMonthlies
    monkeypatch.setattr(service, "_scale_precip_annual_monthlies", lambda _climate: setattr(climate, "_annual", True))
    service.apply_scaling(climate)
    assert climate._annual is True


def test_scale_precip_updates_cli_and_subcatchment_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = ClimateScalingService()
    climate = _ScalingClimate(tmp_path)
    climate.sub_cli_fns = {"1": "sub1.cli"}

    (tmp_path / "main.cli").write_text("main")
    (tmp_path / "sub1.cli").write_text("sub")

    def _fake_scale(src: str, dst: str, _scale_factor: float) -> None:
        Path(dst).write_text(Path(src).read_text())

    monkeypatch.setattr("wepppy.nodb.core.climate_scaling_service.pyo3_cli_p_scale", _fake_scale)
    monkeypatch.setattr("wepppy.nodb.core.climate_scaling_service.pyo3_cli_calculate_monthlies", lambda _fn: [1.0] * 12)

    service.scale_precip(climate, 1.5)

    assert climate.cli_fn == "scale_main.cli"
    assert climate.sub_cli_fns == {"1": "scale_sub1.cli"}
    assert climate.monthlies == [1.0] * 12


def test_spatial_scale_precip_respects_scale_factor_bounds(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = ClimateScalingService()
    climate = _ScalingClimate(tmp_path)
    climate.sub_cli_fns = {"1": "sub1.cli"}

    (tmp_path / "main.cli").write_text("main")
    (tmp_path / "sub1.cli").write_text("sub")
    scale_map = tmp_path / "scale_map.tif"
    scale_map.write_text("stub")

    class _FakeRDI:
        def __init__(self, _path: str) -> None:
            pass

        def get_location_info(self, lng: float, lat: float, method: str | None = None):
            if lng < -115.5:
                return 0.05  # watershed centroid -> skipped as out of range
            return 2.0  # hillslope -> applied

    monkeypatch.setattr("wepppy.nodb.core.climate_scaling_service.RasterDatasetInterpolator", _FakeRDI)

    def _fake_scale(src: str, dst: str, _scale_factor: float) -> None:
        Path(dst).write_text(Path(src).read_text())

    monkeypatch.setattr("wepppy.nodb.core.climate_scaling_service.pyo3_cli_p_scale", _fake_scale)
    monkeypatch.setattr("wepppy.nodb.core.climate_scaling_service.pyo3_cli_calculate_monthlies", lambda _fn: [2.0] * 12)

    service.spatial_scale_precip(climate, str(scale_map))

    # Watershed file stays unscaled due to out-of-range factor; hillslope file scales.
    assert climate.cli_fn == "main.cli"
    assert climate.sub_cli_fns == {"1": "scale_sub1.cli"}


@pytest.mark.parametrize(
    "reference",
    [
        "prism",
        "daymet",
        "gridmet",
    ],
)
def test_scale_precip_annual_monthlies_selects_expected_reference_provider(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    reference: str,
) -> None:
    service = ClimateScalingService()
    climate = _ScalingClimate(tmp_path)
    climate.precip_scaling_reference = reference
    climate.observed_start_year = 2000
    climate.observed_end_year = 2000
    climate.cli_fn = "main.cli"
    (tmp_path / "main.cli").write_text("main")

    provider_calls = {"prism": 0, "daymet": 0, "gridmet": 0}

    def _provider(name: str):
        def _inner(_lng: float, _lat: float, _start_year: int, _end_year: int):
            provider_calls[name] += 1
            return [2.0] * 12

        return _inner

    monkeypatch.setattr(
        "wepppy.nodb.core.climate_scaling_service.pyo3_cli_calculate_annual_monthlies",
        lambda _path: [1.0] * 12,
    )
    monkeypatch.setattr("wepppy.nodb.core.climate.get_prism_p_annual_monthlies", _provider("prism"))
    monkeypatch.setattr("wepppy.nodb.core.climate.get_daymet_p_annual_monthlies", _provider("daymet"))
    monkeypatch.setattr("wepppy.nodb.core.climate.get_gridmet_p_annual_monthlies", _provider("gridmet"))

    captured: dict[str, object] = {}

    def _capture_scale_monthlies(monthly_scale_factors, scale_func):
        captured["monthly_scale_factors"] = monthly_scale_factors
        captured["scale_func"] = scale_func

    climate._scale_precip_monthlies = _capture_scale_monthlies  # type: ignore[assignment]

    service._scale_precip_annual_monthlies(climate)

    assert provider_calls == {
        "prism": 1 if reference == "prism" else 0,
        "daymet": 1 if reference == "daymet" else 0,
        "gridmet": 1 if reference == "gridmet" else 0,
    }
    assert captured["monthly_scale_factors"] == [2.0] * 12
    assert captured["scale_func"] is pyo3_cli_p_scale_annual_monthlies
    assert (tmp_path / "reference_annual_monthlies.csv").exists()


def test_scale_precip_annual_monthlies_uses_one_when_original_month_is_zero(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = ClimateScalingService()
    climate = _ScalingClimate(tmp_path)
    climate.precip_scaling_reference = "prism"
    climate.observed_start_year = 2000
    climate.observed_end_year = 2000
    climate.cli_fn = "main.cli"
    (tmp_path / "main.cli").write_text("main")

    monkeypatch.setattr(
        "wepppy.nodb.core.climate_scaling_service.pyo3_cli_calculate_annual_monthlies",
        lambda _path: [0.0] + [2.0] * 11,
    )
    monkeypatch.setattr(
        "wepppy.nodb.core.climate.get_prism_p_annual_monthlies",
        lambda _lng, _lat, _start_year, _end_year: [5.0] + [4.0] * 11,
    )

    captured: dict[str, object] = {}

    def _capture_scale_monthlies(monthly_scale_factors, scale_func):
        captured["monthly_scale_factors"] = monthly_scale_factors
        captured["scale_func"] = scale_func

    climate._scale_precip_monthlies = _capture_scale_monthlies  # type: ignore[assignment]

    service._scale_precip_annual_monthlies(climate)

    monthly_scale_factors = captured["monthly_scale_factors"]
    assert isinstance(monthly_scale_factors, list)
    assert monthly_scale_factors[0] == 1.0
    assert monthly_scale_factors[1:] == [2.0] * 11
    assert captured["scale_func"] is pyo3_cli_p_scale_annual_monthlies

    csv_path = tmp_path / "reference_annual_monthlies.csv"
    assert csv_path.exists()
    rows = csv_path.read_text().strip().splitlines()
    assert rows[0] == "Year,Month,Reference,Scale_Factor"
    assert len(rows) == 13
