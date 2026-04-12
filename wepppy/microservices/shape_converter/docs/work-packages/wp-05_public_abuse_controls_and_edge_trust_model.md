# WP-05 Work Package: Public Abuse Controls and Edge Trust Model
Status: done
Last Updated: 2026-04-12
Owner: Codex (WP-05 execution)
Parent Plan: `/workdir/wepppy/wepppy/microservices/shape_converter/docs/implementation-plan.md`
Primary Spec: `/workdir/wepppy/wepppy/microservices/shape_converter/docs/specification.md`

## Objective
Deliver WP-05 end-to-end by implementing no-auth abuse controls and trusted-client identity handling for shape-converter public endpoints, including slowloris/timeout protections and edge trust model enforcement.

This package is complete only when all WP-05 gates pass:
- Code gate
- Shape-converter unit-test gate
- QA gate
- Security review gate

## Scope
### In scope
- Implement application-level abuse controls for public `inspect` and `convert` endpoints:
  - per-IP rate limiting
  - per-IP and global in-flight/concurrency limits
  - explicit fast-fail behavior (`429` and/or `503` as documented)
- Implement trusted forwarding-header model:
  - trust client IP only from configured proxy hops
  - ignore/sanitize spoofed forwarding headers from untrusted sources
  - IPv6 aggregation policy (`/64`) for limiter keys
- Implement timeout/slowloris protections in service and edge integration points.
- Enforce deny-all parser egress posture for conversion paths (and verify assumptions).
- Add unit/integration tests and proxied smoke evidence for abuse controls and header trust behavior.
- Run dedicated code, QA, and security reviews and disposition all Medium/High findings.
- Update this work-package evidence and the implementation-plan board row.

### Out of scope
- Cleanup lifecycle guarantees and janitor behavior (WP-04).
- UI implementation and metadata rendering (WP-06).
- Browser relay `response_mode=json_body` behavior (WP-06B).
- Runtime hardening stack completion and secondary sandbox enforcement (WP-07).
- WEPPcloud route/controller changes (separate scope).

## Constraints and Invariants
- No branch creation unless explicitly requested by human operator.
- Do not modify unrelated dirty files.
- Explicitly ignore dirty generated file `wepppy/weppcloud/routes/usersum/generated/docs_index.json`.
- Keep inspect/convert independent uploads; no cross-request staging.
- Keep WEPPcloud route/controller changes out of scope.
- Preserve canonical error payload shape with required `error.details`.
- Preserve public no-auth access model (`inspect`/`convert` remain unauthenticated by design).

## Required Abuse-Control Contract (WP-05)
1. Request identity and trust boundary
   - Only configured trusted proxy hops may influence client identity.
   - Requests from untrusted hops must not trust inbound `X-Forwarded-*` for limiter identity.
   - IPv6 limiter keys are aggregated to `/64`.
2. Rate and concurrency controls
   - Enforce per-IP rate limits for inspect/convert.
   - Enforce per-IP and global in-flight caps to prevent starvation.
   - Apply fast-fail under saturation with explicit canonical error payload (`error.details` required).
3. Timeout and anti-slowloris protections
   - Enforce request body/read constraints and fail quickly on stalled uploads.
   - Enforce response/write constraints for slow receivers and pinned downloads.
4. Egress posture
   - Parser/conversion paths run with deny-all egress posture unless explicitly allowlisted.
   - Abuse controls must not weaken parser safety boundary assumptions.

## Review and Disposition Requirements (Mandatory)
Execute all three review tracks before closing WP-05:
1. Code review
   - Review limiter keying, trusted-proxy parsing, and concurrency/backpressure behavior.
2. QA review
   - Review test adequacy for rate-limit, timeout, spoofed-header, and saturation scenarios.
3. Security review
   - Review bypass resistance (header spoofing, identity confusion, limiter evasion).

Disposition policy:
- Critical/High findings: must be fixed before WP close.
- Medium findings: must be fixed or explicitly deferred with rationale, owner, and target work-package.
- Low findings: may be deferred with rationale.

Disposition ledger (fill during execution):
| Finding ID | Reviewer Track | Severity | Summary | Disposition | Evidence | Owner |
| --- | --- | --- | --- | --- | --- | --- |
| CR-01 | code | Low | Reviewed middleware admission ordering and release semantics; fixed one Medium-risk issue where in-flight slots were released before response send completion. | Closed (fixed in WP-05) | `wepppy/microservices/shape_converter/app.py` inflight release moved to post-response background task; unit/integration gates re-run pass on final diff | Codex |
| QA-01 | qa | Low | Reviewed abuse-control test coverage for rate-limit, saturation (`429`/`503`), spoofed header behavior, and body-read timeout paths. | Closed (no additional action required) | `tests/shape_converter/unit/test_abuse_controls.py`, `tests/shape_converter/integration/test_abuse_controls_api.py`, endpoint timeout tests in inspect/convert unit suites; required gates pass | Codex |
| SEC-01 | security | Low | Reviewed trust-boundary and spoof resistance: only trusted proxy hops influence identity; edge strips inbound forwarding headers; parser path keeps deny-egress GDAL options. | Closed (no additional action required) | `docker/caddy/Caddyfile` header sanitation + transport timeouts; `abuse_controls.py` trusted-hop resolver + IPv6 `/64`; `convert.py` Fiona/GDAL deny-egress options; broad-exception check PASS | Codex |

