# WP-06B Work Package: Browser Relay Mode Support (`json_body`)
Status: done
Last Updated: 2026-04-12
Owner: Codex (WP-06B execution)
Parent Plan: `/workdir/wepppy/wepppy/microservices/shape_converter/docs/implementation-plan.md`
Primary Spec: `/workdir/wepppy/wepppy/microservices/shape_converter/docs/specification.md`

## Objective
Deliver WP-06B end-to-end by implementing relay-friendly convert responses with `response_mode=json_body` for GeoJSON, so browser clients can forward converted payloads downstream without download round-trips.

This package is complete only when all WP-06B gates pass:
- Code gate
- Shape-converter unit-test gate
- QA gate
- Security review gate

## Scope
### In scope
- Implement `POST /utils/shape-converter/v1/convert` support for:
  - `response_mode=json_body`
  - `output_format=geojson` only
- Return JSON body containing:
  - GeoJSON payload
  - conversion metadata/warnings
  - request identifier
- Preserve existing `response_mode=download` behavior and metadata sidecar behavior.
- Add explicit canonical error for unsupported `json_body` combinations (for example non-GeoJSON output).
- Add UI wiring and messaging for relay-mode convert path.
- Add unit + integration tests for relay success and failure paths.
- Add proxied smoke checks for relay-mode behavior.
- Run dedicated code, QA, and security reviews and disposition all Medium/High findings.
- Update this work-package evidence and the implementation-plan board row.

### Out of scope
- WEPPcloud route/controller changes to consume relay payloads.
- New authentication model for shape-converter (service remains public no-auth).
- Runtime hardening stack completion and secondary sandbox enforcement (WP-07).

## Constraints and Invariants
- No branch creation unless explicitly requested by human operator.
- Do not modify unrelated dirty files.
- Explicitly ignore dirty generated file `wepppy/weppcloud/routes/usersum/generated/docs_index.json`.
- Keep inspect/convert independent uploads; no cross-request staging.
- Keep WEPPcloud route/controller changes out of scope.
- Preserve canonical API error contract (`error.code`, `error.message`, `error.details`).
- Preserve cleanup contract: no request artifacts persist after terminal response.

## Required Relay Contract (WP-06B)
1. Accepted relay request
   - `output_format=geojson`
   - `response_mode=json_body`
2. Relay success response
   - `200 application/json`
   - JSON object includes:
     - `request_id`
     - `geojson` (GeoJSON FeatureCollection payload)
     - `metadata` (conversion metadata including warnings and CRS fields)
3. Relay validation errors
   - `response_mode=json_body` + non-GeoJSON output must fail with canonical 4xx error.
   - Unknown `response_mode` values still fail canonically.
4. Existing behavior compatibility
   - `response_mode=download` remains unchanged.
   - Existing metadata sidecar endpoint behavior remains unchanged for download mode.
5. Relay safety
   - Relay mode must not weaken abuse controls from WP-05.
   - Relay mode must preserve request-scoped cleanup guarantees from WP-04.

## Review and Disposition Requirements (Mandatory)
Execute all three review tracks before closing WP-06B:
1. Code review
   - Review convert mode branching, payload shape, and backward compatibility.
2. QA review
   - Review relay success/error tests, UI path behavior, and proxied smoke evidence.
3. Security review
   - Review payload exposure, abuse-control interaction, and cleanup invariants under relay mode.

Disposition policy:
- Critical/High findings: must be fixed before WP close.
- Medium findings: must be fixed or explicitly deferred with rationale, owner, and target work-package.
- Low findings: may be deferred with rationale.

Disposition ledger (fill during execution):
| Finding ID | Reviewer Track | Severity | Summary | Disposition | Evidence | Owner |
| --- | --- | --- | --- | --- | --- | --- |
| CR-01 | code | Low | Reviewed convert-mode branching in `app.py` and backward-compatibility path for `download`; no Medium/High regressions found. | Closed (no additional action required) | `wepppy/microservices/shape_converter/app.py`, `tests/shape_converter/unit/test_convert_endpoint.py`, `tests/shape_converter/integration/test_convert_api.py` | Codex |
| QA-01 | qa | Low | Reviewed relay success/failure/download compatibility across required unit/integration gates plus proxied Caddy smoke matrix; no Medium/High gaps found. | Closed (no additional action required) | Required gate runs + manual smoke outputs in Evidence Log | Codex |
| SEC-01 | security | Low | Reviewed relay payload exposure and trust-boundary behavior: canonical error contracts preserved, no sidecar payload leakage, cleanup and abuse-control invariants unchanged for `json_body`. | Closed (no additional action required) | `wepppy/microservices/shape_converter/app.py`, `wepppy/microservices/shape_converter/ui/app.js`, `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master` => PASS | Codex |

