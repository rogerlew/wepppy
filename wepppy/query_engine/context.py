from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from wepppy.query_engine.activate import activate_query_engine
from wepppy.query_engine.catalog import DatasetCatalog, load_catalog


@dataclass(slots=True)
class RunContext:
    runid: str
    base_dir: Path
    scenario: Optional[str]
    catalog: DatasetCatalog


def resolve_run_context(runid: str, *, scenario: Optional[str] = None, auto_activate: bool = True) -> RunContext:
    base = Path(runid).expanduser()
    if not base.exists():
        raise FileNotFoundError(base)

    scenario_dir = base
    if scenario:
        scenario_dir = base / "_pups" / "omni" / "scenarios" / scenario
        if not scenario_dir.exists():
            raise FileNotFoundError(scenario_dir)

    if auto_activate:
        activate_query_engine(scenario_dir)

    catalog = load_catalog(scenario_dir)
    return RunContext(runid=runid, base_dir=scenario_dir, scenario=scenario, catalog=catalog)
