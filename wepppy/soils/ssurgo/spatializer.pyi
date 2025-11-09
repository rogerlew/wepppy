from __future__ import annotations

from pathlib import Path
from typing import Callable, Iterable, Mapping, Optional, Tuple, Union

from .ssurgo import SurgoSoilCollection
from .surgo_map import SurgoMap

spatial_vars: Tuple[str, ...]


def classifier_factory(lookup: Mapping[str, int]) -> Callable[[Union[str, int]], int]: ...


class SurgoSpatializer:
    ssurgo_c: SurgoSoilCollection
    ssurgo_map: SurgoMap

    def __init__(self, ssurgo_c: SurgoSoilCollection, ssurgo_map: SurgoMap) -> None: ...
    def getFirstHorizonVar(self, mukey: int, var: str) -> float: ...
    def getHorizonsVar(
        self,
        mukey: int,
        var: str,
        aggregator: Callable[[Iterable[float]], float] = ...,
    ) -> float: ...
    def getMajorComponentVar(
        self,
        mukey: int,
        var: str,
        classifier: Optional[Callable[[Union[str, int]], int]] = ...,
    ) -> int: ...
    def spatialize_var(
        self,
        var: str,
        dst_fname: Union[str, Path],
        drivername: str = ...,
        nodata_value: float = ...,
    ) -> None: ...
