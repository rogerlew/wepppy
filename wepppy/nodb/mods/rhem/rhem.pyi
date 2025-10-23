from __future__ import annotations

from typing import ClassVar, Dict, Optional, Tuple

from wepppy.nodb.base import NoDbBase

__all__: list[str] = ["RhemNoDbLockedException", "Rhem"]

CoverValues = Dict[str, float]
RhemRunResult = Tuple[bool, str, float]


class RhemNoDbLockedException(Exception):
    ...


class Rhem(NoDbBase):
    filename: ClassVar[str]
    __name__: ClassVar[str]

    def __new__(cls, *args: object, **kwargs: object) -> Rhem: ...

    def __init__(
        self,
        wd: str,
        cfg_fn: str,
        run_group: Optional[str] = ...,
        group_name: Optional[str] = ...,
    ) -> None: ...

    @property
    def rhem_dir(self) -> str: ...

    @property
    def runs_dir(self) -> str: ...

    @property
    def output_dir(self) -> str: ...

    @property
    def has_run(self) -> bool: ...

    def prep_hillslopes(self) -> None: ...

    def clean(self) -> None: ...

    def run_hillslopes(self) -> None: ...

    def report_loss(self) -> None: ...

    def report_return_periods(self) -> None: ...

    def run_wepp_hillslopes(self) -> None: ...
