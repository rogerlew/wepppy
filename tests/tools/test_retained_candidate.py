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


def test_create_uses_once_resolved_expected_ids_instead_of_mutable_tags(
    candidate_environment,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project, deploy_script, _ = candidate_environment
    original_run = candidate.run
    inspected: list[str] = []

    def recording_run(*command: str, cwd: Path) -> str:
        if command[:3] == ("docker", "image", "inspect"):
            inspected.append(command[-1])
        return original_run(*command, cwd=cwd)

    monkeypatch.setattr(candidate, "run", recording_run)
    args = _args(project, deploy_script)
    args.expected_image = [
        f"{service}={_IMAGE_ID}" for service in args.recreated_service
    ]
    assert candidate.create_candidate(args) == 0
    capsys.readouterr()
    assert inspected == [_IMAGE_ID] * len(args.recreated_service)


def test_create_accepts_wepp3_fork_archive_common_image(
    candidate_environment,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project, deploy_script, _ = candidate_environment
    config = {
        "name": "docker",
        "services": {
            "rq-worker-fork-archive": {
                "image": "wepppy:test",
                "build": {"context": ".."},
            },
        },
    }
    monkeypatch.setattr(candidate, "compose_config", lambda: config)
    args = _args(project, deploy_script)
    args.deploy_mode = "wepp3-fork-archive"
    args.build_service = ["rq-worker-fork-archive"]
    args.recreated_service = ["rq-worker-fork-archive"]

    assert candidate.create_candidate(args) == 0
    receipt = Path(json.loads(capsys.readouterr().out)["receipt"])
    value = json.loads(receipt.read_text(encoding="utf-8"))
    assert value["deploy_mode"] == "wepp3-fork-archive"
    assert value["dependency_service"] == "rq-worker-fork-archive"
    assert value["image_id"] == _IMAGE_ID


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


def test_validate_rejects_deploy_option_drift(
    candidate_environment,
    capsys: pytest.CaptureFixture[str],
) -> None:
    project, deploy_script, _ = candidate_environment
    receipt = _create(candidate_environment, capsys)
    args = _args(project, deploy_script, receipt)
    args.deploy_option = ["skip_themes=true"]

    with pytest.raises(candidate.CandidateError, match="no longer matches"):
        candidate.validate_candidate(args)


def test_validate_rejects_mode_change(
    candidate_environment,
    capsys: pytest.CaptureFixture[str],
) -> None:
    project, deploy_script, _ = candidate_environment
    receipt = _create(candidate_environment, capsys)
    os.chmod(receipt, 0o640)

    with pytest.raises(candidate.CandidateError, match="0600"):
        candidate.validate_candidate(_args(project, deploy_script, receipt))


@pytest.mark.parametrize(
    "environment",
    [
        {"SECRET_KEY": "plaintext"},
        {"JWT_SECRET": "plaintext"},
        {"AGENT_JWT_TOKEN": "plaintext"},
        {"RQ_REDIS_URL": "redis://user:password@redis:6379/9"},
        {"SERVICE_URL": "https://service.invalid/path?api_token=plaintext"},
    ],
)
def test_create_rejects_plaintext_or_url_embedded_secrets(
    candidate_environment,
    monkeypatch: pytest.MonkeyPatch,
    environment: dict[str, str],
) -> None:
    project, deploy_script, _ = candidate_environment
    config = _config()
    config["services"]["weppcloud"]["environment"] = environment
    monkeypatch.setattr(candidate, "compose_config", lambda: config)

    with pytest.raises(candidate.CandidateError, match="plaintext|embeds credentials"):
        candidate.create_candidate(_args(project, deploy_script))


def test_secret_file_and_public_values_are_not_persisted_as_secrets() -> None:
    candidate.require_secret_safe_config({
        "services": {
            "weppcloud": {
                "environment": {
                    "JWT_SECRET_FILE": "/run/secrets/jwt",
                    "PUBLIC_SIGNING_PUBLIC_KEY": "not-secret",
                    "SERVICE_URL": "https://service.invalid/path?mode=public",
                }
            }
        }
    })


def test_atomic_private_json_refuses_late_concurrent_destination(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    destination = tmp_path / "approval.json"
    real_link = candidate.os.link

    def race_link(source, target, *, follow_symlinks):
        destination.write_text('{"winner":true}\n', encoding="utf-8")
        destination.chmod(0o600)
        return real_link(source, target, follow_symlinks=follow_symlinks)

    monkeypatch.setattr(candidate.os, "link", race_link)
    with pytest.raises(candidate.CandidateError, match="refusing to overwrite"):
        candidate.atomic_private_json(destination, {"winner": False})
    assert json.loads(destination.read_text(encoding="utf-8")) == {"winner": True}


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
    publish_args = argparse.Namespace(
        project_root=project,
        receipt=receipt_path,
        evidence_bundle=bundle,
        evidence_manifest_sha256=candidate.sha256_file(manifest),
        dispositions_sha256=disposition_hash,
        approver="reviewer",
        review_trigger="new evidence or candidate identity",
    )
    assert candidate.publish_approval(publish_args) == 0
    approval_path = Path(json.loads(capsys.readouterr().out)["approval"])
    assert approval_path.stat().st_mode & 0o777 == 0o600
    calls: list[list[str]] = []
    run_kwargs: list[dict[str, object]] = []

    def fake_subprocess_run(command, **kwargs):
        calls.append(command)
        run_kwargs.append(kwargs)
        return subprocess.CompletedProcess(command, 0, stdout='{"accepted":true}\n', stderr="")

    monkeypatch.setattr(candidate.subprocess, "run", fake_subprocess_run)

    assert candidate.validate_approval(receipt, receipt_path, project) == approval_path
    command = calls[0]
    assert command[command.index("--image-id") + 1] == _IMAGE_ID
    assert command[command.index("--source-revision") + 1] == _REVISION
    assert run_kwargs[0]["stdout"] is subprocess.PIPE
    assert run_kwargs[0]["stderr"] is subprocess.PIPE

    assert candidate.validate_command(
        _args(project, deploy_script, receipt_path), gate=True
    ) == 0
    assert json.loads(capsys.readouterr().out)["receipt"] == str(receipt_path)


def test_record_activation_atomically_retains_known_good_files(
    candidate_environment,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _project, _deploy_script, _ = candidate_environment
    receipt_path = _create(candidate_environment, capsys)
    known_files = []
    for name, raw in (
        ("compose.json", b'{"services":{}}\n'),
        ("override.json", b'{"services":{}}\n'),
        ("images.tsv", b"weppcloud\t" + _IMAGE_ID.encode() + b"\t1\n"),
    ):
        path = receipt_path.parent / name
        path.write_bytes(raw)
        path.chmod(0o600)
        known_files.append(path)
    args = argparse.Namespace(
        receipt=receipt_path,
        known_good_config=known_files[0],
        known_good_override=known_files[1],
        known_good_rows=known_files[2],
    )

    assert candidate.record_activation(args) == 0
    ledger_path = Path(json.loads(capsys.readouterr().out)["activation_ledger"])
    assert ledger_path.stat().st_mode & 0o777 == 0o600
    assert ledger_path.parent.stat().st_mode & 0o777 == 0o700
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    assert ledger["candidate_receipt_sha256"] == candidate.sha256_file(receipt_path)
    assert set(ledger["known_good_files"]) == {
        "known-good-compose.json",
        "known-good-override.json",
        "known-good-images.tsv",
    }
