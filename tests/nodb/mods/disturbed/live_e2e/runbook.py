from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import random
import re
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from wepppy.wepp.management import Management

from .api_client import LiveAPIClient, LiveApiError
from .manifest import LiveE2EManifest, load_manifest


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_text(payload: str) -> str:
    return _sha256_bytes(payload.encode("utf-8"))


def _canonical_hash(payload: Any) -> str:
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return _sha256_text(text)


def _artifact_text_hash(*, subpath: str, text: str) -> dict[str, Any]:
    payload = text.encode("utf-8")
    return {
        "subpath": subpath,
        "size_bytes": len(payload),
        "sha256": _sha256_bytes(payload),
    }


def _normalize_float_string(value: Any) -> str:
    text = str(value).strip()
    if text == "":
        return text
    try:
        return f"{float(text):.6f}"
    except ValueError:
        return text


def _parse_lookup_rows(csv_text: str) -> list[dict[str, str]]:
    reader = csv.DictReader(io.StringIO(csv_text))
    return [dict(row) for row in reader]


def _lookup_key(row: dict[str, Any]) -> tuple[str, str]:
    luse = str(row.get("luse") or row.get("disturbed_class") or "").strip()
    stext = str(row.get("stext") or row.get("texid") or "").strip()
    return luse, stext


def _find_lookup_row_index(rows: list[dict[str, str]], *, luse: str, stext: str) -> int:
    target = (luse.strip(), stext.strip())
    for index, row in enumerate(rows):
        if _lookup_key(row) == target:
            return index
    raise LiveApiError(f"Target lookup row not found for key {target}")


def _apply_patch(
    rows: list[dict[str, str]],
    *,
    row_index: int,
    patch: dict[str, str],
) -> list[dict[str, str]]:
    out = [dict(row) for row in rows]
    for key, value in patch.items():
        if key not in out[row_index]:
            raise LiveApiError(f"Cannot patch missing column '{key}' in lookup row")
        out[row_index][key] = str(value)
    return out


def _parse_pmetpara(text: str) -> list[dict[str, str]]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        raise LiveApiError("pmetpara.txt was empty")
    records: list[dict[str, str]] = []
    for line in lines[1:]:
        parts = [part.strip() for part in line.split(",", 4)]
        if len(parts) != 5:
            continue
        records.append(
            {
                "plant": parts[0],
                "kcb": parts[1],
                "rawp": parts[2],
                "index": parts[3],
                "description": parts[4],
            }
        )
    return records


def _parse_sol_replacements(sol_text: str) -> dict[str, str]:
    replacements: dict[str, str] = {}
    in_block = False
    for raw_line in sol_text.splitlines():
        line = raw_line.strip()
        if line.startswith("# Replacements"):
            in_block = True
            continue
        if not in_block:
            continue
        if not line.startswith("#"):
            break
        body = line[1:].strip()
        if "->" not in body:
            continue
        key, value = body.split("->", 1)
        replacements[key.strip()] = value.strip()
    if not replacements:
        raise LiveApiError("Could not parse replacement block from .sol artifact")
    return replacements


def _extract_property_index_from_subpath(subpath: str) -> str:
    match = re.search(r"p(\d+)\.sol$", subpath)
    if not match:
        raise LiveApiError(f"Unexpected .sol subpath format: {subpath}")
    return match.group(1)


def _parse_management_fields(man_text: str, *, management_fields: Iterable[str]) -> dict[str, str]:
    with tempfile.TemporaryDirectory(prefix="disturbed-live-e2e-man-") as tmpdir:
        tmp_path = Path(tmpdir) / "probe.man"
        tmp_path.write_text(man_text)
        management = Management.load(
            key=None,
            man_fn=tmp_path.name,
            man_dir=tmpdir,
            desc="disturbed-live-e2e",
        )

    if not management.plants or not management.inis:
        raise LiveApiError("Management file parse did not expose plant/ini sections")

    out: dict[str, str] = {}
    for field in management_fields:
        if field.startswith("plant.data."):
            attr = field[len("plant.data.") :]
            value = getattr(management.plants[0].data, attr)
            out[field] = _normalize_float_string(value)
        elif field.startswith("ini.data."):
            attr = field[len("ini.data.") :]
            value = getattr(management.inis[0].data, attr)
            out[field] = _normalize_float_string(value)
        else:
            raise LiveApiError(f"Unsupported management field selector: {field}")
    return out


