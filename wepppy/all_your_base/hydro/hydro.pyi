from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike, NDArray

__all__: list[str]


def determine_wateryear(year: int, julian: int | None = ..., month: int | None = ...) -> int: ...


def vec_determine_wateryear(
    year: ArrayLike,
    julian: ArrayLike | None = ...,
    month: ArrayLike | None = ...,
) -> NDArray[np.int_]: ...
