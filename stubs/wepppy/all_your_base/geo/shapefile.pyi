from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any

NULL = 0
POINT = 1
POLYLINE = 3
POLYGON = 5
MULTIPOINT = 8
POINTZ = 11
POLYLINEZ = 13
POLYGONZ = 15
MULTIPOINTZ = 18
POINTM = 21
POLYLINEM = 23
POLYGONM = 25
MULTIPOINTM = 28
MULTIPATCH = 31

class Shape:
    shapeType: int
    points: list[list[float]]
    parts: list[int]
    partTypes: list[int]

    def __init__(
        self,
        shapeType: int = ...,
        points: Sequence[Sequence[float]] | None = ...,
        parts: Sequence[int] | None = ...,
        partTypes: Sequence[int] | None = ...,
    ) -> None: ...


class ShapeRecord:
    shape: Shape
    record: list[Any]


class ShapefileException(Exception): ...


class Reader:
    fields: list[tuple[str, str, int, int]]

    def __init__(self, *args: Any, **kwargs: Any) -> None: ...

    def iterShapes(self) -> Iterable[Shape]: ...

    def record(self, index: int) -> list[Any]: ...


class Writer:
    def __init__(self, *args: Any, **kwargs: Any) -> None: ...

    def save(self, target: str | None = ...) -> None: ...


def signed_area(coords: Sequence[Sequence[float]]) -> float: ...


def geojson_to_shape(geoj: dict[str, Any] | None) -> Shape: ...
