# WP-07 Work Package: Runtime Hardening and Sandbox Enforcement
Status: done
Last Updated: 2026-04-12
Owner: Codex (WP-07 execution)
Parent Plan: `/workdir/wepppy/wepppy/microservices/shape_converter/docs/implementation-plan.md`
Primary Spec: `/workdir/wepppy/wepppy/microservices/shape_converter/docs/specification.md`

## Objective
Deliver WP-07 end-to-end by enforcing runtime hardening controls for shape-converter and validating sandbox assumptions at readiness/runtime boundaries.

This package is complete only when all WP-07 gates pass:
- Code gate
- Shape-converter unit-test gate
- QA gate
- Security review gate

## Scope
### In scope
- Apply container/runtime hardening for shape-converter:
  - non-root runtime identity
  - read-only root filesystem
  - `no-new-privileges`
  - capability drop (`cap_drop: [ALL]`)
  - constrained `tmpfs` writable paths and quotas
  - pids/memory/cpu limits
- Enforce and verify parser sandbox assumptions:
  - readiness must fail when required sandbox mode is not active (per policy contract)
  - document sandbox mode signaling/config contract
- Verify and evidence deny-all egress posture for parser/conversion paths.
- Add tests/checks for hardening readiness behavior and config drift detection.
- Add proxied/container smoke checks validating hardened runtime state.
- Run dedicated code, QA, and security reviews and disposition all Medium/High findings.
- Update this work-package evidence and the implementation-plan board row.

### Out of scope
- Public abuse-control logic changes (WP-05 already delivered).
- UI/relay feature changes (WP-06/WP-06B).
- WEPPcloud route/controller changes (separate scope).

## Constraints and Invariants
- No branch creation unless explicitly requested by human operator.
- Do not modify unrelated dirty files.
- Explicitly ignore dirty generated file `wepppy/weppcloud/routes/usersum/generated/docs_index.json`.
- Keep inspect/convert independent uploads; no cross-request staging.
- Keep WEPPcloud route/controller changes out of scope.
- Preserve canonical API error contract (`error.code`, `error.message`, `error.details`).

## Required Hardening Contract (WP-07)
1. Container baseline
   - `read_only: true`
   - non-root `user`
   - `security_opt` includes `no-new-privileges:true`
   - `cap_drop: [ALL]`
   - `pids_limit` and memory/cpu limits set
   - writable mounts restricted to explicit `tmpfs` paths only
2. Sandbox readiness
   - readiness endpoint must validate required sandbox mode and return non-ready when absent.
   - sandbox requirement/config must be explicit and testable.
3. Egress enforcement
   - parser/conversion execution path operates under deny-all egress assumptions.
   - runtime evidence confirms no broad outbound network access for converter container.
4. Regression safety
   - hardening changes must not break inspect/convert functional contracts.

## Review and Disposition Requirements (Mandatory)
Execute all three review tracks before closing WP-07:
1. Code review
   - Review compose/runtime config changes and readiness enforcement logic.
2. QA review
   - Review hardening verification coverage and runtime smoke procedures.
3. Security review
   - Review containment posture, privilege boundaries, and rollback safety.

Disposition policy:
- Critical/High findings: must be fixed before WP close.
- Medium findings: must be fixed or explicitly deferred with rationale, owner, and target work-package.
- Low findings: may be deferred with rationale.

Disposition ledger (fill during execution):
| Finding ID | Reviewer Track | Severity | Summary | Disposition | Evidence | Owner |
| --- | --- | --- | --- | --- | --- | --- |
| CR-01 | code | Medium | `shape-converter` inherited permissive dev runtime posture (writable bind mounts + direct host port publish + no explicit hardening controls). | Closed (fixed in WP-07) | `docker/docker-compose.dev.yml` now enforces rootless user, `read_only`, `cap_drop=ALL`, `no-new-privileges`, bounded `tmpfs`, pids/mem/cpu limits, and no direct `ports` publish. | Codex |
| QA-01 | qa | Low | Reviewed readiness + hardening coverage and regression checks for inspect/convert under enforced sandbox signaling. | Closed (no additional action required) | `tests/shape_converter/unit/test_health_routes.py`, `tests/shape_converter/unit/test_runtime_hardening.py`, `tests/shape_converter/integration/test_runtime_hardening_api.py`; focused/full unit + integration gates pass. | Codex |
| SEC-01 | security | Medium | Reviewed containment posture: egress and east-west isolation previously depended on shared default network assumptions. | Closed (fixed in WP-07) | `docker/docker-compose.dev.yml` adds internal `shape-converter-sandbox` network; `docker inspect` shows shape-converter attached only to sandbox; in-container socket probe to `1.1.1.1:53` returns `Network is unreachable`. | Codex |

