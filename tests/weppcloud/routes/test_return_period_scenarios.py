"""Real filesystem coverage for the return-period scenario selection boundary."""
from types import SimpleNamespace
from pathlib import Path
import shutil

import pytest

from wepppy.weppcloud.routes.nodb_api import return_period_scenarios as selection

pytestmark = pytest.mark.unit


@pytest.fixture
def project(tmp_path, monkeypatch):
    root = tmp_path / "project"
    root.mkdir()
    (root / "omni.nodb").write_text("existing state")
    omni = SimpleNamespace(scenarios=[], _scenario_run_state=[])
    monkeypatch.setattr(selection.Omni, "getInstance", lambda wd: omni)
    return root, omni


def add_scenario(project, name="undisturbed", *, readonly=True, ready=True):
    root, omni = project
    omni.scenarios.append({"type": name})
    child = root / "_pups/omni/scenarios" / name
    (child / "wepp/output/interchange").mkdir(parents=True)
    (child / "wepp/output/loss_pw0.out.parquet").write_bytes(b"existing loss")
    (child / "wepp.nodb").write_text("existing state")
    if readonly:
        (child / "READONLY").touch()
    if ready:
        (child / "_query_engine").mkdir()
        (child / "_query_engine/catalog.json").write_text('{}')
        for filename in ("return_period_events.parquet", "return_period_event_ranks.parquet"):
            (child / "wepp/output/interchange" / filename).write_bytes(b"staged dataset")
    return child


def test_absent_and_empty_omni_do_not_create_state(project):
    root, _ = project
    assert selection.completed_return_period_scenarios(root, "baseline") == []
    (root / "omni.nodb").unlink()
    assert selection.completed_return_period_scenarios(root, "baseline") == []
    assert not (root / "omni.nodb").exists()


def test_completed_sorted_unready_and_scope_specific(project):
    root, _ = project
    add_scenario(project, "uniform_low", ready=False)
    add_scenario(project)
    choices = selection.completed_return_period_scenarios(root, "baseline")
    assert [item["name"] for item in choices] == ["undisturbed", "uniform_low"]
    assert choices[0]["reason"] is None
    assert "return-period" in choices[1]["reason"]
    assert all(item["reason"] for item in selection.completed_return_period_scenarios(root, "roads"))


def test_empty_and_absent_state_use_outputs_but_failed_state_excludes(project):
    root, omni = project
    child = add_scenario(project, readonly=False)
    assert len(selection.completed_return_period_scenarios(root, "baseline")) == 1
    del omni._scenario_run_state
    assert len(selection.completed_return_period_scenarios(root, "baseline")) == 1
    omni._scenario_run_state = [{"scenario": "undisturbed", "status": "failed"}]
    (child / "READONLY").touch()
    assert selection.completed_return_period_scenarios(root, "baseline") == []


def test_current_interchange_completion_artifact(project):
    root, _ = project
    child = add_scenario(project)
    (child / "wepp/output/loss_pw0.out.parquet").rename(child / "wepp/output/interchange/loss_pw0.out.parquet")
    assert selection.completed_return_period_scenarios(root, "baseline")[0]["reason"] is None


@pytest.mark.parametrize("relative", ["_pups", "_pups/omni/scenarios", "_pups/omni/scenarios/undisturbed"])
def test_discovery_rejects_escaping_directory_links(project, tmp_path, relative):
    root, _ = project
    add_scenario(project)
    target = root / relative
    outside = tmp_path / "outside"
    target.rename(outside)
    target.symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="outside"):
        selection.completed_return_period_scenarios(root, "baseline")


@pytest.mark.parametrize("relative", ["wepp.nodb", "_query_engine/catalog.json", "wepp/output", "wepp/output/interchange/return_period_events.parquet"])
def test_discovery_rejects_escaping_output_and_state(project, tmp_path, relative):
    root, _ = project
    child = add_scenario(project)
    target = child / relative
    outside = tmp_path / "outside"
    target.rename(outside)
    target.symlink_to(outside, target_is_directory=outside.is_dir())
    with pytest.raises(ValueError, match="outside"):
        selection.completed_return_period_scenarios(root, "baseline")


def test_restored_project_with_shared_inputs_remains_selectable(project, tmp_path):
    root, _ = project
    child = add_scenario(project)
    for name in ("climate", "watershed"):
        (root / name).mkdir()
        (root / name / "input").write_text("shared")
        (child / name).symlink_to("../../../../" + name, target_is_directory=True)
    archive = shutil.make_archive(str(tmp_path / "snapshot"), "tar", root_dir=root)
    restored = tmp_path / "restored"
    shutil.unpack_archive(archive, restored, filter="data")
    assert (restored / "_pups/omni/scenarios/undisturbed/climate/input").read_text() == "shared"
    assert selection.completed_return_period_scenarios(restored, "baseline")[0]["reason"] is None


@pytest.mark.parametrize("bad_type", ["../../outside", "=SUM(1,2)", "@bad"])
def test_unknown_definition_cannot_supply_paths_or_csv_formulas(project, bad_type):
    root, omni = project
    omni.scenarios = [{"type": bad_type}]
    with pytest.raises(ValueError, match="Invalid Omni"):
        selection.completed_return_period_scenarios(root, "baseline")


def add_preparation_sources(child):
    for name in ("ebe_pw0.parquet", "totalwatsed3.parquet"):
        (child / "wepp/output/interchange" / name).write_bytes(b"source output")
    (child / "_query_engine").mkdir(exist_ok=True)
    (child / "_query_engine/catalog.json").write_text('{}')


def test_unstaged_writable_outputs_are_selectable_without_discovery_writes(project):
    root, _ = project
    child = add_scenario(project, readonly=False, ready=False)
    add_preparation_sources(child)
    before = sorted(str(path) for path in root.rglob("*"))
    assert selection.completed_return_period_scenarios(root, "baseline")[0]["reason"] is None
    assert before == sorted(str(path) for path in root.rglob("*"))
    (child / "READONLY").touch()
    assert "preparation" in selection.completed_return_period_scenarios(root, "baseline")[0]["reason"]


@pytest.mark.parametrize("relative", ["_query_engine/cache", "climate/wepp_cli.parquet",
    "wepp/runs/pw0.cli", "wepp/output/interchange/ebe_pw0.parquet",
    "wepp/output/interchange/return_period_event_ranks.parquet"])
def test_preparation_rejects_escaping_sources_and_targets(project, tmp_path, relative):
    root, _ = project
    child = add_scenario(project, readonly=False, ready=False)
    add_preparation_sources(child)
    target = child / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.unlink(missing_ok=True)
    target.symlink_to(tmp_path / "outside")
    with pytest.raises(ValueError, match="outside"):
        selection.completed_return_period_scenarios(root, "baseline")


def test_preparation_accepts_shared_project_climate_and_cli(project):
    root, _ = project
    child = add_scenario(project, readonly=False, ready=False)
    add_preparation_sources(child)
    (root / "climate").mkdir()
    (root / "climate/source.cli").write_text("shared")
    (child / "climate").symlink_to(root / "climate", target_is_directory=True)
    (child / "wepp/runs").mkdir()
    (child / "wepp/runs/pw0.cli").symlink_to(root / "climate/source.cli")
    assert selection.completed_return_period_scenarios(root, "baseline")[0]["reason"] is None
