from __future__ import annotations

import hashlib
import os
import random
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .api_client import JobWaitResult, LiveAPIClient, LiveApiError
from .artifacts import (
    _artifact_text_hash,
    _canonical_hash,
    _select_property_sol_subpaths,
    _sha256_bytes,
    _sha256_text,
)
from .comparisons import deterministic_payload, stage_assertions
from .evidence import _write_evidence_artifacts
from .lookup_stage import ForkLookup, PropertyArtifact, StageOutputs
from .manifest import LiveE2EManifest, load_manifest


def _utcnow_iso() -> str:
    return datetime.now(UTC).isoformat()


def _fnv32a_hash(text: str) -> int:
    value = 2166136261
    for char in text:
        value ^= ord(char)
        value = (
            value + (value << 1) + (value << 4) + (value << 7) + (value << 8) + (value << 24)
        ) & 0xFFFFFFFF
    return value


def _cap_expand_hex(seed: str, length: int) -> str:
    state = _fnv32a_hash(seed)

    def next_u32() -> int:
        nonlocal state
        state ^= (state << 13) & 0xFFFFFFFF
        state ^= (state >> 17) & 0xFFFFFFFF
        state ^= (state << 5) & 0xFFFFFFFF
        state &= 0xFFFFFFFF
        return state

    out = ""
    while len(out) < length:
        out += f"{next_u32():08x}"
    return out[:length]


def _build_cap_pairs(challenge_payload: dict[str, Any]) -> tuple[str, list[tuple[str, str]]]:
    token = str(challenge_payload.get("token") or "").strip()
    challenge = challenge_payload.get("challenge")
    if not token or not isinstance(challenge, dict):
        raise LiveApiError(f"Unexpected CAP challenge payload: {challenge_payload}")

    count = int(challenge.get("c") or 0)
    salt_len = int(challenge.get("s") or 0)
    target_len = int(challenge.get("d") or 0)
    if count <= 0 or salt_len <= 0 or target_len <= 0:
        raise LiveApiError(f"Invalid CAP challenge dimensions: {challenge}")

    pairs: list[tuple[str, str]] = []
    for idx in range(1, count + 1):
        salt = _cap_expand_hex(f"{token}{idx}", salt_len)
        target = _cap_expand_hex(f"{token}{idx}d", target_len)
        pairs.append((salt, target))
    return token, pairs


def _solve_pow_nonce(*, salt: str, target_hex: str) -> int:
    target_bytes = bytes.fromhex(target_hex)
    target_width = len(target_bytes)
    nonce = 0
    while True:
        digest = hashlib.sha256(f"{salt}{nonce}".encode()).digest()
        if digest[:target_width] == target_bytes:
            return nonce
        nonce += 1


def _solve_cap_token(client: LiveAPIClient, *, cap_endpoint: str) -> tuple[str, dict[str, Any]]:
    challenge_payload = client.cap_challenge(cap_endpoint)
    token, pairs = _build_cap_pairs(challenge_payload)
    solutions = [_solve_pow_nonce(salt=salt, target_hex=target) for salt, target in pairs]
    redeem_payload = client.cap_redeem(cap_endpoint, token=token, solutions=solutions)
    cap_token = str(redeem_payload.get("token") or "").strip()
    if not cap_token or not bool(redeem_payload.get("success")):
        raise LiveApiError(f"CAP redeem did not return success token: {redeem_payload}")
    return cap_token, redeem_payload


def _probe_file(path: str) -> dict[str, Any]:
    target = Path(path)
    info: dict[str, Any] = {"path": str(target), "exists": target.exists()}
    if not target.exists():
        return info

    try:
        payload = target.read_bytes()
        info["size_bytes"] = len(payload)
        info["sha256"] = _sha256_bytes(payload)
    except OSError as exc:
        info["error"] = str(exc)
    return info


def _parse_env_lines(text: str) -> dict[str, str]:
    pairs: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        pairs[key.strip()] = value.strip().strip('"').strip("'")
    return pairs


