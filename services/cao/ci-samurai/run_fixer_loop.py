#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import shlex
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
import fnmatch

import requests


RESULT_JSON_RE = re.compile(
    r"```RESULT_JSON\s*\n([\s\S]*?)\n```|RESULT_JSON[\s\S]*?```(?:json)?\n([\s\S]*?)\n```",
    re.IGNORECASE,
)
PATCH_RE = re.compile(r"```patch\n([\s\S]*?)\n```", re.IGNORECASE)


@dataclass
class Failure:
    kind: str
    test: str
    error: str


def read_failures(path: Path) -> List[Failure]:
    out: List[Failure] = []
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            out.append(Failure(kind=obj.get("kind", "failed"), test=obj["test"], error=obj.get("error", "")))
        except Exception:
            continue
    return out


def read_snippet(repo_root: Path, test_nodeid: str, max_lines: int = 120) -> str:
    # Use the test file as a cheap context snippet
    test_path = test_nodeid.split("::", 1)[0]
    p = repo_root / test_path
    if not p.exists():
        return ""
    lines = p.read_text(encoding="utf-8", errors="ignore").splitlines()
    head = lines[:max_lines]
    return "\n".join(head)


def create_session(cao_base: str, agent_profile: str, session_name: str) -> Dict[str, Any]:
    url = f"{cao_base}/sessions"
    params = {"provider": "codex", "agent_profile": agent_profile, "session_name": session_name}
    r = requests.post(url, params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def send_inbox_message(cao_base: str, terminal_id: str, sender: str, message: str) -> None:
    """Send message using JSON body first; fallback to query params if server is older.

    Older CAO builds only accept query params (sender_id, message) and will
    emit a 422 complaining about missing query fields if JSON is used. We
    fallback to query only when the payload is small to avoid URL length issues.
    """
    url = f"{cao_base}/terminals/{terminal_id}/inbox/messages"
    r = requests.post(url, json={"sender_id": sender, "message": message}, timeout=60)
    if r.status_code == 422 and len(message) < 1500:
        # Fallback for older servers that only accept query params
        r = requests.post(url, params={"sender_id": sender, "message": message}, timeout=60)
    try:
        r.raise_for_status()
    except requests.HTTPError as e:
        hint = ""
        if r.status_code == 422:
            hint = (
                "\nHint: CAO server may require an update to accept JSON body. "
                "If message is large, query fallback may exceed URL limits."
            )
        raise requests.HTTPError(f"{e}\nResponse: {r.text}{hint}") from e


def get_output_tail(cao_base: str, terminal_id: str) -> str:
    url = f"{cao_base}/terminals/{terminal_id}/output"
    # API expects OutputMode enum values: full | last
    params = {"mode": "last"}
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    obj = r.json()
    return obj.get("output", "")


def get_output_full(cao_base: str, terminal_id: str) -> str:
    url = f"{cao_base}/terminals/{terminal_id}/output"
    params = {"mode": "full"}
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    obj = r.json()
    return obj.get("output", "")


def _extract_text_from_codex_json(output: str) -> str:
    """Best-effort extraction of agent-visible text from Codex JSON event stream.

    Aggregates 'item.completed' events' text or aggregated_output so we can
    search for RESULT_JSON/PATCH fences even when the raw terminal contains
    JSONL rather than plain text.
    """
    texts: list[str] = []
    for raw in output.splitlines():
        raw = raw.strip()
        if not raw or raw[0] != '{':
            continue
        try:
            evt = json.loads(raw)
        except Exception:
            continue
        et = evt.get("type")
        if et == "item.completed":
            item = evt.get("item", {})
            t = item.get("text")
            if t:
                texts.append(str(t))
                continue
            if item.get("type") == "command_execution":
                ao = item.get("aggregated_output")
                if ao:
                    texts.append(str(ao))
                    continue
        # Wojak bootstrap compatibility: agent_output/system events
        if et in ("agent_output", "system"):
            t = evt.get("content")
            if t:
                texts.append(str(t))
    return "\n".join(texts)


def parse_result_and_patch(output: str) -> tuple[Optional[Dict[str, Any]], Optional[str]]:
    result_json: Optional[Dict[str, Any]] = None
    patch_text: Optional[str] = None
    m = RESULT_JSON_RE.search(output)
    if m:
        json_blob = m.group(1) or m.group(2)
        if json_blob:
            try:
                result_json = json.loads(json_blob)
            except Exception:
                result_json = None
    m2 = PATCH_RE.search(output)
    if m2:
        patch_text = m2.group(1)
        # Normalize line endings
        patch_text = patch_text.replace("\r\n", "\n")

    # Fallback: attempt to parse Codex JSON event stream and search within extracted text
    if result_json is None and patch_text is None:
        extracted = _extract_text_from_codex_json(output)
        if extracted:
            m = RESULT_JSON_RE.search(extracted)
            if m:
                try:
                    result_json = json.loads(m.group(1))
                except Exception:
                    result_json = None
            m2 = PATCH_RE.search(extracted)
            if m2:
                patch_text = m2.group(1).replace("\r\n", "\n")
    return result_json, patch_text


def ssh(host: str, cmd: str) -> subprocess.CompletedProcess:
    return subprocess.run(["ssh", host, cmd], capture_output=True, text=True)


def scp_to(host: str, local_path: Path, remote_path: str) -> subprocess.CompletedProcess:
    return subprocess.run(["scp", str(local_path), f"{host}:{remote_path}"], capture_output=True, text=True)


def validate_tests(nuc2: str, repo: str, tests: List[str]) -> Dict[str, bool]:
    results: Dict[str, bool] = {}
    for t in tests:
        cmd = f"cd {shlex.quote(repo)} && wctl run-pytest -q {shlex.quote(t)}"
        res = ssh(nuc2, cmd)
        results[t] = res.returncode == 0
    return results


def apply_patch_and_open_pr(nuc2: str, repo: str, patch_text: str, branch: str, title: str, body: str) -> bool:
    # Write patch to a temp file locally, copy to nuc2, and apply in repo
    tmp = Path("/tmp/ci_patch.diff")
    tmp.write_text(patch_text, encoding="utf-8")
    remote_tmp = "/tmp/ci_patch.diff"
    scp_to(nuc2, tmp, remote_tmp)
    # Determine default base branch on remote (master/main)
    head_branch_cmd = f"cd {shlex.quote(repo)} && git remote show origin | sed -n 's/.*HEAD branch: \\([^ ]*\\)/\\1/p'"
    head = ssh(nuc2, head_branch_cmd)
    base_branch = (head.stdout.strip() or "master").splitlines()[0]
    git_cmds = [
        f"cd {shlex.quote(repo)} && git fetch origin && git checkout -B {shlex.quote(branch)} origin/{shlex.quote(base_branch)}",
        f"cd {shlex.quote(repo)} && git apply --index {shlex.quote(remote_tmp)} || (git apply {shlex.quote(remote_tmp)} && git add -A)",
        f"cd {shlex.quote(repo)} && git commit -m {shlex.quote(title)} || true",
        f"cd {shlex.quote(repo)} && git push -u origin {shlex.quote(branch)}",
        f"cd {shlex.quote(repo)} && gh pr create -B {shlex.quote(base_branch)} -H {shlex.quote(branch)} -t {shlex.quote(title)} -b {shlex.quote(body)} -l ci-samurai -l auto-fix",
    ]
    for cmd in git_cmds:
        res = ssh(nuc2, cmd)
        if res.returncode != 0:
            # surface error for debugging
            print(res.stdout)
            print(res.stderr)
            return False
    return True


def _split_globs(spec: str) -> List[str]:
    parts = [g.strip() for g in (spec or "").split(",")]
    return [p for p in parts if p]


def _extract_patch_paths(patch_text: str) -> List[str]:
    paths: List[str] = []
    for line in patch_text.splitlines():
        if line.startswith("diff --git a/"):
            try:
                _, a_path, b_path = line.split(" ", 2)
            except ValueError:
                continue
            # a_path like a/foo.py, b_path like b/foo.py
            if b_path.startswith("b/"):
                paths.append(b_path[2:])
            elif a_path.startswith("a/"):
                paths.append(a_path[2:])
    return paths


def _paths_allowed(paths: List[str], allowlist: str, denylist: str) -> tuple[bool, str]:
    allows = _split_globs(allowlist)
    denys = _split_globs(denylist)
    denied: List[str] = []
    disallowed: List[str] = []

    for p in paths:
        # denylist has priority
        if any(fnmatch.fnmatch(p, d) for d in denys):
            denied.append(p)
            continue
        if allows and not any(fnmatch.fnmatch(p, a) for a in allows):
            disallowed.append(p)

    if denied:
        return False, f"Denied paths: {', '.join(sorted(set(denied)))}"
    if disallowed:
        return False, f"Outside allowlist: {', '.join(sorted(set(disallowed)))}"
    return True, ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--failures", required=True)
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--nuc2", required=True)
    ap.add_argument("--repo", required=True, help="Remote repo path on nuc2 (e.g., /workdir/wepppy)")
    ap.add_argument("--cao-base", required=True)
    ap.add_argument("--allowlist", default="tests/**, wepppy/**/*.py")
    ap.add_argument("--denylist", default="wepppy/wepp/**, wepppy/nodb/base.py, docker/**, .github/workflows/**, deps/linux/**")
    ap.add_argument("--max-context", type=int, default=10)
    ap.add_argument("--max-failures", type=int, default=0, help="Max failures to process (0 = no cap)")
    ap.add_argument("--poll-seconds", type=int, default=120)
    args = ap.parse_args()

    failures = read_failures(Path(args.failures))

    if not failures:
        print("No failures to process")
        return 0
    if args.max_failures and args.max_failures > 0:
        failures = failures[: args.max_failures]

    repo_root = Path(args.repo_root).resolve()

    # Build remaining queue (in-memory for pilot)
    remaining: List[Failure] = failures.copy()
    handled: List[str] = []

    processed = 0
    while remaining:
        primary = remaining.pop(0)
        context_errors = remaining[: args.max_context]

        # Prepare message
        snippet = read_snippet(repo_root, primary.test)
        remaining_lines = [f"- {f.test} :: {f.error}" for f in context_errors]
        validation_cmd = f"ssh {args.nuc2} \"cd {args.repo} && wctl run-pytest -q {primary.test}\""
        message_parts = [
            f"PRIMARY_TEST: {primary.test}",
            f"STACK: {primary.error}",
            "SNIPPET:\n" + snippet,
            "REMAINING_ERRORS:\n" + ("\n".join(remaining_lines) if remaining_lines else "<none>"),
            f"ALLOWLIST: {args.allowlist}",
            f"DENYLIST: {args.denylist}",
            f"VALIDATION_CMD: {validation_cmd}",
            "PR_TEMPLATE:\n## Problem\n...\n\n## Root Cause\n...\n\n## Solution\n...\n\n## Testing\n...\n\n## Edge Cases\n...\n\n**Agent Confidence:** ...",
            "ISSUE_TEMPLATE:\n## Symptoms\n...\n\n## Hypotheses\n...\n\n## Why I'm Stuck\n...\n\n## Next Steps\n...\n\n## Reproduction\n...",
        ]
        message = "\n\n".join(message_parts)

        session_name = f"ci-fix-{int(time.time())}"
        print(f"Creating CAO session at {args.cao_base} (profile=ci_samurai_fixer, name={session_name})")
        term = create_session(args.cao_base, "ci_samurai_fixer", session_name)
        terminal_id = term.get("id")
        session_full_name = term.get("session_name", session_name)
        if not terminal_id:
            print("Failed to create CAO session: missing terminal id")
            break
        print(f"Created terminal: id={terminal_id} name={session_full_name}")
        send_inbox_message(args.cao_base, terminal_id, "gha", message)

        # Poll for output
        deadline = time.time() + args.poll_seconds
        result_json: Optional[Dict[str, Any]] = None
        patch_text: Optional[str] = None
        print(f"Polling for agent RESULT_JSON for up to {args.poll_seconds}s...")
        while time.time() < deadline and result_json is None:
            # Use full output to avoid missing fences split across messages
            out = get_output_full(args.cao_base, terminal_id)
            rj, pt = parse_result_and_patch(out)
            if rj:
                result_json, patch_text = rj, pt
                break
            time.sleep(4)

        if not result_json:
            print(f"No RESULT_JSON received for {primary.test}; capturing transcript and skipping")
            try:
                agent_logs_dir = Path("agent_logs")
                agent_logs_dir.mkdir(exist_ok=True)
                slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", primary.test)
                base = f"{session_full_name}-{terminal_id}-{slug}-noresult"
                full_out = get_output_full(args.cao_base, terminal_id)
                (agent_logs_dir / f"{base}.log").write_text(full_out, encoding="utf-8")
            except Exception as e:
                print(f"Warn: failed to persist agent logs (noresult): {e}")
            continue

        # Validate claims
        handled_tests = result_json.get("handled_tests") or [primary.test]
        print(f"Validating handled tests on {args.nuc2}: {handled_tests}")
        val_results = validate_tests(args.nuc2, args.repo, handled_tests)
        all_green = all(val_results.values())

        if result_json.get("action") == "pr" and all_green and patch_text:
            # Enforce allowlist/denylist on proposed patch before PR
            paths = _extract_patch_paths(patch_text)
            ok_paths, why = _paths_allowed(paths, args.allowlist, args.denylist)
            pr = result_json.get("pr", {})
            branch = pr.get("branch") or f"ci/fix/{int(time.time())}"
            title = pr.get("title") or f"Fix: {primary.test}"
            body = pr.get("body") or "CI Samurai auto-fix"
            if ok_paths:
                ok = apply_patch_and_open_pr(args.nuc2, args.repo, patch_text, branch, title, body)
                if ok:
                    handled.extend(handled_tests)
            else:
                # Open issue instead, citing blocked paths
                issues = result_json.get("issues") or []
                if not issues:
                    issues = [{
                        "title": f"CI Samurai: patch blocked by policy for {primary.test}",
                        "body": f"Patch touched disallowed paths. Details: {why}\n\nPaths: {paths}"
                    }]
                for iss in issues:
                    title2 = iss.get("title", f"CI Samurai: {primary.test}")
                    body2 = iss.get("body", "")
                    cmd = f"cd {shlex.quote(args.repo)} && gh issue create -t {shlex.quote(title2)} -b {shlex.quote(body2)} -l ci-samurai"
                    ssh(args.nuc2, cmd)
                handled.extend([t for t, ok in val_results.items() if ok])
        else:
            # Open issues for each handled test that failed or for action=issue
            issues = result_json.get("issues") or []
            if not issues:
                issues = [{"title": f"CI Samurai: {primary.test}", "body": json.dumps(result_json, indent=2)}]
            for iss in issues:
                title = iss.get("title", f"CI Samurai: {primary.test}")
                body = iss.get("body", "")
                cmd = f"cd {shlex.quote(args.repo)} && gh issue create -t {shlex.quote(title)} -b {shlex.quote(body)} -l ci-samurai"
                ssh(args.nuc2, cmd)
            handled.extend([t for t, ok in val_results.items() if ok])

        # Persist agent transcript for observability
        try:
            agent_logs_dir = Path("agent_logs")
            agent_logs_dir.mkdir(exist_ok=True)
            slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", primary.test)
            base = f"{session_full_name}-{terminal_id}-{slug}"
            # Full transcript
            full_out = get_output_full(args.cao_base, terminal_id)
            (agent_logs_dir / f"{base}.log").write_text(full_out, encoding="utf-8")
            # Result JSON copy
            (agent_logs_dir / f"{base}.result.json").write_text(json.dumps(result_json, indent=2), encoding="utf-8")
            # Patch copy if present
            if patch_text:
                (agent_logs_dir / f"{base}.patch").write_text(patch_text, encoding="utf-8")
        except Exception as e:
            print(f"Warn: failed to persist agent logs: {e}")

        processed += 1
        if args.max_failures and processed >= args.max_failures:
            break

    print(f"Handled tests: {handled}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
