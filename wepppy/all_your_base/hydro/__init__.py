"""Hydrology utilities exported for compatibility with legacy callers."""

from __future__ import annotations

from .hydro import determine_wateryear, vec_determine_wateryear
from .objective_functions import (
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

__all__: list[str] = [
    'determine_wateryear',
    'vec_determine_wateryear',
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