def _fnv32a_hash(text: str) -> int:
    value = 2166136261
    for char in text:
        value ^= ord(char)
        value = (value + (value << 1) + (value << 4) + (value << 7) + (value << 8) + (value << 24)) & 0xFFFFFFFF
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
        digest = hashlib.sha256(f"{salt}{nonce}".encode("utf-8")).digest()
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
        return env_email, env_password, {
            "source": "environment",
            "loaded": True,
            "email_present": True,
            "password_present": True,
        }

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
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    suffix = f"{random.getrandbits(24):06x}"
    return f"live-disturbed-{stamp}-{suffix}"


def _select_property_sol_subpaths(
    client: LiveAPIClient,
    *,
    runid: str,
    config: str,
    bearer_token: str,
    target_luse: str,
    target_stext: str,
    management_fields: list[str],
) -> dict[str, Any]:
    pmetpara_text = client.download_text(
        runid=runid,
        config=config,
        subpath="wepp/runs/pmetpara.txt",
        bearer_token=bearer_token,
    )
    pmet_rows = _parse_pmetpara(pmetpara_text)

    target_entry: dict[str, Any] | None = None
    control_entry: dict[str, Any] | None = None

    for row in pmet_rows:
        index = row.get("index")
        if not index or not str(index).isdigit():
            continue
        sol_subpath = f"wepp/runs/p{index}.sol"
        try:
            sol_text = client.download_text(
                runid=runid,
                config=config,
                subpath=sol_subpath,
                bearer_token=bearer_token,
            )
        except LiveApiError:
            continue

        replacements = _parse_sol_replacements(sol_text)
        key = (
            str(replacements.get("luse") or "").strip(),
            str(replacements.get("stext") or "").strip(),
        )
        entry = {
            "index": index,
            "sol_subpath": sol_subpath,
            "sol_replacements": replacements,
            "key": {"luse": key[0], "stext": key[1]},
        }

        if key == (target_luse, target_stext):
            man_subpath = f"wepp/runs/p{index}.man"
            try:
                man_text = client.download_text(
                    runid=runid,
                    config=config,
                    subpath=man_subpath,
                    bearer_token=bearer_token,
                )
                man_fields = _parse_management_fields(man_text, management_fields=management_fields)
                entry["man_subpath"] = man_subpath
                entry["man_fields"] = man_fields
                target_entry = entry
                if control_entry is not None:
                    break
            except LiveApiError:
                continue
        else:
            if control_entry is None:
                control_entry = entry
            if target_entry is not None:
                break

    if target_entry is None:
        raise LiveApiError(
            f"Could not locate target property resource for lookup key ({target_luse}, {target_stext})"
        )
    if control_entry is None:
        raise LiveApiError("Could not locate non-target control property resource for scope assertion")

    return {
        "target": target_entry,
        "control": control_entry,
        "pmetpara_rows": pmet_rows,
    }


@dataclass(frozen=True)
class RunbookResult:
    evidence_json_path: Path
    evidence_markdown_path: Path
    fork_runid: str
    deterministic_signature: str
    assertions: dict[str, bool]


def _write_evidence_artifacts(
    *,
    evidence_dir: Path,
    evidence: dict[str, Any],
) -> tuple[Path, Path]:
    evidence_dir.mkdir(parents=True, exist_ok=True)
    evidence_json_path = evidence_dir / "evidence.json"
    evidence_markdown_path = evidence_dir / "evidence.md"

    evidence_json_path.write_text(json.dumps(evidence, indent=2, sort_keys=True))

    cleanup = evidence.get("cleanup") or {}
    resource_scope = evidence.get("resource_scope") or {}
    target_scope = resource_scope.get("target") or {}
    control_scope = resource_scope.get("control") or {}
    assertions = evidence.get("assertions") or {}

    summary_lines = [
        "# Disturbed Lookup Live E2E Evidence",
        "",
        f"- run_label: `{evidence.get('run_label', '')}`",
        f"- phase: `{evidence.get('phase', 'unknown')}`",
        f"- fork_runid: `{(evidence.get('fork') or {}).get('fork_runid', 'pending')}`",
        f"- all_assertions_passed: `{evidence.get('all_assertions_passed', False)}`",
        f"- deterministic_signature: `{(evidence.get('determinism') or {}).get('signature', 'pending')}`",
        f"- cleanup_status: `{cleanup.get('status', 'unknown')}`",
        "",
        "## Assertions",
        "",
    ]
    for name, passed in sorted(assertions.items()):
        summary_lines.append(f"- {'PASS' if passed else 'FAIL'}: `{name}`")

    failure = evidence.get("failure")
    if failure:
        summary_lines.extend(
            [
                "",
                "## Failure",
                "",
                f"- type: `{failure.get('type', 'unknown')}`",
                f"- phase: `{failure.get('phase', 'unknown')}`",
                f"- message: `{failure.get('message', '')}`",
            ]
        )

    summary_lines.extend(
        [
            "",
            "## Key Artifacts",
            "",
            f"- target_sol: `{target_scope.get('sol_subpath', 'pending')}`",
            f"- target_man: `{target_scope.get('man_subpath', 'pending')}`",
            f"- control_sol: `{control_scope.get('sol_subpath', 'pending')}`",
            f"- pmet_description: `{(evidence.get('pmetpara') or {}).get('target_description', 'pending')}`",
            "",
            "## Endpoint Trace",
            "",
            f"- total_calls: `{len(evidence.get('endpoint_calls') or [])}`",
        ]
    )
    evidence_markdown_path.write_text("\n".join(summary_lines) + "\n")

    return evidence_json_path, evidence_markdown_path


