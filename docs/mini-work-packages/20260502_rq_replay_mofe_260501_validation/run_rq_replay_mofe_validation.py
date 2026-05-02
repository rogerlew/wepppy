#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

import duckdb
import requests


BASE_HOST = "https://wc.bearhive.duckdns.org"
RQ_BASE = f"{BASE_HOST}/rq-engine/api"
WORK_ROOT = Path("/workdir/wepppy/docs/mini-work-packages/20260502_rq_replay_mofe_260501_validation")
ARTIFACTS_DIR = WORK_ROOT / "artifacts"
RUNS = [
    {"runid": "moth-eaten-blackhead", "config": "disturbed9002-wbt-mofe"},
    {"runid": "cochlear-beriberi", "config": "disturbed9002-mofe"},
    {"runid": "ordained-incentive", "config": "disturbed9002-wbt-mofe"},
    {"runid": "uninsured-deformation", "config": "disturbed9002-wbt-mofe"},
]
WEPP_BIN = "wepp_260501"
DEV_AGENT_ENV_PATH = Path("/workdir/wepppy/docker/secrets/dev-agent.env")
AUDIT_WORKERS_PER_RUN = int(os.getenv("MOFE_AUDIT_WORKERS", "16"))
REQUEST_TIMEOUT_SECONDS = 90
JOB_POLL_INTERVAL_SECONDS = 10
JOB_TIMEOUT_SECONDS = 15 * 60