def _load_dev_agent_credentials(
    *,
    credentials_file: str,
) -> tuple[str, str, dict[str, Any]]:
    env_email = os.getenv("DEV_AGENT_EMAIL", "").strip()
    env_password = os.getenv("DEV_AGENT_PASSWORD", "").strip()
    if env_email and env_password:
        return (
            env_email,
            env_password,
            {
                "source": "environment",
                "loaded": True,
                "email_present": True,
                "password_present": True,
            },
        )

    probe = _probe_file(credentials_file)
    probe["source"] = "file"
    probe["loaded"] = False
    probe["email_present"] = False
    probe["password_present"] = False

    if not probe.get("exists"):
        raise LiveApiError(
            f"Missing dev-agent credentials file at {credentials_file}; "
            "expected DEV_AGENT_EMAIL and DEV_AGENT_PASSWORD"
        )

    try:
        pairs = _parse_env_lines(Path(credentials_file).read_text())
    except OSError as exc:
        probe["error"] = str(exc)
        raise LiveApiError(f"Failed reading dev-agent credentials file: {credentials_file}") from exc

    email = str(pairs.get("DEV_AGENT_EMAIL") or "").strip()
    password = str(pairs.get("DEV_AGENT_PASSWORD") or "").strip()
    probe["loaded"] = bool(email and password)
    probe["email_present"] = bool(email)
    probe["password_present"] = bool(password)

    if not email or not password:
        raise LiveApiError(
            f"Credentials file {credentials_file} is missing DEV_AGENT_EMAIL or DEV_AGENT_PASSWORD"
        )
    return email, password, probe


def _generate_target_runid() -> str:
    stamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    suffix = f"{random.getrandbits(24):06x}"
    return f"live-disturbed-{stamp}-{suffix}"


@dataclass(frozen=True)
class RunbookResult:
    evidence_json_path: Path
    evidence_markdown_path: Path
    fork_runid: str
    deterministic_signature: str
    assertions: dict[str, bool]


@dataclass(frozen=True)
class SourceFingerprint:
    lookup_sha: str | None
    pmet: str

    @classmethod
    def capture(cls, client: LiveAPIClient, manifest: LiveE2EManifest, token: str) -> SourceFingerprint:
        scope = {"runid": manifest.source_runid, "config": manifest.source_config, "bearer_token": token}
        lookup = client.disturbed_lookup_meta(**scope, lookup="base")
        pmet = client.download_text(**scope, subpath="wepp/runs/pmetpara.txt")
        return cls(lookup.get("lookup_sha256"), pmet)

    def evidence(self) -> dict[str, Any]:
        return {"base_lookup_sha256": self.lookup_sha, "pmetpara_sha256": _sha256_text(self.pmet)}