def execute_live_runbook(
    *,
    manifest: LiveE2EManifest | None = None,
    evidence_root: str | Path,
    run_label: str,
) -> RunbookResult:
    manifest = manifest or load_manifest()
    evidence_root_path = Path(evidence_root)
    evidence_root_path.mkdir(parents=True, exist_ok=True)
    evidence_dir = evidence_root_path / f"{run_label}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

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
    phase = "initializing"
    fork_runid = "pending"
    deterministic_signature = "pending"

    def flush_evidence() -> tuple[Path, Path]:
        evidence["phase"] = phase
        return _write_evidence_artifacts(evidence_dir=evidence_dir, evidence=evidence)

    dev_agent_email, dev_agent_password, credentials_probe = _load_dev_agent_credentials(
        credentials_file=manifest.dev_agent_credentials_file,
    )
    evidence["input_probes"] = {"dev_agent_credentials": credentials_probe}

    try:
        phase = "minting_dev_agent_bearer"
        minted_token_payload = client.login_and_mint_dev_agent_bearer(
            email=dev_agent_email,
            password=dev_agent_password,
        )
        minted_bearer_token = str(minted_token_payload.get("token") or "").strip()
        if not minted_bearer_token:
            raise LiveApiError("mint-token flow did not return a bearer token")

        phase = "issuing_source_session_token"
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

        phase = "capturing_source_fingerprints"
        source_lookup_before = client.disturbed_lookup_meta(
            runid=manifest.source_runid,
            config=manifest.source_config,
            bearer_token=source_session_token,
            lookup="base",
        )
        source_pmet_before = client.download_text(
            runid=manifest.source_runid,
            config=manifest.source_config,
            subpath="wepp/runs/pmetpara.txt",
            bearer_token=source_session_token,
        )

        evidence["source_before"] = {
            "base_lookup_sha256": source_lookup_before.get("lookup_sha256"),
            "pmetpara_sha256": _sha256_text(source_pmet_before),
        }
        flush_evidence()

        phase = "solving_cap_token"
        anonymous_cap_client = LiveAPIClient(
            base_url=manifest.base_url,
            request_timeout_seconds=manifest.request_timeout_seconds,
            endpoint_log=endpoint_calls,
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

        phase = "submitting_fork"
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

        phase = "waiting_for_fork"
        fork_wait = client.wait_for_job(
            job_id=fork_job_id,
            timeout_seconds=min(float(manifest.fork_timeout_seconds), 180.0),
            poll_interval_seconds=manifest.poll_interval_seconds,
            bearer_token=source_session_token,
        )

        phase = "issuing_fork_session_token"
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

        phase = "capturing_base_lookup"
        base_snapshot_before = client.disturbed_lookup_snapshot(
        runid=fork_runid,
        config=manifest.source_config,
        bearer_token=fork_session_token,
        lookup="base",
        )
        base_rows_before = _parse_lookup_rows(str(base_snapshot_before.get("csv_text") or ""))
        target_row_index = _find_lookup_row_index(
            base_rows_before,
            luse=manifest.target_luse,
            stext=manifest.target_stext,
        )
        target_row_before = dict(base_rows_before[target_row_index])

        phase = "running_negative_contracts"
        stale_response = client.disturbed_modify(
        runid=fork_runid,
        config=manifest.source_config,
        bearer_token=fork_session_token,
        lookup="base",
        rows=base_rows_before,
        if_match_sha256=manifest.stale_sha256,
        expected_statuses=(409,),
    )
        stale_payload = stale_response.json()

        partial_rows_response = client.disturbed_modify(
        runid=fork_runid,
        config=manifest.source_config,
        bearer_token=fork_session_token,
        lookup="base",
        rows=base_rows_before[:1],
        if_match_sha256=str(base_snapshot_before.get("lookup_sha256") or ""),
        expected_statuses=(400,),
    )
        partial_payload = partial_rows_response.json()

        invalid_columns_response = client.disturbed_modify(
        runid=fork_runid,
        config=manifest.source_config,
        bearer_token=fork_session_token,
        lookup="base",
        rows=[{"luse": manifest.target_luse, "stext": manifest.target_stext}],
        if_match_sha256=str(base_snapshot_before.get("lookup_sha256") or ""),
        expected_statuses=(400,),
    )
        invalid_columns_payload = invalid_columns_response.json()

        phase = "selecting_target_resources"
        selected_resources = _select_property_sol_subpaths(
        client,
        runid=fork_runid,
        config=manifest.source_config,
        bearer_token=fork_session_token,
        target_luse=manifest.target_luse,
        target_stext=manifest.target_stext,
        management_fields=manifest.target_management_fields,
    )
        target_resource = selected_resources["target"]
        control_resource = selected_resources["control"]
        target_sol_before_text = client.download_text(
            runid=fork_runid,
            config=manifest.source_config,
            subpath=str(target_resource["sol_subpath"]),
            bearer_token=fork_session_token,
        )
        target_sol_before = _parse_sol_replacements(target_sol_before_text)
        target_man_before_text = client.download_text(
            runid=fork_runid,
            config=manifest.source_config,
            subpath=str(target_resource["man_subpath"]),
            bearer_token=fork_session_token,
        )
        target_man_before = _parse_management_fields(
            target_man_before_text,
            management_fields=manifest.target_management_fields,
        )
        control_sol_before_text = client.download_text(
            runid=fork_runid,
            config=manifest.source_config,
            subpath=str(control_resource["sol_subpath"]),
            bearer_token=fork_session_token,
        )
        control_sol_before = _parse_sol_replacements(control_sol_before_text)

        phase = "patching_base_lookup"
        patched_base_rows = _apply_patch(
        base_rows_before,
        row_index=target_row_index,
        patch=manifest.base_patch,
    )

        modify_base_response = client.disturbed_modify(
        runid=fork_runid,
        config=manifest.source_config,
        bearer_token=fork_session_token,
        lookup="base",
        rows=patched_base_rows,
        if_match_sha256=str(base_snapshot_before.get("lookup_sha256") or ""),
        expected_statuses=(200,),
    )

        base_snapshot_after_patch = client.disturbed_lookup_snapshot(
        runid=fork_runid,
        config=manifest.source_config,
        bearer_token=fork_session_token,
        lookup="base",
    )
        base_rows_after_patch = _parse_lookup_rows(str(base_snapshot_after_patch.get("csv_text") or ""))
        target_row_after_base_patch = dict(base_rows_after_patch[target_row_index])
        flush_evidence()

        phase = "running_base_build_soils"
        build_soils_job = client.build_soils(
        runid=fork_runid,
        config=manifest.source_config,
        bearer_token=fork_session_token,
    )
        build_soils_wait = client.wait_for_job(
        job_id=build_soils_job,
        timeout_seconds=manifest.build_soils_timeout_seconds,
        poll_interval_seconds=manifest.poll_interval_seconds,
        bearer_token=fork_session_token,
    )

        phase = "running_base_prep_wepp"
        prep_job = client.prep_wepp_watershed(
        runid=fork_runid,
        config=manifest.source_config,
        bearer_token=fork_session_token,
    )
        prep_wait = client.wait_for_job(
        job_id=prep_job,
        timeout_seconds=manifest.prep_wepp_timeout_seconds,
        poll_interval_seconds=manifest.poll_interval_seconds,
        bearer_token=fork_session_token,
    )

        phase = "capturing_base_outputs"
        pmet_after_base = client.download_text(
        runid=fork_runid,
        config=manifest.source_config,
        subpath="wepp/runs/pmetpara.txt",
        bearer_token=fork_session_token,
    )
        pmet_rows_after_base = _parse_pmetpara(pmet_after_base)

        target_sol_after_base_text = client.download_text(
            runid=fork_runid,
            config=manifest.source_config,
            subpath=str(target_resource["sol_subpath"]),
            bearer_token=fork_session_token,
        )
        target_sol_after_base = _parse_sol_replacements(target_sol_after_base_text)
        control_sol_after_base_text = client.download_text(
            runid=fork_runid,
            config=manifest.source_config,
            subpath=str(control_resource["sol_subpath"]),
            bearer_token=fork_session_token,
        )
        control_sol_after_base = _parse_sol_replacements(control_sol_after_base_text)

        phase = "loading_extended_lookup"
        client.load_extended_lookup(
        runid=fork_runid,
        config=manifest.source_config,
        bearer_token=fork_session_token,
    )
        client.sync_base_to_extended_lookup(
        runid=fork_runid,
        config=manifest.source_config,
        bearer_token=fork_session_token,
    )

        extended_snapshot_before_patch = client.disturbed_lookup_snapshot(
        runid=fork_runid,
        config=manifest.source_config,
        bearer_token=fork_session_token,
        lookup="extended",
    )
        extended_rows_before = _parse_lookup_rows(str(extended_snapshot_before_patch.get("csv_text") or ""))
        extended_target_index = _find_lookup_row_index(
        extended_rows_before,
        luse=manifest.target_luse,
        stext=manifest.target_stext,
    )

        phase = "patching_extended_lookup"
        patched_extended_rows = _apply_patch(
        extended_rows_before,
        row_index=extended_target_index,
        patch=manifest.extended_patch,
    )
        modify_extended_response = client.disturbed_modify(
        runid=fork_runid,
        config=manifest.source_config,
        bearer_token=fork_session_token,
        lookup="extended",
        rows=patched_extended_rows,
        if_match_sha256=str(extended_snapshot_before_patch.get("lookup_sha256") or ""),
        expected_statuses=(200,),
    )

        extended_snapshot_after_patch = client.disturbed_lookup_snapshot(
        runid=fork_runid,
        config=manifest.source_config,
        bearer_token=fork_session_token,
        lookup="extended",
    )
        extended_rows_after_patch = _parse_lookup_rows(str(extended_snapshot_after_patch.get("csv_text") or ""))
        target_row_after_extended_patch = dict(extended_rows_after_patch[extended_target_index])

        base_snapshot_after_extended_patch = client.disturbed_lookup_snapshot(
        runid=fork_runid,
        config=manifest.source_config,
        bearer_token=fork_session_token,
        lookup="base",
    )
        base_rows_after_extended_patch = _parse_lookup_rows(str(base_snapshot_after_extended_patch.get("csv_text") or ""))
        flush_evidence()

        phase = "running_extended_build_soils"
        build_soils_extended_job = client.build_soils(
        runid=fork_runid,
        config=manifest.source_config,
        bearer_token=fork_session_token,
    )
        build_soils_extended_wait = client.wait_for_job(
        job_id=build_soils_extended_job,
        timeout_seconds=manifest.build_soils_timeout_seconds,
        poll_interval_seconds=manifest.poll_interval_seconds,
        bearer_token=fork_session_token,
    )

        phase = "running_extended_prep_wepp"
        prep_extended_job = client.prep_wepp_watershed(
        runid=fork_runid,
        config=manifest.source_config,
        bearer_token=fork_session_token,
    )
        prep_extended_wait = client.wait_for_job(
        job_id=prep_extended_job,
        timeout_seconds=manifest.prep_wepp_timeout_seconds,
        poll_interval_seconds=manifest.poll_interval_seconds,
        bearer_token=fork_session_token,
    )

        phase = "capturing_extended_outputs"
        pmet_after_extended = client.download_text(
        runid=fork_runid,
        config=manifest.source_config,
        subpath="wepp/runs/pmetpara.txt",
        bearer_token=fork_session_token,
    )
        pmet_rows_after_extended = _parse_pmetpara(pmet_after_extended)

        target_sol_after_extended_text = client.download_text(
            runid=fork_runid,
            config=manifest.source_config,
            subpath=str(target_resource["sol_subpath"]),
            bearer_token=fork_session_token,
        )
        target_sol_after_extended = _parse_sol_replacements(target_sol_after_extended_text)

        target_man_after_extended_text = client.download_text(
            runid=fork_runid,
            config=manifest.source_config,
            subpath=str(target_resource["man_subpath"]),
            bearer_token=fork_session_token,
        )
        target_man_after_extended = _parse_management_fields(
        target_man_after_extended_text,
        management_fields=manifest.target_management_fields,
    )

        phase = "capturing_source_after"
        source_lookup_after = client.disturbed_lookup_meta(
        runid=manifest.source_runid,
        config=manifest.source_config,
        bearer_token=source_session_token,
        lookup="base",
    )
        source_pmet_after = client.download_text(
        runid=manifest.source_runid,
        config=manifest.source_config,
        subpath="wepp/runs/pmetpara.txt",
        bearer_token=source_session_token,
    )

        target_pmet_rows_base = [
        row
        for row in pmet_rows_after_base
        if row.get("description") == manifest.target_pmet_description
    ]
        target_pmet_rows_extended = [
        row
        for row in pmet_rows_after_extended
        if row.get("description") == manifest.target_pmet_description
    ]

        control_fields_before = {
        field: _normalize_float_string(control_sol_before.get(field))
        for field in manifest.target_sol_fields
    }
        control_fields_after_base = {
        field: _normalize_float_string(control_sol_after_base.get(field))
        for field in manifest.target_sol_fields
    }

        assertions: dict[str, bool] = {
        "run_lifecycle_fork_finished": fork_wait.status_payload.get("status") == "finished",
        "run_lifecycle_base_build_soils_finished": build_soils_wait.status_payload.get("status") == "finished",
        "run_lifecycle_base_prep_wepp_finished": prep_wait.status_payload.get("status") == "finished",
        "run_lifecycle_extended_build_soils_finished": build_soils_extended_wait.status_payload.get("status")
        == "finished",
        "run_lifecycle_extended_prep_wepp_finished": prep_extended_wait.status_payload.get("status") == "finished",
        "source_immutable_lookup_sha": source_lookup_before.get("lookup_sha256")
        == source_lookup_after.get("lookup_sha256"),
        "source_immutable_pmetpara_sha": _sha256_text(source_pmet_before) == _sha256_text(source_pmet_after),
        "negative_stale_lookup_contract": stale_payload.get("error", {}).get("code") == "STALE_LOOKUP",
        "negative_partial_table_contract": "missing existing lookup rows"
        in str(partial_payload.get("error", {}).get("message", "")).lower(),
        "negative_missing_columns_contract": "missing columns"
        in str(invalid_columns_payload.get("error", {}).get("message", "")).lower(),
        "base_lookup_row_patched": all(
            _normalize_float_string(target_row_after_base_patch.get(key)) == _normalize_float_string(value)
            for key, value in manifest.base_patch.items()
        ),
        "base_sol_propagation": all(
            _normalize_float_string(target_sol_after_base.get(key)) == _normalize_float_string(value)
            for key, value in manifest.base_patch.items()
            if key in manifest.target_sol_fields
        ),
        "base_pmetpara_propagation": bool(target_pmet_rows_base)
        and all(
            _normalize_float_string(row.get("kcb")) == _normalize_float_string(manifest.base_patch["pmet_kcb"])
            and _normalize_float_string(row.get("rawp")) == _normalize_float_string(manifest.base_patch["pmet_rawp"])
            for row in target_pmet_rows_base
        ),
        "scope_non_target_unchanged": control_fields_before == control_fields_after_base,
        "extended_lookup_variant_active": str(extended_snapshot_after_patch.get("lookup_variant")) == "extended",
        "extended_sol_precedence": all(
            _normalize_float_string(target_sol_after_extended.get(key)) == _normalize_float_string(value)
            for key, value in manifest.extended_patch.items()
            if key in manifest.target_sol_fields
        ),
        "extended_management_propagation": all(
            target_man_after_extended.get(key) == _normalize_float_string(value)
            for key, value in manifest.extended_patch.items()
            if key in manifest.target_management_fields
        ),
        "base_vs_extended_precedence_pmetpara": bool(target_pmet_rows_extended)
        and all(
            _normalize_float_string(row.get("kcb")) == _normalize_float_string(manifest.extended_patch["pmet_kcb"])
            and _normalize_float_string(row.get("rawp")) == _normalize_float_string(manifest.extended_patch["pmet_rawp"])
            for row in target_pmet_rows_extended
        ),
        "base_table_unchanged_after_extended_patch": all(
            _normalize_float_string(base_rows_after_extended_patch[target_row_index].get(key))
            == _normalize_float_string(manifest.base_patch[key])
            for key in manifest.base_patch
        ),
    }

        evidence["assertions"] = assertions
        evidence["source_after"] = {
        "base_lookup_sha256": source_lookup_after.get("lookup_sha256"),
        "pmetpara_sha256": _sha256_text(source_pmet_after),
    }

        evidence["negative_cases"] = {
        "stale": stale_payload,
        "partial_rows": partial_payload,
        "invalid_columns": invalid_columns_payload,
    }

        evidence["lookup_rows"] = {
        "base_before": {
            "lookup_sha256": base_snapshot_before.get("lookup_sha256"),
            "row_count": len(base_rows_before),
            "target_row": target_row_before,
            "target_row_sha256": _canonical_hash(target_row_before),
        },
        "base_after_patch": {
            "lookup_sha256": base_snapshot_after_patch.get("lookup_sha256"),
            "row_count": len(base_rows_after_patch),
            "target_row": target_row_after_base_patch,
            "target_row_sha256": _canonical_hash(target_row_after_base_patch),
            "response_lookup_sha256": modify_base_response.headers.get("X-Lookup-Sha256"),
        },
        "extended_before": {
            "lookup_sha256": extended_snapshot_before_patch.get("lookup_sha256"),
            "row_count": len(extended_rows_before),
            "target_row": dict(extended_rows_before[extended_target_index]),
            "target_row_sha256": _canonical_hash(extended_rows_before[extended_target_index]),
            "lookup_variant": extended_snapshot_before_patch.get("lookup_variant"),
        },
        "extended_after_patch": {
            "lookup_sha256": extended_snapshot_after_patch.get("lookup_sha256"),
            "row_count": len(extended_rows_after_patch),
            "target_row": target_row_after_extended_patch,
            "target_row_sha256": _canonical_hash(target_row_after_extended_patch),
            "response_lookup_sha256": modify_extended_response.headers.get("X-Lookup-Sha256"),
        },
    }

        evidence["jobs"] = {
        "base_stage": {
            "build_soils": {
                "job_id": build_soils_job,
                "wait_seconds": build_soils_wait.elapsed_seconds,
                "status": build_soils_wait.status_payload,
            },
            "prep_wepp": {
                "job_id": prep_job,
                "wait_seconds": prep_wait.elapsed_seconds,
                "status": prep_wait.status_payload,
            },
        },
        "extended_stage": {
            "build_soils": {
                "job_id": build_soils_extended_job,
                "wait_seconds": build_soils_extended_wait.elapsed_seconds,
                "status": build_soils_extended_wait.status_payload,
            },
            "prep_wepp": {
                "job_id": prep_extended_job,
                "wait_seconds": prep_extended_wait.elapsed_seconds,
                "status": prep_extended_wait.status_payload,
            },
        },
    }

        evidence["resource_scope"] = {
        "target": {
            "sol_subpath": target_resource["sol_subpath"],
            "man_subpath": target_resource["man_subpath"],
            "key": target_resource["key"],
            "sol_before": {
                field: target_sol_before.get(field)
                for field in manifest.target_sol_fields
            },
            "sol_after_base": {
                field: target_sol_after_base.get(field)
                for field in manifest.target_sol_fields
            },
            "sol_after_extended": {
                field: target_sol_after_extended.get(field)
                for field in manifest.target_sol_fields
            },
            "man_before": target_man_before,
            "man_after_extended": target_man_after_extended,
        },
        "control": {
            "sol_subpath": control_resource["sol_subpath"],
            "key": control_resource["key"],
            "sol_before": {
                field: control_sol_before.get(field)
                for field in manifest.target_sol_fields
            },
            "sol_after_base": {
                field: control_sol_after_base.get(field)
                for field in manifest.target_sol_fields
            },
        },
        "scope_notes": (
            "Disturbed lookup edits are global by (luse,stext) key. "
            "Assertions verify target-key resources change while non-target key resources remain unchanged."
        ),
    }

        evidence["artifact_hashes"] = {
        "source_pmetpara_before": _artifact_text_hash(
            subpath="wepp/runs/pmetpara.txt",
            text=source_pmet_before,
        ),
        "source_pmetpara_after": _artifact_text_hash(
            subpath="wepp/runs/pmetpara.txt",
            text=source_pmet_after,
        ),
        "fork_pmetpara_after_base": _artifact_text_hash(
            subpath="wepp/runs/pmetpara.txt",
            text=pmet_after_base,
        ),
        "fork_pmetpara_after_extended": _artifact_text_hash(
            subpath="wepp/runs/pmetpara.txt",
            text=pmet_after_extended,
        ),
        "target_sol_before": _artifact_text_hash(
            subpath=str(target_resource["sol_subpath"]),
            text=target_sol_before_text,
        ),
        "target_sol_after_base": _artifact_text_hash(
            subpath=str(target_resource["sol_subpath"]),
            text=target_sol_after_base_text,
        ),
        "target_sol_after_extended": _artifact_text_hash(
            subpath=str(target_resource["sol_subpath"]),
            text=target_sol_after_extended_text,
        ),
        "target_man_before": _artifact_text_hash(
            subpath=str(target_resource["man_subpath"]),
            text=target_man_before_text,
        ),
        "target_man_after_extended": _artifact_text_hash(
            subpath=str(target_resource["man_subpath"]),
            text=target_man_after_extended_text,
        ),
        "control_sol_before": _artifact_text_hash(
            subpath=str(control_resource["sol_subpath"]),
            text=control_sol_before_text,
        ),
        "control_sol_after_base": _artifact_text_hash(
            subpath=str(control_resource["sol_subpath"]),
            text=control_sol_after_base_text,
        ),
    }

        evidence["pmetpara"] = {
        "target_description": manifest.target_pmet_description,
        "rows_after_base": target_pmet_rows_base,
        "rows_after_extended": target_pmet_rows_extended,
        "sha_after_base": _sha256_text(pmet_after_base),
        "sha_after_extended": _sha256_text(pmet_after_extended),
    }

        deterministic_payload = {
        "base_target_sol": {
            key: _normalize_float_string(target_sol_after_base.get(key))
            for key in manifest.target_sol_fields
        },
        "extended_target_sol": {
            key: _normalize_float_string(target_sol_after_extended.get(key))
            for key in manifest.target_sol_fields
        },
        "extended_target_management": target_man_after_extended,
        "base_target_row": {
            key: _normalize_float_string(target_row_after_base_patch.get(key))
            for key in sorted(manifest.base_patch)
        },
        "extended_target_row": {
            key: _normalize_float_string(target_row_after_extended_patch.get(key))
            for key in sorted(manifest.extended_patch)
        },
        "pmet_base": [
            {
                "kcb": _normalize_float_string(row.get("kcb")),
                "rawp": _normalize_float_string(row.get("rawp")),
            }
            for row in target_pmet_rows_base
        ],
        "pmet_extended": [
            {
                "kcb": _normalize_float_string(row.get("kcb")),
                "rawp": _normalize_float_string(row.get("rawp")),
            }
            for row in target_pmet_rows_extended
        ],
        "artifact_hashes": {
            "target_sol_after_base": _sha256_text(target_sol_after_base_text),
            "target_sol_after_extended": _sha256_text(target_sol_after_extended_text),
            "target_man_after_extended": _sha256_text(target_man_after_extended_text),
            "pmet_after_base": _sha256_text(pmet_after_base),
            "pmet_after_extended": _sha256_text(pmet_after_extended),
        },
    }

        deterministic_signature = _canonical_hash(deterministic_payload)
        evidence["determinism"] = {
        "payload": deterministic_payload,
        "signature": deterministic_signature,
    }

        evidence["cleanup"] = {
            "performed": False,
            "status": "retained",
            "reason": "No authenticated run-delete contract is currently wired into the live harness.",
        }

        evidence["all_assertions_passed"] = all(assertions.values())
        phase = "completed"
        evidence_json_path, evidence_markdown_path = flush_evidence()
    except Exception as exc:
        evidence["failure"] = {
            "type": type(exc).__name__,
            "message": str(exc),
            "phase": phase,
        }
        evidence["all_assertions_passed"] = False
        evidence_json_path, evidence_markdown_path = flush_evidence()
        print(f"failure evidence: {evidence_json_path}", flush=True)
        raise
    finally:
        evidence["completed_at_utc"] = _utcnow_iso()
        evidence["phase"] = phase
        evidence_json_path, evidence_markdown_path = _write_evidence_artifacts(
            evidence_dir=evidence_dir,
            evidence=evidence,
        )

    return RunbookResult(
        evidence_json_path=evidence_json_path,
        evidence_markdown_path=evidence_markdown_path,
        fork_runid=fork_runid,
        deterministic_signature=deterministic_signature,
        assertions=assertions,
    )
