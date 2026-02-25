from __future__ import annotations

import json
from pathlib import Path

import pytest

from wepppy.query_engine.context import resolve_run_context

pytestmark = pytest.mark.unit


def _write_catalog(run_root: Path) -> None:
    catalog_dir = run_root / "_query_engine"
    catalog_dir.mkdir(parents=True, exist_ok=True)
    catalog_payload = {
        "version": 1,
        "generated_at": "2026-01-01T00:00:00+00:00",
        "root": str(run_root),
        "files": [],
    }
    (catalog_dir / "catalog.json").write_text(json.dumps(catalog_payload), encoding="utf-8")


def test_resolve_run_context_with_bare_omni_scenario_name(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    scenario_dir = run_dir / "_pups" / "omni" / "scenarios" / "burned"
    scenario_dir.mkdir(parents=True)
    _write_catalog(scenario_dir)

    context = resolve_run_context(str(run_dir), scenario="burned", auto_activate=False)

    assert context.base_dir == scenario_dir
    assert context.scenario == "burned"


def test_resolve_run_context_with_bare_rhessys_scenario_name(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    scenario_dir = run_dir / "rhessys" / "scenarios" / "S1"
    scenario_dir.mkdir(parents=True)
    _write_catalog(scenario_dir)

    context = resolve_run_context(str(run_dir), scenario="S1", auto_activate=False)

    assert context.base_dir == scenario_dir
    assert context.scenario == "S1"


def test_resolve_run_context_prefers_omni_for_ambiguous_bare_name(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    omni_dir = run_dir / "_pups" / "omni" / "scenarios" / "shared"
    rhessys_dir = run_dir / "rhessys" / "scenarios" / "shared"
    omni_dir.mkdir(parents=True)
    rhessys_dir.mkdir(parents=True)
    _write_catalog(omni_dir)
    _write_catalog(rhessys_dir)

    context = resolve_run_context(str(run_dir), scenario="shared", auto_activate=False)

    assert context.base_dir == omni_dir


def test_resolve_run_context_accepts_explicit_rhessys_path(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    scenario_dir = run_dir / "rhessys" / "scenarios" / "S2"
    scenario_dir.mkdir(parents=True)
    _write_catalog(scenario_dir)

    context = resolve_run_context(str(run_dir), scenario="rhessys/scenarios/S2", auto_activate=False)

    assert context.base_dir == scenario_dir
    assert context.scenario == "rhessys/scenarios/S2"


def test_resolve_run_context_accepts_omni_path_without_pups_prefix(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    scenario_dir = run_dir / "_pups" / "omni" / "scenarios" / "undisturbed"
    scenario_dir.mkdir(parents=True)
    _write_catalog(scenario_dir)

    context = resolve_run_context(str(run_dir), scenario="omni/scenarios/undisturbed", auto_activate=False)

    assert context.base_dir == scenario_dir


def test_resolve_run_context_rejects_traversal_scenarios(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir(parents=True)

    with pytest.raises(FileNotFoundError):
        resolve_run_context(str(run_dir), scenario="../outside", auto_activate=False)


def test_resolve_run_context_treats_blank_scenario_as_base(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir(parents=True)
    _write_catalog(run_dir)

    context = resolve_run_context(str(run_dir), scenario="  ", auto_activate=False)

    assert context.base_dir == run_dir


def test_resolve_run_context_does_not_treat_arbitrary_child_dir_as_bare_scenario(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    child_dir = run_dir / "dem"
    child_dir.mkdir(parents=True)
    _write_catalog(child_dir)

    with pytest.raises(FileNotFoundError):
        resolve_run_context(str(run_dir), scenario="dem", auto_activate=False)
