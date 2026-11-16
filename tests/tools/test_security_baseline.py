from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

from tools import check_security_baseline as gate

pytestmark = pytest.mark.unit


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


@pytest.fixture
def repository(tmp_path: Path) -> tuple[Path, str]:
    git(tmp_path, "init", "-q")
    git(tmp_path, "config", "user.email", "test@example.invalid")
    git(tmp_path, "config", "user.name", "Test")
    source = tmp_path / "wepppy/microservices/shape_converter/parser.py"
    source.parent.mkdir(parents=True)
    source.write_text("accepted parser\n")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-qm", "accepted")
    return tmp_path, git(tmp_path, "rev-parse", "HEAD")


def commit(root: Path, path: str, content: str | None) -> str:
    target = root / path
    if content is None:
        target.unlink()
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
    git(root, "add", "-A")
    git(root, "commit", "-qm", "candidate")
    return git(root, "rev-parse", "HEAD")


def test_unrelated_change_passes_without_approval(repository):
    root, base = repository
    head = commit(root, "unrelated.txt", "soils")
    assert gate.check_policy(root, base, head, "")["changed_paths"] == []


@pytest.mark.parametrize("content", [None, "old GDAL implementation"])
def test_revert_or_deletion_retains_ancestry_but_requires_approval(repository, content):
    root, base = repository
    head = commit(root, "wepppy/microservices/shape_converter/parser.py", content)
    with pytest.raises(gate.GateError, match="POLICY_APPROVAL_REQUIRED"):
        gate.check_policy(root, base, head, "")
    paths, digest = gate.policy_delta(root, base, head)
    assert len(paths) == 1
    assert gate.check_policy(root, base, head, f"{head}:{digest}")["approved_transition"]
    with pytest.raises(gate.GateError):
        gate.check_policy(root, base, head, f"{base}:{digest}")


def test_symlink_replacement_requires_approval(repository):
    root, base = repository
    path = root / "wepppy/microservices/shape_converter/parser.py"
    path.unlink()
    path.symlink_to("/tmp/parser.py")
    git(root, "add", "-A")
    git(root, "commit", "-qm", "symlink")
    with pytest.raises(gate.GateError, match="POLICY_APPROVAL_REQUIRED"):
        gate.check_policy(root, base, git(root, "rev-parse", "HEAD"), "")


def test_checker_deletion_requires_trusted_checker_approval(repository):
    root, base = repository
    base = commit(root, "tools/check_security_baseline.py", "trusted checker")
    head = commit(root, "tools/check_security_baseline.py", None)
    with pytest.raises(gate.GateError, match="POLICY_APPROVAL_REQUIRED"):
        gate.check_policy(root, base, head, "")


def test_divergent_candidate_rejected_even_with_approval(repository):
    root, base = repository
    other = commit(root, "unrelated.txt", "new accepted")
    with pytest.raises(gate.GateError, match="Git failed"):
        gate.check_policy(root, other, base, "")


def test_bootstrap_requires_fixed_base_and_digest(repository, tmp_path):
    root, base = repository
    head = commit(root, "tools/check_security_baseline.py", "candidate checker")
    with pytest.raises(gate.GateError, match="approved bootstrap"):
        gate.bootstrap(root, base, head, tmp_path / "checker", hashlib.sha256(b"candidate checker").hexdigest())


def test_existing_checker_loaded_from_base_not_candidate(repository, tmp_path):
    root, _ = repository
    base = commit(root, "tools/check_security_baseline.py", "trusted checker")
    head = commit(root, "tools/check_security_baseline.py", "weakened checker")
    destination = tmp_path / "loaded"
    gate.bootstrap(root, base, head, destination, "")
    assert destination.read_text() == "trusted checker"


def run(**overrides):
    value = {"id": 1, "run_attempt": 1, "workflow_id": 2, "head_sha": "a" * 40,
             "event": "push", "head_branch": "master", "repository": {"full_name": "owner/repo"},
             "status": "completed", "conclusion": "success"}
    value.update(overrides)
    return value