Medium/High disposition status: **0 open, 0 deferred**.

## Target File Plan
Expected new/modified files for WP-05 (adjust only if justified):
- `wepppy/microservices/shape_converter/app.py`
- `wepppy/microservices/shape_converter/abuse_controls.py` (recommended new module)
- `wepppy/microservices/shape_converter/cleanup.py` (only if coupling needed)
- `wepppy/microservices/shape_converter/inspect.py` (only if timeout integration needed)
- `wepppy/microservices/shape_converter/convert.py` (only if timeout integration needed)
- `docker/caddy/Caddyfile` (only for edge trust/timeout alignment)
- `tests/shape_converter/unit/test_abuse_controls.py` (recommended new)
- `tests/shape_converter/unit/test_app_bootstrap.py`
- `tests/shape_converter/unit/test_inspect_endpoint.py`
- `tests/shape_converter/unit/test_convert_endpoint.py`
- `tests/shape_converter/integration/test_inspect_api.py`
- `tests/shape_converter/integration/test_convert_api.py`
- `tests/shape_converter/integration/test_abuse_controls_api.py` (recommended new)

Doc updates required:
- `/workdir/wepppy/wepppy/microservices/shape_converter/docs/work-packages/wp-05_public_abuse_controls_and_edge_trust_model.md` (fill evidence)
- `/workdir/wepppy/wepppy/microservices/shape_converter/docs/implementation-plan.md` (WP-05 state + gates + note)

## Implementation Steps (Execute Sequentially)
1. Define abuse-control configuration contract (env vars + safe defaults).
2. Implement trusted client identity extraction with configured proxy trust and IPv6 `/64` aggregation.
3. Implement per-IP rate limiting and per-IP/global in-flight caps with explicit canonical error mapping.
4. Wire abuse controls into inspect/convert request flow (no auth assumptions preserved).
5. Add timeout/slowloris protections for request/response lifecycle paths.
6. Align edge proxy behavior (forwarding header sanitation and timeout policy) where applicable.
7. Add unit tests for identity parsing, limiter behavior, and timeout guardrails.
8. Add integration tests for saturation, spoofed-header rejection, and expected 429/503 behavior.
9. Run required gates and capture outputs.
10. Run code/QA/security reviews and fill disposition ledger.
11. Update this WP evidence log and parent implementation plan row.

## Commands and Validation
## Focused unit iteration
```bash
cd /workdir/wepppy
wctl run-pytest tests/shape_converter/unit -k "abuse or rate or timeout or forwarded or inspect or convert" --maxfail=1
```

## Full unit gate
```bash
cd /workdir/wepppy
wctl run-pytest tests/shape_converter/unit
```

## Integration gate (abuse-control focused)
```bash
cd /workdir/wepppy
wctl run-pytest tests/shape_converter/integration -k "abuse or rate or timeout or inspect or convert" --maxfail=1
```

## Security hygiene check for changed files
```bash
cd /workdir/wepppy
python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master
```

## Manual proxied QA smoke (Caddy + abuse controls)
```bash
cd /workdir/wepppy
docker compose -f docker/docker-compose.dev.yml up -d caddy shape-converter

# Baseline no-auth reachability
curl -i -H 'X-Forwarded-Proto: https' \
  -F 'archive=@<valid_zip>' \
  http://127.0.0.1:8080/utils/shape-converter/v1/inspect

# Burst requests to trigger limiter/saturation behavior
for i in $(seq 1 40); do
  curl -s -o /tmp/sc_resp_$i.json -w "%{http_code}\n" -H 'X-Forwarded-Proto: https' \
    -F 'archive=@<valid_zip>' \
    http://127.0.0.1:8080/utils/shape-converter/v1/inspect
done

# Header spoof probe (should not bypass identity policy when source is untrusted)
curl -i -H 'X-Forwarded-For: 1.2.3.4,5.6.7.8' -H 'X-Forwarded-Proto: https' \
  -F 'archive=@<valid_zip>' \
  http://127.0.0.1:8080/utils/shape-converter/v1/inspect
```

Expected:
- Baseline request remains accessible without auth.
- Burst requests produce explicit canonical throttle/saturation responses (`429` and/or `503`) with populated `error.details`.
- Spoofed forwarding header does not bypass limiter identity/trust policy.

## Gate Checklist
## Code gate
- [x] WP-05 implementation scope complete.
- [x] Code review completed and findings dispositioned.
- [x] Lint/static checks for touched files pass.

## Shape-converter unit-test gate
- [x] `wctl run-pytest tests/shape_converter/unit -k "abuse or rate or timeout or forwarded or inspect or convert" --maxfail=1` passes.
- [x] `wctl run-pytest tests/shape_converter/unit` passes.

## QA gate
- [x] Integration tests cover throttle/saturation and timeout behavior.
- [x] Manual proxied smoke verifies expected no-auth + abuse-control behavior.
- [x] QA review findings dispositioned.

