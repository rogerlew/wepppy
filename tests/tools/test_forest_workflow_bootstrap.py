"""Standalone CI must not inherit Forest host environment or cleanup."""

import copy
from pathlib import Path
import runpy

import pytest
import yaml


@pytest.fixture
def builder(monkeypatch):
    # The generator customizes inherited PyYAML resolvers; isolate that mutation.
    for loader in (yaml.SafeLoader, yaml.SafeDumper):
        monkeypatch.setattr(loader, "yaml_implicit_resolvers", copy.deepcopy(loader.yaml_implicit_resolvers))
    return runpy.run_path(str(Path(__file__).parents[2] / "scripts/build_forest_workflows.py"))


def test_standalone_job_excludes_host_bootstrap_without_changing_default(builder):
    spec = yaml.load("""
jobs:
  standalone:
    forest_bootstrap: false
    env: {COMPOSE_PROJECT_NAME: isolated}
    steps: [{run: test}]
  forest:
    steps: [{run: test}]
""", Loader=builder["WorkflowLoader"])
    before = copy.deepcopy(spec)
    bootstrap = {"env": {"RUNNER_DOCKER_ENV": "host.env"},
                 "setup_steps": [{"run": "host setup"}],
                 "cleanup_steps": [{"run": "host cleanup"}]}
    result = builder["build_workflow"](spec, bootstrap)
    assert result["jobs"]["standalone"] == {
        "env": {"COMPOSE_PROJECT_NAME": "isolated"}, "steps": [{"run": "test"}]}
    assert result["jobs"]["forest"] == {
        "env": bootstrap["env"],
        "steps": [{"run": "host setup"}, {"run": "test"}, {"run": "host cleanup"}]}
    assert spec == before


def test_invalid_bootstrap_selection_fails_explicitly(builder):
    with pytest.raises(ValueError, match="Invalid forest_bootstrap"):
        builder["build_workflow"]({"jobs": {"test": {"forest_bootstrap": "disabled"}}}, {})
