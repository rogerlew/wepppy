from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess

import pytest

from tools.security import retained_candidate as candidate


pytestmark = pytest.mark.unit

_IMAGE_ID = "sha256:" + "1" * 64
_REVISION = "2" * 40


def _config() -> dict[str, object]:
    shared = {"image": "wepppy:test", "build": {"context": ".."}}
    return {
        "name": "docker",
        "services": {
            "weppcloud": shared,
            "rq-worker": shared,
            "redis": {"image": "redis:test"},
        },
    }


def _args(project: Path, deploy_script: Path, receipt: Path | None = None) -> argparse.Namespace:
    return argparse.Namespace(
        project_root=project,
        deploy_script=deploy_script,
        deploy_mode="full",
        deploy_option=[],
        build_service=["weppcloud"],
        recreated_service=["weppcloud", "rq-worker", "redis"],
        receipt=receipt,
    )


@pytest.fixture
def candidate_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    project = tmp_path / "project"
    project.mkdir(mode=0o700)
    lock = project / candidate.LOCK_PATH
    lock.parent.mkdir(parents=True)
    lock.write_text('{"lockfileVersion":3}\n', encoding="utf-8")
    deploy_script = project / "scripts" / "deploy-production.sh"
    deploy_script.parent.mkdir()
    deploy_script.write_text("#!/bin/bash\n", encoding="utf-8")
    wctl = tmp_path / "wctl"
    wctl.write_text("#!/bin/bash\n", encoding="utf-8")
    wctl.chmod(0o755)
    store = tmp_path / "security"
    monkeypatch.setattr(candidate, "STORE_ROOT", store)
    monkeypatch.setattr(candidate, "machine_id_hash", lambda: "a" * 64)
    monkeypatch.setattr(candidate.socket, "gethostname", lambda: "test-host")
    monkeypatch.setattr(candidate.shutil, "which", lambda name: str(wctl))
    state = {"engine": "engine-one", "image": _IMAGE_ID, "dirty": ""}

    def fake_run(*command: str, cwd: Path) -> str:
        del cwd
        if command[:3] == ("git", "rev-parse", "HEAD"):
            return _REVISION
        if command[:2] == ("git", "status"):
            return state["dirty"]
        if command[:3] == ("docker", "image", "inspect"):
            return state["image"]
        if command[:2] == ("docker", "info"):
            return state["engine"]
        raise AssertionError(command)

    monkeypatch.setattr(candidate, "run", fake_run)
    monkeypatch.setattr(candidate, "compose_config", _config)
    return project, deploy_script, state


def _create(candidate_environment, capsys: pytest.CaptureFixture[str]) -> Path:
    project, deploy_script, _ = candidate_environment
    assert candidate.create_candidate(_args(project, deploy_script)) == 0
    output = json.loads(capsys.readouterr().out)
    return Path(output["receipt"])


def test_create_is_atomic_private_and_validate_rechecks_all_identities(
    candidate_environment,
    capsys: pytest.CaptureFixture[str],
) -> None:
    project, deploy_script, _ = candidate_environment
    receipt = _create(candidate_environment, capsys)

    assert receipt.stat().st_mode & 0o777 == 0o600
    assert receipt.parent.stat().st_mode & 0o777 == 0o700
    assert not list(receipt.parent.parent.glob(".candidate-*"))
    value, validated, activation, override = candidate.validate_candidate(
        _args(project, deploy_script, receipt)
    )
    assert validated == receipt
    assert value["image_id"] == _IMAGE_ID
    assert json.loads(activation.read_text(encoding="utf-8")) == _config()
    assert json.loads(override.read_text(encoding="utf-8")) == {
        "services": {
            "rq-worker": {"image": _IMAGE_ID},
            "redis": {"image": _IMAGE_ID},
            "weppcloud": {"image": _IMAGE_ID},
        }
    }


