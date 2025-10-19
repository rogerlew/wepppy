from __future__ import annotations

from typing import Any, Tuple

__all__: list[str]


class GeoTransformer:
    transformer: Any
    reverse_transformer: Any

    def __init__(
        self,
        src_proj4: str | None = ...,
        src_epsg: int | None = ...,
        dst_proj4: str | None = ...,
        dst_epsg: int | None = ...,
    ) -> None: ...

    def transform(self, x: Any, y: Any) -> Tuple[Any, Any]: ...
    def reverse(self, x: Any, y: Any) -> Tuple[Any, Any]: ...
