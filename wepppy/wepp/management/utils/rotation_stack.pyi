from __future__ import annotations

from typing import List, Sequence

from wepppy.wepp.management.managements import Management

class ManagementRotationSynth:
    managements: List[Management]
    nofe: int
    mode: str
    warnings: List[str]

    def __init__(self, managements: Sequence[Management], mode: str = ...) -> None: ...
    @property
    def description(self) -> str: ...
    def build(self, key: str | None = ..., desc: str | None = ...) -> Management: ...
