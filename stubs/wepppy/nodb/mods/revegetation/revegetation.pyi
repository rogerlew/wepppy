from __future__ import annotations

from typing import ClassVar, Dict, Optional, Tuple

from ...base import NoDbBase, TriggerEvents
import numpy as np
import numpy.typing as npt

__all__: list[str] = ["RevegetationNoDbLockedException", "Revegetation"]

CoverTransform = Dict[Tuple[str, str], npt.NDArray[np.float32]]


class RevegetationNoDbLockedException(Exception):
    ...


class Revegetation(NoDbBase):
    __name__: ClassVar[str]
    filename: ClassVar[str]
    _cover_transform_fn: str
    _user_defined_cover_transform: bool

    def __new__(cls, *args: object, **kwargs: object) -> Revegetation: ...

    def __init__(
        self,
        wd: str,
        cfg_fn: str,
        run_group: Optional[str] = ...,
        group_name: Optional[str] = ...,
    ) -> None: ...

    def validate_user_defined_cover_transform(self, fn: str) -> None: ...

    @property
    def user_defined_cover_transform(self) -> bool: ...

    def load_cover_transform(self, reveg_scenario: str) -> None: ...

    @property
    def cover_transform_fn(self) -> str: ...

    @cover_transform_fn.setter
    def cover_transform_fn(self, value: str) -> None: ...

    @property
    def revegetation_dir(self) -> str: ...

    @property
    def cover_transform_path(self) -> str: ...

    @property
    def cover_transform(self) -> Optional[CoverTransform]: ...

    def clean(self) -> None: ...

    def on(self, evt: TriggerEvents) -> None: ...
