#!/usr/bin/env python3

from __future__ import annotations

import copy
from pathlib import Path
from typing import Dict, List

from build_forest_workflows import (
    FOREST_DIR,
    WORKFLOWS_DIR,
    dump_yaml,
    load_yaml,
)


REMOVE_STEP_NAMES = {
    "Checkout repository",
    "Ensure docker/.env exists",
    "Install wctl shim",
    "Verify wctl tooling",
    "Verify wctl / wctl2 availability",
    "Remove redis data directory",
}


def should_convert(path: Path) -> bool:
    if "wctl" not in path.read_text(encoding="utf-8"):
        return False
    spec_path = FOREST_DIR / path.name
    return not spec_path.exists()


def convert_workflow(path: Path) -> Dict:
    data = load_yaml(path)
    spec = copy.deepcopy(data)
    for job in spec.get("jobs", {}).values():
        env = job.get("env", {})
        if env.get("RUNNER_DOCKER_ENV") == "/workdir/wepppy/docker/.env":
            env.pop("RUNNER_DOCKER_ENV")
        if not env:
            job.pop("env", None)

        steps: List[Dict] = job.get("steps", [])
        filtered = [step for step in steps if step.get("name") not in REMOVE_STEP_NAMES]
        job["steps"] = filtered
    return spec


def main() -> int:
    specs_dir = FOREST_DIR
    specs_dir.mkdir(parents=True, exist_ok=True)

    targets = sorted(p for p in WORKFLOWS_DIR.glob("*.yml") if should_convert(p))
    if not targets:
        print("No workflows to convert.")
        return 0

    for workflow_path in targets:
        spec = convert_workflow(workflow_path)
        spec_path = specs_dir / workflow_path.name
        spec_path.write_text(dump_yaml(spec), encoding="utf-8")
        print(f"Wrote spec {spec_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
