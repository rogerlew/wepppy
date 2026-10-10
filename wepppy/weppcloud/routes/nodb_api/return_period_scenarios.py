"""Read-only Omni choices for the return-period comparison report."""
from pathlib import Path

from wepppy.nodb.mods.omni import Omni
from wepppy.nodb.mods.omni.omni import OmniScenario, _scenario_name_from_scenario_definition
from wepppy.wepp.reports.output_scope import scoped_dataset_path


def _contained(path: Path, root: Path) -> Path:
    resolved = path.resolve()
    if not resolved.is_relative_to(root) or resolved == root:
        raise ValueError("Omni scenario path resolves outside its authorized directory")
    return resolved


def _readable(path: Path) -> bool:
    try:
        with path.open("rb") as stream:
            stream.read(1)
    except (FileNotFoundError, PermissionError, IsADirectoryError):
        return False
    return True


def _preparation_sources(child: Path, root: Path, output_scope: str) -> bool:
    """Validate the existing reader's source and derived-artifact boundaries."""
    for relative in ("_query_engine", "_query_engine/cache", "wepp/runs"):
        _contained(child / relative, child)
    climate = _contained(child / "climate", root)
    _contained(climate / "wepp_cli.parquet", root)
    for candidate in climate.rglob("*.parquet"):
        _contained(candidate, root)
    for candidate in (child / "wepp/runs").rglob("*.cli"):
        _contained(candidate, root)
    ebe_paths = [
        _contained(child / scoped_dataset_path(relative, output_scope), child)
        for relative in ("wepp/output/interchange/ebe_pw0.parquet", "wepp/output/ebe_pw0.parquet")
    ]
    total = _contained(child / scoped_dataset_path(
        "wepp/output/interchange/totalwatsed3.parquet", output_scope), child)
    return any(_readable(path) for path in ebe_paths) and _readable(total)


def completed_return_period_scenarios(wd, output_scope):
    """List artifact-backed children independently of their editing policy.

    Discovery never prepares assets. Selected writable children can use the
    normal reader to derive missing report tables from existing model outputs.
    """
    root = Path(wd).resolve()
    omni_path = _contained(root / "omni.nodb", root)
    if not omni_path.is_file():
        return []
    scenario_root = _contained(root / "_pups/omni/scenarios", root)
    omni = Omni.getInstance(str(root))
    states = getattr(omni, "_scenario_run_state", None)
    latest = {entry["scenario"]: entry["status"] for entry in (states or [])}
    choices = {}
    for definition in omni.scenarios:
        try:
            # The generator accepts unknown strings; validate the enum first so
            # only established name prefixes enter paths, HTML, and CSV cells.
            OmniScenario.parse(definition.get("type"))
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("Invalid Omni scenario definition") from exc
        name = _scenario_name_from_scenario_definition(definition)
        if "/" in name or "\\" in name or name in (".", ".."):
            raise ValueError("Invalid Omni scenario name")
        child = _contained(scenario_root / name, scenario_root)
        loss_paths = [
            _contained(child / relative, child) for relative in (
                "wepp/output/interchange/loss_pw0.out.parquet",
                "wepp/output/loss_pw0.out.parquet",
            )
        ]
        marker = _contained(child / "READONLY", child)
        if not any(path.is_file() for path in loss_paths):
            continue
        if name in latest and latest[name] not in ("executed", "skipped"):
            continue
        state_paths = [_contained(child / relative, child) for relative in (
            "wepp.nodb", "_query_engine/catalog.json")]
        staged = [_contained(child / scoped_dataset_path(
            f"wepp/output/interchange/{filename}", output_scope), child)
            for filename in ("return_period_events.parquet", "return_period_event_ranks.parquet")]
        reason = None
        if not all(_readable(path) for path in state_paths):
            reason = f"Required {output_scope} return-period inputs are unavailable."
        elif not all(_readable(path) for path in staged):
            if marker.is_file():
                reason = "Return-period tables need preparation; this scenario is readonly."
            elif not _preparation_sources(child, root, output_scope):
                reason = f"Required {output_scope} return-period source outputs are unavailable."
        choices[name] = {"name": name, "path": str(child), "reason": reason}
    return [choices[name] for name in sorted(choices)]
