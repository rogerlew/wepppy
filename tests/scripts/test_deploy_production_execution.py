from __future__ import annotations

import fcntl
import json
import os
import subprocess
from pathlib import Path

import pytest


pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEPLOY = _REPO_ROOT / "scripts" / "deploy-production.sh"
_RQ_SUSPEND = "from rq.suspension import is_suspended, suspend"
_RQ_RENEW = "from rq.suspension import suspend"
_RQ_RESUME = "from rq.suspension import resume"


def _write_executable(path: Path, source: str) -> None:
    path.write_text(source, encoding="utf-8")
    path.chmod(0o755)


def _service(image: str, *, build: bool = True) -> dict[str, object]:
    result: dict[str, object] = {"image": image}
    if build:
        result["build"] = {"context": ".."}
    return result


def _run_deploy(
    tmp_path: Path,
    services: dict[str, object],
    *arguments: str,
    candidate_mismatch: bool = False,
    recovery_failure: bool = False,
    stale_renderer: bool = False,
    local_worker_registration_failure: bool = False,
    rq_fence_loss: bool = False,
    rq_renew_once: bool = False,
    rq_renew_transient_failure: bool = False,
    rq_renew_block_at_resume: bool = False,
    rq_renew_hangs_once: bool = False,
    rq_heartbeat_failure: bool = False,
    rq_resume_failure: bool = False,
    rq_pre_suspended: bool = False,
    rq_competing_deploy: bool = False,
    controller_backup_failure: bool = False,
    caddy_inspection_failure: bool = False,
    controller_build_failure: bool = False,
    lock_held: bool = False,
    skip_docker_prune: bool = True,
) -> tuple[subprocess.CompletedProcess[str], list[str]]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(parents=True)
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    command_log = tmp_path / "commands.log"

    _write_executable(
        bin_dir / "wctl",
        r'''#!/bin/bash
set -euo pipefail
printf 'wctl|%s\n' "$*" >> "${FAKE_COMMAND_LOG}"
args="$*"
if [[ "${args}" == *"config --services"* ]]; then
    printf '%s\n' "${FAKE_SERVICES}"
elif [[ "${args}" == *"config --format json"* ]]; then
    printf '%s\n' "${FAKE_CONFIG}"
elif [[ "${args}" == *"docker compose config"* ]]; then
    printf '%s\n' "${FAKE_CONFIG}"
elif [[ "${args}" == *"ps --status running --services"* ]]; then
    printf '%s\n' "${FAKE_SERVICES}"
elif [[ "${args}" == *"ps --all --format json"* ]]; then
    printf '%s\n' "${FAKE_PS}"
elif [[ "${args}" == *" ps "* && "${args}" == *" -q "* ]] \
    || [[ "${args}" == *" ps -q "* ]]; then
    service="${!#}"
    printf 'cid-%s\n' "${service}"
elif [[ "${args}" == *"StartedJobRegistry"* ]]; then
    printf '0\n'
elif [[ "${args}" == *"from rq.suspension import is_suspended, suspend"* ]]; then
    printf 'rq-token|acquire|%s\n' "${!#}" >> "${FAKE_COMMAND_LOG}"
    if [ "${FAKE_RQ_COMPETING_DEPLOY:-0}" = 1 ]; then
        echo 'another deployment owns the RQ fence' >&2
        exit 79
    fi
    if [ "${FAKE_RQ_PRE_SUSPENDED:-0}" = 1 ]; then
        echo 'RQ is already suspended by an external operator' >&2
        exit 80
    fi
    printf 'no\n'
elif [[ "${args}" == *"from rq.suspension import suspend"* ]]; then
    printf 'rq-token|renew|%s\n' "${!#}" >> "${FAKE_COMMAND_LOG}"
    : > "${FAKE_RENEWAL_SEEN}"
    renew_call_count=0
    [ ! -f "${FAKE_RQ_RENEW_CALL_COUNT}" ] \
        || renew_call_count="$(cat "${FAKE_RQ_RENEW_CALL_COUNT}")"
    renew_call_count=$((renew_call_count + 1))
    printf '%s\n' "${renew_call_count}" > "${FAKE_RQ_RENEW_CALL_COUNT}"
    if [ "${FAKE_RQ_RENEW_HANGS_ONCE:-0}" = 1 ] \
        && [ "${renew_call_count}" -le 2 ]; then
        /bin/sleep 5
    fi
    if [ "${FAKE_RQ_RENEW_BLOCK_AT_RESUME:-0}" = 1 ]; then
        /bin/sleep 0.2
        printf 'rq-token|renew-complete|%s\n' "${!#}" >> "${FAKE_COMMAND_LOG}"
    fi
    if [ "${FAKE_RQ_RENEW_TRANSIENT_FAILURE:-0}" = 1 ] \
        && [ "${renew_call_count}" -le 2 ]; then
        exit 75
    fi
    if [ "${FAKE_HEARTBEAT_FAILURE:-0}" = 1 ]; then
        exit 75
    fi
elif [[ "${args}" == *"from rq.suspension import is_suspended"* ]]; then
    printf 'rq-token|assert|%s\n' "${!#}" >> "${FAKE_COMMAND_LOG}"
    count=0
    [ ! -f "${FAKE_FENCE_ASSERT_COUNT}" ] || count="$(cat "${FAKE_FENCE_ASSERT_COUNT}")"
    count=$((count + 1))
    printf '%s\n' "${count}" > "${FAKE_FENCE_ASSERT_COUNT}"
    if [ "${FAKE_RENEW_ONCE:-0}" = 1 ] || [ "${FAKE_HEARTBEAT_FAILURE:-0}" = 1 ]; then
        for _attempt in $(seq 1 100); do
            [ -f "${FAKE_RENEWAL_SEEN}" ] && break
            /bin/sleep 0.01
        done
        /bin/sleep 0.02
    fi
    if [ "${FAKE_RQ_RENEW_TRANSIENT_FAILURE:-0}" = 1 ] \
        || [ "${FAKE_RQ_RENEW_HANGS_ONCE:-0}" = 1 ]; then
        for _attempt in $(seq 1 200); do
            renew_call_count=0
            [ ! -f "${FAKE_RQ_RENEW_CALL_COUNT}" ] \
                || renew_call_count="$(cat "${FAKE_RQ_RENEW_CALL_COUNT}")"
            [ "${renew_call_count}" -ge 3 ] && break
            /bin/sleep 0.01
        done
    fi
    if [ "${FAKE_FENCE_LOSS:-0}" = 1 ] && [ "${count}" -ge 2 ]; then
        printf 'no\n'
    else
        printf 'yes\n'
    fi
elif [[ "${args}" == *"from rq.suspension import resume"* ]]; then
    printf 'rq-token|resume|%s\n' "${!#}" >> "${FAKE_COMMAND_LOG}"
    if [ "${FAKE_RQ_RESUME_FAILURE:-0}" = 1 ]; then
        exit 78
    fi
elif [[ "${args}" == *"Worker.all"* ]]; then
    if [ "${FAKE_LOCAL_WORKER_REGISTRATION_FAILURE:-0}" = 1 ]; then
        printf '0:1\n'
    else
        printf '1:1\n'
    fi
elif [[ "${args}" == *"exec -T rq-worker hostname"* ]]; then
    printf 'default-worker-host\n'
elif [[ "${args}" == *"exec -T rq-worker-batch hostname"* ]]; then
    printf 'batch-worker-host\n'
elif [[ "${args}" == *"exec -T rq-worker-fork-archive id -u"* ]]; then
    printf '1002\n'
elif [[ "${args}" == *"exec -T rq-worker-fork-archive id -g"* ]]; then
    printf '130\n'
elif [[ "${args}" == *"exec -T rq-worker-fork-archive"* && "${args}" == *"fork-archive"* ]]; then
    printf '1:1\n'
elif [[ "${args}" == *"docker compose run"* ]]; then
    # The wepp3 preflight only needs the command to prove secret readability.
    :
elif [[ "${args}" == *"docker compose exec -T cap"* ]]; then
    :
elif [[ "${args}" == *"build --no-cache"* ]] \
    || [[ "${args}" == *"docker compose stop"* ]] \
    || [[ "${args}" == "up -d --force-recreate" || "${args}" == *" up -d"* ]] \
    || [[ "${args}" == "down" || "${args}" == *" down"* ]] \
    || [[ "${args}" == *" rq-info "* ]]; then
    :
else
    echo "unexpected wctl call: ${args}" >&2
    exit 90
fi
''',
    )
    _write_executable(
        bin_dir / "docker",
        r'''#!/bin/bash
set -euo pipefail
printf 'docker|%s\n' "$*" >> "${FAKE_COMMAND_LOG}"
if [ "${1:-}" = "inspect" ]; then
    format="${3:-}"
    container="${4:-}"
    case "${format}" in
        *State.Running*) printf 'true\n' ;;
        *RestartCount*) printf 'container-%s 0\n' "${container}" ;;
        *Image*)
            if [ "${FAKE_CANDIDATE_MISMATCH:-0}" = 1 ] && [ "${container}" = "cid-cap" ]; then
                printf 'sha-known-good\n'
            else
                printf 'sha-candidate\n'
            fi
            ;;
        *Mounts*) printf 'cap-data\n' ;;
        *) printf 'sha-candidate\n' ;;
    esac
elif [ "${1:-}" = "image" ] && [ "${2:-}" = "inspect" ]; then
    if [ "${3:-}" = "--format" ]; then
        printf 'sha-candidate\n'
    fi
elif [ "${1:-}" = "compose" ]; then
    if [[ "$*" == *" up -d --no-deps --force-recreate cap"* ]] \
        && [ "${FAKE_RECOVERY_FAILURE:-0}" = 1 ]; then
        exit 73
    fi
    if [[ "$*" == *" ps -q caddy"* ]]; then
        if [ "${FAKE_CADDY_INSPECTION_FAILURE:-0}" = 1 ]; then
            exit 76
        fi
        printf 'cid-caddy\n'
    fi
elif [ "${1:-}" = "builder" ] || [ "${1:-}" = "system" ] || [ "${1:-}" = "tag" ]; then
    :
else
    echo "unexpected docker call: $*" >&2
    exit 91
fi
''',
    )
    _write_executable(
        bin_dir / "curl",
        "#!/bin/bash\nset -euo pipefail\nprintf 'curl|%s\\n' \"$*\" >> \"${FAKE_COMMAND_LOG}\"\n",
    )
    _write_executable(
        bin_dir / "sleep",
        r'''#!/bin/bash
set -euo pipefail
if [ "${1:-}" != "30" ]; then
    exit 0
fi
exec >/dev/null 2>&1
if [ "${FAKE_RQ_RESUME_FAILURE:-0}" = 1 ]; then
    exit 1
fi
if [ "${FAKE_RENEW_ONCE:-0}" = 1 ] || [ "${FAKE_HEARTBEAT_FAILURE:-0}" = 1 ]; then
    if mkdir "${FAKE_RENEW_ONCE_MARKER}" 2>/dev/null; then
        exit 0
    fi
fi
deployment_parent="$(awk '{print $4}' "/proc/${PPID}/stat")"
while kill -0 "${deployment_parent}" 2>/dev/null; do
    /bin/sleep 0.02
done
''',
    )
    _write_executable(
        bin_dir / "cp",
        r'''#!/bin/bash
set -euo pipefail
if [ "${FAKE_CONTROLLER_BACKUP_FAILURE:-0}" = 1 ]; then
    exit 77
fi
exec /bin/cp "$@"
''',
    )

    cap_validator = tmp_path / "cap-validator"
    _write_executable(
        cap_validator,
        "#!/bin/bash\nprintf 'cap-validator|%s\\n' \"$*\" >> \"${FAKE_COMMAND_LOG}\"\n",
    )
    cap_preparer = tmp_path / "cap-preparer"
    _write_executable(
        cap_preparer,
        "#!/bin/bash\nprintf 'cap-preparer|%s\\n' \"$*\" >> \"${FAKE_COMMAND_LOG}\"\n",
    )
    weppcloudr_validator = tmp_path / "weppcloudr-validator"
    _write_executable(
        weppcloudr_validator,
        "#!/bin/bash\nset -euo pipefail\n"
        "printf 'weppcloudr-validator|%s\\n' \"$*\" >> \"${FAKE_COMMAND_LOG}\"\n"
        "if [ \"${FAKE_STALE_RENDERER:-0}\" = 1 ]; then exit 74; fi\n",
    )
    controller_builder = tmp_path / "controller_builder.py"
    controller_builder.write_text(
        "import argparse, os\nfrom pathlib import Path\n"
        "p=argparse.ArgumentParser(); p.add_argument('--output', required=True); a=p.parse_args()\n"
        "if os.environ.get('FAKE_CONTROLLER_FAILURE') == '1': raise SystemExit(72)\n"
        "Path(a.output).write_text('candidate controllers', encoding='utf-8')\n"
        "Path(os.environ['FAKE_COMMAND_LOG']).open('a', encoding='utf-8').write('controller-builder\\n')\n",
        encoding="utf-8",
    )
    controller_target = tmp_path / "controllers-gl.js"
    controller_target.write_text("known-good controllers", encoding="utf-8")

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
    environment = os.environ.copy()
    environment.update(
        {
            "PATH": f"{bin_dir}:{environment['PATH']}",
            "FAKE_COMMAND_LOG": str(command_log),
            "FAKE_SERVICES": "\n".join(services),
            "FAKE_CONFIG": json.dumps({"services": services}),
            "FAKE_PS": json.dumps(records),
            "FAKE_CANDIDATE_MISMATCH": "1" if candidate_mismatch else "0",
            "FAKE_RECOVERY_FAILURE": "1" if recovery_failure else "0",
            "FAKE_STALE_RENDERER": "1" if stale_renderer else "0",
            "FAKE_LOCAL_WORKER_REGISTRATION_FAILURE": (
                "1" if local_worker_registration_failure else "0"
            ),
            "FAKE_FENCE_LOSS": "1" if rq_fence_loss else "0",
            "FAKE_RENEW_ONCE": "1" if rq_renew_once else "0",
            "FAKE_RQ_RENEW_TRANSIENT_FAILURE": (
                "1" if rq_renew_transient_failure else "0"
            ),
            "FAKE_RQ_RENEW_BLOCK_AT_RESUME": (
                "1" if rq_renew_block_at_resume else "0"
            ),
            "FAKE_RQ_RENEW_HANGS_ONCE": "1" if rq_renew_hangs_once else "0",
            "FAKE_HEARTBEAT_FAILURE": "1" if rq_heartbeat_failure else "0",
            "FAKE_RQ_RESUME_FAILURE": "1" if rq_resume_failure else "0",
            "FAKE_RQ_PRE_SUSPENDED": "1" if rq_pre_suspended else "0",
            "FAKE_RQ_COMPETING_DEPLOY": "1" if rq_competing_deploy else "0",
            "FAKE_CONTROLLER_BACKUP_FAILURE": "1" if controller_backup_failure else "0",
            "FAKE_CADDY_INSPECTION_FAILURE": "1" if caddy_inspection_failure else "0",
            "FAKE_FENCE_ASSERT_COUNT": str(tmp_path / "fence-assert-count"),
            "FAKE_RENEWAL_SEEN": str(tmp_path / "renewal-seen"),
            "FAKE_RENEW_ONCE_MARKER": str(tmp_path / "renew-once-marker"),
            "FAKE_RQ_RENEW_FAILURE_MARKER": str(tmp_path / "renew-failure-marker"),
            "FAKE_RQ_RENEW_HANG_MARKER": str(tmp_path / "renew-hang-marker"),
            "FAKE_RQ_RENEW_CALL_COUNT": str(tmp_path / "renew-call-count"),
            "RQ_FENCE_CONTROL_TIMEOUT_SECONDS": "0.1" if rq_renew_hangs_once else "10",
            "RQ_FENCE_RENEW_RETRIES": "1" if rq_heartbeat_failure else "20",
            "RQ_FENCE_RETRY_DELAY_SECONDS": "0.01",
            "FAKE_CONTROLLER_FAILURE": "1" if controller_build_failure else "0",
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
        }
    )
    lock_handle = (tmp_path / "deploy.lock").open("a", encoding="utf-8")
    if lock_held:
        fcntl.flock(lock_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    try:
        deploy_arguments = [
            str(_DEPLOY),
            "--skip-pull",
            "--skip-themes",
        ]
        if skip_docker_prune:
            deploy_arguments.append("--skip-docker-prune")
        deploy_arguments.extend(arguments)
        result = subprocess.run(
            deploy_arguments,
            cwd=_REPO_ROOT,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
            timeout=20,
        )
    finally:
        lock_handle.close()
    commands = command_log.read_text(encoding="utf-8").splitlines()
    return result, commands


def _position(commands: list[str], fragment: str) -> int:
    return next(index for index, command in enumerate(commands) if fragment in command)


def _positions(commands: list[str], fragment: str) -> list[int]:
    return [index for index, command in enumerate(commands) if fragment in command]


def _rq_assert_positions(commands: list[str]) -> list[int]:
    return [
        index
        for index, command in enumerate(commands)
        if "from rq.suspension import is_suspended" in command and _RQ_SUSPEND not in command
    ]


def _rq_tokens(commands: list[str], operation: str) -> list[str]:
    prefix = f"rq-token|{operation}|"
    return [command.removeprefix(prefix) for command in commands if command.startswith(prefix)]


def _full_services_with_cap_and_renderer() -> dict[str, object]:
    return {
        "weppcloud": _service("wepppy:test"),
        "rq-engine": _service("wepppy:test"),
        "rq-worker": _service("wepppy:test"),
        "rq-worker-batch": _service("wepppy:test"),
        "weppcloudr": _service("weppcloudr:test"),
        "cap": _service("cap:test"),
        "caddy": _service("caddy:test", build=False),
        "redis": _service("redis:test", build=False),
    }


def test_full_execution_builds_then_stops_workers_and_recreates_without_down(tmp_path: Path) -> None:
    result, commands = _run_deploy(tmp_path, _full_services_with_cap_and_renderer())

    assert result.returncode == 0, result.stdout + result.stderr
    build = _position(commands, "wctl|build --no-cache weppcloud weppcloudr cap")
    renderer_validation = _position(
        commands,
        "weppcloudr-validator|weppcloudr:test wepppy:test",
    )
    cap_validation = _position(commands, "cap-validator|cap:test")
    suspend = _position(commands, _RQ_SUSPEND)
    stop = _position(commands, "stop --timeout 216000 rq-worker rq-worker-batch")
    cap_stop = _position(commands, "wctl|docker compose stop cap")
    start = _position(commands, "wctl|up -d --force-recreate")
    registration = _position(commands, "Worker.all")
    resume = _position(commands, _RQ_RESUME)
    fence_assertions = _rq_assert_positions(commands)
    assert build < renderer_validation < cap_validation < suspend < stop < cap_stop < start
    assert start < registration < fence_assertions[-1] < resume
    assert not any(command.endswith(" down") for command in commands)
    assert not any(command.startswith("docker|system prune") for command in commands)
    assert (tmp_path / "controllers-gl.js").read_text(encoding="utf-8") == "candidate controllers"
    assert not list(tmp_path.glob("controllers-gl.js.deploy.*"))
    assert "Published controllers-gl.js atomically" in result.stdout
    assert "CAP readiness and functional canary passed" in result.stdout
    assert "Skipping broad Docker runtime prune" in result.stdout
    assert "Deployment complete!" in result.stdout


def test_stale_renderer_is_rejected_before_cap_preparation_or_activation(tmp_path: Path) -> None:
    result, commands = _run_deploy(
        tmp_path,
        _full_services_with_cap_and_renderer(),
        stale_renderer=True,
    )

    assert result.returncode == 74
    assert any(command.startswith("weppcloudr-validator|") for command in commands)
    assert not any(command.startswith("cap-validator|") for command in commands)
    assert not any(command.startswith("cap-preparer|") for command in commands)
    assert not any("docker compose stop" in command for command in commands)
    assert not any("up -d" in command for command in commands)
    assert not any(_RQ_SUSPEND in command or _RQ_RESUME in command for command in commands)
    assert not any(command.startswith("docker|system prune") for command in commands)
    assert "Deployment complete!" not in result.stdout


def test_full_candidate_failure_recovers_cap_and_never_reports_success_or_prunes(tmp_path: Path) -> None:
    result, commands = _run_deploy(
        tmp_path,
        _full_services_with_cap_and_renderer(),
        candidate_mismatch=True,
    )

    assert result.returncode != 0
    suspend = _position(commands, _RQ_SUSPEND)
    activation = _position(commands, "wctl|up -d --force-recreate")
    resume = _position(commands, _RQ_RESUME)
    recovery = _position(commands, "docker|compose -f")
    caddy_check = _position(commands, "ps -q caddy")
    assert suspend < activation < recovery < caddy_check < resume
    assert "Known-good CAP rescue image restored" in result.stderr
    assert (tmp_path / "controllers-gl.js").read_text(encoding="utf-8") == "known-good controllers"
    assert "Restored the pre-deploy controllers bundle" in result.stderr
    assert not any(command.startswith("docker|system prune") for command in commands)
    assert "Deployment complete!" not in result.stdout


def test_targeted_web_recreates_only_web_boundaries_and_leaves_cap_workers_and_renderer_untouched(
    tmp_path: Path,
) -> None:
    result, commands = _run_deploy(
        tmp_path,
        _full_services_with_cap_and_renderer(),
        "--targeted-web",
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert any("wctl|build --no-cache weppcloud" in command for command in commands)
    assert any(
        "up -d --no-deps --force-recreate weppcloud rq-engine" in command
        for command in commands
    )
    assert not any(command.startswith("weppcloudr-validator|") for command in commands)
    assert not any(command.startswith("cap-validator|") for command in commands)
    assert not any(command.startswith("cap-preparer|") for command in commands)
    assert not any("stop --timeout 216000 rq-worker" in command for command in commands)
    assert not any("docker compose stop cap" in command for command in commands)
    assert not any(_RQ_SUSPEND in command or _RQ_RESUME in command for command in commands)
    assert not any(command.endswith(" down") for command in commands)
    assert not any(command.startswith("docker|system prune") for command in commands)
    assert "rq-engine is healthy" in result.stdout
    assert "Deployment complete!" in result.stdout


def test_concurrent_deploy_lock_fails_before_build_or_activation(tmp_path: Path) -> None:
    services = {
        "weppcloud": _service("wepppy:test"),
        "rq-worker": _service("wepppy:test"),
    }
    result, commands = _run_deploy(tmp_path, services, lock_held=True)

    assert result.returncode != 0
    assert "Another deployment holds" in result.stderr
    assert not any("build --no-cache" in command for command in commands)
    assert not any("up -d" in command for command in commands)


def test_controller_builder_failure_removes_staged_bundle_before_cutover(tmp_path: Path) -> None:
    services = {
        "weppcloud": _service("wepppy:test"),
        "rq-worker": _service("wepppy:test"),
    }
    result, commands = _run_deploy(tmp_path, services, controller_build_failure=True)

    assert result.returncode == 72
    assert not list(tmp_path.glob("controllers-gl.js.deploy.*"))
    assert (tmp_path / "controllers-gl.js").read_text(encoding="utf-8") == "known-good controllers"
    assert not any("up -d" in command for command in commands)


def test_controller_backup_failure_preserves_old_bundle_recovers_cap_and_resumes(tmp_path: Path) -> None:
    result, commands = _run_deploy(
        tmp_path,
        _full_services_with_cap_and_renderer(),
        controller_backup_failure=True,
    )

    assert result.returncode != 0
    recovery = _position(commands, "docker|compose -f")
    resume = _position(commands, _RQ_RESUME)
    assert recovery < resume
    assert (tmp_path / "controllers-gl.js").read_text(encoding="utf-8") == "known-good controllers"
    assert not any(command == "wctl|up -d --force-recreate" for command in commands)
    assert "Known-good CAP rescue image restored" in result.stderr
    assert "Deployment complete!" not in result.stdout


def test_worker_execution_warm_stops_before_down_and_recreates_worker_stack(tmp_path: Path) -> None:
    services = {
        "rq-worker": _service("wepppy:test"),
        "rq-worker-batch": _service("wepppy:test"),
        "weppcloudr": _service("weppcloudr:test", build=False),
    }
    result, commands = _run_deploy(tmp_path, services)

    assert result.returncode == 0, result.stdout + result.stderr
    suspend = _position(commands, _RQ_SUSPEND)
    stop = _position(commands, "stop --timeout 216000 rq-worker rq-worker-batch")
    down = _position(commands, "wctl|down")
    start = _position(commands, "wctl|up -d --force-recreate")
    registration = _position(commands, "Worker.all")
    resume = _position(commands, _RQ_RESUME)
    assert suspend < stop < down < start < registration < resume
    assert "Skipping WEPPcloud health check" in result.stdout


def test_worker_runtime_prune_is_fenced_after_acceptance_and_registration(tmp_path: Path) -> None:
    services = {
        "rq-worker": _service("wepppy:test"),
        "rq-worker-batch": _service("wepppy:test"),
        "weppcloudr": _service("weppcloudr:test", build=False),
    }
    result, commands = _run_deploy(
        tmp_path,
        services,
        skip_docker_prune=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    suspend = _position(commands, _RQ_SUSPEND)
    registration = _position(commands, "Worker.all")
    resume = _position(commands, _RQ_RESUME)
    prune = _position(commands, "docker|system prune -a -f")
    assert suspend < registration < resume < prune
    assert "Every locally built recreated service runs its candidate image" in result.stdout
    assert "Recreated services remained stable" in result.stdout
    assert "RQ default/batch workers are registered" in result.stdout
    assert "Deployment complete!" in result.stdout


def test_worker_renews_rq_fence_and_reasserts_it_before_resume(tmp_path: Path) -> None:
    services = {
        "rq-worker": _service("wepppy:test"),
        "rq-worker-batch": _service("wepppy:test"),
        "weppcloudr": _service("weppcloudr:test", build=False),
    }
    result, commands = _run_deploy(tmp_path, services, rq_renew_once=True)

    assert result.returncode == 0, result.stdout + result.stderr
    suspend = _position(commands, _RQ_SUSPEND)
    renewal = _position(commands, _RQ_RENEW)
    stop = _position(commands, "stop --timeout 216000 rq-worker rq-worker-batch")
    registration = _position(commands, "Worker.all")
    fence_assertions = _rq_assert_positions(commands)
    resume = _position(commands, _RQ_RESUME)
    assert suspend < renewal < stop < registration < fence_assertions[-1] < resume
    assert len(fence_assertions) >= 3
    acquisition_tokens = _rq_tokens(commands, "acquire")
    assert len(acquisition_tokens) == 1
    acquisition_token = acquisition_tokens[0]
    assert acquisition_token
    for operation in ("renew", "assert", "resume"):
        operation_tokens = _rq_tokens(commands, operation)
        assert operation_tokens
        assert set(operation_tokens) == {acquisition_token}


def test_worker_tolerates_transient_rq_renewal_failure_during_recreation(
    tmp_path: Path,
) -> None:
    services = {
        "rq-worker": _service("wepppy:test"),
        "rq-worker-batch": _service("wepppy:test"),
        "weppcloudr": _service("weppcloudr:test", build=False),
    }
    result, commands = _run_deploy(
        tmp_path,
        services,
        rq_renew_once=True,
        rq_renew_transient_failure=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert len(_positions(commands, _RQ_RENEW)) >= 3
    assert "Global RQ suspension heartbeat failed" not in result.stderr
    assert "Deployment complete!" in result.stdout


def test_worker_joins_inflight_renewal_before_resuming_rq(tmp_path: Path) -> None:
    services = {
        "rq-worker": _service("wepppy:test"),
        "rq-worker-batch": _service("wepppy:test"),
        "weppcloudr": _service("weppcloudr:test", build=False),
    }
    result, commands = _run_deploy(
        tmp_path,
        services,
        rq_renew_once=True,
        rq_renew_block_at_resume=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    renewal_complete = _position(commands, "rq-token|renew-complete|")
    resume = _position(commands, _RQ_RESUME)
    assert renewal_complete < resume
    assert not any(_RQ_RENEW in command for command in commands[resume + 1 :])


def test_worker_bounds_hung_renewal_and_uses_fallback_control_container(
    tmp_path: Path,
) -> None:
    services = {
        "rq-worker": _service("wepppy:test"),
        "rq-worker-batch": _service("wepppy:test"),
        "weppcloudr": _service("weppcloudr:test", build=False),
    }
    result, commands = _run_deploy(
        tmp_path,
        services,
        rq_renew_once=True,
        rq_renew_hangs_once=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert len(_positions(commands, _RQ_RENEW)) >= 3
    assert "Deployment complete!" in result.stdout


@pytest.mark.parametrize(
    ("failure_flag", "expected_message"),
    [
        ("rq_pre_suspended", "RQ is already suspended by an external operator"),
        ("rq_competing_deploy", "another deployment owns the RQ fence"),
    ],
)
def test_rq_fence_acquisition_fails_closed_without_mutation(
    tmp_path: Path,
    failure_flag: str,
    expected_message: str,
) -> None:
    services = {
        "rq-worker": _service("wepppy:test"),
        "rq-worker-batch": _service("wepppy:test"),
        "weppcloudr": _service("weppcloudr:test", build=False),
    }
    result, commands = _run_deploy(tmp_path, services, **{failure_flag: True})

    assert result.returncode != 0
    assert expected_message in result.stderr
    assert any(_RQ_SUSPEND in command for command in commands)
    assert not any(_RQ_RESUME in command for command in commands)
    assert not any("stop --timeout 216000 rq-worker" in command for command in commands)
    assert not any("up -d" in command for command in commands)
    assert "Deployment complete!" not in result.stdout


def test_lost_rq_fence_fails_before_activation_and_resumes_owned_suspension(tmp_path: Path) -> None:
    services = {
        "rq-worker": _service("wepppy:test"),
        "rq-worker-batch": _service("wepppy:test"),
        "weppcloudr": _service("weppcloudr:test", build=False),
    }
    result, commands = _run_deploy(tmp_path, services, rq_fence_loss=True)

    assert result.returncode != 0
    suspend = _position(commands, _RQ_SUSPEND)
    fence_assertions = _rq_assert_positions(commands)
    resume = _position(commands, _RQ_RESUME)
    assert suspend < fence_assertions[-1] < resume
    assert len(fence_assertions) == 2
    assert "Global RQ suspension fence was lost" in result.stderr
    assert not any("up -d" in command for command in commands)
    assert "Deployment complete!" not in result.stdout


def test_rq_heartbeat_failure_file_is_detected_before_success_and_resumes(tmp_path: Path) -> None:
    services = {
        "rq-worker": _service("wepppy:test"),
        "rq-worker-batch": _service("wepppy:test"),
        "weppcloudr": _service("weppcloudr:test", build=False),
    }
    result, commands = _run_deploy(tmp_path, services, rq_heartbeat_failure=True)

    assert result.returncode != 0
    renewal_attempts = _positions(commands, _RQ_RENEW)
    resume = _position(commands, _RQ_RESUME)
    assert renewal_attempts
    assert renewal_attempts[-1] < resume
    assert "Global RQ suspension heartbeat failed" in result.stderr
    assert not any(command.startswith("docker|system prune") for command in commands)
    assert "Deployment complete!" not in result.stdout


def test_both_rq_resume_paths_failing_returns_87_without_false_success(tmp_path: Path) -> None:
    services = {
        "rq-worker": _service("wepppy:test"),
        "rq-worker-batch": _service("wepppy:test"),
        "weppcloudr": _service("weppcloudr:test", build=False),
    }
    result, commands = _run_deploy(
        tmp_path,
        services,
        rq_resume_failure=True,
        skip_docker_prune=False,
    )

    assert result.returncode == 87
    resume_attempts = _positions(commands, _RQ_RESUME)
    assert len(resume_attempts) >= 4
    assert "Failed to resume the deployment-owned global RQ suspension" in result.stderr
    assert "RQ_RESUME_FAILED" in result.stderr
    assert "Resumed global RQ dequeue" not in result.stdout
    assert not any(command.startswith("docker|system prune") for command in commands)
    assert "Deployment complete!" not in result.stdout


def test_worker_rejects_missing_current_host_registration_before_prune_or_success(tmp_path: Path) -> None:
    services = {
        "rq-worker": _service("wepppy:test"),
        "rq-worker-batch": _service("wepppy:test"),
        "weppcloudr": _service("weppcloudr:test", build=False),
    }
    result, commands = _run_deploy(
        tmp_path,
        services,
        local_worker_registration_failure=True,
        skip_docker_prune=False,
    )

    assert result.returncode != 0
    suspend = _position(commands, _RQ_SUSPEND)
    assert any("exec -T rq-worker hostname" in command for command in commands)
    assert any("exec -T rq-worker-batch hostname" in command for command in commands)
    registration = _position(commands, "Worker.all")
    resume = _position(commands, _RQ_RESUME)
    assert suspend < registration < resume
    assert "RQ default/batch worker registration is incomplete: 0:1" in result.stderr
    assert not any(command.startswith("docker|system prune") for command in commands)
    assert "Deployment complete!" not in result.stdout


def test_wepp3_execution_warm_stops_and_checks_identity_and_registration(tmp_path: Path) -> None:
    services = {"rq-worker-fork-archive": _service("wepppy:test")}
    result, commands = _run_deploy(tmp_path, services)

    assert result.returncode == 0, result.stdout + result.stderr
    stop = _position(commands, "stop --timeout 216000 rq-worker-fork-archive")
    down = _position(commands, "wctl|down")
    start = _position(commands, "wctl|up -d --force-recreate")
    assert stop < down < start
    assert any("exec -T rq-worker-fork-archive id -u" in command for command in commands)
    assert "running as 1002:130 and registered with RQ" in result.stdout


def test_targeted_cap_execution_validates_before_short_stop_and_functional_canary(tmp_path: Path) -> None:
    services = {
        "weppcloud": _service("wepppy:test"),
        "rq-worker": _service("wepppy:test"),
        "cap": _service("cap:test"),
    }
    result, commands = _run_deploy(tmp_path, services, "--targeted-cap")

    assert result.returncode == 0, result.stdout + result.stderr
    validator = _position(commands, "cap-validator|cap:test")
    secret = _position(commands, "cap-preparer|--secret-only")
    stop = _position(commands, "wctl|docker compose stop cap")
    data = _position(commands, "cap-preparer|--data-only")
    start = _position(commands, "up -d --no-deps --force-recreate cap")
    assert validator < secret < stop < data < start
    assert not any("stop --timeout 216000 rq-worker" in command for command in commands)
    assert not any(command.startswith("weppcloudr-validator|") for command in commands)
    assert not any(command == "controller-builder" for command in commands)
    assert not any(command.startswith("docker|system prune") for command in commands)
    assert not any(_RQ_SUSPEND in command or _RQ_RESUME in command for command in commands)
    assert "CAP readiness and functional canary passed" in result.stdout
    assert "Skipping static assets" in result.stdout


def test_targeted_cap_candidate_failure_restores_known_good_image(tmp_path: Path) -> None:
    services = {
        "weppcloud": _service("wepppy:test"),
        "rq-worker": _service("wepppy:test"),
        "cap": _service("cap:test"),
        "caddy": _service("caddy:test", build=False),
    }
    result, commands = _run_deploy(
        tmp_path,
        services,
        "--targeted-cap",
        candidate_mismatch=True,
    )

    assert result.returncode != 0
    candidate_failure = _position(commands, "docker|inspect --format {{.Image}} cid-cap")
    recovery = _position(commands, "docker|compose -f")
    assert candidate_failure < recovery
    assert "Known-good CAP rescue image restored" in result.stderr
    assert "CAP_RESCUE_FAILED" not in result.stderr


def test_targeted_cap_recovery_failure_returns_distinct_rescue_signal(tmp_path: Path) -> None:
    services = {
        "weppcloud": _service("wepppy:test"),
        "rq-worker": _service("wepppy:test"),
        "cap": _service("cap:test"),
    }
    result, _commands = _run_deploy(
        tmp_path,
        services,
        "--targeted-cap",
        candidate_mismatch=True,
        recovery_failure=True,
    )

    assert result.returncode == 86
    assert "CAP_RESCUE_FAILED" in result.stderr


def test_full_caddy_inspection_failure_returns_distinct_rescue_signal_and_resumes(tmp_path: Path) -> None:
    result, commands = _run_deploy(
        tmp_path,
        _full_services_with_cap_and_renderer(),
        candidate_mismatch=True,
        caddy_inspection_failure=True,
    )

    assert result.returncode == 86
    caddy = _position(commands, "ps -q caddy")
    resume = _position(commands, _RQ_RESUME)
    assert caddy < resume
    assert "CAP_RESCUE_FAILED: unable to inspect Caddy" in result.stderr
    assert not any(command.startswith("docker|system prune") for command in commands)
    assert "Deployment complete!" not in result.stdout
