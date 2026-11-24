from __future__ import annotations

import sys
from pathlib import Path

import pytest

from tests.scripts.deploy_execution_harness import DEPLOY as _DEPLOY, run_deploy as _run_deploy


pytestmark = pytest.mark.unit

_RQ_SUSPEND = "# rq-fence-acquire"
_RQ_RENEW = "# rq-fence-renew"
_RQ_RESUME = "# rq-fence-resume"


def _service(image: str, *, build: bool = True) -> dict[str, object]:
    result: dict[str, object] = {"image": image, "environment": {
        "SECRET_KEY": "test-only", "SECURITY_PASSWORD_SALT": "test-only",
        "POSTGRES_PASSWORD": "test-only",
    }}
    if build:
        result["build"] = {"context": ".."}
    return result


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
        "shape-converter": _service("shape-converter:test"),
    }


def _full_services_with_shape_converter() -> dict[str, object]:
    return _full_services_with_cap_and_renderer()


def test_full_execution_builds_then_stops_workers_and_recreates_without_down(tmp_path: Path) -> None:
    result, commands = _run_deploy(tmp_path, _full_services_with_cap_and_renderer())

    assert result.returncode == 0, result.stdout + result.stderr
    build = _position(
        commands,
        "wctl|build --no-cache weppcloud weppcloudr cap shape-converter",
    )
    renderer_validation = _position(
        commands,
        "weppcloudr-validator|sha256:" + "0" * 63 + "1 sha256:" + "0" * 63 + "1",
    )
    cap_validation = _position(commands, "cap-validator|sha256:" + "0" * 63 + "1")
    suspend = _position(commands, _RQ_SUSPEND)
    stop = _position(commands, "stop --timeout 216000 rq-worker rq-worker-batch")
    cap_stop = _position(commands, "wctl|docker compose stop cap")
    start = _position(commands, "docker|compose -f")
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
    assert "retained|record-activation" in commands
    assert any(command.startswith("docker|tag sha256:") for command in commands)
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
    assert not any("docker compose stop cap" in command for command in commands)
    assert any("docker|stop --time 30 cid-shape-converter" in command for command in commands)
    assert not any("up -d" in command for command in commands)
    assert not any(_RQ_SUSPEND in command or _RQ_RESUME in command for command in commands)
    assert not any(command.startswith("docker|system prune") for command in commands)
    assert "Deployment complete!" not in result.stdout


def test_post_drain_gate_failure_releases_fence_without_stopping_services(tmp_path: Path) -> None:
    result, commands = _run_deploy(
        tmp_path,
        _full_services_with_cap_and_renderer(),
        gate_failure_call=2,
    )

    assert result.returncode != 0
    assert _position(commands, _RQ_SUSPEND) < _position(commands, _RQ_RESUME)
    assert not any("stop --timeout" in command for command in commands)
    assert not any("docker compose stop" in command for command in commands)
    assert not any(command.startswith("docker|compose -f") for command in commands)


def test_running_map_drift_after_drain_refuses_cutover_and_releases_fence(
    tmp_path: Path,
) -> None:
    result, commands = _run_deploy(
        tmp_path,
        _full_services_with_cap_and_renderer(),
        running_map_drift_before_stop=True,
    )

    assert result.returncode != 0
    assert "rq-worker image changed after known-good capture" in result.stderr
    assert _position(commands, _RQ_SUSPEND) < _position(commands, _RQ_RESUME)
    assert not any("stop --timeout" in command for command in commands)
    assert not any("docker compose stop" in command for command in commands)
    assert not any(
        command.startswith("docker|compose -f") and " up -d " in command
        for command in commands
    )


def test_gate_failure_after_stop_restores_prior_map_before_fence_release(tmp_path: Path) -> None:
    result, commands = _run_deploy(
        tmp_path,
        _full_services_with_cap_and_renderer(),
        gate_failure_call=4,
    )

    assert result.returncode != 0
    stop = _position(commands, "stop --timeout 216000 rq-worker rq-worker-batch")
    recovery = _position(commands, "docker|compose -f")
    resume = _position(commands, _RQ_RESUME)
    assert stop < recovery < resume
    assert "Retained workloads restored and verified; fail-closed services remain stopped" in result.stderr
    compose_commands = [command for command in commands if command.startswith("docker|compose -f")]
    assert len(compose_commands) == 1
    assert "wepppy-known-good" in compose_commands[0]


