from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Callable, ClassVar, Dict, Mapping, Optional, OrderedDict as OrderedDictType, Sequence

from .base import NoDbBase

__all__ = [
    "converters",
    "precisions",
    "get_unit_class",
    "UnitTargetResolution",
    "UnitConversionMetadata",
    "UnitizedScalar",
    "UnitizedSequence",
    "UnitizedTable",
    "UnitizerNoDbLockedException",
    "Unitizer",
]

ConverterRegistry = Dict[str, Dict[tuple[str, str], Callable[[float], float]]]
PrecisionRegistry = OrderedDictType[str, OrderedDictType[str, int]]

converters: ConverterRegistry
precisions: PrecisionRegistry

def get_unit_class(in_units: Optional[str]) -> Optional[str]: ...

@dataclass(frozen=True)
class UnitTargetResolution:
    source_unit: Optional[str]
    target_unit: Optional[str]
    unit_class: Optional[str]
    precision_policy: Optional[int]
    pass_through_reason: Optional[str]

@dataclass(frozen=True)
class UnitConversionMetadata:
    source_unit: Optional[str]
    target_unit: Optional[str]
    unit_class: Optional[str]
    precision_policy: Optional[int]
    conversion_applied: bool
    pass_through_reason: Optional[str]

@dataclass(frozen=True)
class UnitizedScalar:
    value: Any
    metadata: UnitConversionMetadata

@dataclass(frozen=True)
class UnitizedSequence:
    values: list[Any]
    metadata: UnitConversionMetadata

@dataclass(frozen=True)
class UnitizedTable:
    data: Any
    metadata_by_column: Dict[str, UnitConversionMetadata]


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

    def set_preferences(self, kwds: Mapping[str, object], *, strict: bool = ...) -> Dict[str, str]: ...
    def preferences_fingerprint(self) -> str: ...
    def resolve_target_unit(
        self,
        source_unit: Optional[str],
        *,
        units_mode: str = ...,
        target_unit: Optional[str] = ...,
    ) -> UnitTargetResolution: ...
    def convert_scalar(
        self,
        value: Any,
        source_unit: Optional[str],
        *,
        units_mode: str = ...,
        target_unit: Optional[str] = ...,
    ) -> UnitizedScalar: ...
    def convert_sequence(
        self,
        values: Sequence[Any],
        source_unit: Optional[str],
        *,
        units_mode: str = ...,
        target_unit: Optional[str] = ...,
    ) -> UnitizedSequence: ...
    def convert_table(
        self,
        table: Any,
        column_units: Mapping[str, Optional[str]],
        *,
        units_mode: str = ...,
        target_units: Optional[Mapping[str, Optional[str]]] = ...,
    ) -> UnitizedTable: ...

    @staticmethod
    def context_processor_package() -> Dict[str, Callable[..., str]]: ...
