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


def _normalize_relative_scenario_parts(raw_scenario: str) -> tuple[str, ...]:
    scenario_value = str(raw_scenario).strip()
    if not scenario_value:
        raise FileNotFoundError("Scenario path is empty")

    scenario_path = Path(scenario_value)
    if scenario_path.is_absolute():
        raise FileNotFoundError(scenario_path)

    normalized_parts: list[str] = []
    for part in scenario_path.parts:
        if part in ("", "."):
            continue
        if part == "..":
            raise FileNotFoundError(scenario_path)
        normalized_parts.append(part)

    if not normalized_parts:
        raise FileNotFoundError(scenario_path)
    return tuple(normalized_parts)


def _resolve_scenario_dir(base: Path, scenario: str | None) -> Path:
    if scenario is None:
        return base
    if str(scenario).strip() == "":
        return base

    parts = _normalize_relative_scenario_parts(scenario)
    candidates: list[Path] = []

    def _add_candidate(path: Path) -> None:
        if path not in candidates:
            candidates.append(path)

    if len(parts) == 1:
        scenario_name = parts[0]
        # Preserve legacy behaviour for bare names.
        _add_candidate(base / "_pups" / "omni" / "scenarios" / scenario_name)
        # Support RHESSys scenario directories under the run root.
        _add_candidate(base / "rhessys" / "scenarios" / scenario_name)
    else:
        explicit_path = base.joinpath(*parts)
        _add_candidate(explicit_path)
        if len(parts) >= 2 and parts[0] == "omni" and parts[1] == "scenarios":
            _add_candidate(base / "_pups" / explicit_path.relative_to(base))

    for candidate in candidates:
        if candidate.is_dir():
            return candidate

    raise FileNotFoundError(candidates[0] if candidates else base)


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
        scenario: Optional scenario selector. Supports:
            - bare scenario names (e.g., ``mulch_30_sbs_map`` or ``S1``)
            - explicit relative paths (e.g., ``_pups/omni/scenarios/mulch_30_sbs_map`` or
              ``rhessys/scenarios/S1``)
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

    scenario_dir = _resolve_scenario_dir(base, scenario)

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
