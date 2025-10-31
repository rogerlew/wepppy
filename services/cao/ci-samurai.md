# CI Samurai (Lean)

> Goal: Provide automated regression identification with fixes or diagnoses.

- Status: Active
- Trigger: Nightly GitHub Action (self‑hosted runner)
- Scope (pilot): tests/nodb (expand to tests/wepp)

## Objective
Convert failing tests into fixes or clear bug reports using a two-stage agent loop (infrastructure validation + fixer) with strict safety rules.

## Operating Model
- Fresh agent per error: one short‑lived GPT‑5‑Codex session per failure.
- Coalescing: agent may also fix clearly similar errors from the remaining list in the same session.
- CI is the arbiter: validates claims, opens PRs/issues, updates queues.

## Inputs / Outputs
- Inputs
  - Latest triage logs: `/wc1/ci-samurai/logs/<ts>/triage.txt`
  - Repository on NUCs: `/workdir/wepppy`
  - CAO API endpoints on each NUC (e.g., `http://nuc2.local:9889`)
- Outputs
  - PRs labeled `ci-samurai` (and `infra-check` when infra agent succeeds) with validation evidence
  - Issues labeled `ci-samurai`/`infra-check` describing failures, blocked checks, or missing dependencies
  - Logs + JSON queues under `/wc1/ci-samurai/logs/<ts>/` plus `agent_logs/` transcripts

## Nightly Workflow
1) Triage (nuc1)
   - Run pytest; capture logs; single rerun of first failure for flake tag
   - Package logs as artifact (done)

2) Parse
   - Convert triage log → `failures.jsonl` (fields: `test`, `file`, `error`, `signature?`)
   - Initialize `remaining.jsonl` from `failures.jsonl`; create empty `handled.jsonl`

3) Infra validation (nuc2)
   - Create CAO session (profile: `ci_samurai_infra`) with `REMOTE_HOST`, `REMOTE_REPO`, `SAMPLE_TEST`, allow/deny lists, and branch prefix
   - Agent executes six checks in order (SSH, repo cleanliness, tooling, `wctl run-pytest` smoke, git remote/branch, `gh auth status`)
   - On success, agent may apply minimal fixes (within allowlist) and open a PR using `gh pr create --label ci-samurai --label infra-check`
   - On failure, agent files a labeled issue (`gh issue create --label ci-samurai --label infra-check`) capturing blocked checks; fixer loop still runs but treats infrastructure as degraded

4) Fixer loop (serial; add small parallel factor later)
   - Pop `primary` from `remaining.jsonl`
   - Create CAO session (profile: `ci_samurai_fixer`) and send one structured message:
     - PRIMARY_TEST, STACK/SNIPPET, up to N REMAINING_ERRORS, ALLOWLIST/DENYLIST, VALIDATION_CMD, PR/Issue templates
     - Directive: must resolve the primary; may also resolve clearly similar errors
   - Agent must activate `/workdir/wepppy/services/cao/.venv` (or call its Python directly), run `VALIDATION_CMD` (`wctl run-pytest -q <test>`), and only push a PR when validation exits zero
   - Labels such as `ci-samurai`/`auto-fix` must exist; agent creates missing labels via `gh label create`
   - Agent runs `gh pr create` (PR flow) or `gh issue create` (issue flow) and records the resulting URLs
   - Append RESULT_JSON to `handled.jsonl` and remove validated tests from `remaining.jsonl`
   - Remove validated handled tests from `remaining.jsonl`; continue until queue empty or budget reached

## Safety Rules
- Allowlist (pilot): `tests/**`, `wepppy/**/*.py`
- Denylist: `wepppy/nodb/base.py`, `docker/**`, `.github/workflows/**`, `deps/linux/**`
- Agents must operate from the project virtualenv (`services/cao/.venv`); bare `python` is not assumed
- Required GitHub labels (`ci-samurai`, `infra-check`, confidence tags) must exist or be created before PR/issue submission
- Infra step runs once per workflow; fixer gets one attempt per failure—unresolved errors generate issues
- Branch naming: `ci/fix/<date>/<test-slug>` (fixer) and `ci/infra/<timestamp>` (infra PRs)
- Testing and tooling must go through `wctl` helpers (`wctl run-pytest`, `wctl up -d`, etc.) to ensure container parity with production; direct `pytest`/`docker compose` calls are discouraged unless explicitly noted
- Codex sessions always run with `--sandbox danger-full-access` so agents can issue `ssh`/`gh` without prompts; tighten behavior by editing `inbox_service.py` rather than via environment variables

## CAO Profiles
- `ci_samurai_infra` (per-run validation)
  - Ensures SSH connectivity, repo health, tooling availability, smoke tests, git/gh access; may apply trivial infra fixes and open PR/issue
- `ci_samurai_fixer` (worker‑only)
  - Single-error prompt; RESULT_JSON schema; strict allowlist; must validate with `wctl run-pytest` before opening a PR
- (`ci_samurai_merge` deferred) – not active in current rollout

## Telemetry
- Track PR outcomes (merged/edited/rejected) and issue counts by pattern/path
- Maintain `handled.jsonl` (claim → validation result)
- Optional Slack summary with links to PRs/issues and artifact path

## Rollout
- Phase 1: wider coalescing; optional merge bundling

## Tasks
- Parser: `services/cao/ci-samurai/parse_pytest_log.py` (triage → failures.jsonl)
- Profile: `services/cao/src/cli_agent_orchestrator/agent_store/ci_samurai_fixer.md`
- Workflow: extend nightly job to loop remaining.jsonl → CAO → validate → PR/issue → update queues
- Keep existing dry‑run + artifact packaging

## RESULT_JSON (agent → CI)
```json
{
  "action": "pr" | "issue",
  "confidence": "high" | "medium" | "low",
  "primary_test": "tests/nodb/test_x.py::test_y",
  "handled_tests": ["tests/...::...", "..."],
  "similarity_basis": "same assertion/helper/signature",
  "pr": {
    "branch": "ci/fix/2025-10-30/test_y",
    "title": "Fix: ...",
    "body": "...",
    "url": "https://github.com/owner/repo/pull/123"
  },
  "issues": [
    {
      "title": "...",
      "body": "...",
      "url": "https://github.com/owner/repo/issues/456"
    }
  ]
}
```

**Notes**
- Infra RESULT_JSON follows the same schema; when the agent cannot complete checks (e.g., DNS failure), it emits `action: "issue"` with diagnostics.
- CI trusts the recorded URLs and does not re-create PRs or issues—agents must report fatal command failures in the JSON payload so the loop can fall back gracefully.
