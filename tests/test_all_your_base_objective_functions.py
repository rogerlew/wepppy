import math
from typing import List, Tuple

import numpy as np
import pytest

from wepppy.all_your_base.hydro.objective_functions import (
    agreementindex,
    bias,
    calculate_all_functions,
    correlationcoefficient,
    covariance,
    decomposed_mse,
    kge,
    kge_non_parametric,
    log_p,
    lognashsutcliffe,
    mae,
    mse,
    nashsutcliffe,
    pbias,
    rmse,
    rrmse,
    rsquared,
    rsr,
    volume_error,
)


EVALUATION = np.array([1.0, 2.0, 3.0, 4.0])
SIMULATION = np.array([1.1, 1.9, 3.2, 3.8])


def _spearman_manual(x: np.ndarray, y: np.ndarray) -> float:
    ranks_x = np.argsort(np.argsort(x)) + 1
    ranks_y = np.argsort(np.argsort(y)) + 1
    mean_x = np.nanmean(ranks_x)
    mean_y = np.nanmean(ranks_y)
    numerator = np.nansum((ranks_x - mean_x) * (ranks_y - mean_y))
    denominator = math.sqrt(
        np.nansum((ranks_x - mean_x) ** 2) * np.nansum((ranks_y - mean_y) ** 2)
    )
    return float(numerator / denominator)


def test_bias_and_pbias() -> None:
    expected_bias = float(np.nanmean(EVALUATION - SIMULATION))
    expected_pbias = float(100.0 * np.nansum(SIMULATION - EVALUATION) / np.nansum(EVALUATION))
    assert bias(EVALUATION, SIMULATION) == pytest.approx(expected_bias)
    assert pbias(EVALUATION, SIMULATION) == pytest.approx(expected_pbias)


def test_nash_variants() -> None:
    mean_obs = np.nanmean(EVALUATION)
    numerator = np.nansum((EVALUATION - SIMULATION) ** 2)
    denominator = np.nansum((EVALUATION - mean_obs) ** 2)
    expected_nash = 1.0 - numerator / denominator
    assert nashsutcliffe(EVALUATION, SIMULATION) == pytest.approx(expected_nash)

    expected_log_nash = 1.0 - np.nansum((np.log(EVALUATION) - np.log(SIMULATION)) ** 2) / np.nansum(
        (np.log(EVALUATION) - np.nanmean(np.log(EVALUATION))) ** 2
    )
    assert lognashsutcliffe(EVALUATION, SIMULATION) == pytest.approx(expected_log_nash)


def test_log_probability_metric() -> None:
    scale = max(np.nanmean(EVALUATION) / 10.0, 0.01)
    residual = (EVALUATION - SIMULATION) / scale
    normpdf = -residual ** 2 / 2.0 - np.log(np.sqrt(2.0 * np.pi))
    expected = np.nanmean(normpdf)
    assert log_p(EVALUATION, SIMULATION) == pytest.approx(expected)


def test_correlation_and_covariance_metrics() -> None:
    expected_corr = np.corrcoef(EVALUATION, SIMULATION)[0, 1]
    assert correlationcoefficient(EVALUATION, SIMULATION) == pytest.approx(expected_corr)
    assert rsquared(EVALUATION, SIMULATION) == pytest.approx(expected_corr ** 2)

    expected_covariance = np.nanmean(
        (EVALUATION - np.nanmean(EVALUATION)) * (SIMULATION - np.nanmean(SIMULATION))
    )
    assert covariance(EVALUATION, SIMULATION) == pytest.approx(expected_covariance)


def test_error_metrics() -> None:
    expected_mse = np.nanmean((EVALUATION - SIMULATION) ** 2)
    expected_rmse = math.sqrt(expected_mse)
    expected_mae = np.nanmean(np.abs(SIMULATION - EVALUATION))
    expected_rrmse = expected_rmse / np.nanmean(EVALUATION)

    assert mse(EVALUATION, SIMULATION) == pytest.approx(expected_mse)
    assert rmse(EVALUATION, SIMULATION) == pytest.approx(expected_rmse)
    assert mae(EVALUATION, SIMULATION) == pytest.approx(expected_mae)
    assert rrmse(EVALUATION, SIMULATION) == pytest.approx(expected_rrmse)


