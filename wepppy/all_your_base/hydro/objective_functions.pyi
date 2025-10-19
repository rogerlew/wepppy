from __future__ import annotations

from typing import Callable, List, Tuple

from numpy.typing import ArrayLike

__all__: list[str]


def agreementindex(evaluation: ArrayLike, simulation: ArrayLike) -> float: ...


def bias(evaluation: ArrayLike, simulation: ArrayLike) -> float: ...


def calculate_all_functions(
    evaluation: ArrayLike,
    simulation: ArrayLike,
) -> List[Tuple[str, float]]: ...


def correlationcoefficient(evaluation: ArrayLike, simulation: ArrayLike) -> float: ...


def covariance(evaluation: ArrayLike, simulation: ArrayLike) -> float: ...


def decomposed_mse(evaluation: ArrayLike, simulation: ArrayLike) -> float: ...


def kge(
    evaluation: ArrayLike,
    simulation: ArrayLike,
    return_all: bool = ...,
) -> float | Tuple[float, float, float, float]: ...


def kge_non_parametric(
    evaluation: ArrayLike,
    simulation: ArrayLike,
    return_all: bool = ...,
) -> float | Tuple[float, float, float, float]: ...


def log_p(evaluation: ArrayLike, simulation: ArrayLike) -> float: ...


def lognashsutcliffe(
    evaluation: ArrayLike,
    simulation: ArrayLike,
    epsilon: float = ...,
) -> float: ...


def mae(evaluation: ArrayLike, simulation: ArrayLike) -> float: ...


def mse(evaluation: ArrayLike, simulation: ArrayLike) -> float: ...


def nashsutcliffe(evaluation: ArrayLike, simulation: ArrayLike) -> float: ...


def pbias(evaluation: ArrayLike, simulation: ArrayLike) -> float: ...


def rmse(evaluation: ArrayLike, simulation: ArrayLike) -> float: ...


def rrmse(evaluation: ArrayLike, simulation: ArrayLike) -> float: ...


def rsquared(evaluation: ArrayLike, simulation: ArrayLike) -> float: ...


def rsr(evaluation: ArrayLike, simulation: ArrayLike) -> float: ...


def volume_error(evaluation: ArrayLike, simulation: ArrayLike) -> float: ...