@pytest.mark.parametrize("overrides", [
    {"head_sha": "b" * 40}, {"workflow_id": 3}, {"event": "pull_request"},
    {"head_branch": "topic"}, {"repository": {"full_name": "attacker/repo"}},
    {"status": "in_progress"},
])
def test_publication_rejects_wrong_identity_or_unfinished_evidence(overrides):
    assert gate.eligible_run([run(**overrides)], "a" * 40, 2, "owner/repo") is None


@pytest.mark.parametrize("conclusion", ["failure", "cancelled", "skipped", "neutral", None])
def test_publication_requires_positive_success(conclusion):
    with pytest.raises(gate.GateError, match="did not succeed"):
        gate.eligible_run([run(conclusion=conclusion)], "a" * 40, 2, "owner/repo")


def test_failed_latest_rerun_cannot_reuse_old_success():
    with pytest.raises(gate.GateError):
        gate.eligible_run([run(), run(run_attempt=2, conclusion="failure")], "a" * 40, 2, "owner/repo")


def test_publication_current_master_and_exact_workflow(monkeypatch):
    def response(repository, suffix, token):
        if suffix.startswith("actions/workflows/") and "runs?" not in suffix:
            return {"path": ".github/workflows/integration-governance.yml", "state": "active", "id": 2}
        if suffix == "git/ref/heads/master":
            return {"object": {"sha": "a" * 40}}
        return {"workflow_runs": [run()]}
    monkeypatch.setattr(gate, "api", response)
    assert gate.publication("owner/repo", "a" * 40, "", 0)["run_id"] == 1
    with pytest.raises(gate.GateError, match="not current remote master"):
        gate.publication("owner/repo", "b" * 40, "", 0)


def test_publication_missing_check_fails_closed(monkeypatch):
    def response(repository, suffix, token):
        if suffix == "git/ref/heads/master":
            return {"object": {"sha": "a" * 40}}
        if "runs?" in suffix:
            return {"workflow_runs": []}
        return {"path": ".github/workflows/integration-governance.yml", "state": "active", "id": 2}
    monkeypatch.setattr(gate, "api", response)
    with pytest.raises(gate.GateError, match="missing or unfinished"):
        gate.publication("owner/repo", "a" * 40, "", 0)


def test_workflow_and_publish_consumers_are_wired():
    # Verify the actual YAML consumers rather than merely testing a helper nobody calls.
    from scripts.build_forest_workflows import load_yaml
    root = Path(__file__).resolve().parents[2]
    source = load_yaml(root / ".github/forest_workflows/integration-governance.yml")
    assert source["on"]["pull_request"] is None
    assert "paths" not in source["on"]["push"]
    job = source["jobs"]["integration-governance"]
    assert job["runs-on"] == "ubuntu-24.04"
    text = json.dumps(job)
    assert 'git show' in text and '${base}:tools/check_security_baseline.py' in text
    assert "policy --base" in text and "smoke --binary" in text
    for filename in ["publish-weppcloud-image.yml", "publish-weppcloud-aux-images.yml"]:
        workflow = load_yaml(root / ".github/workflows" / filename)
        assert workflow["jobs"]["publish"]["needs"] == "governance"
        gate_job = workflow["jobs"]["governance"]
        assert gate_job["permissions"] == {"contents": "read", "actions": "read"}
        assert gate_job["runs-on"] == "ubuntu-24.04"
        assert "publication --repository" in json.dumps(gate_job)


