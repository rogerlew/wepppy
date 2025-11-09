from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional, Tuple, Union

import numpy as np


class NoValidSoilsException(Exception):
    __name__: str


class SurgoMap:
    data: np.ndarray
    transform: Tuple[float, ...]
    proj: str
    mukeys: list[int]
    fname: str

    def __init__(self, fname: Union[str, Path]) -> None: ...
    def _get_dominant(
        self,
        indices: Optional[Tuple[np.ndarray, np.ndarray]] = ...,
        valid_mukeys: Optional[Iterable[int]] = ...,
    ) -> Optional[int]: ...