@dataclass
class JobResult:
    job_id: str
    terminal_status: str
    runtime_seconds: float | None
    started_at: str | None
    ended_at: str | None
    failure_payload: dict[str, Any] | None


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_env_file(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        out[key.strip()] = value.strip().strip('"').strip("'")
    return out


def extract_csrf(html: str) -> str:
    match = re.search(r'<meta[^>]+name="csrf-token"[^>]+content="([^"]+)"', html, re.I)
    if not match:
        raise RuntimeError("Could not find csrf-token meta tag")
    token = match.group(1).strip()
    if not token:
        raise RuntimeError("CSRF token was empty")
    return token


def safe_excerpt(text: str, limit: int = 500) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "...(truncated)"


def parse_json_or_none(response: requests.Response) -> Any:
    ctype = response.headers.get("content-type", "")
    if "application/json" not in ctype:
        return None
    try:
        return response.json()
    except Exception:
        return None


def log_call(
    transcript: list[dict[str, Any]],
    *,
    method: str,
    path: str,
    status_code: int | None,
    request_preview: dict[str, Any] | None = None,
    response_json: Any | None = None,
    response_text: str | None = None,
    note: str | None = None,
) -> None:
    entry = {
        "timestamp_utc": utc_now(),
        "method": method.upper(),
        "path": path,
        "status_code": status_code,
    }
    if request_preview is not None:
        entry["request"] = request_preview
    if response_json is not None:
        entry["response_json"] = response_json
    elif response_text is not None:
        entry["response_text"] = safe_excerpt(response_text)
    if note:
        entry["note"] = note
    transcript.append(entry)


def api_request(
    session: requests.Session,
    transcript: list[dict[str, Any]],
    *,
    method: str,
    path: str,
    bearer_token: str | None = None,
    json_body: dict[str, Any] | None = None,
    form_data: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    allow_statuses: tuple[int, ...] = (200,),
    allow_redirects: bool = False,
    redact_request: bool = False,
    redact_response: bool = False,
) -> requests.Response:
    url = f"{BASE_HOST}{path}"
    req_headers = dict(headers or {})
    if bearer_token:
        req_headers["Authorization"] = f"Bearer {bearer_token}"

    preview: dict[str, Any] = {}
    if json_body is not None:
        preview["json"] = "<redacted>" if redact_request else json_body
    if form_data is not None:
        preview["form"] = "<redacted>" if redact_request else form_data
    if req_headers:
        preview["headers"] = {
            key: ("<redacted>" if key.lower() in {"authorization", "x-csrftoken", "cookie"} else value)
            for key, value in req_headers.items()
        }

    try:
        response = session.request(
            method=method.upper(),
            url=url,
            json=json_body,
            data=form_data,
            headers=req_headers,
            timeout=REQUEST_TIMEOUT_SECONDS,
            allow_redirects=allow_redirects,
        )
    except requests.RequestException as exc:
        log_call(
            transcript,
            method=method,
            path=path,
            status_code=None,
            request_preview=preview,
            note=f"request_exception: {exc}",
        )
        raise

    response_payload = parse_json_or_none(response)
    if response_payload is not None:
        logged_payload = "<redacted>" if redact_response else response_payload
        log_call(
            transcript,
            method=method,
            path=path,
            status_code=response.status_code,
            request_preview=preview,
            response_json=logged_payload,
        )
    else:
        log_call(
            transcript,
            method=method,
            path=path,
            status_code=response.status_code,
            request_preview=preview,
            response_text="<redacted>" if redact_response else response.text,
        )

    if response.status_code not in allow_statuses:
        raise RuntimeError(
            f"Unexpected HTTP {response.status_code} for {method.upper()} {path}: {safe_excerpt(response.text, 1200)}"
        )
    return response


def resolve_run_root(runid: str) -> Path:
    roots = list(Path("/wc1/runs").glob(f"*/{runid}"))
    if not roots:
        raise RuntimeError(f"Run root not found for runid={runid}")
    if len(roots) > 1:
        raise RuntimeError(f"Multiple run roots found for runid={runid}: {roots}")
    return roots[0]


def parse_timestamp(ts: Any) -> datetime | None:
    if not ts:
        return None
    text = str(ts).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed
    except ValueError:
        return None


def poll_job(
    session: requests.Session,
    transcript: list[dict[str, Any]],
    *,
    bearer_token: str,
    job_id: str,
) -> JobResult:
    started_monotonic = time.monotonic()
    last_payload: dict[str, Any] | None = None

    while True:
        status_resp = api_request(
            session,
            transcript,
            method="GET",
            path=f"/rq-engine/api/jobstatus/{quote(job_id, safe='')}",
            bearer_token=bearer_token,
            allow_statuses=(200,),
        )
        payload = status_resp.json()
        last_payload = payload
        status = str(payload.get("status") or "").strip().lower()

        if status in {"finished", "failed", "stopped", "canceled"}:
            started_at = payload.get("started_at")
            ended_at = payload.get("ended_at")
            runtime_seconds: float | None = None
            dt_start = parse_timestamp(started_at)
            dt_end = parse_timestamp(ended_at)
            if dt_start and dt_end:
                runtime_seconds = max(0.0, (dt_end - dt_start).total_seconds())
            else:
                runtime_seconds = time.monotonic() - started_monotonic

            failure_payload: dict[str, Any] | None = None
            if status in {"failed", "stopped", "canceled"}:
                info_resp = api_request(
                    session,
                    transcript,
                    method="GET",
                    path=f"/rq-engine/api/jobinfo/{quote(job_id, safe='')}",
                    bearer_token=bearer_token,
                    allow_statuses=(200, 404, 500),
                )
                maybe = parse_json_or_none(info_resp)
                if isinstance(maybe, dict):
                    failure_payload = maybe

            return JobResult(
                job_id=job_id,
                terminal_status=status,
                runtime_seconds=runtime_seconds,
                started_at=str(started_at) if started_at else None,
                ended_at=str(ended_at) if ended_at else None,
                failure_payload=failure_payload,
            )

        if status not in {"queued", "started", "deferred", "scheduled"}:
            info_resp = api_request(
                session,
                transcript,
                method="GET",
                path=f"/rq-engine/api/jobinfo/{quote(job_id, safe='')}",
                bearer_token=bearer_token,
                allow_statuses=(200, 404, 500),
            )
            maybe = parse_json_or_none(info_resp)
            failure_payload = maybe if isinstance(maybe, dict) else {"note": "jobinfo unavailable"}
            return JobResult(
                job_id=job_id,
                terminal_status=f"unexpected_{status}",
                runtime_seconds=time.monotonic() - started_monotonic,
                started_at=str(payload.get("started_at") or ""),
                ended_at=str(payload.get("ended_at") or ""),
                failure_payload=failure_payload,
            )

        if time.monotonic() - started_monotonic > JOB_TIMEOUT_SECONDS:
            info_resp = api_request(
                session,
                transcript,
                method="GET",
                path=f"/rq-engine/api/jobinfo/{quote(job_id, safe='')}",
                bearer_token=bearer_token,
                allow_statuses=(200, 404, 500),
            )
            maybe = parse_json_or_none(info_resp)
            failure_payload = maybe if isinstance(maybe, dict) else {"note": "jobinfo unavailable"}
            if isinstance(failure_payload, dict) and "timeout_context" not in failure_payload:
                failure_payload["timeout_context"] = {"last_jobstatus_payload": last_payload}
            return JobResult(
                job_id=job_id,
                terminal_status="timeout",
                runtime_seconds=time.monotonic() - started_monotonic,
                started_at=str((last_payload or {}).get("started_at") or ""),
                ended_at=str((last_payload or {}).get("ended_at") or ""),
                failure_payload=failure_payload,
            )

        time.sleep(JOB_POLL_INTERVAL_SECONDS)


def find_run_wepp_operation_id(operation_docs: dict[str, Any]) -> str:
    for operation_id, block in operation_docs.items():
        descriptor = (block or {}).get("operation_descriptor") or {}
        op_path = str(descriptor.get("path") or "")
        method = str(descriptor.get("method") or "").upper()
        if method == "POST" and op_path.endswith("/run-wepp"):
            return operation_id
    raise RuntimeError("Could not find run-wepp operation in operation_docs")


def operation_descriptor_for_id(operation_docs: dict[str, Any], operation_id: str) -> dict[str, Any]:
    block = operation_docs.get(operation_id)
    if not isinstance(block, dict):
        raise RuntimeError(f"Missing operation_docs entry for {operation_id}")
    descriptor = block.get("operation_descriptor")
    if not isinstance(descriptor, dict):
        raise RuntimeError(f"Missing operation_descriptor for {operation_id}")
    return descriptor


def run_prerequisite_operation(
    session: requests.Session,
    transcript: list[dict[str, Any]],
    *,
    bearer_token: str,
    runid: str,
    config: str,
    operation_id: str,
    operation_docs: dict[str, Any],
) -> JobResult | None:
    descriptor = operation_descriptor_for_id(operation_docs, operation_id)
    op_path_template = str(descriptor.get("path") or "")
    op_method = str(descriptor.get("method") or "POST").upper()
    if op_method != "POST":
        raise RuntimeError(f"Unsupported prerequisite operation method for {operation_id}: {op_method}")

    # Descriptor path is /api/runs/{runid}/{config}/...; convert to proxied path.
    resolved_path = op_path_template.replace("{runid}", quote(runid, safe="")).replace(
        "{config}", quote(config, safe="")
    )
    if resolved_path.startswith("/api/"):
        resolved_path = "/rq-engine" + resolved_path

    submit_resp = api_request(
        session,
        transcript,
        method="POST",
        path=resolved_path,
        bearer_token=bearer_token,
        json_body={},
        allow_statuses=(200, 202),
    )
    payload = parse_json_or_none(submit_resp)
    if not isinstance(payload, dict):
        return None
    job_id = str(payload.get("job_id") or "").strip()
    if not job_id:
        return None
    return poll_job(session, transcript, bearer_token=bearer_token, job_id=job_id)


def collect_binary_evidence(run_root: Path) -> dict[str, Any]:
    cmd = [
        "rg",
        "-n",
        "--fixed-strings",
        WEPP_BIN,
        str(run_root),
        "--glob",
        "*.log",
        "--glob",
        "*.nodb",
        "--glob",
        "*.cfg",
    ]
    proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
    evidence_lines = [line for line in proc.stdout.splitlines() if line.strip()]
    first_line = evidence_lines[0] if evidence_lines else None
    return {
        "has_match": bool(first_line),
        "first_match": first_line,
        "match_count": len(evidence_lines),
    }


def get_wepp_ids(interchange_dir: Path) -> list[int]:
    wat_path = interchange_dir / "H.wat.parquet"
    con = duckdb.connect(":memory:")
    rows = con.execute(
        "SELECT DISTINCT CAST(wepp_id AS INTEGER) AS wepp_id FROM read_parquet(?) ORDER BY 1",
        [str(wat_path)],
    ).fetchall()
    return [int(row[0]) for row in rows]


def run_single_hillslope_audit(interchange_dir: Path, output_root: Path, wepp_id: int) -> dict[str, Any]:
    output_dir = output_root / f"H{wepp_id}"
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "hillslope_mofe_daily_closure_audit_summary.json"
    top_days_path = output_dir / "hillslope_mofe_daily_closure_audit_top_days.csv"
    if not summary_path.exists() or not top_days_path.exists():
        cmd = [
            sys.executable,
            "tools/hillslope_mofe_daily_closure_audit.py",
            str(interchange_dir),
            "--wepp-id",
            str(wepp_id),
            "--output-dir",
            str(output_dir),
        ]
        env = dict(os.environ)
        env["PYTHONPATH"] = "/workdir/wepppy"
        proc = subprocess.run(
            cmd,
            cwd="/workdir/wepppy",
            env=env,
            check=False,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            raise RuntimeError(
                f"MOFE audit failed for wepp_id={wepp_id}; rc={proc.returncode}; stderr={safe_excerpt(proc.stderr, 1600)}"
            )
        if not summary_path.exists() or not top_days_path.exists():
            raise RuntimeError(
                f"MOFE audit outputs missing for wepp_id={wepp_id}: summary={summary_path.exists()} top={top_days_path.exists()}"
            )

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    full = summary.get("full_physical_closure") or {}
    chain = summary.get("mofe_chain") or {}

    return {
        "wepp_id": wepp_id,
        "topaz_id": summary.get("topaz_id"),
        "requires_scientific_review": bool(full.get("requires_scientific_review", False)),
        "requires_scientific_review_days": int(full.get("requires_scientific_review_days") or 0),
        "max_abs_closure_mm": float(((full.get("closure_residual_mm") or {}).get("max_abs") or 0.0)),
        "max_abs_ofe_closure_mm": float(((full.get("max_abs_ofe_closure_residual_mm") or {}).get("max_abs") or 0.0)),
        "max_abs_chain_surface_m3": float(
            (((chain.get("surface_transfer_residual_m3_geometry_sensitive") or {}).get("max_abs")) or 0.0)
        ),
        "max_abs_chain_subsurface_m3": float(
            (((chain.get("subsurface_transfer_residual_m3") or {}).get("max_abs")) or 0.0)
        ),
        "summary_json_path": str(summary_path),
        "top_days_csv_path": str(top_days_path),
    }


def extract_worst_top_day(top_days_csv_path: str) -> dict[str, Any] | None:
    path = Path(top_days_csv_path)
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
    if not rows:
        return None

    def abs_float(row: dict[str, str], key: str) -> float:
        value = row.get(key)
        try:
            return abs(float(value)) if value not in (None, "") else 0.0
        except ValueError:
            return 0.0

    ranked = sorted(
        rows,
        key=lambda row: abs_float(row, "audit_full_physical_closure_residual_mm"),
        reverse=True,
    )
    best = ranked[0]
    return {
        "year": best.get("year"),
        "month": best.get("month"),
        "day_of_month": best.get("day_of_month"),
        "julian": best.get("julian"),
        "audit_full_physical_closure_residual_mm": best.get("audit_full_physical_closure_residual_mm"),
        "audit_full_max_abs_ofe_closure_residual_mm": best.get("audit_full_max_abs_ofe_closure_residual_mm"),
    }


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def render_api_transcript_markdown(transcript: list[dict[str, Any]], auth_mode: str) -> str:
    lines: list[str] = []
    lines.append("# API Transcript")
    lines.append("")
    lines.append(f"- Generated UTC: {utc_now()}")
    lines.append(f"- BASE_HOST: `{BASE_HOST}`")
    lines.append(f"- rq-engine base: `{RQ_BASE}`")
    lines.append(f"- Auth mode: {auth_mode}")
    lines.append("- Token values are redacted.")
    lines.append("")
    lines.append("## Calls")
    lines.append("")
    lines.append("| UTC | Method | Path | Status | Key Fields |")
    lines.append("|---|---|---|---:|---|")

    for entry in transcript:
        ts = entry.get("timestamp_utc", "")
        method = entry.get("method", "")
        path = entry.get("path", "")
        status = entry.get("status_code")
        if status is None:
            status_text = "ERR"
        else:
            status_text = str(status)

        key_fields: list[str] = []
        response_json = entry.get("response_json")
        if isinstance(response_json, dict):
            for key in ("job_id", "job_ids", "status", "error", "requested_scopes", "granted_scopes", "message"):
                if key in response_json:
                    value = response_json.get(key)
                    if key == "error" and isinstance(value, dict):
                        message = value.get("message")
                        code = value.get("code")
                        key_fields.append(f"error={message!r} code={code!r}")
                    else:
                        key_fields.append(f"{key}={value!r}")
            if not key_fields:
                key_fields.append(f"keys={list(response_json.keys())[:8]!r}")
        elif isinstance(entry.get("response_text"), str):
            text = entry["response_text"]
            key_fields.append(safe_excerpt(text, 140).replace("|", "\\|"))

        if note := entry.get("note"):
            key_fields.append(str(note))

        lines.append(f"| {ts} | {method} | `{path}` | {status_text} | {'; '.join(key_fields)} |")

    lines.append("")
    return "\n".join(lines)


def render_defect_summary_markdown(
    *,
    run_rows: list[dict[str, Any]],
    run_details: dict[tuple[str, str], dict[str, Any]],
    audit_rows: list[dict[str, Any]],
    final_verdict: str,
    verdict_reasons: list[str],
) -> str:
    lines: list[str] = []
    lines.append("# Defect Summary")
    lines.append("")
    lines.append(f"- Generated UTC: {utc_now()}")
    lines.append(f"- Target binary: `{WEPP_BIN}`")
    lines.append("")

    for run_row in run_rows:
        runid = run_row["runid"]
        config = run_row["config"]
        key = (runid, config)
        detail = run_details[key]
        lines.append(f"## {runid} / {config}")
        lines.append("")
        lines.append(f"- rerun status: `{run_row['terminal_status']}` (job_id `{run_row['submit_job_id']}`)")
        lines.append(f"- binary verification: `{run_row['binary_verification']}`")

        evidence_a = detail.get("binary_evidence_a") or ""
        evidence_b = detail.get("binary_evidence_b") or ""
        lines.append(f"- binary evidence A (request accepted): `{evidence_a}`")
        lines.append(f"- binary evidence B (run artifact snippet): `{evidence_b}`")

        per_run_audits = [row for row in audit_rows if row["runid"] == runid and row["config"] == config]
        flagged = [row for row in per_run_audits if str(row["requires_scientific_review"]).lower() == "true"]
        lines.append(f"- hillslopes flagged for scientific review: `{len(flagged)}` of `{len(per_run_audits)}`")

        if flagged:
            top_flagged = sorted(
                flagged,
                key=lambda row: float(row["max_abs_closure_mm"]),
                reverse=True,
            )[0]
            lines.append(
                "- largest flagged closure anomaly: "
                f"H{top_flagged['wepp_id']} max_abs_closure_mm={top_flagged['max_abs_closure_mm']}"
            )

        worst = detail.get("worst_top_day")
        if worst:
            lines.append(
                "- worst anomaly day: "
                f"year={worst.get('year')} month={worst.get('month')} day={worst.get('day_of_month')} "
                f"julian={worst.get('julian')} closure_mm={worst.get('audit_full_physical_closure_residual_mm')} "
                f"max_abs_ofe_mm={worst.get('audit_full_max_abs_ofe_closure_residual_mm')}"
            )
        else:
            lines.append("- worst anomaly day: not available (top-days csv missing or empty)")

        lines.append("")

    lines.append("## Final Verdict")
    lines.append("")
    lines.append(f"- verdict: **{final_verdict}**")
    if verdict_reasons:
        lines.append("- rationale:")
        for reason in verdict_reasons:
            lines.append(f"  - {reason}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    transcript: list[dict[str, Any]] = []

    creds = parse_env_file(DEV_AGENT_ENV_PATH)
    email = creds.get("DEV_AGENT_EMAIL")
    password = creds.get("DEV_AGENT_PASSWORD")
    if not email or not password:
        raise RuntimeError("DEV_AGENT_EMAIL/DEV_AGENT_PASSWORD missing in docker/secrets/dev-agent.env")

    session = requests.Session()

    # Auth bootstrap: browser login + profile mint token + machine-safe operator token mint.
    login_get = api_request(session, transcript, method="GET", path="/weppcloud/login", allow_statuses=(200,))
    login_csrf = extract_csrf(login_get.text)

    api_request(
        session,
        transcript,
        method="POST",
        path="/weppcloud/login",
        form_data={
            "email": email,
            "password": password,
            "remember": "y",
            "csrf_token": login_csrf,
        },
        allow_statuses=(200, 302),
        allow_redirects=False,
        redact_request=True,
    )

    profile_get = api_request(session, transcript, method="GET", path="/weppcloud/profile", allow_statuses=(200,))
    profile_csrf = extract_csrf(profile_get.text)

    mint_resp = api_request(
        session,
        transcript,
        method="POST",
        path="/weppcloud/profile/mint-token",
        headers={"X-CSRFToken": profile_csrf},
        allow_statuses=(200,),
        redact_request=True,
        redact_response=True,
    )
    mint_payload = mint_resp.json()
    token_payload = mint_payload.get("Content") or mint_payload.get("content") or mint_payload.get("success") or {}
    profile_token = str(token_payload.get("token") or "").strip()
    if not profile_token:
        raise RuntimeError(f"profile/mint-token did not return token payload: {mint_payload}")

    api_token = profile_token
    auth_mode = "login session + CSRF POST /weppcloud/profile/mint-token (bearer user token)"

    run_matrix_rows: list[dict[str, Any]] = []
    hillslope_rows: list[dict[str, Any]] = []
    run_details: dict[tuple[str, str], dict[str, Any]] = {}

    for run in RUNS:
        runid = run["runid"]
        config = run["config"]
        print(f"[INFO] Processing run {runid}/{config}")

        key = (runid, config)
        run_details[key] = {
            "binary_evidence_a": "",
            "binary_evidence_b": "",
            "worst_top_day": None,
            "audit_errors": [],
            "job_failure_payload": None,
        }

        pipeline = api_request(
            session,
            transcript,
            method="GET",
            path=f"/rq-engine/api/runs/{quote(runid, safe='')}/{quote(config, safe='')}/pipeline",
            bearer_token=api_token,
            allow_statuses=(200,),
        ).json()

        readiness = api_request(
            session,
            transcript,
            method="GET",
            path=f"/rq-engine/api/runs/{quote(runid, safe='')}/{quote(config, safe='')}/readiness",
            bearer_token=api_token,
            allow_statuses=(200,),
        ).json()

        endpoints = api_request(
            session,
            transcript,
            method="GET",
            path=(
                f"/rq-engine/api/runs/{quote(runid, safe='')}/{quote(config, safe='')}/endpoints"
                "?include_operation_docs=true"
            ),
            bearer_token=api_token,
            allow_statuses=(200,),
        ).json()
        operation_docs = endpoints.get("operation_docs")
        if not isinstance(operation_docs, dict):
            raise RuntimeError(f"operation_docs missing for run {runid}/{config}")

        run_wepp_operation_id = find_run_wepp_operation_id(operation_docs)

        ineligible = readiness.get("ineligible_operations") or []
        run_wepp_block = next(
            (
                block
                for block in ineligible
                if isinstance(block, dict) and str(block.get("operation_id") or "") == run_wepp_operation_id
            ),
            None,
        )

        if run_wepp_block is not None:
            blocked_ids = list(run_wepp_block.get("blocked_by_issue_ids") or [])
            issues = [
                issue
                for issue in (readiness.get("blocking_issues") or [])
                if isinstance(issue, dict) and issue.get("issue_id") in blocked_ids
            ]
            executed_any = False
            for issue in issues:
                for action in issue.get("recovery_actions") or []:
                    op_id = action.get("operation_id")
                    if not op_id or op_id == run_wepp_operation_id:
                        continue
                    print(f"[INFO] run-wepp blocked; executing prerequisite {op_id} for {runid}/{config}")
                    prereq_result = run_prerequisite_operation(
                        session,
                        transcript,
                        bearer_token=api_token,
                        runid=runid,
                        config=config,
                        operation_id=str(op_id),
                        operation_docs=operation_docs,
                    )
                    executed_any = True
                    if prereq_result and prereq_result.terminal_status != "finished":
                        raise RuntimeError(
                            f"Prerequisite operation {op_id} failed for {runid}/{config}: {prereq_result.terminal_status}"
                        )

            readiness = api_request(
                session,
                transcript,
                method="GET",
                path=f"/rq-engine/api/runs/{quote(runid, safe='')}/{quote(config, safe='')}/readiness",
                bearer_token=api_token,
                allow_statuses=(200,),
            ).json()

            ineligible2 = readiness.get("ineligible_operations") or []
            still_blocked = any(
                isinstance(block, dict) and str(block.get("operation_id") or "") == run_wepp_operation_id
                for block in ineligible2
            )
            if still_blocked and not executed_any:
                raise RuntimeError(
                    f"run-wepp still blocked for {runid}/{config} and no executable prerequisite could be derived"
                )

        submit_resp = api_request(
            session,
            transcript,
            method="POST",
            path=f"/rq-engine/api/runs/{quote(runid, safe='')}/{quote(config, safe='')}/run-wepp",
            bearer_token=api_token,
            json_body={"wepp_bin": WEPP_BIN},
            allow_statuses=(200, 202),
        )
        submit_payload = submit_resp.json()
        submit_job_id = str(submit_payload.get("job_id") or "").strip()
        if not submit_job_id:
            raise RuntimeError(f"run-wepp submit missing job_id for {runid}/{config}: {submit_payload}")

        run_details[key]["binary_evidence_a"] = "POST /run-wepp accepted payload with wepp_bin=wepp_260501"

        job_result = poll_job(
            session,
            transcript,
            bearer_token=api_token,
            job_id=submit_job_id,
        )
        run_details[key]["job_failure_payload"] = job_result.failure_payload

        run_root = resolve_run_root(runid)
        interchange_dir = run_root / "wepp" / "output" / "interchange"
        if not interchange_dir.exists():
            raise RuntimeError(f"Interchange directory missing for {runid}/{config}: {interchange_dir}")

        binary_ev = collect_binary_evidence(run_root)
        binary_evidence_b = str(binary_ev.get("first_match") or "")
        run_details[key]["binary_evidence_b"] = binary_evidence_b or "NO_MATCH"

        binary_verification = "PASS"
        if not binary_ev["has_match"]:
            binary_verification = "FAIL"

        run_matrix_rows.append(
            {
                "runid": runid,
                "config": config,
                "submit_job_id": submit_job_id,
                "terminal_status": job_result.terminal_status,
                "runtime_seconds": f"{(job_result.runtime_seconds or 0.0):.3f}",
                "binary_verification": binary_verification,
                "interchange_dir": str(interchange_dir),
            }
        )

        # Full hillslope MOFE audits.
        wepp_ids = get_wepp_ids(interchange_dir)
        print(f"[INFO] {runid}/{config} -> auditing {len(wepp_ids)} hillslopes with {AUDIT_WORKERS_PER_RUN} workers")
        per_run_output_root = ARTIFACTS_DIR / f"{runid}_{config}"
        per_run_output_root.mkdir(parents=True, exist_ok=True)

        completed = 0
        per_run_records: list[dict[str, Any]] = []
        with ThreadPoolExecutor(max_workers=AUDIT_WORKERS_PER_RUN) as executor:
            future_map = {
                executor.submit(run_single_hillslope_audit, interchange_dir, per_run_output_root, wepp_id): wepp_id
                for wepp_id in wepp_ids
            }
            for future in as_completed(future_map):
                wepp_id = future_map[future]
                try:
                    result = future.result()
                except Exception as exc:
                    msg = f"hillslope audit failure run={runid}/{config} wepp_id={wepp_id}: {exc}"
                    run_details[key]["audit_errors"].append(msg)
                    print(f"[ERROR] {msg}")
                    continue
                completed += 1
                if completed % 25 == 0 or completed == len(wepp_ids):
                    print(f"[INFO] {runid}/{config} hillslope audits completed {completed}/{len(wepp_ids)}")
                per_run_records.append(result)

        for rec in sorted(per_run_records, key=lambda row: int(row["wepp_id"])):
            hillslope_rows.append(
                {
                    "runid": runid,
                    "config": config,
                    "wepp_id": rec["wepp_id"],
                    "topaz_id": rec["topaz_id"] if rec["topaz_id"] is not None else "",
                    "requires_scientific_review": str(rec["requires_scientific_review"]),
                    "requires_scientific_review_days": rec["requires_scientific_review_days"],
                    "max_abs_closure_mm": f"{rec['max_abs_closure_mm']:.6f}",
                    "max_abs_ofe_closure_mm": f"{rec['max_abs_ofe_closure_mm']:.6f}",
                    "max_abs_chain_surface_m3": f"{rec['max_abs_chain_surface_m3']:.6f}",
                    "max_abs_chain_subsurface_m3": f"{rec['max_abs_chain_subsurface_m3']:.6f}",
                    "summary_json_path": rec["summary_json_path"],
                    "top_days_csv_path": rec["top_days_csv_path"],
                }
            )

        if per_run_records:
            worst = max(per_run_records, key=lambda row: float(row["max_abs_closure_mm"]))
            run_details[key]["worst_top_day"] = extract_worst_top_day(worst["top_days_csv_path"])

        # Touch pipeline/readiness payloads so transcript includes key run-level state responses.
        _ = pipeline, readiness

    # Write required CSV outputs.
    run_execution_matrix_path = ARTIFACTS_DIR / "run_execution_matrix.csv"
    write_csv(
        run_execution_matrix_path,
        run_matrix_rows,
        [
            "runid",
            "config",
            "submit_job_id",
            "terminal_status",
            "runtime_seconds",
            "binary_verification",
            "interchange_dir",
        ],
    )

    hillslope_rollup_path = ARTIFACTS_DIR / "hillslope_audit_rollup.csv"
    write_csv(
        hillslope_rollup_path,
        hillslope_rows,
        [
            "runid",
            "config",
            "wepp_id",
            "topaz_id",
            "requires_scientific_review",
            "requires_scientific_review_days",
            "max_abs_closure_mm",
            "max_abs_ofe_closure_mm",
            "max_abs_chain_surface_m3",
            "max_abs_chain_subsurface_m3",
            "summary_json_path",
            "top_days_csv_path",
        ],
    )

    all_reruns_success = all(row["terminal_status"] == "finished" for row in run_matrix_rows)
    all_binary_pass = all(row["binary_verification"] == "PASS" for row in run_matrix_rows)

    expected_hillslopes = 0
    for run in RUNS:
        run_root = resolve_run_root(run["runid"])
        expected_hillslopes += len(get_wepp_ids(run_root / "wepp" / "output" / "interchange"))
    all_hillslope_audits_completed = len(hillslope_rows) == expected_hillslopes

    any_audit_errors = any(run_details[(r["runid"], r["config"])]["audit_errors"] for r in RUNS)

    severe_unexpected_defect = (not all_reruns_success) or (not all_binary_pass) or any_audit_errors

    final_verdict = "PASS" if (all_reruns_success and all_binary_pass and not severe_unexpected_defect) else "FAIL"
    verdict_reasons: list[str] = []
    if not all_reruns_success:
        verdict_reasons.append("At least one rerun did not reach terminal finished status.")
    if not all_binary_pass:
        verdict_reasons.append("At least one run failed binary verification.")
    if not all_hillslope_audits_completed:
        verdict_reasons.append(
            f"Hillslope audit coverage incomplete: expected {expected_hillslopes}, got {len(hillslope_rows)}."
        )
    if any_audit_errors:
        verdict_reasons.append("One or more hillslope MOFE audits failed.")

    defect_summary_path = ARTIFACTS_DIR / "defect_summary.md"
    defect_summary_path.write_text(
        render_defect_summary_markdown(
            run_rows=run_matrix_rows,
            run_details=run_details,
            audit_rows=hillslope_rows,
            final_verdict=final_verdict,
            verdict_reasons=verdict_reasons,
        ),
        encoding="utf-8",
    )

    api_transcript_path = ARTIFACTS_DIR / "api_transcript.md"
    api_transcript_path.write_text(
        render_api_transcript_markdown(transcript, auth_mode),
        encoding="utf-8",
    )

    summary_payload = {
        "generated_utc": utc_now(),
        "base_host": BASE_HOST,
        "rq_base": RQ_BASE,
        "auth_mode": auth_mode,
        "all_reruns_success": all_reruns_success,
        "all_binary_pass": all_binary_pass,
        "all_hillslope_audits_completed": all_hillslope_audits_completed,
        "expected_hillslopes": expected_hillslopes,
        "audited_hillslopes": len(hillslope_rows),
        "final_verdict": final_verdict,
        "verdict_reasons": verdict_reasons,
    }
    (ARTIFACTS_DIR / "validation_summary.json").write_text(json.dumps(summary_payload, indent=2), encoding="utf-8")

    print(f"[INFO] Wrote: {run_execution_matrix_path}")
    print(f"[INFO] Wrote: {hillslope_rollup_path}")
    print(f"[INFO] Wrote: {defect_summary_path}")
    print(f"[INFO] Wrote: {api_transcript_path}")
    print(f"[INFO] Final verdict: {final_verdict}")
    if verdict_reasons:
        for reason in verdict_reasons:
            print(f"[INFO] - {reason}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
