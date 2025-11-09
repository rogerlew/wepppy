"""Smoke-test harness for instantiating reports against a run directory."""

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
        """Register a callable that builds a report for the given run directory.

        Args:
            name: Unique label for the report factory.
            factory: Callable that accepts a ``Path`` and returns a report instance.

        Raises:
            TypeError: If ``factory`` is not callable.
        """
        if not callable(factory):
            raise TypeError("ReportHarness.register expects a callable factory")
        self.registry[name] = factory

    def extend(self, entries: Mapping[str, ReportFactory] | Iterable[tuple[str, ReportFactory]]) -> None:
        """Bulk-register report factories.

        Args:
            entries: Either a mapping of ``name -> factory`` or an iterable of pairs.
        """
        if isinstance(entries, Mapping):
            items = entries.items()
        else:
            items = entries
        for name, factory in items:
            self.register(name, factory)

    def smoke(self, run_directory: Path, *, raise_on_error: bool = False) -> Dict[str, object]:
        """Execute each registered report factory against the run directory.

        Args:
            run_directory: Fully provisioned WEPP run directory to test against.
            raise_on_error: When ``True`` the first failure is re-raised to halt the run.

        Returns:
            Dict mapping the factory name to ``True`` on success or the captured exception.
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