@pytest.mark.parametrize("drift", ["engine", "image", "dirty"])
def test_validate_rejects_host_source_or_image_drift(
    candidate_environment,
    capsys: pytest.CaptureFixture[str],
    drift: str,
) -> None:
    project, deploy_script, state = candidate_environment
    receipt = _create(candidate_environment, capsys)
    state[drift] = {
        "engine": "engine-two",
        "image": "sha256:" + "3" * 64,
        "dirty": " M scripts/deploy-production.sh",
    }[drift]

    with pytest.raises(candidate.CandidateError):
        candidate.validate_candidate(_args(project, deploy_script, receipt))


def test_validate_rejects_symlinked_receipt(
    candidate_environment,
    capsys: pytest.CaptureFixture[str],
) -> None:
    project, deploy_script, _ = candidate_environment
    receipt = _create(candidate_environment, capsys)
    link = receipt.parent / "linked-receipt.json"
    link.symlink_to(receipt)

    with pytest.raises(candidate.CandidateError):
        candidate.validate_candidate(_args(project, deploy_script, link))


def test_validate_rejects_mode_change(
    candidate_environment,
    capsys: pytest.CaptureFixture[str],
) -> None:
    project, deploy_script, _ = candidate_environment
    receipt = _create(candidate_environment, capsys)
    os.chmod(receipt, 0o640)

    with pytest.raises(candidate.CandidateError, match="0600"):
        candidate.validate_candidate(_args(project, deploy_script, receipt))


def test_approval_is_derived_from_receipt_hash_and_invokes_exact_subject(
    candidate_environment,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project, deploy_script, _ = candidate_environment
    receipt_path = _create(candidate_environment, capsys)
    receipt, _, _, _ = candidate.validate_candidate(
        _args(project, deploy_script, receipt_path)
    )
    policy = project / candidate.POLICY_PATH
    policy.parent.mkdir(parents=True)
    policy.write_text("approved policy\n", encoding="utf-8")
    bundle = candidate.STORE_ROOT / "evidence" / "bundle"
    bundle.mkdir(parents=True, mode=0o700)
    os.chmod(candidate.STORE_ROOT / "evidence", 0o700)
    manifest = bundle / "manifest.json"
    manifest.write_text("{}\n", encoding="utf-8")
    manifest.chmod(0o600)
    disposition_raw = b'{"findings":[]}\n'
    disposition_hash = candidate.sha256_bytes(disposition_raw)
    disposition_dir = candidate.STORE_ROOT / "approvals" / "dispositions"
    disposition_dir.mkdir(parents=True, mode=0o700)
    os.chmod(candidate.STORE_ROOT / "approvals", 0o700)
    disposition = disposition_dir / f"{disposition_hash}.json"
    disposition.write_bytes(disposition_raw)
    disposition.chmod(0o600)
    host_approvals = candidate.STORE_ROOT / "approvals" / ("a" * 64)
    host_approvals.mkdir(mode=0o700)
    approval_path = host_approvals / f"{candidate.sha256_file(receipt_path)}.json"
    approval = {
        "schema_version": 1,
        "candidate_receipt_sha256": candidate.sha256_file(receipt_path),
        "evidence_bundle": str(bundle),
        "evidence_manifest_sha256": candidate.sha256_file(manifest),
        "policy_sha256": candidate.sha256_file(policy),
        "dispositions_sha256": disposition_hash,
        "approved_at": candidate.datetime.now(candidate.timezone.utc).isoformat(),
        "approver": "reviewer",
        "review_trigger": "new evidence or candidate identity",
    }
    approval_path.write_bytes(candidate.canonical_json(approval) + b"\n")
    approval_path.chmod(0o600)
    calls: list[list[str]] = []

    def fake_subprocess_run(command, **kwargs):
        del kwargs
        calls.append(command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(candidate.subprocess, "run", fake_subprocess_run)

    assert candidate.validate_approval(receipt, receipt_path, project) == approval_path
    command = calls[0]
    assert command[command.index("--image-id") + 1] == _IMAGE_ID
    assert command[command.index("--source-revision") + 1] == _REVISION