Medium/High disposition status: **0 open, 0 deferred**.

## Target File Plan
Expected new/modified files for WP-06B (adjust only if justified):
- `wepppy/microservices/shape_converter/app.py`
- `wepppy/microservices/shape_converter/convert.py`
- `wepppy/microservices/shape_converter/ui/app.js`
- `wepppy/microservices/shape_converter/ui/index.html`
- `tests/shape_converter/unit/test_convert_endpoint.py`
- `tests/shape_converter/unit/test_ui_endpoints.py` (if UI contract changes)
- `tests/shape_converter/integration/test_convert_api.py`
- `tests/shape_converter/integration/test_ui_flow.py`

Doc updates required:
- `/workdir/wepppy/wepppy/microservices/shape_converter/docs/work-packages/wp-06b_browser_relay_mode_json_body.md` (fill evidence)
- `/workdir/wepppy/wepppy/microservices/shape_converter/docs/implementation-plan.md` (WP-06B state + gates + note)
- `/workdir/wepppy/wepppy/microservices/shape_converter/docs/specification.md` (if relay contract wording changes)

## Implementation Steps (Execute Sequentially)
1. Define final relay response schema for `json_body` mode.
2. Implement convert endpoint branch for `json_body` when `output_format=geojson`.
3. Keep download-mode path untouched and compatible.
4. Add canonical validation errors for unsupported relay combinations.
5. Wire UI relay action/state messaging for `json_body`.
6. Add unit tests for relay success + validation failure matrix.
7. Add integration tests for proxied relay behavior and backward compatibility.
8. Run required gates and capture outputs.
9. Run code/QA/security reviews and fill disposition ledger.
10. Update this WP evidence log and parent implementation plan row.

## Commands and Validation
## Focused unit iteration
```bash
cd /workdir/wepppy
wctl run-pytest tests/shape_converter/unit -k "json_body or relay or convert or ui" --maxfail=1
```

## Full unit gate
```bash
cd /workdir/wepppy
wctl run-pytest tests/shape_converter/unit
```

## Integration gate (relay-focused)
```bash
cd /workdir/wepppy
wctl run-pytest tests/shape_converter/integration -k "json_body or relay or convert or ui" --maxfail=1
```

## Security hygiene check for changed files
```bash
cd /workdir/wepppy
python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master
```

## Manual proxied QA smoke
```bash
cd /workdir/wepppy
docker compose -f docker/docker-compose.dev.yml up -d caddy shape-converter

# Relay success (GeoJSON + json_body)
curl -i -H 'X-Forwarded-Proto: https' \
  -F 'archive=@<valid_zip>' \
  -F 'output_format=geojson' \
  -F 'target_crs=wgs84' \
  -F 'response_mode=json_body' \
  http://127.0.0.1:8080/utils/shape-converter/v1/convert

# Relay invalid combination (GeoParquet + json_body)
curl -i -H 'X-Forwarded-Proto: https' \
  -F 'archive=@<valid_zip>' \
  -F 'output_format=geoparquet' \
  -F 'target_crs=wgs84' \
  -F 'response_mode=json_body' \
  http://127.0.0.1:8080/utils/shape-converter/v1/convert

# Backward compatibility (download mode)
curl -i -H 'X-Forwarded-Proto: https' \
  -F 'archive=@<valid_zip>' \
  -F 'output_format=geojson' \
  -F 'target_crs=wgs84' \
  -F 'response_mode=download' \
  http://127.0.0.1:8080/utils/shape-converter/v1/convert
```

Expected:
- Relay success returns JSON body containing GeoJSON + metadata.
- Invalid relay combination returns canonical 4xx with populated `error.details`.
- Download path remains unchanged.

## Gate Checklist
## Code gate
- [x] WP-06B implementation scope complete.
- [x] Code review completed and findings dispositioned.
- [x] Lint/static checks for touched files pass.

## Shape-converter unit-test gate
- [x] `wctl run-pytest tests/shape_converter/unit -k "json_body or relay or convert or ui" --maxfail=1` passes.
- [x] `wctl run-pytest tests/shape_converter/unit` passes.

## QA gate
- [x] Integration tests cover relay success and relay validation failure paths.
- [x] Manual proxied smoke verifies relay + download compatibility behavior.
- [x] QA review findings dispositioned.

## Security review gate
- [x] Relay payload exposure reviewed; no sensitive-sidecar leakage introduced.
- [x] Abuse controls remain effective under relay mode.
- [x] Security review findings dispositioned (no unresolved High findings).

