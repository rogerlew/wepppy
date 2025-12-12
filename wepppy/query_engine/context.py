"""Resolve run metadata and catalogs for query-engine execution."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from wepppy.query_engine.catalog import DatasetCatalog, load_catalog

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class RunContext:
    """Activation metadata for a runid and optional scenario."""

    runid: str
    base_dir: Path
    scenario: str | None
    catalog: DatasetCatalog


def resolve_run_context(
    runid: str,
    *,
    scenario: str | None = None,
    auto_activate: bool = True,
    run_interchange: bool = True,
    force_refresh: bool = False,
) -> RunContext:
    """Load the query-engine catalog for a run (and optional scenario).

    Args:
        runid: Path or slug to the WEPP run directory.
        scenario: Optional scenario slug, relative to the run root.
        auto_activate: When True, trigger `activate_query_engine` if needed.
        run_interchange: When auto-activating, whether to generate interchange outputs.
        force_refresh: When auto-activating, force a catalog rebuild.

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

    catalog: DatasetCatalog | None = None
    try:
        catalog = load_catalog(scenario_dir)
    except FileNotFoundError:
        if not auto_activate:
            raise
    except Exception:  # pragma: no cover - defensive rebuild on corrupt catalogs
        if not auto_activate:
            raise
        LOGGER.warning("Existing catalog for %s is unreadable; rebuilding", scenario_dir, exc_info=True)
        catalog = None

    if catalog is None:
        if auto_activate:
            from wepppy.query_engine.activate import activate_query_engine

            activate_query_engine(
                scenario_dir,
                run_interchange=run_interchange,
                force_refresh=force_refresh,
            )
            catalog = load_catalog(scenario_dir)
        else:
            raise FileNotFoundError(scenario_dir / "_query_engine" / "catalog.json")

    return RunContext(runid=runid, base_dir=scenario_dir, scenario=scenario, catalog=catalog)
