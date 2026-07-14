from __future__ import annotations

from typing import Iterable, List

from wepppy.wepp.management.managements import Management

class ManagementMultipleOfeSynth:
    stack: List[Management]
    deduplicate_scenarios: bool

    def __init__(
        self,
        stack: Iterable[Management] | None = ...,
        *,
        deduplicate_scenarios: bool = ...,
    ) -> None: ...
    @property
    def description(self) -> str: ...
    @property
    def num_ofes(self) -> int: ...
    def write(self, dst_fn: str) -> None: ...
