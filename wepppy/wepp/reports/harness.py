from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, Iterable, Mapping, MutableMapping


ReportFactory = Callable[[Path], object]


@dataclass
class ReportHarness:
    """Lightweight registry that will be expanded into the full report test harness."""

    registry: MutableMapping[str, ReportFactory] = field(default_factory=dict)

    def register(self, name: str, factory: ReportFactory) -> None:
        """Register a callable that builds a report for the given run directory."""
        if not callable(factory):
            raise TypeError("ReportHarness.register expects a callable factory")
        self.registry[name] = factory

    def extend(self, entries: Mapping[str, ReportFactory] | Iterable[tuple[str, ReportFactory]]) -> None:
        """Bulk-register report factories."""
        if isinstance(entries, Mapping):
            items = entries.items()
        else:
            items = entries
        for name, factory in items:
            self.register(name, factory)

    def smoke(self, run_directory: Path, *, raise_on_error: bool = False) -> Dict[str, object]:
        """Execute each registered report factory against the run directory.

        Any exceptions are captured in the result map, allowing callers to
        inspect failures without raising immediately.
        """
        run_directory = Path(run_directory)
        results: Dict[str, object] = {}
        for name, factory in self.registry.items():
            try:
                factory(run_directory)
                results[name] = True
            except Exception as exc:  # pragma: no cover - smoke harness intentionally lenient
                results[name] = exc
                if raise_on_error:
                    raise
        return results

