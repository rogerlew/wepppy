"""Objective functions for evaluating hydrologic simulations."""

from __future__ import annotations

import logging
from typing import Callable, List, Tuple

import numpy as np
from numpy.typing import ArrayLike, NDArray

__all__ = [
    'agreementindex',
    'bias',
    'calculate_all_functions',
    'correlationcoefficient',
    'covariance',
    'decomposed_mse',
    'kge',
    'kge_non_parametric',
    'log_p',
    'lognashsutcliffe',
    'mae',
    'mse',
    'nashsutcliffe',
    'pbias',
    'rmse',
    'rrmse',
    'rsquared',
    'rsr',
    'volume_error',
]

logger = logging.getLogger(__name__)


def _ensure_arrays(
    evaluation: ArrayLike,
    simulation: ArrayLike,
) -> Tuple[NDArray[np.float_], NDArray[np.float_]] | None:
    obs = np.asarray(evaluation, dtype=float)
    sim = np.asarray(simulation, dtype=float)
    if obs.shape != sim.shape:
        logger.warning('evaluation and simulation sequences must share the same shape.')
        return None
    return obs, sim


def bias(evaluation: ArrayLike, simulation: ArrayLike) -> float:
    """Mean bias between observed and simulated values."""
    arrays = _ensure_arrays(evaluation, simulation)
    if arrays is None:
        return float('nan')
    obs, sim = arrays
    return float(np.nanmean(obs - sim))


def pbias(evaluation: ArrayLike, simulation: ArrayLike) -> float:
    """Percent bias."""
    arrays = _ensure_arrays(evaluation, simulation)
    if arrays is None:
        return float('nan')
    obs, sim = arrays
    denominator = np.nansum(obs)
    if denominator == 0:
        return float('nan')
    return float(100.0 * np.nansum(sim - obs) / denominator)


def nashsutcliffe(evaluation: ArrayLike, simulation: ArrayLike) -> float:
    """Nash–Sutcliffe model efficiency coefficient."""
    arrays = _ensure_arrays(evaluation, simulation)
    if arrays is None:
        return float('nan')
    obs, sim = arrays
    mean_obs = np.nanmean(obs)
    numerator = np.nansum((obs - sim) ** 2)
    denominator = np.nansum((obs - mean_obs) ** 2)
    return float(1.0 - numerator / denominator)


def lognashsutcliffe(
    evaluation: ArrayLike,
    simulation: ArrayLike,
    epsilon: float = 0.0,
) -> float:
    """Log-transformed Nash–Sutcliffe efficiency."""
    arrays = _ensure_arrays(evaluation, simulation)
    if arrays is None:
        return float('nan')
    obs, sim = arrays
    obs = np.asarray(obs, dtype=float) + epsilon
    sim = np.asarray(sim, dtype=float) + epsilon
    numerator = np.nansum((np.log(obs) - np.log(sim)) ** 2)
    denominator = np.nansum((np.log(obs) - np.nanmean(np.log(obs))) ** 2)
    return float(1.0 - numerator / denominator)


def log_p(evaluation: ArrayLike, simulation: ArrayLike) -> float:
    """Logarithmic probability distribution."""
    arrays = _ensure_arrays(evaluation, simulation)
    if arrays is None:
        return float('nan')
    obs, sim = arrays
    scale = max(np.nanmean(obs) / 10.0, 0.01)
    residual = (obs - sim) / scale
    normpdf = -residual ** 2 / 2.0 - np.log(np.sqrt(2.0 * np.pi))
    return float(np.nanmean(normpdf))


def correlationcoefficient(evaluation: ArrayLike, simulation: ArrayLike) -> float:
    """Pearson correlation coefficient."""
    arrays = _ensure_arrays(evaluation, simulation)
    if arrays is None:
        return float('nan')
    obs, sim = arrays
    return float(np.corrcoef(obs, sim)[0, 1])


def rsquared(evaluation: ArrayLike, simulation: ArrayLike) -> float:
    """Coefficient of determination (R²)."""
    corr = correlationcoefficient(evaluation, simulation)
    return float(corr ** 2)


def mse(evaluation: ArrayLike, simulation: ArrayLike) -> float:
    """Mean squared error."""
    arrays = _ensure_arrays(evaluation, simulation)
    if arrays is None:
        return float('nan')
    obs, sim = arrays
    return float(np.nanmean((obs - sim) ** 2))


def rmse(evaluation: ArrayLike, simulation: ArrayLike) -> float:
    """Root mean squared error."""
    value = mse(evaluation, simulation)
    return float(np.sqrt(value))


def mae(evaluation: ArrayLike, simulation: ArrayLike) -> float:
    """Mean absolute error."""
    arrays = _ensure_arrays(evaluation, simulation)
    if arrays is None:
        return float('nan')
    obs, sim = arrays
    return float(np.nanmean(np.abs(sim - obs)))


def rrmse(evaluation: ArrayLike, simulation: ArrayLike) -> float:
    """Relative root mean squared error."""
    arrays = _ensure_arrays(evaluation, simulation)
    if arrays is None:
        return float('nan')
    obs, _ = arrays
    rmse_value = rmse(evaluation, simulation)
    mean_obs = np.nanmean(obs)
    return float(rmse_value / mean_obs)