def _prepare_fork(
    client: LiveAPIClient,
    manifest: LiveE2EManifest,
    evidence: dict[str, Any],
    flush_evidence: Callable[[], tuple[Path, Path]],
    dev_agent_email: str,
    dev_agent_password: str,
) -> tuple[ForkLookup, str, SourceFingerprint, JobWaitResult]:
    evidence["phase"] = "minting_dev_agent_bearer"
    minted_token_payload = client.login_and_mint_dev_agent_bearer(
        email=dev_agent_email,
        password=dev_agent_password,
    )
    minted_bearer_token = str(minted_token_payload.get("token") or "").strip()
    if not minted_bearer_token:
        raise LiveApiError("mint-token flow did not return a bearer token")

    evidence["phase"] = "issuing_source_session_token"
    source_token_payload = client.issue_session_token(
        runid=manifest.source_runid,
        config=manifest.source_config,
        session_origin=manifest.session_origin,
        bearer_token=minted_bearer_token,
    )

    source_session_token = str(source_token_payload.get("token") or "").strip()
    if not source_session_token:
        raise LiveApiError("session-token endpoint did not return a token for source run")

    evidence["auth"] = {
        "mode": "dev_agent_login_mint_token",
        "minted_token_class": minted_token_payload.get("token_class"),
        "minted_scopes": minted_token_payload.get("scopes"),
        "minted_audience": minted_token_payload.get("aud"),
        "source_session_token_mode": "minted_bearer",
        "source_token_class": source_token_payload.get("token_class"),
        "source_scopes": source_token_payload.get("scopes"),
    }
    flush_evidence()

    evidence["phase"] = "capturing_source_fingerprints"
    source_before = SourceFingerprint.capture(client, manifest, source_session_token)
    evidence["source_before"] = source_before.evidence()
    flush_evidence()

    evidence["phase"] = "solving_cap_token"
    anonymous_cap_client = LiveAPIClient(
        base_url=manifest.base_url,
        request_timeout_seconds=manifest.request_timeout_seconds,
        endpoint_log=evidence["endpoint_calls"],
    )
    cap_endpoint = anonymous_cap_client.discover_cap_endpoint(
        runid=manifest.source_runid,
        config=manifest.source_config,
    )
    cap_token, cap_redeem_payload = _solve_cap_token(anonymous_cap_client, cap_endpoint=cap_endpoint)
    evidence["cap"] = {
        "endpoint": cap_endpoint,
        "redeem_success": bool(cap_redeem_payload.get("success")),
        "expires": cap_redeem_payload.get("expires"),
    }
    flush_evidence()

    evidence["phase"] = "submitting_fork"
    fork_target_runid = _generate_target_runid()
    fork_payload = client.fork_run(
        source_runid=manifest.source_runid,
        config=manifest.source_config,
        bearer_token=source_session_token,
        target_runid=fork_target_runid,
        cap_token=cap_token,
    )
    fork_job_id = str(fork_payload.get("job_id") or "").strip()
    fork_runid = str(fork_payload.get("new_runid") or fork_target_runid)
    if not fork_job_id:
        raise LiveApiError(f"fork response missing job_id: {fork_payload}")
    evidence["fork"] = {
        "requested_target_runid": fork_target_runid,
        "fork_runid": fork_runid,
        "fork_job_id": fork_job_id,
    }
    flush_evidence()

    evidence["phase"] = "waiting_for_fork"
    fork_wait = client.wait_for_job(
        job_id=fork_job_id,
        timeout_seconds=min(float(manifest.fork_timeout_seconds), 180.0),
        poll_interval_seconds=manifest.poll_interval_seconds,
        bearer_token=source_session_token,
    )

    evidence["phase"] = "issuing_fork_session_token"
    fork_token_payload = client.issue_session_token(
        runid=fork_runid,
        config=manifest.source_config,
        session_origin=manifest.session_origin,
        bearer_token=minted_bearer_token,
    )
    fork_session_token = str(fork_token_payload.get("token") or "").strip()
    if not fork_session_token:
        raise LiveApiError(f"session-token endpoint missing fork token: {fork_token_payload}")

    evidence["fork"] = {
        "requested_target_runid": fork_target_runid,
        "fork_runid": fork_runid,
        "fork_job_id": fork_job_id,
        "fork_wait_seconds": fork_wait.elapsed_seconds,
        "fork_status": fork_wait.status_payload,
        "fork_session_token_mode": "minted_bearer",
        "fork_token_class": fork_token_payload.get("token_class"),
    }
    flush_evidence()
    fork = ForkLookup(
        client,
        manifest,
        {
            "runid": fork_runid,
            "config": manifest.source_config,
            "bearer_token": fork_session_token,
        },
    )
    return fork, source_session_token, source_before, fork_wait


@dataclass
class PropertyBaseline:
    target: dict[str, Any]
    control: dict[str, Any]
    target_soil: PropertyArtifact
    target_management: PropertyArtifact
    control_soil: PropertyArtifact

    @classmethod
    def capture(cls, fork: ForkLookup) -> PropertyBaseline:
        manifest = fork.manifest
        resources = _select_property_sol_subpaths(
            fork.client,
            **fork.scope,
            target_luse=manifest.target_luse,
            target_stext=manifest.target_stext,
            management_fields=manifest.target_management_fields,
        )
        target, control = resources["target"], resources["control"]
        return cls(target, control, fork.soil(target), fork.management(target), fork.soil(control))


