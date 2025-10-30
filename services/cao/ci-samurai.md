# CI Samurai (Lean)

> Goal: Provide automated regression identification with fixes or diagnoses.

- Status: Active
- Trigger: Nightly GitHub Action (self‑hosted runner)
- Scope (pilot): tests/nodb (expand to tests/wepp)

## Objective
Convert failing tests into fixes or clear bug reports using a “fresh agent per error” loop with simple CI orchestration and strict safety rules.

## Operating Model
- Fresh agent per error: one short‑lived GPT‑5‑Codex session per failure.
- Coalescing: agent may also fix clearly similar errors from the remaining list in the same session.
- CI is the arbiter: validates claims, opens PRs/issues, updates queues.

## Inputs / Outputs
- Inputs
  - Latest triage logs: `/wc1/ci-samurai/logs/<ts>/triage_nodb.txt`
  - Repository on NUCs: `/workdir/wepppy`
- Outputs
  - PRs labeled `ci-samurai` with structured reports
  - Issues labeled `ci-samurai` with analysis + reproduction
  - Logs + JSON queues under `/wc1/ci-samurai/logs/<ts>/`

## Nightly Workflow
1) Triage (nuc1)
   - Run pytest; capture logs; single rerun of first failure for flake tag
   - Package logs as artifact (done)

2) Parse
   - Convert triage log → `failures.jsonl` (fields: `test`, `file`, `error`, `signature?`)
   - Initialize `remaining.jsonl` from `failures.jsonl`; create empty `handled.jsonl`

3) Iterate (serial; add small parallel factor later)
   - Pop `primary` from `remaining.jsonl`
   - Create CAO session (profile: `ci_samurai_fixer`) and send one structured message:
     - PRIMARY_TEST, STACK/SNIPPET, up to N REMAINING_ERRORS, ALLOWLIST/DENYLIST, VALIDATION_CMD, PR/Issue templates
     - Directive: must resolve the primary; may also resolve clearly similar errors
   - Agent returns RESULT_JSON (action, confidence, primary_test, handled_tests, PR/issue metadata)
   - Validate each `handled_test` on nuc2: `wctl run-pytest -q <test>` (fallback to docker compose exec)
   - If green → open PR(s); else → open issue(s) with analysis; append to `handled.jsonl`
   - Remove validated handled tests from `remaining.jsonl`; continue until queue empty or budget reached

## Safety Rules
- Allowlist (pilot): `tests/**`, `wepppy/**/*.py`
- Denylist: `wepppy/nodb/base.py`, `docker/**`, `.github/workflows/**`, `deps/linux/**`
- One attempt per error (pilot); unresolved → issue
- Branch: `ci/fix/<date>/<test-slug>`; labels: `ci-samurai`, `auto-fix`, confidence tags

## CAO Profiles
- `ci_samurai_fixer` (worker‑only)
  - Single‑error prompt; RESULT_JSON schema; strict allowlist; targeted validation
- (Later) `ci_samurai_merge` (optional)
  - Bundle several trivial fixes; not needed for pilot

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
  "handled_tests": ["tests/...::..."],
  "similarity_basis": "same assertion/helper/signature",
  "pr": { "branch": "ci/fix/2025-10-30/test_y", "title": "Fix: ...", "body": "..." },
  "issues": [{ "title": "...", "body": "..." }]
}
```