Medium/High disposition status: **0 open, 0 deferred**.

## Target File Plan
Expected new/modified files for WP-07 (adjust only if justified):
- `docker/docker-compose.dev.yml`
- `docker/caddy/Caddyfile` (only if proxy/hardening coupling needed)
- `wepppy/microservices/shape_converter/app.py`
- `wepppy/microservices/shape_converter/cleanup.py` (if sandbox/readiness plumbing needed)
- `tests/shape_converter/unit/test_health_routes.py`
- `tests/shape_converter/unit/test_app_bootstrap.py`
- `tests/shape_converter/unit/test_runtime_hardening.py` (recommended new)
- `tests/shape_converter/integration/test_runtime_hardening_api.py` (recommended new)

Doc updates required:
- `/workdir/wepppy/wepppy/microservices/shape_converter/docs/work-packages/wp-07_runtime_hardening_and_sandbox_enforcement.md` (fill evidence)
- `/workdir/wepppy/wepppy/microservices/shape_converter/docs/implementation-plan.md` (WP-07 state + gates + note)
- `/workdir/wepppy/wepppy/microservices/shape_converter/docs/specification.md` (if hardening contract wording changes)

## Implementation Steps (Execute Sequentially)
1. Define concrete hardening target state and environment contract for shape-converter service.
2. Apply compose/runtime hardening settings for the shape-converter container.
3. Implement readiness checks that enforce required sandbox mode signaling.
4. Add hardening verification tests (unit + integration) for readiness and configuration.
5. Run functional regression checks for inspect/convert behavior.
6. Execute container/proxy smoke checks to evidence runtime hardening state.
7. Run required gates and capture outputs.
8. Run code/QA/security reviews and fill disposition ledger.
9. Update this WP evidence log and parent implementation plan row.

## Commands and Validation
## Focused unit iteration
```bash
cd /workdir/wepppy
wctl run-pytest tests/shape_converter/unit -k "health or readiness or hardening or sandbox" --maxfail=1
```

## Full unit gate
```bash
cd /workdir/wepppy
wctl run-pytest tests/shape_converter/unit
```

## Integration gate (hardening-focused)
```bash
cd /workdir/wepppy
wctl run-pytest tests/shape_converter/integration -k "hardening or readiness or convert or inspect" --maxfail=1
```

## Security hygiene check for changed files
```bash
cd /workdir/wepppy
python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master
```

## Runtime hardening smoke checks
```bash
cd /workdir/wepppy
docker compose -f docker/docker-compose.dev.yml up -d shape-converter caddy

# Verify container host-config posture
docker inspect wepppy-shape-converter --format 'read_only={{.HostConfig.ReadonlyRootfs}} pids_limit={{.HostConfig.PidsLimit}} cap_drop={{json .HostConfig.CapDrop}} security_opt={{json .HostConfig.SecurityOpt}}'

# Verify service readiness reports sandbox/hardening state
curl -i http://127.0.0.1:8080/utils/shape-converter/health/ready

# Functional regression sanity
curl -i -H 'X-Forwarded-Proto: https' \
  -F 'archive=@<valid_zip>' \
  http://127.0.0.1:8080/utils/shape-converter/v1/inspect
```

Expected:
- container hardening settings are present and match target state.
- readiness reflects sandbox/hardening requirements.
- inspect/convert still function under hardened runtime.

## Gate Checklist
## Code gate
- [x] WP-07 implementation scope complete.
- [x] Code review completed and findings dispositioned.
- [x] Lint/static checks for touched files pass.

## Shape-converter unit-test gate
- [x] `wctl run-pytest tests/shape_converter/unit -k "health or readiness or hardening or sandbox" --maxfail=1` passes.
- [x] `wctl run-pytest tests/shape_converter/unit` passes.

## QA gate
- [x] Integration tests cover readiness/hardening behavior and functional regression.
- [x] Manual runtime hardening smoke checks completed.
- [x] QA review findings dispositioned.

## Security review gate
- [x] Runtime privilege/containment controls validated (`read_only`, caps drop, no-new-privileges, sandbox signaling).
- [x] No unresolved High findings in runtime hardening surface.
- [x] Security review findings dispositioned (Mediums fixed or explicitly deferred with rationale).

