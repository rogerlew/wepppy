"""Subprocess harness for the production deploy execution scenarios."""

from __future__ import annotations

import fcntl
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[2]
DEPLOY = _REPO_ROOT / "scripts" / "deploy-production.sh"
_FIXTURES = _REPO_ROOT / "tests" / "data" / "deploy_execution"


def _install_command(directory: Path, name: str) -> Path:
    target = directory / name
    shutil.copyfile(_FIXTURES / f"{name}.sh", target)
    target.chmod(0o755)
    return target


def _flag(enabled: bool) -> str:
    return "1" if enabled else "0"


def _execute(arguments: list[str], environment: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        arguments,
        cwd=_REPO_ROOT,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
        timeout=20,
    )


def _execute_deploy(
    arguments: tuple[str, ...], environment: dict[str, str], receipt: Path, skip_docker_prune: bool
) -> subprocess.CompletedProcess[str]:
    command = [str(DEPLOY), "--skip-pull", "--skip-themes"]
    if skip_docker_prune:
        command.append("--skip-docker-prune")
    command.extend(arguments)
    single_phase_options = {
        "--targeted-web", "--targeted-cap", "--targeted-batch", "--print-plan",
        "--skip-build", "--retain-images-from",
    }
    if single_phase_options.intersection(arguments):
        return _execute(command, environment)

    build = _execute([*command, "--build-retained-candidate"], environment)
    if build.returncode:
        return build
    resume = _execute([*command, "--resume-retained-candidate", str(receipt)], environment)
    return subprocess.CompletedProcess(
        resume.args, resume.returncode, build.stdout + resume.stdout, build.stderr + resume.stderr
    )


