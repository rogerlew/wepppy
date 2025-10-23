from __future__ import annotations

from typing import ClassVar, Dict, Iterator, Optional, Tuple

from ...base import NoDbBase, TriggerEvents

from .treecanopy_map import TreecanopyMap

__all__: list[str] = [
    "TreecanopyNoDbLockedException",
    "nlcd_treecanopy_layers",
    "TreecanopyPointData",
    "Treecanopy",
]

TreecanopyDataset = str
TreecanopyData = Dict[int | str, float]
TreecanopyReport = Dict[str, float]

nlcd_treecanopy_layers: Tuple[TreecanopyDataset, ...]


class TreecanopyNoDbLockedException(Exception):
    ...


class TreecanopyPointData:
    treecanopy: Optional[float]

    def __init__(self, **kwds: Optional[float]) -> None: ...

    @property
    def isvalid(self) -> bool: ...


class Treecanopy(NoDbBase):
    __name__: ClassVar[str]
    filename: ClassVar[str]
    data: Optional[TreecanopyData]

    def __new__(cls, *args: object, **kwargs: object) -> Treecanopy: ...

    def __init__(
        self,
        wd: str,
        cfg_fn: str,
        run_group: Optional[str] = ...,
        group_name: Optional[str] = ...,
    ) -> None: ...

    @property
    def treecanopy_dir(self) -> str: ...

    @property
    def treecanopy_fn(self) -> str: ...

    def acquire_raster(self) -> None: ...

    def on(self, evt: TriggerEvents) -> None: ...

    def load_map(self) -> TreecanopyMap: ...

    def analyze(self) -> None: ...

    @property
    def report(self) -> Optional[TreecanopyReport]: ...

    def __iter__(self) -> Iterator[Tuple[int | str, TreecanopyPointData]]: ...