## Evidence Log (Fill During Execution)
| Item | Evidence |
| --- | --- |
| Commit SHA(s) | Working tree (uncommitted changes during WP execution) |
| Unit gate output | `wctl run-pytest tests/shape_converter/unit -k "health or readiness or hardening or sandbox" --maxfail=1` => **8 passed**, 0 failed (2026-04-12). `wctl run-pytest tests/shape_converter/unit` => **88 passed**, 0 failed (2026-04-12). |
| Integration gate output | `wctl run-pytest tests/shape_converter/integration -k "hardening or readiness or convert or inspect" --maxfail=1` => **27 passed**, 0 failed (2026-04-12). |
| Runtime smoke output | `docker compose ... up -d shape-converter caddy` recreated hardened containers; `docker inspect wepppy-shape-converter` shows `read_only=true`, `user=10001:10001`, `pids_limit=256`, `cap_drop=[\"ALL\"]`, `security_opt=[\"no-new-privileges:true\"]`, `mem_limit=1073741824`, `nano_cpus=1500000000`, hardened `tmpfs` mounts, and only `wepppy-shape-converter-sandbox` attachment. Proxied ready check `curl -i .../health/ready` => `200` with `sandbox_mode=container`/`required_sandbox_mode=container`. Proxied inspect sanity `curl -i -F archive=@/tmp/shape_converter_smoke_valid.zip .../v1/inspect` => `200`. Proxied convert sanity `curl -i -F archive=... -F output_format=geojson -F target_crs=wgs84 .../v1/convert` => `200`. In-container egress probe (`socket.create_connection((\"1.1.1.1\", 53))`) => `egress_probe=blocked error=[Errno 101] Network is unreachable`. |
| Code review reference | 2026-04-12 focused manual diff review of `app.py`, `docker-compose.dev.yml`, readiness/hardening tests, and contract documentation updates. |
| QA review reference | 2026-04-12 review of focused/full unit gates, integration hardening gate, and proxied runtime smoke matrix (ready + inspect + convert under hardened compose). |
| Security review reference | 2026-04-12 review of runtime containment controls (`read_only`, rootless user, `no-new-privileges`, `cap_drop=ALL`, internal network isolation) plus `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master` => PASS. |
| Disposition ledger summary | 3 findings recorded (code/qa/security); 2 Medium + 1 Low, all closed in WP-07; Medium/High open findings: 0. |
| Residual risks | Deferred to WP-08/WP-09: full CI automation for runtime hardening drift checks and release-cut dependency/CVE watchlist closeout (including parser stack cadence + final release artifact attestation). |

## Completion Criteria
WP-07 is `done` only when:
- All four gates are `pass` (or explicitly waived with rationale/approver).
- Code/QA/security review findings are fully dispositioned and recorded.
- Parent orchestration board is updated with WP-07 state/gates and evidence notes.
- This work-package evidence table is filled with concrete references.

## Agent Execution Prompt (E2E)
Use this prompt to run WP-07 end-to-end with mandatory reviews/dispositions:

```text
You are working in /workdir/wepppy.

Execute WP-07 end-to-end using:
- /workdir/wepppy/wepppy/microservices/shape_converter/docs/work-packages/wp-07_runtime_hardening_and_sandbox_enforcement.md
- /workdir/wepppy/wepppy/microservices/shape_converter/docs/implementation-plan.md
- /workdir/wepppy/wepppy/microservices/shape_converter/docs/specification.md

Goal:
Deliver WP-07 “Runtime hardening and sandbox enforcement” completely, including all required gates:
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
1. Enforce runtime hardening controls for shape-converter container (`read_only`, non-root, no-new-privileges, caps drop, resource limits, constrained writable paths).
2. Implement readiness enforcement for required sandbox mode signaling.
3. Verify deny-all egress posture assumptions for parser/conversion runtime.
4. Add unit/integration tests for readiness/hardening behavior.
5. Ensure inspect/convert regressions are not introduced by hardening changes.
6. Run code review, QA review, and security review; disposition all Medium/High findings.
7. Update evidence and gate states in:
   - /workdir/wepppy/wepppy/microservices/shape_converter/docs/work-packages/wp-07_runtime_hardening_and_sandbox_enforcement.md
   - /workdir/wepppy/wepppy/microservices/shape_converter/docs/implementation-plan.md
   - /workdir/wepppy/wepppy/microservices/shape_converter/docs/specification.md (if contract text changes)

Validation required:
- wctl run-pytest tests/shape_converter/unit -k "health or readiness or hardening or sandbox" --maxfail=1
- wctl run-pytest tests/shape_converter/unit
- wctl run-pytest tests/shape_converter/integration -k "hardening or readiness or convert or inspect" --maxfail=1
- python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master
- Manual runtime hardening smoke checks (docker inspect posture + readiness + proxied inspect sanity).

Final response format:
- Findings first (bugs/risks/blockers with file:line), if any.
- Then concise change summary with exact files touched.
- Include exact validation commands run and outcomes.
- Include code/QA/security review findings and explicit dispositions.
- Include remaining deferred risks for WP-08/WP-09.
```