def run_deploy(
    tmp_path: Path,
    services: dict[str, object],
    *arguments: str,
    rq_probe_worker_stopped: bool = False,
    rq_probe_result: str = "0",
    candidate_mismatch: bool = False,
    recovery_failure: bool = False,
    stale_renderer: bool = False,
    local_worker_registration_failure: bool = False,
    catalog_registration_failure: bool = False,
    rq_fence_loss: bool = False,
    rq_renew_once: bool = False,
    rq_renew_transient_failure: bool = False,
    rq_renew_block_at_resume: bool = False,
    rq_renew_hangs_once: bool = False,
    rq_heartbeat_failure: bool = False,
    rq_renew_after_stop: bool = False,
    rq_resume_failure: bool = False,
    rq_resume_reply_lost: bool = False,
    rq_pre_suspended: bool = False,
    rq_competing_deploy: bool = False,
    rq_acquire_reply_lost: bool = False,
    controller_backup_failure: bool = False,
    caddy_inspection_failure: bool = False,
    gate_failure_call: int = 0,
    governance_failure: bool = False,
    worker_stops_after_stop: bool = False,
    controller_build_failure: bool = False,
    shape_readiness_failure: bool = False,
    shape_stop_failure: bool = False,
    shape_discovery_failure: bool = False,
    shape_ps_failure: bool = False,
    shape_git_status_failure: bool = False,
    shape_build_inputs_clean: bool = True,
    shape_dirty_build_input: str = "wepppy/microservices/shape_converter/convert.py",
    compose_files: str | None = None,
    preset_query_failure: bool = False,
    compose_render_failure: bool = False,
    lock_held: bool = False,
    skip_docker_prune: bool = True,
    recovery_health_delay_checks: int = 0,
    recovery_registration_delay_checks: int = 0,
    running_map_drift_before_stop: bool = False,
    new_service: str = "",
    stopped_new_service: bool = False,
    new_inventory_failure: bool = False,
    new_cleanup_failure: bool = False,
    import_images_failure: bool = False,
) -> tuple[subprocess.CompletedProcess[str], list[str]]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(parents=True)
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    command_log = tmp_path / "commands.log"

    for name in ("wctl", "docker", "python3", "curl", "git", "sleep", "cp"):
        _install_command(bin_dir, name)
    cap_validator = _install_command(tmp_path, "cap-validator")
    cap_preparer = _install_command(tmp_path, "cap-preparer")
    weppcloudr_validator = _install_command(tmp_path, "weppcloudr-validator")
    controller_builder = tmp_path / "controller_builder.py"
    shutil.copyfile(_FIXTURES / controller_builder.name, controller_builder)
    controller_target = tmp_path / "controllers-gl.js"
    controller_target.write_text("known-good controllers", encoding="utf-8")
    fake_receipt = state_dir / "receipt.json"
    fake_receipt.write_text("{}\n", encoding="utf-8")
    fake_approval = state_dir / "approval.json"
    fake_approval.write_text("{}\n", encoding="utf-8")
    fake_activation = state_dir / "activation-compose.json"
    fake_activation.write_text(json.dumps({"services": services}), encoding="utf-8")
    fake_override = state_dir / "image-override.json"
    fake_override.write_text(
        json.dumps(
            {
                "services": {
                    name: {"image": "sha256:" + "0" * 63 + "1"}
                    for name, definition in services.items()
                    if isinstance(definition, dict) and definition.get("image")
                }
            }
        ),
        encoding="utf-8",
    )

    records = [
        {
            "Service": service,
            "Name": f"cid-{service}",
            "State": "running",
            "Health": "healthy",
        }
        for service, definition in services.items()
        if not isinstance(definition, dict)
        or (definition.get("deploy") or {}).get("replicas") != 0
    ]
    starting_records = [dict(record, Health="starting") for record in records]
    if compose_files is None:
        if "weppcloud" in services:
            compose_files = "docker/docker-compose.prod.yml"
        elif set(services) == {"rq-worker-fork-archive", "rq-worker-query-catalog"}:
            compose_files = "docker/docker-compose.prod.wepp3.yml"
        else:
            compose_files = "docker/docker-compose.prod.worker.yml"

    environment = os.environ.copy()
    environment.update(
        {
            "PATH": f"{bin_dir}:{environment['PATH']}",
            "FAKE_RQ_PROBE_WORKER_STOPPED": _flag(rq_probe_worker_stopped),
            "FAKE_RQ_PROBE_RESULT": rq_probe_result,
            "FAKE_COMMAND_LOG": str(command_log),
            "FAKE_SERVICES": "\n".join(services),
            "FAKE_NEW_SERVICE": new_service,
            "FAKE_KNOWN_ROWS_RETAINED": str(state_dir / "retained-images.tsv"),
            "FAKE_IMPORT_IMAGES_FAILURE": _flag(import_images_failure),
            "FAKE_STOPPED_NEW_SERVICE": _flag(stopped_new_service),
            "FAKE_NEW_INVENTORY_FAILURE": _flag(new_inventory_failure),
            "FAKE_NEW_CLEANUP_FAILURE": _flag(new_cleanup_failure),
            "FAKE_NEW_MARKER": str(tmp_path / "introduced-service-running"),
            "FAKE_COMPOSE_FILES": compose_files,
            "FAKE_PRESET_QUERY_FAILURE": _flag(preset_query_failure),
            "FAKE_COMPOSE_RENDER_FAILURE": _flag(compose_render_failure),
            "FAKE_CONFIG": json.dumps({"services": services}),
            "FAKE_PS": json.dumps(records),
            "FAKE_CANDIDATE_MISMATCH": _flag(candidate_mismatch),
            "FAKE_RECOVERY_FAILURE": _flag(recovery_failure),
            "FAKE_STALE_RENDERER": _flag(stale_renderer),
            "FAKE_CATALOG_REGISTRATION_FAILURE": _flag(catalog_registration_failure),
            "FAKE_LOCAL_WORKER_REGISTRATION_FAILURE": _flag(local_worker_registration_failure),
            "FAKE_FENCE_LOSS": _flag(rq_fence_loss),
            "FAKE_RENEW_ONCE": _flag(rq_renew_once),
            "FAKE_RQ_RENEW_TRANSIENT_FAILURE": _flag(rq_renew_transient_failure),
            "FAKE_RQ_RENEW_BLOCK_AT_RESUME": _flag(rq_renew_block_at_resume),
            "FAKE_RQ_RENEW_HANGS_ONCE": _flag(rq_renew_hangs_once),
            "FAKE_HEARTBEAT_FAILURE": _flag(rq_heartbeat_failure),
            "FAKE_RQ_RENEW_AFTER_STOP": _flag(rq_renew_after_stop),
            "FAKE_RQ_RESUME_FAILURE": _flag(rq_resume_failure),
            "FAKE_RQ_RESUME_REPLY_LOST": _flag(rq_resume_reply_lost),
            "FAKE_RQ_PRE_SUSPENDED": _flag(rq_pre_suspended),
            "FAKE_RQ_COMPETING_DEPLOY": _flag(rq_competing_deploy),
            "FAKE_RQ_ACQUIRE_REPLY_LOST": _flag(rq_acquire_reply_lost),
            "FAKE_CONTROLLER_BACKUP_FAILURE": _flag(controller_backup_failure),
            "FAKE_CADDY_INSPECTION_FAILURE": _flag(caddy_inspection_failure),
            "FAKE_FENCE_ASSERT_COUNT": str(tmp_path / "fence-assert-count"),
            "FAKE_RENEWAL_SEEN": str(tmp_path / "renewal-seen"),
            "FAKE_RENEW_ONCE_MARKER": str(tmp_path / "renew-once-marker"),
            "FAKE_RQ_RENEW_FAILURE_MARKER": str(tmp_path / "renew-failure-marker"),
            "FAKE_RQ_RENEW_HANG_MARKER": str(tmp_path / "renew-hang-marker"),
            "FAKE_RQ_RENEW_CALL_COUNT": str(tmp_path / "renew-call-count"),
            "FAKE_RQ_ACQUIRE_REPLY_MARKER": str(tmp_path / "acquire-reply-marker"),
            "FAKE_RQ_RESUME_REPLY_MARKER": str(tmp_path / "resume-reply-marker"),
            "RQ_FENCE_CONTROL_TIMEOUT_SECONDS": "0.1" if rq_renew_hangs_once else "10",
            "RQ_FENCE_RENEW_RETRIES": "1" if rq_heartbeat_failure else "20",
            "RQ_FENCE_RETRY_DELAY_SECONDS": "0.01",
            "FAKE_CONTROLLER_FAILURE": _flag(controller_build_failure),
            "FAKE_SHAPE_READINESS_FAILURE": _flag(shape_readiness_failure),
            "FAKE_SHAPE_STOP_FAILURE": _flag(shape_stop_failure),
            "FAKE_SHAPE_DISCOVERY_FAILURE": _flag(shape_discovery_failure),
            "FAKE_SHAPE_PS_FAILURE": _flag(shape_ps_failure),
            "FAKE_SHAPE_GIT_STATUS_FAILURE": _flag(shape_git_status_failure),
            "FAKE_SHAPE_BUILD_INPUTS_CLEAN": _flag(shape_build_inputs_clean),
            "FAKE_SHAPE_DIRTY_BUILD_INPUT": shape_dirty_build_input,
            "FAKE_SHAPE_STOPPED_MARKER": str(tmp_path / "shape-stopped"),
            "FAKE_SHAPE_PS_CALL_COUNT": str(tmp_path / "shape-ps-call-count"),
            "CAP_RUNTIME_VALIDATOR": str(cap_validator),
            "CAP_RUNTIME_PREPARER": str(cap_preparer),
            "WEPPCLOUDR_RUNTIME_VALIDATOR": str(weppcloudr_validator),
            "CONTROLLERS_JS_BUILDER": str(controller_builder),
            "CONTROLLERS_JS_TARGET": str(controller_target),
            "DEPLOY_LOCK_FILE": str(tmp_path / "deploy.lock"),
            "DEPLOY_STATE_DIR": str(state_dir),
            "HEALTHCHECK_URL": "https://forest.invalid/weppcloud/health",
            "RQ_ENGINE_HEALTHCHECK_URL": "https://forest.invalid/rq-engine/health",
            "CAP_HEALTHCHECK_URL": "https://forest.invalid/cap/health",
            "WCTL_COMPOSE_RETRIES": "1",
            "RQ_DRAIN_TIMEOUT_SECONDS": "10" if rq_probe_result == "0" else "0",
            "REAL_PYTHON": sys.executable,
            "FAKE_RECEIPT": str(fake_receipt),
            "FAKE_APPROVAL": str(fake_approval),
            "FAKE_ACTIVATION_CONFIG": str(fake_activation),
            "FAKE_IMAGE_OVERRIDE": str(fake_override),
            "FAKE_GATE_COUNT": str(state_dir / "gate-count"),
            "FAKE_GATE_FAILURE_CALL": str(gate_failure_call),
            "FAKE_GOVERNANCE_FAILURE": _flag(governance_failure),
            "FAKE_STOPPED_WORKER_AFTER_STOP": _flag(worker_stops_after_stop),
            "FAKE_WORKER_STOPPED_MARKER": str(state_dir / "worker-stopped"),
            "FAKE_RECOVERY_STARTED_MARKER": str(state_dir / "recovery-started"),
            "FAKE_RECOVERY_HEALTH_COUNT": str(state_dir / "recovery-health-count"),
            "FAKE_RECOVERY_REGISTRATION_COUNT": str(state_dir / "recovery-registration-count"),
            "FAKE_RECOVERY_HEALTH_DELAY_CHECKS": str(recovery_health_delay_checks),
            "FAKE_RECOVERY_REGISTRATION_DELAY_CHECKS": str(recovery_registration_delay_checks),
            "FAKE_PS_STARTING": json.dumps(starting_records),
            "KNOWN_GOOD_READINESS_ATTEMPTS": "10",
            "KNOWN_GOOD_READINESS_DELAY_SECONDS": "0.01",
            "FAKE_RUNNING_MAP_DRIFT": _flag(running_map_drift_before_stop),
        }
    )
    with (tmp_path / "deploy.lock").open("a", encoding="utf-8") as lock_handle:
        if lock_held:
            fcntl.flock(lock_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        result = _execute_deploy(arguments, environment, fake_receipt, skip_docker_prune)
    commands = (
        command_log.read_text(encoding="utf-8").splitlines()
        if command_log.exists()
        else []
    )
    return result, commands
