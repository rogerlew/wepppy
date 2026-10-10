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


def completed_return_period_scenarios(wd, output_scope):
    """List defined, completed children; missing staged inputs disable a choice.

    READONLY is removed by cloning and written at finalization. Old runs without
    run-state metadata may instead prove completion with their established loss
    artifact. Neither policy treats an empty modern state list as legacy.
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
        if not any(path.is_file() for path in loss_paths) or (states is not None and not marker.is_file()):
            continue
        if name in latest and latest[name] not in ("executed", "skipped"):
            continue
        required = [child / "wepp.nodb", child / "_query_engine/catalog.json"] + [
            child / scoped_dataset_path(f"wepp/output/interchange/{filename}", output_scope)
            for filename in ("return_period_events.parquet", "return_period_event_ranks.parquet")
        ]
        reason = None
        for path in required:
            path = _contained(path, child)
            try:
                with path.open("rb") as stream:
                    stream.read(1)
            except (FileNotFoundError, PermissionError, IsADirectoryError):
                reason = f"Required {output_scope} return-period inputs are unavailable."
        choices[name] = {"name": name, "path": str(child), "reason": reason}
    return [choices[name] for name in sorted(choices)]
