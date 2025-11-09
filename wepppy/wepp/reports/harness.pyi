from __future__ import annotations

from pathlib import Path
from typing import Callable, Dict, Iterable, Mapping, MutableMapping, Protocol


class Report(Protocol):
    header: list[str]


ReportFactory = Callable[[Path], Report]


class ReportHarness:
    registry: MutableMapping[str, ReportFactory]

    def __init__(self, registry: MutableMapping[str, ReportFactory] | None = ...) -> None: ...

    def register(self, name: str, factory: ReportFactory) -> None: ...

    def extend(self, entries: Mapping[str, ReportFactory] | Iterable[tuple[str, ReportFactory]]) -> None: ...

    def smoke(self, run_directory: Path, *, raise_on_error: bool = ...) -> Dict[str, object]: ...
