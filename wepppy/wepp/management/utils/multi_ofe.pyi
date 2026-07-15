from __future__ import annotations

from typing import Iterable, List

from wepppy.wepp.management.managements import Management

class ManagementMultipleOfeSynth:
    WEPP_HILLSLOPE_MAX_YEARLY_SCENARIOS: int
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
    def build(
        self,
        *,
        enforce_yearly_scenario_limit: bool = ...,
    ) -> Management: ...
    def render(
        self,
        *,
        enforce_yearly_scenario_limit: bool = ...,
    ) -> str: ...
    def write(self, dst_fn: str) -> None: ...
