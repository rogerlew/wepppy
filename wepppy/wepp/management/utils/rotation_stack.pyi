from __future__ import annotations

from pathlib import Path
from typing import List, Sequence

from wepppy.wepp.management.managements import Management

__all__ = ['ManagementRotationSynth']

class ManagementRotationSynth:
    managements: List[Management]
    nofe: int
    mode: str
    warnings: List[str]

    def __init__(self, managements: Sequence[Management], mode: str = ...) -> None: ...
    @property
    def description(self) -> str: ...
    def build(self, key: str | None = ..., desc: str | None = ...) -> Management: ...
    def write(
        self,
        dst_path: str | Path,
        key: str | None = ...,
        desc: str | None = ...,
        include_header: bool = ...,
    ) -> Path: ...
