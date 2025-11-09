from __future__ import annotations

from collections.abc import Sequence

TIMEOUT: int
WMESQUE_ENDPOINT: str
WMESQUE2_ENDPOINT: str


def isfloat(x: object) -> bool: ...


def _wmesque1_retrieve(
    dataset: str,
    extent: Sequence[float],
    fname: str,
    cellsize: float,
    resample: str | None = ...,
) -> int: ...


def _b64url_to_bytes(s: str) -> bytes: ...


def wmesque_retrieve(
    dataset: str,
    extent: Sequence[float],
    fname: str,
    cellsize: float,
    resample: str | None = ...,
    v: int = ...,
    write_meta: bool = ...,
    wmesque_endpoint: str | None = ...,
) -> int: ...