def _record_artifacts(
    evidence: dict[str, Any],
    manifest: LiveE2EManifest,
    properties: PropertyBaseline,
    control_after: PropertyArtifact,
    base: StageOutputs,
    extended: StageOutputs,
    man_after: PropertyArtifact,
    source_before: SourceFingerprint,
    source_after: SourceFingerprint,
) -> None:
    def soil_fields(soil: PropertyArtifact) -> dict[str, Any]:
        return {field: soil.fields.get(field) for field in manifest.target_sol_fields}

    evidence["resource_scope"] = {
        "target": {
            "sol_subpath": properties.target["sol_subpath"],
            "man_subpath": properties.target["man_subpath"],
            "key": properties.target["key"],
            "sol_before": soil_fields(properties.target_soil),
            "sol_after_base": soil_fields(base.target_soil),
            "sol_after_extended": soil_fields(extended.target_soil),
            "man_before": properties.target_management.fields,
            "man_after_extended": man_after.fields,
        },
        "control": {
            "sol_subpath": properties.control["sol_subpath"],
            "key": properties.control["key"],
            "sol_before": soil_fields(properties.control_soil),
            "sol_after_base": soil_fields(control_after),
        },
        "scope_notes": (
            "Disturbed lookup edits are global by (luse,stext) key. "
            "Assertions verify target-key resources change while non-target key resources remain unchanged."
        ),
    }
    evidence["artifact_hashes"] = {
        "source_pmetpara_before": _artifact_text_hash(
            subpath="wepp/runs/pmetpara.txt", text=source_before.pmet
        ),
        "source_pmetpara_after": _artifact_text_hash(
            subpath="wepp/runs/pmetpara.txt", text=source_after.pmet
        ),
        "fork_pmetpara_after_base": _artifact_text_hash(subpath="wepp/runs/pmetpara.txt", text=base.pmet),
        "fork_pmetpara_after_extended": _artifact_text_hash(
            subpath="wepp/runs/pmetpara.txt", text=extended.pmet
        ),
        "target_sol_before": properties.target_soil.fingerprint(),
        "target_sol_after_base": base.target_soil.fingerprint(),
        "target_sol_after_extended": extended.target_soil.fingerprint(),
        "target_man_before": properties.target_management.fingerprint(),
        "target_man_after_extended": man_after.fingerprint(),
        "control_sol_before": properties.control_soil.fingerprint(),
        "control_sol_after_base": control_after.fingerprint(),
    }


def _exercise_fork(
    fork: ForkLookup,
    source_token: str,
    source_before: SourceFingerprint,
    fork_wait: JobWaitResult,
    evidence: dict[str, Any],
    flush_evidence: Callable[[], tuple[Path, Path]],
) -> None:
    manifest = fork.manifest
    evidence["phase"] = "capturing_base_lookup"
    before = fork.snapshot("base")
    index = fork.target_index(before)
    evidence["phase"] = "running_negative_contracts"
    negative = fork.negative_cases(before)

    evidence["phase"] = "selecting_target_resources"
    properties = PropertyBaseline.capture(fork)

    evidence["phase"] = "patching_base_lookup"
    base_edit = fork.patch("base", before, index, manifest.base_patch)
    flush_evidence()
    base = fork.rebuild("base", properties.target, evidence)
    control_after = fork.soil(properties.control)

    evidence["phase"] = "loading_extended_lookup"
    fork.client.load_extended_lookup(**fork.scope)
    fork.client.sync_base_to_extended_lookup(**fork.scope)
    extended_before = fork.snapshot("extended")
    extended_index = fork.target_index(extended_before)
    evidence["phase"] = "patching_extended_lookup"
    extended_edit = fork.patch("extended", extended_before, extended_index, manifest.extended_patch)
    base_after_extended = fork.snapshot("base")
    flush_evidence()
    extended = fork.rebuild("extended", properties.target, evidence)
    man_after = fork.management(properties.target)

    evidence["phase"] = "capturing_source_after"
    source_after = SourceFingerprint.capture(fork.client, manifest, source_token)

    assertions = {"run_lifecycle_fork_finished": fork_wait.status_payload.get("status") == "finished"}
    for variant, stage in (("base", base), ("extended", extended)):
        for job, record in stage.jobs.items():
            assertions[f"run_lifecycle_{variant}_{job}_finished"] = (
                record["status"].get("status") == "finished"
            )
    assertions.update(
        {
            "source_immutable_lookup_sha": source_before.lookup_sha == source_after.lookup_sha,
            "source_immutable_pmetpara_sha": _sha256_text(source_before.pmet)
            == _sha256_text(source_after.pmet),
            "negative_stale_lookup_contract": negative["stale"].get("error", {}).get("code")
            == "STALE_LOOKUP",
            "negative_partial_table_contract": "missing existing lookup rows"
            in str(negative["partial_rows"].get("error", {}).get("message", "")).lower(),
            "negative_missing_columns_contract": "missing columns"
            in str(negative["invalid_columns"].get("error", {}).get("message", "")).lower(),
        }
    )
    assertions.update(
        stage_assertions(
            manifest,
            base,
            extended,
            base_edit,
            extended_edit,
            base_after_extended.rows,
            properties.control_soil,
            control_after,
            man_after,
        )
    )
    evidence["assertions"] = assertions
    evidence["source_after"] = source_after.evidence()
    evidence["negative_cases"] = negative
    evidence["lookup_rows"] = {
        "base_before": before.row_evidence(index),
        "base_after_patch": base_edit.after_evidence(),
        "extended_before": extended_before.row_evidence(extended_index)
        | {"lookup_variant": extended_before.metadata.get("lookup_variant")},
        "extended_after_patch": extended_edit.after_evidence(),
    }
    evidence["jobs"] = {"base_stage": base.jobs, "extended_stage": extended.jobs}

    _record_artifacts(
        evidence,
        manifest,
        properties,
        control_after,
        base,
        extended,
        man_after,
        source_before,
        source_after,
    )
    evidence["pmetpara"] = {
        "target_description": manifest.target_pmet_description,
        "rows_after_base": base.target_pmet_rows,
        "rows_after_extended": extended.target_pmet_rows,
        "sha_after_base": _sha256_text(base.pmet),
        "sha_after_extended": _sha256_text(extended.pmet),
    }
    payload = deterministic_payload(manifest, base, extended, base_edit, extended_edit, man_after)
    evidence["determinism"] = {"payload": payload, "signature": _canonical_hash(payload)}


