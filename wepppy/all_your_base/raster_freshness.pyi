from dataclasses import dataclass, field
from os import PathLike
from typing import Iterable

__all__ = ["RasterDependencyObservation", "observe_raster_dependencies",
           "raster_dependency_signature", "raster_dependency_signatures"]

@dataclass(frozen=True)
class RasterDependencyObservation:
    signature: tuple
    read_guard: tuple = field(compare=False, hash=False)
    def check_unchanged(self) -> None: ...

def observe_raster_dependencies(paths: Iterable[str | PathLike[str]]) -> RasterDependencyObservation | None: ...
def raster_dependency_signature(path: str | PathLike[str]) -> tuple | None: ...
def raster_dependency_signatures(paths: Iterable[str | PathLike[str]]) -> tuple | None: ...

# Internal same-call inventory validation used by Geneva.
def _companions(path: str) -> tuple[tuple[str, str], ...]: ...
