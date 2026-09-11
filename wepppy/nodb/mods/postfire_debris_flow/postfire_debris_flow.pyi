from typing import Any, Callable, ClassVar
from wepppy.nodb.base import NoDbBase

__all__: list[str] = ['PostfireDebrisFlow']

def empty_state() -> dict[str, Any]: ...

class PostfireDebrisFlow(NoDbBase):
    __name__: ClassVar[str]
    filename: ClassVar[str]
    def __init__(self, wd: str, cfg_fn: str, run_group: str | None = None, group_name: str | None = None) -> None: ...
    @property
    def state(self) -> dict[str, Any]: ...
    def change(self, callback: Callable[[dict[str, Any]], None]) -> None: ...