def test_agreement_index_and_decomposed_mse() -> None:
    mean_obs = np.nanmean(EVALUATION)
    numerator = np.nansum((EVALUATION - SIMULATION) ** 2)
    denominator = np.nansum((np.abs(SIMULATION - mean_obs) + np.abs(EVALUATION - mean_obs)) ** 2)
    expected_agreement = 1.0 - numerator / denominator
    assert agreementindex(EVALUATION, SIMULATION) == pytest.approx(expected_agreement)

    bias_term = bias(EVALUATION, SIMULATION) ** 2
    obs_std = float(np.nanstd(EVALUATION))
    sim_std = float(np.nanstd(SIMULATION))
    sdsd = (obs_std - sim_std) ** 2
    corr = correlationcoefficient(EVALUATION, SIMULATION)
    lcs = 2.0 * obs_std * sim_std * (1.0 - corr)
    expected_decomposed = bias_term + sdsd + lcs
    assert decomposed_mse(EVALUATION, SIMULATION) == pytest.approx(expected_decomposed)


def test_kge_variants() -> None:
    value_only = kge(EVALUATION, SIMULATION)
    value_with_components = kge(EVALUATION, SIMULATION, return_all=True)
    assert value_only == pytest.approx(value_with_components[0])

    cc = np.corrcoef(EVALUATION, SIMULATION)[0, 1]
    alpha = np.nanstd(SIMULATION) / np.nanstd(EVALUATION)
    beta = np.nansum(SIMULATION) / np.nansum(EVALUATION)
    expected_kge = 1.0 - math.sqrt((cc - 1.0) ** 2 + (alpha - 1.0) ** 2 + (beta - 1.0) ** 2)
    assert value_only == pytest.approx(expected_kge)

    cc_np = _spearman_manual(EVALUATION, SIMULATION)
    fdc_sim = np.sort(SIMULATION / (np.nanmean(SIMULATION) * len(SIMULATION)))
    fdc_obs = np.sort(EVALUATION / (np.nanmean(EVALUATION) * len(EVALUATION)))
    alpha_np = 1.0 - 0.5 * np.nanmean(np.abs(fdc_sim - fdc_obs))
    beta_np = np.nanmean(SIMULATION) / np.nanmean(EVALUATION)
    expected_kge_np = 1.0 - math.sqrt((cc_np - 1.0) ** 2 + (alpha_np - 1.0) ** 2 + (beta_np - 1.0) ** 2)

    value_non_parametric = kge_non_parametric(EVALUATION, SIMULATION)
    assert value_non_parametric == pytest.approx(expected_kge_np)

    value_non_parametric_full = kge_non_parametric(EVALUATION, SIMULATION, return_all=True)
    assert value_non_parametric_full[0] == pytest.approx(expected_kge_np)
    assert value_non_parametric_full[1:] == pytest.approx((cc_np, alpha_np, beta_np))


def test_rsr_and_volume_error() -> None:
    expected_rsr = rmse(EVALUATION, SIMULATION) / np.nanstd(EVALUATION)
    assert rsr(EVALUATION, SIMULATION) == pytest.approx(expected_rsr)

    expected_volume_error = np.nansum(SIMULATION - EVALUATION) / np.nansum(EVALUATION)
    assert volume_error(EVALUATION, SIMULATION) == pytest.approx(expected_volume_error)


def test_calculate_all_functions_reports_every_metric() -> None:
    results = calculate_all_functions(EVALUATION, SIMULATION)
    names = [name for name, _ in results]
    expected_names = {
        "agreementindex",
        "bias",
        "correlationcoefficient",
        "covariance",
        "decomposed_mse",
        "kge",
        "log_p",
        "lognashsutcliffe",
        "mae",
        "mse",
        "nashsutcliffe",
        "pbias",
        "rmse",
        "rrmse",
        "rsquared",
        "rsr",
        "volume_error",
    }
    assert set(names) == expected_names

    result_map = dict(results)
    for metric in expected_names:
        assert isinstance(result_map[metric], float)


def test_metrics_return_nan_on_shape_mismatch() -> None:
    mismatched = [1.0, 2.0]
    assert math.isnan(bias(EVALUATION, mismatched))