def test_trusted_policy_never_executes_candidate_code_and_binds_head():
    from scripts.build_forest_workflows import load_yaml
    root = Path(__file__).resolve().parents[2]
    workflow = load_yaml(root / ".github/forest_workflows/integration-policy.yml")
    assert "pull_request_target" in workflow["on"]
    policy = workflow["jobs"]["trusted-policy"]
    assert policy["steps"][0]["with"]["ref"] == "${{ github.event.pull_request.base.sha }}"
    assert policy["steps"][0]["with"]["persist-credentials"] in (False, "false")
    commands = "\n".join(step.get("run", "") for step in policy["steps"])
    assert 'git fetch --no-tags origin "${CANDIDATE_SHA}"' in commands
    assert "cargo" not in commands and "git checkout" not in commands
    assert "python3 tools/check_security_baseline.py policy" in commands
    report = workflow["jobs"]["report-policy"]
    assert report["permissions"] == {"checks": "write"}
    assert report["needs"] == "trusted-policy"
    assert not any("uses" in step for step in report["steps"])
    assert '"head_sha": candidate' in report["steps"][0]["run"]


@pytest.mark.parametrize("path", [
    "tools/wctl2/checkout_identity.py",
    "docker/requirements-shape-converter.txt",
    "docker/docker-compose.prod.wepp1.yml",
    ".github/forest_workflows/integration-policy.yml",
])
def test_indirect_security_consumers_require_owner_transition(repository, path):
    root, _ = repository
    base = commit(root, path, "accepted control")
    head = commit(root, path, "silently weakened control")
    with pytest.raises(gate.GateError, match="POLICY_APPROVAL_REQUIRED"):
        gate.check_policy(root, base, head, "")


def test_ambient_git_variables_cannot_redirect_explicit_root(repository, tmp_path, monkeypatch):
    root, base = repository
    other = tmp_path / "other-checkout"
    other.mkdir()
    git(other, "init", "-q")
    git(other, "config", "user.email", "test@example.invalid")
    git(other, "config", "user.name", "Test")
    other_sha = commit(other, "wepppy/microservices/shape_converter/parser.py", "other repository")
    head = commit(root, "wepppy/microservices/shape_converter/parser.py", "weakened")
    for key, value in {
        "GIT_DIR": str(other / ".git"), "GIT_COMMON_DIR": str(other / ".git"),
        "GIT_WORK_TREE": str(other), "GIT_INDEX_FILE": str(other / ".git/index"),
        "GIT_OBJECT_DIRECTORY": str(other / ".git/objects"),
        "GIT_ALTERNATE_OBJECT_DIRECTORIES": str(other / ".git/objects"),
        "GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "core.worktree",
        "GIT_CONFIG_VALUE_0": str(other),
    }.items():
        monkeypatch.setenv(key, value)
    assert gate.git(root, "rev-parse", "HEAD").decode().strip() == head
    assert head != other_sha
    with pytest.raises(gate.GateError, match="POLICY_APPROVAL_REQUIRED"):
        gate.check_policy(root, base, head, "")


def test_workflow_generator_does_not_change_global_yaml_boolean_parsing():
    # A fresh process exercises the first import even if an earlier wiring test
    # imported the generator. Global resolver mutation broke downstream feature
    # registry and Usersum validation in the full suite.
    code = r"""
import copy
import yaml
before_load = copy.deepcopy(yaml.SafeLoader.yaml_implicit_resolvers)
before_dump = copy.deepcopy(yaml.SafeDumper.yaml_implicit_resolvers)
before_text = yaml.safe_dump({'enabled': True})
import runpy
builder = runpy.run_path("scripts/build_forest_workflows.py")
WorkflowLoader, dump_yaml = builder["WorkflowLoader"], builder["dump_yaml"]
assert yaml.SafeLoader.yaml_implicit_resolvers == before_load
assert yaml.SafeDumper.yaml_implicit_resolvers == before_dump
assert yaml.safe_load('enabled: true')['enabled'] is True
assert yaml.safe_load('enabled: false')['enabled'] is False
assert yaml.safe_dump({'enabled': True}) == before_text
workflow = yaml.load('on: {push: null}\nflag: false', Loader=WorkflowLoader)
assert workflow == {'on': {'push': None}, 'flag': 'false'}
assert yaml.load(dump_yaml(workflow), Loader=WorkflowLoader) == workflow
"""
    result = subprocess.run(
        [sys.executable, "-c", code], cwd=Path(__file__).resolve().parents[2],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