def execute_live_runbook(
    *,
    manifest: LiveE2EManifest | None = None,
    evidence_root: str | Path,
    run_label: str,
) -> RunbookResult:
    manifest = manifest or load_manifest()
    evidence_root_path = Path(evidence_root)
    evidence_root_path.mkdir(parents=True, exist_ok=True)
    evidence_dir = evidence_root_path / f"{run_label}_{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"

    endpoint_calls: list[dict[str, Any]] = []
    client = LiveAPIClient(
        base_url=manifest.base_url,
        request_timeout_seconds=manifest.request_timeout_seconds,
        endpoint_log=endpoint_calls,
    )

    evidence: dict[str, Any] = {
        "run_label": run_label,
        "started_at_utc": _utcnow_iso(),
        "source_run": {"runid": manifest.source_runid, "config": manifest.source_config},
        "target_lookup": {"luse": manifest.target_luse, "stext": manifest.target_stext},
        "endpoint_calls": endpoint_calls,
        "assertions": {},
    }
    evidence["phase"] = "initializing"

    def flush_evidence() -> tuple[Path, Path]:
        return _write_evidence_artifacts(evidence_dir=evidence_dir, evidence=evidence)

    dev_agent_email, dev_agent_password, credentials_probe = _load_dev_agent_credentials(
        credentials_file=manifest.dev_agent_credentials_file,
    )
    evidence["input_probes"] = {"dev_agent_credentials": credentials_probe}

    try:
        fork, source_token, source_before, fork_wait = _prepare_fork(
            client,
            manifest,
            evidence,
            flush_evidence,
            dev_agent_email,
            dev_agent_password,
        )
        _exercise_fork(fork, source_token, source_before, fork_wait, evidence, flush_evidence)
        evidence["cleanup"] = {
            "performed": False,
            "status": "retained",
            "reason": "No authenticated run-delete contract is currently wired into the live harness.",
        }

        evidence["all_assertions_passed"] = all(evidence["assertions"].values())
        evidence["phase"] = "completed"
        flush_evidence()
    # Preserve the last phase and both evidence files for every runbook failure.
    except Exception as exc:
        evidence["failure"] = {
            "type": type(exc).__name__,
            "message": str(exc),
            "phase": evidence["phase"],
        }
        evidence["all_assertions_passed"] = False
        evidence_json_path, evidence_markdown_path = flush_evidence()
        print(f"failure evidence: {evidence_json_path}", flush=True)
        raise
    finally:
        evidence["completed_at_utc"] = _utcnow_iso()
        evidence_json_path, evidence_markdown_path = flush_evidence()

    return RunbookResult(
        evidence_json_path=evidence_json_path,
        evidence_markdown_path=evidence_markdown_path,
        fork_runid=fork.scope["runid"],
        deterministic_signature=evidence["determinism"]["signature"],
        assertions=evidence["assertions"],
    )
