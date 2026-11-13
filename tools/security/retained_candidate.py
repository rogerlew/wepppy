#!/usr/bin/env python3
"""Create and verify immutable host-local deployment candidate receipts."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import socket
import stat
import subprocess
import sys
import tempfile
from typing import Any


STORE_ROOT = Path("/workdir/weppcloud-deployments/.local/dependency-security")
POLICY_PATH = Path(
    "docs/work-packages/20261110_wepp1_dependency_security_gate/"
    "artifacts/20261110_scope_and_policy_decision.md"
)
LOCK_PATH = Path("wepppy/weppcloud/static-src/package-lock.json")
IMAGE_ID_RE = re.compile(r"sha256:[0-9a-f]{64}")
REVISION_RE = re.compile(r"[0-9a-f]{40}")
HASH_RE = re.compile(r"[0-9a-f]{64}")
DEPENDENCY_SERVICES = (
    "weppcloud",
    "rq-worker",
    "rq-worker-batch",
)
RECEIPT_FIELDS = {
    "schema_version", "created_at", "hostname", "machine_id_sha256",
    "docker_engine_id", "source_revision", "source_clean", "exit_status",
    "static_build_lock_sha256", "deploy_script_sha256", "wctl_path",
    "wctl_sha256", "deploy_mode", "deploy_options", "compose_config_sha256",
    "activation_config_sha256", "image_override_sha256", "build_services",
    "recreated_services", "images", "dependency_service", "image_id",
}
APPROVAL_FIELDS = {
    "schema_version", "candidate_receipt_sha256", "evidence_bundle",
    "evidence_manifest_sha256", "policy_sha256", "dispositions_sha256",
    "approved_at", "approver", "review_trigger",
}
IMAGE_FIELDS = {"service", "source_image", "image_id"}


class CandidateError(ValueError):
    """The retained candidate violates its trust or identity contract."""


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise CandidateError("duplicate JSON key")
        value[key] = item
    return value


def load_object(raw: bytes, label: str) -> dict[str, Any]:
    value = json.loads(raw, object_pairs_hook=unique_object)
    if not isinstance(value, dict):
        raise CandidateError(f"{label} must contain one JSON object")
    return value


def run(*command: str, cwd: Path) -> str:
    result = subprocess.run(
        command,
        cwd=cwd,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout.strip()


def private_directory(path: Path, *, create: bool = False) -> Path:
    if create:
        path.mkdir(mode=0o700, parents=True, exist_ok=True)
    metadata = path.lstat()
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or stat.S_IMODE(metadata.st_mode) != 0o700
        or metadata.st_uid != os.geteuid()
    ):
        raise CandidateError(f"{path} must be an operator-owned 0700 directory")
    return path.resolve(strict=True)


def private_file(path: Path) -> bytes:
    metadata = path.lstat()
    if (
        not stat.S_ISREG(metadata.st_mode)
        or stat.S_IMODE(metadata.st_mode) != 0o600
        or metadata.st_uid != os.geteuid()
    ):
        raise CandidateError(f"{path} must be an operator-owned 0600 regular file")
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(descriptor, "rb") as stream:
        before = os.fstat(stream.fileno())
        raw = stream.read()
        after = os.fstat(stream.fileno())
    identity = lambda item: (item.st_dev, item.st_ino, item.st_size, item.st_mtime_ns, item.st_ctime_ns)
    if identity(before) != identity(after):
        raise CandidateError(f"{path} changed while read")
    return raw


def write_private(path: Path, raw: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def machine_id_hash() -> str:
    raw = Path("/etc/machine-id").read_bytes().strip()
    if not raw:
        raise CandidateError("host machine ID is unavailable")
    return sha256_bytes(raw)


def compose_config() -> dict[str, Any]:
    raw = sys.stdin.buffer.read()
    if not raw:
        raise CandidateError("effective Compose JSON is required on stdin")
    return load_object(raw, "Compose configuration")


def immutable_image_id(image: str, project_root: Path) -> str:
    image_id = run(
        "docker", "image", "inspect", "--format", "{{.Id}}", image,
        cwd=project_root,
    )
    if IMAGE_ID_RE.fullmatch(image_id) is None:
        raise CandidateError(f"image {image!r} has no immutable image ID")
    return image_id


def base_state(args: argparse.Namespace, config: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    project_root = args.project_root.resolve(strict=True)
    revision = run("git", "rev-parse", "HEAD", cwd=project_root)
    if REVISION_RE.fullmatch(revision) is None:
        raise CandidateError("source revision is not an exact Git commit")
    dirty = run("git", "status", "--porcelain=v1", "--untracked-files=all", cwd=project_root)
    if dirty:
        raise CandidateError("source worktree must be clean")

    services = config.get("services")
    if not isinstance(services, dict):
        raise CandidateError("Compose configuration has no services object")
    built_images: dict[str, str] = {}
    for service_name in args.build_service:
        service = services.get(service_name)
        if not isinstance(service, dict) or "build" not in service:
            raise CandidateError(f"build service {service_name!r} is not locally built")
        source_image = service.get("image")
        if not isinstance(source_image, str) or not source_image:
            raise CandidateError(f"build service {service_name!r} has no image")
        built_images[source_image] = immutable_image_id(source_image, project_root)

    images: list[dict[str, str]] = []
    override_services: dict[str, dict[str, str]] = {}
    for service_name in args.recreated_service:
        service = services.get(service_name)
        if not isinstance(service, dict):
            raise CandidateError(f"recreated service {service_name!r} is absent")
        source_image = service.get("image")
        if not isinstance(source_image, str) or not source_image:
            raise CandidateError(f"recreated service {service_name!r} has no image")
        image_id = built_images.get(source_image)
        if image_id is None:
            image_id = immutable_image_id(source_image, project_root)
        images.append({
            "service": service_name,
            "source_image": source_image,
            "image_id": image_id,
        })
        override_services[service_name] = {"image": image_id}
    if not images:
        raise CandidateError("deployment selection has no locally built recreated image")
    dependency_row = next(
        (row for name in DEPENDENCY_SERVICES for row in images if row["service"] == name),
        None,
    )
    if dependency_row is None:
        raise CandidateError("deployment selection has no dependency-gated common image")

    wctl_command = shutil.which("wctl")
    if wctl_command is None:
        raise CandidateError("installed wctl executable cannot be identified")
    wctl_path = Path(wctl_command).resolve(strict=True)
    if not wctl_path.is_file():
        raise CandidateError("installed wctl executable cannot be identified")
    deploy_script = args.deploy_script.resolve(strict=True)
    lock_path = (project_root / LOCK_PATH).resolve(strict=True)
    activation_raw = canonical_json(config) + b"\n"
    override = {"services": override_services}
    override_raw = canonical_json(override) + b"\n"
    docker_engine_id = run("docker", "info", "--format", "{{.ID}}", cwd=project_root)
    if not docker_engine_id:
        raise CandidateError("Docker Engine ID is unavailable")
    state = {
        "schema_version": 1,
        "hostname": socket.gethostname(),
        "machine_id_sha256": machine_id_hash(),
        "docker_engine_id": docker_engine_id,
        "source_revision": revision,
        "source_clean": True,
        "exit_status": 0,
        "static_build_lock_sha256": sha256_file(lock_path),
        "deploy_script_sha256": sha256_file(deploy_script),
        "wctl_path": str(wctl_path),
        "wctl_sha256": sha256_file(wctl_path),
        "deploy_mode": args.deploy_mode,
        "deploy_options": args.deploy_option,
        "compose_config_sha256": sha256_bytes(activation_raw),
        "activation_config_sha256": sha256_bytes(activation_raw),
        "image_override_sha256": sha256_bytes(override_raw),
        "build_services": args.build_service,
        "recreated_services": args.recreated_service,
        "images": images,
        "dependency_service": dependency_row["service"],
        "image_id": dependency_row["image_id"],
    }
    return state, {"activation": activation_raw, "override": override_raw}


def candidate_host_root(*, create: bool) -> Path:
    store = private_directory(STORE_ROOT, create=create)
    candidates = private_directory(store / "candidates", create=create)
    return private_directory(candidates / machine_id_hash(), create=create)


def approval_path(receipt_path: Path) -> Path:
    store = private_directory(STORE_ROOT)
    approvals = private_directory(store / "approvals")
    host_approvals = private_directory(approvals / machine_id_hash())
    return host_approvals / f"{sha256_file(receipt_path)}.json"


def create_candidate(args: argparse.Namespace) -> int:
    config = compose_config()
    state, files = base_state(args, config)
    host_root = candidate_host_root(create=True)
    temporary = Path(tempfile.mkdtemp(prefix=".candidate-", dir=host_root))
    os.chmod(temporary, 0o700)
    try:
        write_private(temporary / "activation-compose.json", files["activation"])
        write_private(temporary / "image-override.json", files["override"])
        state["created_at"] = datetime.now(timezone.utc).isoformat()
        write_private(temporary / "receipt.json", canonical_json(state) + b"\n")
        fsync_directory(temporary)
        candidate_name = f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{state['source_revision'][:12]}-{temporary.name[-6:]}"
        destination = host_root / candidate_name
        os.rename(temporary, destination)
        fsync_directory(host_root)
    finally:
        if temporary.exists():
            for child in temporary.iterdir():
                child.unlink()
            temporary.rmdir()
    receipt = destination / "receipt.json"
    print(json.dumps({
        "receipt": str(receipt),
        "receipt_sha256": sha256_file(receipt),
        "approval": str(
            STORE_ROOT.resolve(strict=True) / "approvals" / machine_id_hash()
            / f"{sha256_file(receipt)}.json"
        ),
    }, sort_keys=True))
    return 0


def validate_candidate(args: argparse.Namespace) -> tuple[dict[str, Any], Path, Path, Path]:
    receipt_path = args.receipt.absolute()
    receipt_raw = private_file(receipt_path)
    host_root = candidate_host_root(create=False)
    resolved_receipt = receipt_path.resolve(strict=True)
    try:
        resolved_receipt.relative_to(host_root)
    except ValueError as error:
        raise CandidateError("receipt is outside the canonical host candidate root") from error
    if resolved_receipt.name != "receipt.json":
        raise CandidateError("candidate receipt must be named receipt.json")
    candidate_dir = private_directory(resolved_receipt.parent)
    receipt = load_object(receipt_raw, "candidate receipt")
    if set(receipt) != RECEIPT_FIELDS or receipt.get("schema_version") != 1:
        raise CandidateError("unsupported candidate receipt schema")
    images = receipt.get("images")
    if not isinstance(images, list) or not images or any(
        not isinstance(row, dict) or set(row) != IMAGE_FIELDS for row in images
    ):
        raise CandidateError("invalid candidate image map")
    activation_path = candidate_dir / "activation-compose.json"
    override_path = candidate_dir / "image-override.json"
    activation_raw = private_file(activation_path)
    override_raw = private_file(override_path)
    if sha256_bytes(activation_raw) != receipt["activation_config_sha256"]:
        raise CandidateError("retained activation configuration hash mismatch")
    if sha256_bytes(override_raw) != receipt["image_override_sha256"]:
        raise CandidateError("retained image override hash mismatch")
    current, _ = base_state(args, compose_config())
    created_at = receipt.pop("created_at")
    if not isinstance(created_at, str) or receipt != current:
        raise CandidateError("candidate no longer matches host, source, configuration, or images")
    receipt["created_at"] = created_at
    for row in images:
        if immutable_image_id(row["image_id"], args.project_root.resolve(strict=True)) != row["image_id"]:
            raise CandidateError("retained image ID is unavailable")
    return receipt, resolved_receipt, activation_path, override_path


def validate_approval(receipt: dict[str, Any], receipt_path: Path, project_root: Path) -> Path:
    path = approval_path(receipt_path)
    approval = load_object(private_file(path), "operator approval")
    if set(approval) != APPROVAL_FIELDS or approval.get("schema_version") != 1:
        raise CandidateError("unsupported operator approval schema")
    if approval["candidate_receipt_sha256"] != sha256_file(receipt_path):
        raise CandidateError("operator approval targets another candidate")
    for key in ("evidence_manifest_sha256", "policy_sha256", "dispositions_sha256"):
        if not isinstance(approval[key], str) or HASH_RE.fullmatch(approval[key]) is None:
            raise CandidateError(f"invalid {key}")
    for key in ("approver", "review_trigger"):
        if not isinstance(approval[key], str) or not approval[key].strip():
            raise CandidateError(f"missing {key}")
    approved_at = datetime.fromisoformat(str(approval["approved_at"]).replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    if approved_at.tzinfo is None or not now - timedelta(hours=24) <= approved_at <= now + timedelta(minutes=5):
        raise CandidateError("operator approval is stale or future-dated")

    evidence_root = private_directory(STORE_ROOT / "evidence")
    bundle = Path(str(approval["evidence_bundle"])).resolve(strict=True)
    try:
        bundle.relative_to(evidence_root)
    except ValueError as error:
        raise CandidateError("evidence bundle is outside the canonical private store") from error
    manifest = bundle / "manifest.json"
    if sha256_file(manifest) != approval["evidence_manifest_sha256"]:
        raise CandidateError("evidence manifest hash mismatch")
    policy = (project_root / POLICY_PATH).resolve(strict=True)
    if sha256_file(policy) != approval["policy_sha256"]:
        raise CandidateError("policy hash mismatch")
    dispositions = private_directory(STORE_ROOT / "approvals" / "dispositions") / f"{approval['dispositions_sha256']}.json"
    if sha256_bytes(private_file(dispositions)) != approval["dispositions_sha256"]:
        raise CandidateError("disposition hash mismatch")
    command = [
        sys.executable,
        str(project_root / "tools/security/evaluate_dependency_evidence.py"),
        "--bundle", str(bundle),
        "--manifest-hash", approval["evidence_manifest_sha256"],
        "--image-id", receipt["image_id"],
        "--lock-hash", receipt["static_build_lock_sha256"],
        "--source-revision", receipt["source_revision"],
        "--policy", str(policy),
        "--policy-hash", approval["policy_sha256"],
        "--dispositions", str(dispositions),
        "--dispositions-hash", approval["dispositions_sha256"],
    ]
    result = subprocess.run(command, cwd=project_root, check=False)
    if result.returncode != 0:
        raise CandidateError("dependency evidence policy rejected the candidate")
    return path


def validate_command(args: argparse.Namespace, *, gate: bool) -> int:
    receipt, receipt_path, activation_path, override_path = validate_candidate(args)
    approval = validate_approval(receipt, receipt_path, args.project_root.resolve(strict=True)) if gate else None
    print(json.dumps({
        "receipt": str(receipt_path),
        "activation_config": str(activation_path),
        "image_override": str(override_path),
        "approval": str(approval) if approval else str(approval_path(receipt_path)),
    }, sort_keys=True))
    return 0


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    commands = result.add_subparsers(dest="command", required=True)
    for name in ("create", "validate", "gate"):
        command = commands.add_parser(name)
        command.add_argument("--project-root", type=Path, required=True)
        command.add_argument("--deploy-script", type=Path, required=True)
        command.add_argument("--deploy-mode", choices=("full", "worker"), required=True)
        command.add_argument("--deploy-option", action="append", default=[])
        command.add_argument("--build-service", action="append", required=True)
        command.add_argument("--recreated-service", action="append", required=True)
        if name != "create":
            command.add_argument("--receipt", type=Path, required=True)
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "create":
            return create_candidate(args)
        return validate_command(args, gate=args.command == "gate")
    except (
        CandidateError,
        json.JSONDecodeError,
        OSError,
        subprocess.SubprocessError,
        TypeError,
        KeyError,
    ) as error:
        print(f"Retained candidate rejected: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