## Security review gate
- [x] Trusted-proxy identity model validated against spoofing/bypass cases.
- [x] No unresolved High findings in abuse-control surface.
- [x] Security review findings dispositioned (Mediums fixed or explicitly deferred with rationale).

## Evidence Log (Fill During Execution)
| Item | Evidence |
| --- | --- |
| Commit SHA(s) | Working tree (uncommitted changes during WP execution) |
| Unit gate output | `wctl run-pytest tests/shape_converter/unit -k "abuse or rate or timeout or forwarded or inspect or convert" --maxfail=1` => **73 passed**, 0 failed (2026-04-12) |
| Full unit gate output | `wctl run-pytest tests/shape_converter/unit` => **73 passed**, 0 failed (2026-04-12) |
| Integration gate output | `wctl run-pytest tests/shape_converter/integration -k "abuse or rate or timeout or inspect or convert" --maxfail=1` => **19 passed**, 0 failed (2026-04-12) |
| QA smoke output | Proxied Caddy smoke on `http://127.0.0.1:8080/utils/shape-converter`: baseline inspect no-auth `200`; throttling run (`SHAPE_CONVERTER_RATE_LIMIT_COUNT=5`) yielded **4x200 + 8x429** with canonical `rate_limited` payload + `Retry-After`; spoofed `X-Forwarded-For` probe returned `429` with limiter key still `172.28.0.1` (spoof ignored); saturation run (`MAX_INFLIGHT_GLOBAL=1`) with 20 parallel requests yielded **1x200 + 19x503** with canonical `service_saturated` details |
| Code review reference | 2026-04-12 focused manual diff review of `abuse_controls.py`, `app.py`, `convert.py`, Caddy/compose wiring, and abuse-control tests |
| QA review reference | 2026-04-12 review of unit + integration abuse-control coverage and manual proxied smoke matrix (baseline/throttle/spoof/saturation) |
| Security review reference | 2026-04-12 review of trusted forwarding-hop identity model, spoof resistance, and parser deny-egress controls; `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master` => PASS |
| Disposition ledger summary | 3 findings recorded (code/qa/security), all Low; one Medium-risk release-order issue identified and fixed before close; Medium/High open findings: 0 |
| Residual risks | Deferred to downstream packages: WP-06 (UI exposure of throttle/saturation guidance), WP-06B (`response_mode=json_body` relay backpressure UX), WP-07 (runtime hardening completion: seccomp/AppArmor/SELinux profiles, deny-all network policy enforcement in deployment, secondary parser sandbox verification) |

## Completion Criteria
WP-05 is `done` only when:
- All four gates are `pass` (or explicitly waived with rationale/approver).
- Code/QA/security review findings are fully dispositioned and recorded.
- Parent orchestration board is updated with WP-05 state/gates and evidence notes.
- This work-package evidence table is filled with concrete references.

## Agent Execution Prompt (E2E)
Use this prompt to run WP-05 end-to-end with mandatory reviews/dispositions:

```text
You are working in /workdir/wepppy.

Execute WP-05 end-to-end using:
- /workdir/wepppy/wepppy/microservices/shape_converter/docs/work-packages/wp-05_public_abuse_controls_and_edge_trust_model.md
- /workdir/wepppy/wepppy/microservices/shape_converter/docs/implementation-plan.md
- /workdir/wepppy/wepppy/microservices/shape_converter/docs/specification.md

Goal:
Deliver WP-05 “Public abuse controls and edge trust model” completely, including all required gates:
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
1. Implement per-IP rate limits and per-IP/global in-flight controls for public inspect/convert endpoints.
2. Enforce trusted forwarding-header identity model (trusted proxy hops only, IPv6 `/64` aggregation).
3. Implement slowloris/read/write timeout protections and explicit fast-fail behavior.
4. Preserve deny-all parser egress posture and verify assumptions.
5. Add unit/integration tests for limiter, trust-boundary, spoofed-header, and saturation paths.
6. Run code review, QA review, and security review; disposition all Medium/High findings.
7. Update evidence and gate states in:
   - /workdir/wepppy/wepppy/microservices/shape_converter/docs/work-packages/wp-05_public_abuse_controls_and_edge_trust_model.md
   - /workdir/wepppy/wepppy/microservices/shape_converter/docs/implementation-plan.md

Validation required:
- wctl run-pytest tests/shape_converter/unit -k "abuse or rate or timeout or forwarded or inspect or convert" --maxfail=1
- wctl run-pytest tests/shape_converter/unit
- wctl run-pytest tests/shape_converter/integration -k "abuse or rate or timeout or inspect or convert" --maxfail=1
- python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master
- Manual proxied smoke checks via Caddy for no-auth baseline, throttling/saturation, and spoofed-header behavior.

Final response format:
- Findings first (bugs/risks/blockers with file:line), if any.
- Then concise change summary with exact files touched.
- Include exact validation commands run and outcomes.
- Include code/QA/security review findings and explicit dispositions.
- Include remaining deferred risks for WP-06/WP-06B/WP-07.
```
