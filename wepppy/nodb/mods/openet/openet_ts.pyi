from __future__ import annotations

from typing import Any, ClassVar, Dict, Optional

from wepppy.nodb.base import NoDbBase, TriggerEvents

__all__: list[str] = ["OpenETNoDbLockedException", "OpenET_TS"]


class OpenETNoDbLockedException(Exception):
    ...


class OpenET_TS(NoDbBase):
    __name__: ClassVar[str]
    filename: ClassVar[str]
    data: Optional[Any]

    def __new__(cls, *args: object, **kwargs: object) -> OpenET_TS: ...

    def __init__(
        self,
        wd: str,
        cfg_fn: str,
        run_group: Optional[str] = ...,
        group_name: Optional[str] = ...,
    ) -> None: ...

    def __getstate__(self) -> Dict[str, Any]: ...

    @classmethod
    def _post_instance_loaded(cls, instance: OpenET_TS) -> OpenET_TS: ...

    @property
    def openet_start_year(self) -> Optional[int]: ...

    @openet_start_year.setter
    def openet_start_year(self, value: int) -> None: ...

    @property
    def openet_end_year(self) -> Optional[int]: ...

    @openet_end_year.setter
    def openet_end_year(self, value: int) -> None: ...

    @property
    def openet_dir(self) -> str: ...

    @property
    def openet_parquet_path(self) -> str: ...

    @property
    def openet_individual_dir(self) -> str: ...

    def acquire_timeseries(
        self,
        start_year: Optional[int] = ...,
        end_year: Optional[int] = ...,
        max_workers: int = ...,
    ) -> None: ...

    def analyze(self) -> None: ...

    def on(self, evt: TriggerEvents) -> None: ...
