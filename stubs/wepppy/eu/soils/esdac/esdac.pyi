from __future__ import annotations

from collections.abc import Sequence

from wepppy.wepp.soils import HorizonMixin

TextureDescriptor = dict[str, float]

def _attr_fmt(attr: str) -> str: ...


class Horizon(HorizonMixin):
    clay: float | None
    sand: float | None
    silt: float | None
    om: float | None
    bd: float | None
    gravel: float | None
    _cec: str | None
    depth: float | None

    def __init__(
        self,
        clay: float | None = ...,
        sand: float | None = ...,
        silt: float | None = ...,
        om: float | None = ...,
        bd: float | None = ...,
        gravel: float | None = ...,
        _cec: str | None = ...,
        depth: float | None = ...,
    ) -> None: ...

    @property
    def vfs(self) -> float | None: ...

    @property
    def cec(self) -> float: ...

    @property
    def smr(self) -> float | None: ...

    def as_dict(self) -> dict[str, float | None]: ...


class ESDAC:
    catalog: dict[str, str]
    rats: dict[str, dict[str, str]]
    derived_db_catalog: dict[str, str]

    def __init__(self) -> None: ...

    @staticmethod
    def _rat_extract(fn: str) -> dict[str, str]: ...

    def query(
        self,
        lng: float,
        lat: float,
        attrs: Sequence[str],
    ) -> dict[str, tuple[str, str, str]]: ...

    def query_derived_db(
        self,
        lng: float,
        lat: float,
        attrs: Sequence[str],
    ) -> dict[str, float | None]: ...

    def build_wepp_soil(
        self,
        lng: float,
        lat: float,
        soils_dir: str = ...,
        res_lyr_ksat_threshold: float = ...,
        ksflag: int = ...,
    ) -> tuple[str, Horizon, str]: ...
