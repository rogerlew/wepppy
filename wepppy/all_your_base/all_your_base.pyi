from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping
import json
from typing import Any, Final, NamedTuple, Optional, TypeAlias, Union

NCPU: Final[int]
geodata_dir: Final[str]
SCRATCH: Final[str]
IS_WINDOWS: Final[bool]


class RGBA(NamedTuple):
    red: int
    green: int
    blue: int
    alpha: int

    def tohex(self) -> str: ...

    @classmethod
    def random(cls) -> RGBA: ...


class NumpyEncoder(json.JSONEncoder):
    def default(self, obj: Any) -> Any: ...


RangeType: TypeAlias = Union[int, tuple[int, int]]


def cmyk_to_rgb(c: float, m: float, y: float, k: float) -> tuple[float, float, float]: ...


def flatten(iterable: Iterable[Any]) -> Iterator[Any]: ...


def find_ranges(iterable: Iterable[int], as_str: bool = False) -> Union[list[RangeType], str]: ...


def clamp(x: float, minimum: float, maximum: float) -> float: ...


def clamp01(x: float) -> float: ...


def cp_chmod(src: str, dst: str, mode: int) -> None: ...


def splitall(path: str) -> list[str]: ...


def isint(x: Any) -> bool: ...


def isfloat(f: Any) -> bool: ...


def isbool(x: Any) -> bool: ...


def isnan(f: Any) -> bool: ...


def isinf(f: Any) -> bool: ...


def try_parse(f: Any) -> Any: ...


def try_parse_float(f: Any, default: float = ...) -> float: ...


def parse_name(colname: str) -> str: ...


def parse_units(colname: str) -> Optional[str]: ...


class RowData:
    row: Mapping[str, Any]

    def __init__(self, row: Mapping[str, Any]) -> None: ...

    def __getitem__(self, item: str) -> Any: ...

    def __iter__(self) -> Iterator[tuple[Any, Optional[str]]]: ...


def c_to_f(x: float) -> float: ...


def f_to_c(x: float) -> float: ...
