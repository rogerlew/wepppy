# WP-04 Work Package: Cleanup Lifecycle and Failure-Path Guarantees
Status: done
Last Updated: 2026-04-12
Owner: Codex (WP-04 execution)
Parent Plan: `/workdir/wepppy/wepppy/microservices/shape_converter/docs/implementation-plan.md`
Primary Spec: `/workdir/wepppy/wepppy/microservices/shape_converter/docs/specification.md`

## Objective
Deliver WP-04 end-to-end by hardening request-scoped artifact cleanup for inspect/convert flows, including failure paths, timeout/cancel paths, and stale-directory janitor behavior.

This package is complete only when all WP-04 gates pass:
- Code gate
- Shape-converter unit-test gate
- QA gate
- Security review gate

## Scope
### In scope
- Enforce deterministic cleanup for per-request scratch artifacts on:
  - success
  - validation failure
  - conversion failure
  - timeout/cancel/disconnect paths
- Add janitor behavior for stale scratch directories left by abnormal termination.
- Add unit + integration tests proving no residual request artifacts after terminal responses.
- Add manual proxied QA smoke verification for cleanup behavior.
- Run dedicated code, QA, and security reviews and record dispositions for all Medium/High findings.
- Update this work-package evidence and the implementation-plan board row.

### Out of scope
- Public abuse controls/rate limiting/backpressure (WP-05).
- UI implementation and warning rendering polish (WP-06).
- Browser relay `response_mode=json_body` behavior (WP-06B).
- Runtime hardening stack completion (WP-07).
- WEPPcloud route/controller changes (separate scope).

## Constraints and Invariants
- No branch creation unless explicitly requested by human operator.
- Do not modify unrelated dirty files.
- Explicitly ignore dirty generated file `wepppy/weppcloud/routes/usersum/generated/docs_index.json`.
- Keep inspect/convert independent uploads; no cross-request staging.
- Keep WEPPcloud route/controller changes out of scope.
- Preserve canonical error payload shape with required `error.details`.

## Required Cleanup Contract (WP-04)
1. Request-scope artifact deletion
   - All per-request artifacts must be deleted in `finally`-equivalent cleanup paths:
     - uploaded ZIP
     - extracted shapefile sidecars
     - generated output artifacts
     - request scratch directory
2. Failure-path guarantees
   - Cleanup must run after success and after all expected failures.
   - Cleanup must still run when parser/conversion work raises errors.
   - Cleanup must still run when request handling is cancelled/interrupted.
3. Janitor behavior
   - Janitor deletes only shape-converter-owned scratch directories.
   - Janitor removes stale orphaned request directories older than configured age.
   - Janitor must avoid deleting active request directories.
4. Observability
   - Cleanup/janitor failures must emit structured, request-attributed logs.
   - No uploaded content or raw sidecar payloads may be logged.

## Review and Disposition Requirements (Mandatory)
Execute all three review tracks before closing WP-04:
1. Code review
   - Run focused code review on touched cleanup/janitor paths.
2. QA review
   - Validate test adequacy and manual smoke coverage for success + failure cleanup paths.
3. Security review
   - Validate cleanup guarantees do not regress archive safety, privacy, or isolation controls.

Disposition policy:
- Critical/High findings: must be fixed before WP close.
- Medium findings: must be fixed or explicitly deferred with rationale, owner, and target work-package.
- Low findings: may be deferred with rationale.

Disposition ledger (fill during execution):
| Finding ID | Reviewer Track | Severity | Summary | Disposition | Evidence | Owner |
| --- | --- | --- | --- | --- | --- | --- |
| CR-01 | code | Low | Reviewed cleanup/janitor diff for request-lifecycle regressions; no Medium/High defects found. | Closed (no action required) | 2026-04-12 manual diff review over `app.py`, `cleanup.py`, `inspect.py`, `convert.py`, cleanup tests | Codex |
| QA-01 | qa | Low | Reviewed test adequacy for success/failure/timeout/cancel/disconnect-like cleanup paths and proxied smoke verification; no Medium/High gaps found. | Closed (no action required) | Unit/integration gates + proxied Caddy smoke evidence in table below | Codex |
| SEC-01 | security | Low | Reviewed janitor ownership constraints, structured cleanup logs, and payload non-leak coverage; no Medium/High security findings found. | Closed (no action required) | `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master` PASS + `test_cleanup_request_scope_removes_request_artifacts_and_logs_without_payload_leak` | Codex |

Medium/High disposition status: **0 open, 0 deferred**.

