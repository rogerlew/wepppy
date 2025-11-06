from __future__ import annotations

from collections import OrderedDict
from typing import Callable, ClassVar, Dict, Mapping, Optional, OrderedDict as OrderedDictType

from .base import NoDbBase

__all__ = [
    "converters",
    "precisions",
    "UnitizerNoDbLockedException",
    "Unitizer",
]

ConverterRegistry = Dict[str, Dict[tuple[str, str], Callable[[float], float]]]
PrecisionRegistry = OrderedDictType[str, OrderedDictType[str, int]]

converters: ConverterRegistry
precisions: PrecisionRegistry


class UnitizerNoDbLockedException(Exception):
    ...


class Unitizer(NoDbBase):
    filename: ClassVar[str]
    __name__: ClassVar[str]

    def __init__(
        self,
        wd: str,
        cfg_fn: str,
        run_group: Optional[str] = ...,
        group_name: Optional[str] = ...,
    ) -> None: ...

    @property
    def preferences(self) -> Dict[str, str]: ...

    @property
    def is_english(self) -> Optional[bool]: ...

    def set_preferences(self, kwds: Mapping[str, object]) -> Dict[str, str]: ...

    @staticmethod
    def context_processor_package() -> Dict[str, Callable[..., str]]: ...