def test_failed_known_good_restore_returns_distinct_signal_and_retains_fence(tmp_path: Path) -> None:
    result, commands = _run_deploy(
        tmp_path,
        _full_services_with_cap_and_renderer(),
        candidate_mismatch=True,
        recovery_failure=True,
    )

    assert result.returncode == 88
    assert "KNOWN_GOOD_RESTORE_FAILED" in result.stderr
    assert not any(_RQ_RESUME in command for command in commands)


def test_stopped_worker_rq_control_uses_known_good_immutable_override(tmp_path: Path) -> None:
    result, commands = _run_deploy(
        tmp_path,
        _full_services_with_cap_and_renderer(),
        worker_stops_after_stop=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    stop = _position(commands, "stop --timeout 216000 rq-worker rq-worker-batch")
    pinned_runs = [
        index for index, command in enumerate(commands)
        if command.startswith("docker|compose -f") and " run " in command
    ]
    assert pinned_runs and all(stop < index for index in pinned_runs)
    assert all("wepppy-known-good" in commands[index] for index in pinned_runs)
    assert not any(
        index > stop and "wctl|docker compose run" in command and "rq-worker" in command
        for index, command in enumerate(commands)
    )


def test_post_stop_heartbeat_renewal_uses_known_good_immutable_override(
    tmp_path: Path,
) -> None:
    result, commands = _run_deploy(
        tmp_path,
        _full_services_with_cap_and_renderer(),
        worker_stops_after_stop=True,
        rq_renew_after_stop=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    stop = _position(commands, "stop --timeout 216000 rq-worker rq-worker-batch")
    renew = _position(commands, "rq-fallback|renew|compose -f")
    assert stop < renew
    assert "wepppy-known-good" in commands[renew]


def test_recovery_waits_for_health_and_worker_registration_before_resume(
    tmp_path: Path,
) -> None:
    result, commands = _run_deploy(
        tmp_path,
        _full_services_with_cap_and_renderer(),
        gate_failure_call=4,
        recovery_health_delay_checks=2,
        recovery_registration_delay_checks=2,
    )

    assert result.returncode != 0
    recovery = _position(commands, "docker|compose -f")
    recovery_command = commands[recovery]
    assert "--no-deps" in recovery_command
    assert "shape-converter" not in recovery_command.split("--no-deps", 1)[1].split()
    assert "rq-worker" in recovery_command.split("--no-deps", 1)[1].split()
    resume = _position(commands, _RQ_RESUME)
    recovery_ps = [
        index for index, command in enumerate(commands)
        if index > recovery and "ps --all --format json" in command
    ]
    recovery_registration = [
        index for index, command in enumerate(commands)
        if index > recovery and "Worker.all" in command
    ]
    assert len(recovery_ps) >= 3
    assert len(recovery_registration) >= 3
    assert max(recovery_registration) < resume
    assert "Retained workloads restored and verified; fail-closed services remain stopped" in result.stderr


def test_full_candidate_failure_recovers_cap_and_never_reports_success_or_prunes(tmp_path: Path) -> None:
    result, commands = _run_deploy(
        tmp_path,
        _full_services_with_cap_and_renderer(),
        candidate_mismatch=True,
    )

    assert result.returncode != 0
    suspend = _position(commands, _RQ_SUSPEND)
    activations = _positions(commands, "docker|compose -f")
    activation = activations[0]
    resume = _position(commands, _RQ_RESUME)
    recovery = activations[1]
    assert suspend < activation < recovery < resume
    assert "Retained workloads restored and verified; fail-closed services remain stopped" in result.stderr
    assert (tmp_path / "controllers-gl.js").read_text(encoding="utf-8") == "known-good controllers"
    assert "Restored the pre-deploy controllers bundle" in result.stderr
    assert not any(command.startswith("docker|system prune") for command in commands)
    assert "Deployment complete!" not in result.stdout


def test_shape_readiness_failure_stops_converter_and_never_reports_success_or_prunes(
    tmp_path: Path,
) -> None:
    result, commands = _run_deploy(
        tmp_path,
        _full_services_with_shape_converter(),
        shape_readiness_failure=True,
        skip_docker_prune=False,
    )

    assert result.returncode != 0
    readiness = _position(commands, "/utils/shape-converter/health/ready")
    stop = _position(commands, "docker|stop --time 30 cid-shape-converter")
    down_check = _position(commands, "docker|ps -q --filter label=com.docker.compose.service=shape-converter")
    assert readiness < stop < down_check
    assert "shape-converter is down" in result.stderr
    assert not any(command.startswith("docker|system prune") for command in commands)
    assert "Deployment complete!" not in result.stdout


def test_shape_readiness_failure_detects_stop_failure(tmp_path: Path) -> None:
    result, commands = _run_deploy(
        tmp_path,
        _full_services_with_shape_converter(),
        shape_readiness_failure=True,
        shape_stop_failure=True,
    )

    assert result.returncode == 88
    assert any("docker|stop --time 30 cid-shape-converter" in command for command in commands)
    assert "SHAPE_CONVERTER_FAIL_CLOSED_FAILED" in result.stderr
    assert not any(_RQ_RESUME in command for command in commands)
    assert "Deployment complete!" not in result.stdout


def test_shape_readiness_failure_detects_container_discovery_failure(tmp_path: Path) -> None:
    result, commands = _run_deploy(
        tmp_path,
        _full_services_with_shape_converter(),
        shape_readiness_failure=True,
        shape_discovery_failure=True,
    )

    assert result.returncode == 88
    assert any("docker|ps -aq" in command for command in commands)
    assert not any("docker|stop --time 30" in command for command in commands)
    assert "unable to discover service containers" in result.stderr
    assert "Deployment complete!" not in result.stdout


def test_shape_readiness_failure_detects_state_verification_failure(tmp_path: Path) -> None:
    result, commands = _run_deploy(
        tmp_path,
        _full_services_with_shape_converter(),
        shape_readiness_failure=True,
        shape_ps_failure=True,
    )

    assert result.returncode == 88
    assert any("docker|stop --time 30 cid-shape-converter" in command for command in commands)
    assert any("com.docker.compose.service=shape-converter" in command for command in commands)
    assert "unable to verify service state" in result.stderr
    assert "Deployment complete!" not in result.stdout


def test_shape_release_build_rejects_dirty_inputs_even_with_skip_pull(tmp_path: Path) -> None:
    result, commands = _run_deploy(
        tmp_path,
        _full_services_with_shape_converter(),
        shape_build_inputs_clean=False,
    )

    assert result.returncode != 0
    assert "inputs differ from HEAD" in result.stderr
    assert any("docker|stop --time 30 cid-shape-converter" in command for command in commands)
    assert any("com.docker.compose.service=shape-converter" in command for command in commands)
    assert not any("build --no-cache" in command for command in commands)
    assert not any("up -d" in command for command in commands)
    assert "Deployment complete!" not in result.stdout


def test_shape_release_build_rejects_dirty_dockerfile_specific_ignore(
    tmp_path: Path,
) -> None:
    result, commands = _run_deploy(
        tmp_path,
        _full_services_with_shape_converter(),
        shape_build_inputs_clean=False,
        shape_dirty_build_input="docker/Dockerfile.shape-converter.dockerignore",
    )

    assert result.returncode != 0
    assert "Dockerfile.shape-converter.dockerignore" in result.stderr
    assert any("docker|stop --time 30 cid-shape-converter" in command for command in commands)
    assert any("com.docker.compose.service=shape-converter" in command for command in commands)
    assert not any("build --no-cache" in command for command in commands)
    assert not any("up -d" in command for command in commands)


def test_shape_release_build_rejects_dirty_production_compose_with_skip_pull(
    tmp_path: Path,
) -> None:
    result, commands = _run_deploy(
        tmp_path,
        _full_services_with_shape_converter(),
        shape_build_inputs_clean=False,
        shape_dirty_build_input="docker/docker-compose.prod.yml",
    )

    assert result.returncode != 0
    assert "docker/docker-compose.prod.yml" in result.stderr
    assert any("docker|stop --time 30 cid-shape-converter" in command for command in commands)
    assert any("com.docker.compose.service=shape-converter" in command for command in commands)
    assert not any("build --no-cache" in command for command in commands)
    assert not any("up -d" in command for command in commands)
    assert "Deployment complete!" not in result.stdout


def test_shape_release_build_rejects_git_status_failure_and_stops_service(
    tmp_path: Path,
) -> None:
    result, commands = _run_deploy(
        tmp_path,
        _full_services_with_shape_converter(),
        shape_git_status_failure=True,
    )

    assert result.returncode != 0
    assert "unable to inspect build inputs" in result.stderr
    assert any("docker|stop --time 30 cid-shape-converter" in command for command in commands)
    assert any("com.docker.compose.service=shape-converter" in command for command in commands)
    assert not any("build --no-cache" in command for command in commands)
    assert not any("up -d" in command for command in commands)
    assert "Deployment complete!" not in result.stdout


def test_shape_release_rejects_effective_service_without_build_contract(
    tmp_path: Path,
) -> None:
    services = _full_services_with_shape_converter()
    services["shape-converter"] = _service("shape-converter:test", build=False)

    result, commands = _run_deploy(tmp_path, services)

    assert result.returncode != 0
    assert "without the reviewed shape-converter service/build contract" in result.stderr
    assert any("docker|stop --time 30 cid-shape-converter" in command for command in commands)
    assert any("com.docker.compose.service=shape-converter" in command for command in commands)
    assert not any("build --no-cache" in command for command in commands)
    assert not any("up -d" in command for command in commands)
    assert "Deployment complete!" not in result.stdout


def test_clean_full_preset_stops_labeled_orphan_when_shape_service_is_missing(
    tmp_path: Path,
) -> None:
    services = _full_services_with_shape_converter()
    services.pop("shape-converter")

    result, commands = _run_deploy(tmp_path, services)

    assert result.returncode != 0
    discovery = _position(
        commands,
        "docker|ps -aq --filter label=com.docker.compose.service=shape-converter",
    )
    stop = _position(commands, "docker|stop --time 30 cid-shape-converter")
    verification = _position(
        commands,
        "docker|ps -q --filter label=com.docker.compose.service=shape-converter",
    )
    assert discovery < stop < verification
    assert "without the reviewed shape-converter service/build contract" in result.stderr
    assert "shape-converter is down" in result.stderr
    assert not any("build --no-cache" in command for command in commands)
    assert not any("up -d" in command for command in commands)
    assert "Deployment complete!" not in result.stdout


@pytest.mark.parametrize("mutation", ["image", "service"])
def test_shape_release_rejects_dirty_effective_contract_mutation(
    tmp_path: Path,
    mutation: str,
) -> None:
    services = _full_services_with_shape_converter()
    if mutation == "image":
        services["shape-converter"] = _service("unreviewed-shape:test")
    else:
        services.pop("shape-converter")

    result, commands = _run_deploy(
        tmp_path,
        services,
        shape_build_inputs_clean=False,
        shape_dirty_build_input="docker/docker-compose.prod.yml",
    )

    assert result.returncode != 0
    assert "docker/docker-compose.prod.yml" in result.stderr
    assert any("docker|stop --time 30 cid-shape-converter" in command for command in commands)
    assert any("com.docker.compose.service=shape-converter" in command for command in commands)
    assert not any("build --no-cache" in command for command in commands)
    assert not any("up -d" in command for command in commands)
    assert "Deployment complete!" not in result.stdout


def test_dirty_full_preset_cannot_reclassify_as_worker_to_bypass_shape_gate(
    tmp_path: Path,
) -> None:
    services = _full_services_with_shape_converter()
    services.pop("weppcloud")
    services.pop("shape-converter")

    result, commands = _run_deploy(
        tmp_path,
        services,
        shape_build_inputs_clean=False,
        shape_dirty_build_input="docker/docker-compose.prod.yml",
        compose_files="docker/docker-compose.prod.yml",
    )

    assert result.returncode != 0
    assert "docker/docker-compose.prod.yml" in result.stderr
    assert any("docker|stop --time 30 cid-shape-converter" in command for command in commands)
    assert any("com.docker.compose.service=shape-converter" in command for command in commands)
    assert not any("build --no-cache" in command for command in commands)
    assert not any("up -d" in command for command in commands)
    assert "Deployment complete!" not in result.stdout


def test_targeted_web_fails_closed_until_retained_scope_is_reviewed(
    tmp_path: Path,
) -> None:
    result, commands = _run_deploy(
        tmp_path,
        _full_services_with_cap_and_renderer(),
        "--targeted-web",
    )

    assert result.returncode != 0
    assert "fail-closed" in result.stderr
    assert not any("build --no-cache" in command for command in commands)
    assert not any("up -d" in command for command in commands)


def test_concurrent_deploy_lock_fails_before_build_or_activation(tmp_path: Path) -> None:
    services = {
        "weppcloud": _service("wepppy:test"),
        "rq-worker": _service("wepppy:test"),
        "shape-converter": _service("shape-converter:test"),
    }
    result, commands = _run_deploy(tmp_path, services, lock_held=True)

    assert result.returncode != 0
    assert "Another deployment holds" in result.stderr
    assert not any("build --no-cache" in command for command in commands)
    assert not any("up -d" in command for command in commands)


@pytest.mark.parametrize("argument", ["--print-plan", "--targeted-web"])
def test_preset_query_failure_in_non_shape_scope_never_stops_converter(
    tmp_path: Path,
    argument: str,
) -> None:
    result, commands = _run_deploy(
        tmp_path,
        _full_services_with_shape_converter(),
        argument,
        preset_query_failure=True,
    )

    assert result.returncode != 0
    assert "Unable to identify the installed wctl deployment preset" in result.stderr
    assert not any("com.docker.compose.service=shape-converter" in command for command in commands)
    assert not any("docker|stop" in command for command in commands)


def test_full_preset_compose_render_failure_stops_converter(tmp_path: Path) -> None:
    result, commands = _run_deploy(
        tmp_path,
        _full_services_with_shape_converter(),
        compose_render_failure=True,
    )

    assert result.returncode != 0
    assert any("docker|stop --time 30 cid-shape-converter" in command for command in commands)
    assert any("com.docker.compose.service=shape-converter" in command for command in commands)
    assert "shape-converter is down" in result.stderr
    assert not any("up -d" in command for command in commands)


def test_controller_builder_failure_removes_staged_bundle_before_cutover(tmp_path: Path) -> None:
    services = {
        "weppcloud": _service("wepppy:test"),
        "rq-worker": _service("wepppy:test"),
        "shape-converter": _service("shape-converter:test"),
    }
    result, commands = _run_deploy(tmp_path, services, controller_build_failure=True)

    assert result.returncode == 72
    assert not list(tmp_path.glob("controllers-gl.js.deploy.*"))
    assert (tmp_path / "controllers-gl.js").read_text(encoding="utf-8") == "known-good controllers"
    assert not any("up -d" in command for command in commands)


def test_controller_backup_failure_preserves_old_bundle_recovers_and_resumes(tmp_path: Path) -> None:
    result, commands = _run_deploy(
        tmp_path,
        _full_services_with_cap_and_renderer(),
        controller_backup_failure=True,
    )

    assert result.returncode != 0
    recovery = _position(commands, "docker|compose -f")
    resume = _position(commands, _RQ_RESUME)
    assert _position(commands, _RQ_SUSPEND) < recovery < resume
    assert (tmp_path / "controllers-gl.js").read_text(encoding="utf-8") == "known-good controllers"
    assert not any(command == "wctl|up -d --force-recreate" for command in commands)
    assert "Retained workloads restored and verified; fail-closed services remain stopped" in result.stderr
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
    start = _position(commands, "docker|compose -f")
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
    deploy_source = _DEPLOY.read_text(encoding="utf-8")
    assert "redis.call([[set]], KEYS[2], [[1]], [[EX]], ARGV[2])" in deploy_source
    assert "redis.call([[del]], KEYS[2])" in deploy_source
    assert "redis.call([[del]], KEYS[1])" in deploy_source


def test_rq_acquisition_is_idempotent_after_committed_reply_loss(tmp_path: Path) -> None:
    services = {
        "rq-worker": _service("wepppy:test"),
        "rq-worker-batch": _service("wepppy:test"),
        "weppcloudr": _service("weppcloudr:test", build=False),
    }
    result, commands = _run_deploy(tmp_path, services, rq_acquire_reply_lost=True)

    assert result.returncode == 0, result.stdout + result.stderr
    acquisition_tokens = _rq_tokens(commands, "acquire")
    assert len(acquisition_tokens) == 2
    assert len(set(acquisition_tokens)) == 1
    assert _rq_tokens(commands, "resume") == [acquisition_tokens[0]]


def test_rq_resume_is_idempotent_after_committed_reply_loss(tmp_path: Path) -> None:
    services = {
        "rq-worker": _service("wepppy:test"),
        "rq-worker-batch": _service("wepppy:test"),
        "weppcloudr": _service("weppcloudr:test", build=False),
    }
    result, commands = _run_deploy(tmp_path, services, rq_resume_reply_lost=True)

    assert result.returncode == 0, result.stdout + result.stderr
    resume_tokens = _rq_tokens(commands, "resume")
    assert len(resume_tokens) == 2
    assert len(set(resume_tokens)) == 1
    assert "Deployment complete!" in result.stdout


def test_rq_acquisition_checks_resume_tombstone_before_creating_fence() -> None:
    deploy_source = _DEPLOY.read_text(encoding="utf-8")
    acquire_start = deploy_source.index("# rq-fence-acquire")
    acquire_end = deploy_source.index("' \"${RQ_FENCE_TOKEN}\")", acquire_start)
    acquire_program = deploy_source[acquire_start:acquire_end]

    receipt_check = acquire_program.index("redis.call([[get]], KEYS[3])")
    fence_publish = acquire_program.index("redis.call([[set]], KEYS[1]")
    suspension_publish = acquire_program.index("redis.call([[set]], KEYS[2]")
    assert receipt_check < fence_publish
    assert receipt_check < suspension_publish
    assert '"wepppy:deploy:rq-fence:resumed:" + token' in acquire_program


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
    assert len(_positions(commands, _RQ_RENEW)) >= 2
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
    assert suspend < registration
    assert result.returncode == 88
    assert "KNOWN_GOOD_RESTORE_FAILED" in result.stderr
    assert not any(_RQ_RESUME in command for command in commands)
    assert "RQ default/batch worker registration is incomplete: 0:1" in result.stderr
    assert not any(command.startswith("docker|system prune") for command in commands)
    assert "Deployment complete!" not in result.stdout


def test_wepp3_retained_execution_drains_and_activates_immutable_image(tmp_path: Path) -> None:
    services = {name: _service("wepppy:test") for name in ("rq-worker-fork-archive", "rq-worker-query-catalog")}
    result, commands = _run_deploy(tmp_path, services)

    assert result.returncode == 0, result.stdout + result.stderr
    build = _position(commands, "wctl|build --no-cache rq-worker-fork-archive")
    suspend = _position(commands, _RQ_SUSPEND)
    stop = _position(commands, "stop --timeout 216000 rq-worker-fork-archive")
    down = _position(commands, "wctl|down")
    activation = _position(commands, "docker|compose -f")
    registration = _position(commands, "Worker.all")
    resume = _position(commands, _RQ_RESUME)
    governance = _position(commands, "governance|check")
    secret_preflight = _position(commands, "test -r /run/secrets/redis_password")
    assert governance < secret_preflight < build < suspend < stop < down < activation < registration < resume
    assert any("stop --timeout 216000 rq-worker-fork-archive rq-worker-query-catalog" in line for line in commands)
    assert any("exec -T rq-worker-query-catalog id -u" in line for line in commands)
    assert "fork-archive and query-catalog RQ registries are drained" in result.stdout
    assert "retained|record-activation" in commands
    assert any("wepppy-retained-rollback:" in command for command in commands)
    assert not any(command.startswith("docker|system prune") for command in commands)
    assert "Deployment complete!" in result.stdout


def test_wepp3_active_job_timeout_releases_fence_without_stopping_worker(tmp_path: Path) -> None:
    services = {name: _service("wepppy:test") for name in ("rq-worker-fork-archive", "rq-worker-query-catalog")}
    result, commands = _run_deploy(tmp_path, services, rq_probe_result="1")

    assert result.returncode != 0
    assert "Timed out draining 1 active fork-archive and query-catalog RQ jobs" in result.stderr
    assert _position(commands, _RQ_SUSPEND) < _position(commands, _RQ_RESUME)
    assert not any("stop --timeout" in command for command in commands)
    assert not any(command.startswith("docker|compose -f") and " up -d " in command for command in commands)


def test_catalog_registration_failure_restores_serial_worker_and_removes_first_install(tmp_path: Path) -> None:
    catalog = "rq-worker-query-catalog"
    services = {name: _service("wepppy:test") for name in ("rq-worker-fork-archive", catalog)}
    result, commands = _run_deploy(
        tmp_path, services, "--new-service", catalog, new_service=catalog, catalog_registration_failure=True,
    )
    assert result.returncode != 0, result.stdout
    assert "Expected one live exclusive rq-worker-query-catalog registration" in result.stderr
    assert "KNOWN_GOOD_RESTORE_FAILED" not in result.stderr
    assert any(" rm --stop --force " in command and command.endswith(catalog) for command in commands)
    assert any(_RQ_RESUME in command for command in commands)


def test_wepp3_registration_failure_restores_known_good_and_retains_fence_on_failure(
    tmp_path: Path,
) -> None:
    services = {name: _service("wepppy:test") for name in ("rq-worker-fork-archive", "rq-worker-query-catalog")}
    result, commands = _run_deploy(
        tmp_path,
        services,
        local_worker_registration_failure=True,
        recovery_failure=True,
    )

    assert result.returncode == 88
    assert "KNOWN_GOOD_RESTORE_FAILED" in result.stderr
    assert any("wepppy-known-good" in command and "up -d" in command for command in commands)
    assert not any(command.startswith("docker|system prune") for command in commands)
    assert "Deployment complete!" not in result.stdout


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


def test_full_failure_uses_exact_map_recovery_without_legacy_caddy_rescue(tmp_path: Path) -> None:
    result, commands = _run_deploy(
        tmp_path,
        _full_services_with_cap_and_renderer(),
        candidate_mismatch=True,
        caddy_inspection_failure=True,
    )

    assert result.returncode != 0
    resume = _position(commands, _RQ_RESUME)
    recovery = _positions(commands, "docker|compose -f")[1]
    assert recovery < resume
    assert "Retained workloads restored and verified; fail-closed services remain stopped" in result.stderr
    assert not any(
        command.startswith("docker|compose -f") and "ps -q caddy" in command
        for command in commands
    )
    assert not any(command.startswith("docker|system prune") for command in commands)
    assert "Deployment complete!" not in result.stdout


def test_shape_takedown_and_retained_recovery_failure_keep_fence(tmp_path: Path) -> None:
    result, commands = _run_deploy(
        tmp_path,
        _full_services_with_cap_and_renderer(),
        candidate_mismatch=True,
        recovery_failure=True,
        shape_stop_failure=True,
    )

    assert result.returncode == 88
    assert any("docker|stop --time 30 cid-shape-converter" in command for command in commands)
    assert "SHAPE_CONVERTER_FAIL_CLOSED_FAILED" in result.stderr
    assert "KNOWN_GOOD_RESTORE_FAILED" in result.stderr
    assert not any(_RQ_RESUME in command for command in commands)
    assert "Deployment complete!" not in result.stdout


@pytest.mark.parametrize("worker_stopped", [False, True])
@pytest.mark.parametrize("probe_result", ["0", "2", "error", "invalid"])
def test_active_job_probe_preserves_gate_with_stopped_worker(
    tmp_path: Path, worker_stopped: bool, probe_result: str,
) -> None:
    services = {
        "rq-worker": _service("worker:latest"),
        "rq-worker-batch": _service("worker:latest"),
        "weppcloudr": _service("renderer:latest"),
    }
    result, commands = _run_deploy(
        tmp_path, services,
        rq_probe_worker_stopped=worker_stopped,
        rq_probe_result=probe_result,
    )
    assert "rq-probe|exec" in commands
    assert ("rq-probe|run" in commands) is (worker_stopped or probe_result == "error")
    if probe_result == "0":
        assert result.returncode == 0, result.stdout + result.stderr
        assert _position(commands, "build --no-cache") < _position(commands, "rq-probe|exec")
    else:
        assert result.returncode != 0
        assert not any("stop --timeout" in command for command in commands)
        assert not any(
            command.startswith("docker|compose -f") and " up -d " in command
            for command in commands
        )
        assert not any("docker compose stop" in command for command in commands)
        assert not any("up -d" in command for command in commands)
        if probe_result == "2":
            assert "Timed out draining 2 active default and batch RQ jobs" in result.stderr
        elif probe_result == "invalid":
            assert "Unable to determine active RQ job count" in result.stderr
        else:
            assert "Redis connection unavailable" in result.stderr


@pytest.mark.parametrize("worker_only", [False, True])
def test_targeted_batch_fails_closed_until_retained_scope_is_reviewed(tmp_path: Path, worker_only: bool) -> None:
    services = _full_services_with_cap_and_renderer()
    if worker_only:
        services = {k: v for k, v in services.items() if k in {"rq-worker", "rq-worker-batch", "weppcloudr"}}
    services["rq-worker-batch"]["image"] = "wepppy:rollback-test"
    result, commands = _run_deploy(tmp_path, services, "--targeted-batch",
                                   "--batch-rollback-image-id", "sha256:" + "0" * 64)
    assert result.returncode != 0
    assert "fail-closed" in result.stderr
    assert not any("stop --timeout" in command for command in commands)
    assert not any("up -d" in command for command in commands)


def test_active_job_probe_never_cleans_registry(monkeypatch, capsys):
    """An old host's pre-build probe must not mutate newer shared RQ state."""
    import redis
    import rq.registry
    import wepppy.config.redis_settings as settings

    source = _DEPLOY.read_text(encoding="utf-8")
    active_function = source.split("active_rq_job_count() {", 1)[1].split(
        "\n}\n\nassert_no_active_rq_jobs", 1
    )[0]
    program = active_function.split("run_rq_control_program '\n", 1)[1].split("\n'", 1)[0]
    calls = []
    class Connection:
        def zcard(self, key):
            calls.append(key)
            return 1 if key == "rq:wip:default" else 0

    connection = Connection()

    class Registry:
        def __init__(self, name, connection):
            self.key = "rq:wip:" + name

        def get_job_ids(self):
            raise AssertionError("RQ 1.16 get_job_ids unconditionally cleans shared state")

    monkeypatch.setattr(redis, "Redis", lambda **kwargs: connection)
    monkeypatch.setattr(settings, "redis_connection_kwargs", lambda db: {})
    monkeypatch.setattr(rq.registry, "StartedJobRegistry", Registry)
    monkeypatch.setattr(sys, "argv", [str(_DEPLOY), "default,batch"])
    exec(compile(program, str(_DEPLOY), "exec"), {})
    assert calls == ["rq:wip:default", "rq:wip:batch"]
    assert capsys.readouterr().out.strip() == "1"


@pytest.mark.parametrize("topology", ["full", "wepp3"])
def test_governance_failure_precedes_build_stop_and_activation(tmp_path: Path, topology: str) -> None:
    services = (_full_services_with_cap_and_renderer() if topology == "full"
                else {name: _service("wepppy:test") for name in ("rq-worker-fork-archive", "rq-worker-query-catalog")})
    result, commands = _run_deploy(tmp_path, services, governance_failure=True)
    assert result.returncode == 89
    assert "governance|check" in commands
    assert not any("test -r /run/secrets/redis_password" in command for command in commands)
    assert not any(_RQ_SUSPEND in command for command in commands)
    assert not any("build " in command or "--force-recreate" in command for command in commands)
    assert not any(command.startswith("docker|stop ") for command in commands)


def test_first_install_service_is_retained_as_absent(tmp_path: Path) -> None:
    services = _full_services_with_cap_and_renderer()
    services['soil-api'] = _service('soil:test')
    result, commands = _run_deploy(tmp_path, services, '--new-service', 'soil-api', new_service='soil-api')
    assert result.returncode == 0, result.stderr
    rows = (tmp_path / 'state/retained-images.tsv').read_text()
    assert 'soil-api\t-\t0\n' in rows
    assert not any('tag - ' in command for command in commands)
    assert 'Deployment complete!' in result.stdout


@pytest.mark.parametrize('failure', ['undeclared', 'stopped', 'inventory'])
def test_first_install_requires_explicit_verified_absence(tmp_path: Path, failure: str) -> None:
    services = _full_services_with_cap_and_renderer()
    services['soil-api'] = _service('soil:test')
    flags = () if failure == 'undeclared' else ('--new-service', 'soil-api')
    result, commands = _run_deploy(tmp_path, services, *flags, new_service='soil-api',
                                  stopped_new_service=failure == 'stopped',
                                  new_inventory_failure=failure == 'inventory')
    assert result.returncode != 0
    assert not any('up -d' in command or 'stop --timeout' in command for command in commands)


@pytest.mark.parametrize('cleanup_failure', [False, True])
def test_rollback_removes_new_containers_preserves_volumes_and_restores_existing(tmp_path: Path, cleanup_failure: bool) -> None:
    services = _full_services_with_cap_and_renderer()
    services['soil-api'] = _service('soil:test')
    result, commands = _run_deploy(tmp_path, services, '--new-service', 'soil-api',
                                  new_service='soil-api', candidate_mismatch=True,
                                  new_cleanup_failure=cleanup_failure)
    assert result.returncode != 0
    cleanup = next(command for command in commands if ' rm --stop --force ' in command)
    assert cleanup.endswith(' soil-api')
    assert '--volumes' not in cleanup and ' -v' not in cleanup
    restores = [command for command in commands if 'wepppy-known-good' in command and ' up -d ' in command]
    assert restores and all('soil-api' not in command for command in restores)
    if cleanup_failure:
        assert result.returncode == 88
        assert not any(_RQ_RESUME in command for command in commands)
    else:
        assert any(_RQ_RESUME in command for command in commands)
        assert not (tmp_path / 'introduced-service-running').exists()


@pytest.mark.parametrize('rejected', [False, True])
def test_imported_images_skip_build_and_never_activate(tmp_path: Path, rejected: bool) -> None:
    result, commands = _run_deploy(
        tmp_path, _full_services_with_cap_and_renderer(),
        '--retain-images-from', '/source/receipt.json',
        '--source-receipt-sha256', 'a' * 64,
        import_images_failure=rejected,
    )
    assert (result.returncode != 0) == rejected, result.stderr
    assert 'retained|prepare-images' in commands
    assert ('retained|create' in commands) == (not rejected)
    assert not any('build --no-cache' in command or 'builder prune' in command or
                   ' up -d ' in command or _RQ_SUSPEND in command for command in commands)