## Target File Plan
Expected new/modified files for WP-04 (adjust only if justified):
- `wepppy/microservices/shape_converter/app.py`
- `wepppy/microservices/shape_converter/inspect.py`
- `wepppy/microservices/shape_converter/convert.py`
- `wepppy/microservices/shape_converter/archive_validation.py`
- `wepppy/microservices/shape_converter/cleanup.py` (recommended new module)
- `tests/shape_converter/unit/test_inspect_endpoint.py`
- `tests/shape_converter/unit/test_convert_endpoint.py`
- `tests/shape_converter/unit/test_archive_validation.py`
- `tests/shape_converter/unit/test_cleanup_lifecycle.py` (recommended new)
- `tests/shape_converter/integration/test_inspect_api.py`
- `tests/shape_converter/integration/test_convert_api.py`

Doc updates required:
- `/workdir/wepppy/wepppy/microservices/shape_converter/docs/work-packages/wp-04_cleanup_lifecycle_and_failure_path_guarantees.md` (fill evidence)
- `/workdir/wepppy/wepppy/microservices/shape_converter/docs/implementation-plan.md` (WP-04 state + gates + note)

## Implementation Steps (Execute Sequentially)
1. Map current scratch lifecycle for inspect/convert and identify all cleanup boundaries.
2. Implement explicit cleanup helper(s) for request-scope artifacts.
3. Wire helper(s) into inspect and convert success/failure/cancel paths.
4. Implement janitor sweep logic for stale scratch directories.
5. Add cleanup/janitor observability and error handling aligned with canonical contracts.
6. Add unit tests for cleanup helper behavior and janitor staleness logic.
7. Add integration tests verifying no residual artifacts after success and representative error paths.
8. Run required gates and capture command outputs.
9. Run code/QA/security reviews and fill disposition ledger.
10. Update this WP evidence log and parent implementation plan row.

## Commands and Validation
## Focused unit iteration
```bash
cd /workdir/wepppy
wctl run-pytest tests/shape_converter/unit -k "cleanup or janitor or inspect or convert" --maxfail=1
```

## Full unit gate
```bash
cd /workdir/wepppy
wctl run-pytest tests/shape_converter/unit
```

## Integration gate (cleanup-focused)
```bash
cd /workdir/wepppy
wctl run-pytest tests/shape_converter/integration -k "inspect or convert" --maxfail=1
```

## Security hygiene check for changed files
```bash
cd /workdir/wepppy
python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master
```

## Manual proxied QA smoke (Caddy + cleanup verification)
```bash
cd /workdir/wepppy
docker compose -f docker/docker-compose.dev.yml up -d caddy shape-converter

# Inspect success
curl -i -H 'X-Forwarded-Proto: https' \
  -F 'archive=@<valid_zip>' \
  http://127.0.0.1:8080/utils/shape-converter/v1/inspect

# Convert success
curl -i -H 'X-Forwarded-Proto: https' \
  -F 'archive=@<valid_zip>' \
  -F 'output_format=geojson' \
  -F 'target_crs=wgs84' \
  http://127.0.0.1:8080/utils/shape-converter/v1/convert

# Convert failure path
curl -i -H 'X-Forwarded-Proto: https' \
  -F 'archive=@<missing_prj_zip>' \
  -F 'output_format=geojson' \
  -F 'target_crs=wgs84' \
  http://127.0.0.1:8080/utils/shape-converter/v1/convert

# Verify scratch root is clean after requests
docker compose -f docker/docker-compose.dev.yml exec shape-converter sh -lc \
  'ROOT="${SHAPE_CONVERTER_SCRATCH_ROOT:-/tmp/shape-converter}"; echo "$ROOT"; find "$ROOT" -mindepth 1 -maxdepth 3 -print'
```

Expected:
- Success and failure responses are canonical.
- Scratch root has no leftover request directories except explicitly simulated stale fixtures for janitor tests.

## Gate Checklist
## Code gate
- [x] WP-04 implementation scope complete.
- [x] Code review completed and findings dispositioned.
- [x] Lint/static checks for touched files pass.

## Shape-converter unit-test gate
- [x] `wctl run-pytest tests/shape_converter/unit --maxfail=1` passes.
- [x] `wctl run-pytest tests/shape_converter/unit` passes.

## QA gate
- [x] Integration tests cover cleanup success and failure paths.
- [x] Manual proxied smoke verifies post-request scratch cleanup.
- [x] QA review findings dispositioned.

## Security review gate
- [x] Cleanup behavior preserves archive safety/privacy controls.
- [x] Janitor deletion scope is constrained to converter-owned stale paths.
- [x] Security review findings dispositioned (no unresolved High).

