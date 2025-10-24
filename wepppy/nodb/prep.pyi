from __future__ import annotations

from typing import Any, ClassVar, Optional

from .base import NoDbBase

__all__ = [
    "PrepNoDbLockedException",
    "Prep",
]


class PrepNoDbLockedException(Exception):
    ...


class Prep(NoDbBase):
    filename: ClassVar[str]
    __name__: ClassVar[str]

    def __new__(cls, *args: Any, **kwargs: Any) -> "Prep": ...

    def __init__(
        self,
        wd: str,
        cfg_fn: str,
        run_group: Optional[str] = ...,
        group_name: Optional[str] = ...,
    ) -> None: ...

    @property
    def sbs_required(self) -> bool: ...

    @sbs_required.setter
    def sbs_required(self, value: bool) -> None: ...

    @property
    def has_sbs(self) -> bool: ...

    @has_sbs.setter
    def has_sbs(self, value: bool) -> None: ...

    def timestamp(self, key: str) -> None: ...

    def __setitem__(self, key: str, value: int) -> None: ...

    def __getitem__(self, key: str) -> Optional[int]: ...