## Evidence Log (Fill During Execution)
| Item | Evidence |
| --- | --- |
| Commit SHA(s) | Working tree (uncommitted changes during WP execution) |
| Unit gate output | `wctl run-pytest tests/shape_converter/unit -k "json_body or relay or convert or ui" --maxfail=1` => **83 passed**, 0 failed (2026-04-12); `wctl run-pytest tests/shape_converter/unit` => **83 passed**, 0 failed (2026-04-12) |
| Integration gate output | `wctl run-pytest tests/shape_converter/integration -k "json_body or relay or convert or ui" --maxfail=1` => **25 passed**, 0 failed (2026-04-12) |
| QA smoke output | Proxied Caddy smoke on `http://127.0.0.1:8080/utils/shape-converter/v1/convert` with `X-Forwarded-Proto: https` and fixture `/tmp/shape_converter_wp06b_smoke.zip`: relay success (`output_format=geojson,response_mode=json_body`) returned `200` with keys `request_id`,`geojson`,`metadata`; invalid combo (`output_format=geoparquet,response_mode=json_body`) returned canonical `400 invalid_request` with explicit combination details; download compatibility (`response_mode=download`) returned `200`, `Content-Type=application/geo+json`, attachment header, and metadata sidecar path `/utils/shape-converter/v1/convert/metadata/<id>`; metadata fetch with forwarded-proto baseline returned `200` with expected payload fields (`request_id`,`output_format`,`target_crs`) |
| Code review reference | 2026-04-12 focused code-path review of relay-mode endpoint branch + backward-compatible download path + test coverage updates |
| QA review reference | 2026-04-12 review of required gate outputs and proxied relay smoke matrix (success, invalid combination, download compatibility) |
| Security review reference | 2026-04-12 relay trust-boundary review + `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master` => PASS |
| Disposition ledger summary | 3 findings recorded (code/qa/security), all Low; Medium/High open findings: 0 |
| Residual risks | Deferred to WP-07: runtime hardening completion (rootless+RO verification at deploy target, seccomp/AppArmor/SELinux enforcement, deny-all network policy verification, secondary parser sandbox readiness enforcement) |

## Completion Criteria
WP-06B is `done` only when:
- All four gates are `pass` (or explicitly waived with rationale/approver).
- Code/QA/security review findings are fully dispositioned and recorded.
- Parent orchestration board is updated with WP-06B state/gates and evidence notes.
- This work-package evidence table is filled with concrete references.

## Agent Execution Prompt (E2E)
Use this prompt to run WP-06B end-to-end with mandatory reviews/dispositions:

```text
You are working in /workdir/wepppy.

Execute WP-06B end-to-end using:
- /workdir/wepppy/wepppy/microservices/shape_converter/docs/work-packages/wp-06b_browser_relay_mode_json_body.md
- /workdir/wepppy/wepppy/microservices/shape_converter/docs/implementation-plan.md
- /workdir/wepppy/wepppy/microservices/shape_converter/docs/specification.md

Goal:
Deliver WP-06B “Browser relay mode support (`json_body`)” completely, including all required gates:
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
1. Implement `response_mode=json_body` for `output_format=geojson`.
2. Return relay response with `request_id`, `geojson`, and `metadata` fields.
3. Keep `response_mode=download` unchanged and backward compatible.
4. Return explicit canonical 4xx error for unsupported relay combinations (for example `geoparquet + json_body`).
5. Update UI relay action/state messaging for `json_body`.
6. Add unit/integration tests for relay success/failure and download compatibility.
7. Run code review, QA review, and security review; disposition all Medium/High findings.
8. Update evidence and gate states in:
   - /workdir/wepppy/wepppy/microservices/shape_converter/docs/work-packages/wp-06b_browser_relay_mode_json_body.md
   - /workdir/wepppy/wepppy/microservices/shape_converter/docs/implementation-plan.md
   - /workdir/wepppy/wepppy/microservices/shape_converter/docs/specification.md (if contract text changes)

Validation required:
- wctl run-pytest tests/shape_converter/unit -k "json_body or relay or convert or ui" --maxfail=1
- wctl run-pytest tests/shape_converter/unit
- wctl run-pytest tests/shape_converter/integration -k "json_body or relay or convert or ui" --maxfail=1
- python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master
- Manual proxied smoke checks via Caddy for relay success, relay invalid-combination error, and download compatibility.

Final response format:
- Findings first (bugs/risks/blockers with file:line), if any.
- Then concise change summary with exact files touched.
- Include exact validation commands run and outcomes.
- Include code/QA/security review findings and explicit dispositions.
- Include remaining deferred risks for WP-07.
```
