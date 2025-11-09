"""Resolve run metadata and catalogs for query-engine execution."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from wepppy.query_engine.catalog import DatasetCatalog, load_catalog


@dataclass(slots=True)
class RunContext:
    """Activation metadata for a runid and optional scenario."""

    runid: str
    base_dir: Path
    scenario: str | None
    catalog: DatasetCatalog


def resolve_run_context(runid: str, *, scenario: str | None = None, auto_activate: bool = True) -> RunContext:
    """Load the query-engine catalog for a run (and optional scenario).

    Args:
        runid: Path or slug to the WEPP run directory.
        scenario: Optional scenario slug, relative to the run root.
        auto_activate: When True, trigger `activate_query_engine` if needed.

    Returns:
        RunContext with resolved base directory and DatasetCatalog.

    Raises:
        FileNotFoundError: If the run directory or scenario path does not exist.
    """
    base = Path(runid).expanduser()
    if not base.exists():
        raise FileNotFoundError(base)

    scenario_dir = base
    if scenario:
        scenario_dir = base / "_pups" / "omni" / "scenarios" / scenario
        if not scenario_dir.exists():
            raise FileNotFoundError(scenario_dir)

    if auto_activate:
        from wepppy.query_engine.activate import activate_query_engine

        activate_query_engine(scenario_dir)

    catalog = load_catalog(scenario_dir)
    return RunContext(runid=runid, base_dir=scenario_dir, scenario=scenario, catalog=catalog)
