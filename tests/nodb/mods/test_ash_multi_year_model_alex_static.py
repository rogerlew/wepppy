from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from wepppy.all_your_base.dateutils import YearlessDate
from wepppy.nodb.mods.ash_transport import ash_multi_year_model_alex as alex_model

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("previous_runoff_mm", "runoff_increment_mm", "expected_transport_tonspha"),
    (
        (0.0, 0.0, 0.0),
        (0.0, 1.0, 1.9032516392808096),
        (1.0, 1.0, 1.722133299159554),
    ),
)
def test_static_transport_matches_approved_vectors(
    previous_runoff_mm: float,
    runoff_increment_mm: float,
    expected_transport_tonspha: float,
) -> None:
    transport = alex_model._calc_static_transport_increment(
        initial_transport_capacity=2.0,
        depletion_coefficient=0.1,
        previous_cumulative_runoff_mm=previous_runoff_mm,
        runoff_increment_mm=runoff_increment_mm,
    )

    assert transport == pytest.approx(expected_transport_tonspha)


def _run_static_model(
    *,
    initial_ash_tonspha: float = 20.0,
    runoff_mm: tuple[float, ...] = (0.0, 6.0, 6.0, 6.0),
    initial_transport_capacity: float = 2.0,
    depletion_coefficient: float = 0.1,
    slope: float = 0.05,
    organic_matter: float = 0.04,
    beta_coefficients: tuple[float, float, float, float] = (
        14.33,
        0.22,
        5.85,
        -0.36,
    ),
) -> pd.DataFrame:
    size = len(runoff_mm)
    hill_wat_df = pd.DataFrame(
        {
            "year": np.full(size, 2020),
            "month": np.full(size, 8),
            "day_of_month": np.arange(4, 4 + size),
            "julian": np.arange(217, 217 + size),
            "P": runoff_mm,
            "RM": runoff_mm,
            "Q": runoff_mm,
            "Total-Soil Water": np.zeros(size),
            "Snow-Water": np.zeros(size),
        }
    )
    cli_df = pd.DataFrame({"w-vl": np.zeros(size)})

    model = alex_model.WhiteAshModel()
    model.transport_mode = "static"
    model.initranscap = initial_transport_capacity
    model.depletcoeff = depletion_coefficient
    model.decomp_fac = 0.0
    model.roughness_limit = 0.0
    model.run_wind_transport = False
    model.slope = slope
    model.org_mat = organic_matter
    model.beta0, model.beta1, model.beta2, model.beta3 = beta_coefficients

    return model._run_ash_model_until_gone(
        fire_date=YearlessDate(8, 4),
        hill_wat_df=hill_wat_df,
        cli_df=cli_df,
        ini_ash_load=initial_ash_tonspha,
        start_index=0,
        year0=2020,
    )


def test_static_model_uses_scalar_cumulative_runoff_and_balances_mass() -> None:
    with pytest.warns(UserWarning, match="ash transportable"):
        result = _run_static_model()

    transport = result["transport (tonne/ha)"].to_numpy()
    water_transport = result["water_transport (tonne/ha)"].to_numpy()
    ash_runoff = result["ash_runoff (mm)"].to_numpy()
    cumulative_runoff = result["cum_ash_runoff (mm)"].to_numpy()

    for i in range(1, len(result)):
        expected = alex_model._calc_static_transport_increment(
            2.0,
            0.1,
            cumulative_runoff[i - 1],
            ash_runoff[i],
        )
        assert transport[i] == pytest.approx(expected)

    assert np.all(water_transport >= 0.0)
    np.testing.assert_allclose(
        20.0 - result["remaining_ash (tonne/ha)"],
        result["cum_ash_transport (tonne/ha)"]
        + result["cum_ash_decomp (tonne/ha)"],
    )


def test_static_model_is_independent_of_dynamic_only_parameters() -> None:
    with pytest.warns(UserWarning, match="ash transportable"):
        baseline = _run_static_model()
    with pytest.warns(UserWarning, match="ash transportable"):
        changed = _run_static_model(
            slope=0.9,
            organic_matter=0.9,
            beta_coefficients=(-2.0, 3.0, -4.0, 0.5),
        )

    columns = [
        "transport (tonne/ha)",
        "water_transport (tonne/ha)",
        "ash_transport (tonne/ha)",
        "remaining_ash (tonne/ha)",
        "cum_ash_transport (tonne/ha)",
    ]
    pd.testing.assert_frame_equal(baseline[columns], changed[columns])


def test_static_model_clips_transport_to_available_ash() -> None:
    result = _run_static_model(
        initial_ash_tonspha=4.0,
        runoff_mm=(0.0, 10.0, 0.0),
        initial_transport_capacity=100.0,
    )

    assert result.loc[1, "transport (tonne/ha)"] > 4.0
    assert result.loc[1, "water_transport (tonne/ha)"] == pytest.approx(4.0)
    assert result.loc[1, "remaining_ash (tonne/ha)"] == pytest.approx(0.0)
    assert result.loc[1, "cum_ash_transport (tonne/ha)"] == pytest.approx(4.0)