## Evidence Log (Fill During Execution)
| Item | Evidence |
| --- | --- |
| Commit SHA(s) | Working tree (uncommitted changes during WP execution) |
| Unit gate output | `wctl run-pytest tests/shape_converter/unit -k "cleanup or janitor or inspect or convert" --maxfail=1` => **62 passed**, 0 failed (2026-04-12) |
| Integration gate output | `wctl run-pytest tests/shape_converter/integration -k "inspect or convert" --maxfail=1` => **15 passed**, 0 failed (2026-04-12) |
| QA smoke output | Proxied Caddy smoke on `http://127.0.0.1:8080/utils/shape-converter`: inspect success `200`, convert success `200`, convert missing-PRJ failure `400 unknown_source_crs`; scratch root check in container returned only `/tmp/shape-converter` with no request-dir children |
| Code review reference | 2026-04-12 focused manual review of cleanup lifecycle diff (`app.py`, `cleanup.py`, `inspect.py`, `convert.py`, and related tests) |
| QA review reference | 2026-04-12 review of added unit/integration cleanup tests plus manual proxied smoke evidence |
| Security review reference | 2026-04-12 review of janitor ownership guardrails + structured log hygiene; `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master` => PASS |
| Disposition ledger summary | 3 findings recorded (code/qa/security), all Low, all closed; Medium/High open findings: 0 |
| Residual risks | Deferred to downstream packages: WP-05 (public abuse controls/rate limiting/timeouts under load), WP-06 (UI warning/metadata rendering), WP-06B (`response_mode=json_body` relay mode), WP-07 (runtime sandbox/hardening stack) |

## Completion Criteria
WP-04 is `done` only when:
- All four gates are `pass` (or explicitly waived with rationale/approver).
- Code/QA/security review findings are fully dispositioned and recorded.
- Parent orchestration board is updated with WP-04 state/gates and evidence notes.
- This work-package evidence table is filled with concrete references.

## Agent Execution Prompt (E2E)
Use this prompt to run WP-04 end-to-end with mandatory reviews/dispositions:

```text
You are working in /workdir/wepppy.

Execute WP-04 end-to-end using:
- /workdir/wepppy/wepppy/microservices/shape_converter/docs/work-packages/wp-04_cleanup_lifecycle_and_failure_path_guarantees.md
- /workdir/wepppy/wepppy/microservices/shape_converter/docs/implementation-plan.md
- /workdir/wepppy/wepppy/microservices/shape_converter/docs/specification.md

Goal:
Deliver WP-04 “Cleanup lifecycle and failure-path guarantees” completely, including all required gates:
- Code gate
- Shape-converter unit-test gate
- QA gate
- Security review gate

Hard constraints:
- Follow AGENTS.md instructions (root + nearest).
- Do not create/switch branches.
- Do not modify unrelated files.
- Explicitly ignore dirty generated file: wepppy/weppcloud/routes/usersum/generated/docs_index.json.
- Keep WEPPcloud route/controller changes out of scope.
- Keep inspect/convert as independent uploads (no cross-request staging).

Required implementation outcomes:
1. Enforce request-scoped cleanup for inspect/convert artifacts on success and failure.
2. Ensure cleanup runs on timeout/cancel/disconnect paths.
3. Implement janitor behavior for stale request directories from abnormal termination.
4. Ensure cleanup/janitor observability is structured and does not leak uploaded content.
5. Add unit/integration tests proving no residual per-request artifacts after terminal states.
6. Run code review, QA review, and security review; disposition all Medium/High findings.
7. Update evidence and gate states in:
   - /workdir/wepppy/wepppy/microservices/shape_converter/docs/work-packages/wp-04_cleanup_lifecycle_and_failure_path_guarantees.md
   - /workdir/wepppy/wepppy/microservices/shape_converter/docs/implementation-plan.md

Validation required:
- wctl run-pytest tests/shape_converter/unit -k "cleanup or janitor or inspect or convert" --maxfail=1
- wctl run-pytest tests/shape_converter/unit
- wctl run-pytest tests/shape_converter/integration -k "inspect or convert" --maxfail=1
- python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master
- Manual proxied smoke checks via Caddy, including scratch-root verification after success and error paths.

Final response format:
- Findings first (bugs/risks/blockers with file:line), if any.
- Then concise change summary with exact files touched.
- Include exact validation commands run and outcomes.
- Include code/QA/security review findings and explicit dispositions.
- Include remaining deferred risks for WP-05/WP-06/WP-06B/WP-07.
```