def agreementindex(evaluation: ArrayLike, simulation: ArrayLike) -> float:
    """Willmott agreement index."""
    arrays = _ensure_arrays(evaluation, simulation)
    if arrays is None:
        return float('nan')
    obs, sim = arrays
    numerator = np.nansum((obs - sim) ** 2)
    denominator = np.nansum((np.abs(sim - np.nanmean(obs)) + np.abs(obs - np.nanmean(obs))) ** 2)
    return float(1.0 - numerator / denominator)


def covariance(evaluation: ArrayLike, simulation: ArrayLike) -> float:
    """Sample covariance between observed and simulated series."""
    arrays = _ensure_arrays(evaluation, simulation)
    if arrays is None:
        return float('nan')
    obs, sim = arrays
    obs_mean = np.nanmean(obs)
    sim_mean = np.nanmean(sim)
    return float(np.nanmean((obs - obs_mean) * (sim - sim_mean)))


def decomposed_mse(evaluation: ArrayLike, simulation: ArrayLike) -> float:
    """Kobayashi and Salam decomposed mean squared error."""
    arrays = _ensure_arrays(evaluation, simulation)
    if arrays is None:
        return float('nan')
    obs, sim = arrays
    bias_sq = bias(obs, sim) ** 2
    obs_std = float(np.nanstd(obs))
    sim_std = float(np.nanstd(sim))
    sdsd = (obs_std - sim_std) ** 2
    lcs = 2.0 * obs_std * sim_std * (1.0 - correlationcoefficient(obs, sim))
    return float(bias_sq + sdsd + lcs)


def kge(
    evaluation: ArrayLike,
    simulation: ArrayLike,
    return_all: bool = False,
) -> float | Tuple[float, float, float, float]:
    """Kling–Gupta efficiency."""
    arrays = _ensure_arrays(evaluation, simulation)
    if arrays is None:
        return float('nan')
    obs, sim = arrays
    cc = float(np.corrcoef(obs, sim)[0, 1])
    alpha = float(np.nanstd(sim) / np.nanstd(obs))
    beta = float(np.nansum(sim) / np.nansum(obs))
    kge_value = float(1.0 - np.sqrt((cc - 1.0) ** 2 + (alpha - 1.0) ** 2 + (beta - 1.0) ** 2))
    if return_all:
        return kge_value, cc, alpha, beta
    return kge_value


def _spearmann_corr(evaluation: ArrayLike, simulation: ArrayLike) -> float:
    obs = np.asarray(evaluation, dtype=float)
    sim = np.asarray(simulation, dtype=float)
    ranks_x = np.argsort(np.argsort(obs)) + 1
    ranks_y = np.argsort(np.argsort(sim)) + 1
    mean_x = np.nanmean(ranks_x)
    mean_y = np.nanmean(ranks_y)
    numerator = np.nansum((ranks_x - mean_x) * (ranks_y - mean_y))
    denominator = np.sqrt(np.nansum((ranks_x - mean_x) ** 2) * np.nansum((ranks_y - mean_y) ** 2))
    return float(numerator / denominator)


def kge_non_parametric(
    evaluation: ArrayLike,
    simulation: ArrayLike,
    return_all: bool = False,
) -> float | Tuple[float, float, float, float]:
    """Non-parametric Kling–Gupta efficiency."""
    arrays = _ensure_arrays(evaluation, simulation)
    if arrays is None:
        return float('nan')
    obs, sim = arrays
    cc = _spearmann_corr(obs, sim)
    fdc_sim = np.sort(sim / (np.nanmean(sim) * len(sim)))
    fdc_obs = np.sort(obs / (np.nanmean(obs) * len(obs)))
    alpha = float(1.0 - 0.5 * np.nanmean(np.abs(fdc_sim - fdc_obs)))
    beta = float(np.nanmean(sim) / np.nanmean(obs))
    kge_value = float(1.0 - np.sqrt((cc - 1.0) ** 2 + (alpha - 1.0) ** 2 + (beta - 1.0) ** 2))
    if return_all:
        return kge_value, cc, alpha, beta
    return kge_value


def rsr(evaluation: ArrayLike, simulation: ArrayLike) -> float:
    """RMSE-observations standard deviation ratio."""
    arrays = _ensure_arrays(evaluation, simulation)
    if arrays is None:
        return float('nan')
    obs, _ = arrays
    return float(rmse(evaluation, simulation) / np.nanstd(obs))


def volume_error(evaluation: ArrayLike, simulation: ArrayLike) -> float:
    """Volume error between the observed and simulated series."""
    arrays = _ensure_arrays(evaluation, simulation)
    if arrays is None:
        return float('nan')
    obs, sim = arrays
    denominator = np.nansum(obs)
    if denominator == 0:
        return float('nan')
    return float(np.nansum(sim - obs) / denominator)


_ALL_FUNCTIONS: Tuple[Callable[[ArrayLike, ArrayLike], float], ...] = (
    agreementindex,
    bias,
    correlationcoefficient,
    covariance,
    decomposed_mse,
    kge,
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


def calculate_all_functions(
    evaluation: ArrayLike,
    simulation: ArrayLike,
) -> List[Tuple[str, float]]:
    """Evaluate every supported objective function."""
    results: List[Tuple[str, float]] = []
    for func in _ALL_FUNCTIONS:
        try:
            value = func(evaluation, simulation)
        except Exception:  # pragma: no cover - guard against unexpected errors
            value = float('nan')
        results.append((func.__name__, float(value)))
    return results
