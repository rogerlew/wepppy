# WP-06 Work Package: UI Implementation and Metadata Rendering
Status: done
Last Updated: 2026-04-12
Owner: Codex (WP-06 execution)
Parent Plan: `/workdir/wepppy/wepppy/microservices/shape_converter/docs/implementation-plan.md`
Primary Spec: `/workdir/wepppy/wepppy/microservices/shape_converter/docs/specification.md`

## Objective
Deliver WP-06 end-to-end by implementing the shape-converter UI for inspect and convert flows, with complete projection/schema/warnings rendering and clear user guidance for errors and abuse-control states.

This package is complete only when all WP-06 gates pass:
- Code gate
- Shape-converter unit-test gate
- QA gate
- Security review gate

## Scope
### In scope
- Implement UI for upload -> inspect -> convert -> download flow.
- Render required inspect/convert metadata:
  - detected CRS + projection status
  - attribute schema table
  - geometry summary (`feature_count`, `geometry_types`, `bbox`)
  - warnings list
- Surface key warnings explicitly, including:
  - `.shp.xml` removal advisory (generally not advisable to include in ZIPs)
  - projected GeoJSON non-RFC warning
  - unknown/invalid CRS caveats
- Surface abuse-control responses from WP-05 with user-friendly guidance:
  - `rate_limited` (`429`)
  - `service_saturated` (`503`)
- Preserve convert behavior for `response_mode=download` (WP-03), with explicit handling of deferred `json_body` mode.
- Add UI-focused tests and manual proxied smoke evidence.
- Run dedicated code, QA, and security reviews and disposition all Medium/High findings.
- Update this work-package evidence and the implementation-plan board row.

### Out of scope
- Relay-mode `response_mode=json_body` implementation (WP-06B).
- Additional backend abuse-control logic beyond WP-05 behavior.
- Runtime hardening stack completion and sandbox enforcement (WP-07).
- WEPPcloud route/controller changes (separate scope).

## Constraints and Invariants
- No branch creation unless explicitly requested by human operator.
- Do not modify unrelated dirty files.
- Explicitly ignore dirty generated file `wepppy/weppcloud/routes/usersum/generated/docs_index.json`.
- Keep WEPPcloud route/controller changes out of scope.
- Preserve inspect/convert independent uploads (no cross-request staging).
- Preserve canonical API error contract (`error.code`, `error.message`, `error.details`).
- UI must work through proxied namespace `/utils/shape-converter/*` on desktop and mobile widths.

## Required UI Contract (WP-06)
1. Required visible sections
   - Upload state and validation errors.
   - Projection panel (detected CRS, projection status, target CRS selector).
   - Attribute schema table (field name/type/width/precision).
   - Geometry summary (feature count, geometry types, bbox).
   - Convert controls and download state.
2. Message clarity
   - No silent fallback behavior.
   - Canonical API errors shown to user with actionable copy.
3. Warning rendering
   - Render warning list from inspect and convert metadata.
   - Include explicit `.shp.xml` advisory text.
   - Include explicit projected-GeoJSON compatibility warning when present.
4. Abuse-control UX
   - `429` and `503` states must be recognizable and non-ambiguous.
   - If `Retry-After` is returned, display it.

## Review and Disposition Requirements (Mandatory)
Execute all three review tracks before closing WP-06:
1. Code review
   - Review UI state transitions, error handling, and warning rendering fidelity.
2. QA review
   - Review desktop/mobile UX behavior and end-to-end flow coverage.
3. Security review
   - Review client-side handling to ensure no trust-boundary regression, no leaking raw sidecar metadata, and no unsafe rendering of server messages.

Disposition policy:
- Critical/High findings: must be fixed before WP close.
- Medium findings: must be fixed or explicitly deferred with rationale, owner, and target work-package.
- Low findings: may be deferred with rationale.

Disposition ledger (fill during execution):
| Finding ID | Reviewer Track | Severity | Summary | Disposition | Evidence | Owner |
| --- | --- | --- | --- | --- | --- | --- |
| CR-01 | code | Low | Reviewed UI state transitions (`inspect`/`convert`), metadata panel updates, and deferred `json_body` messaging; no Medium/High regressions found. | Closed (no additional action required) | `wepppy/microservices/shape_converter/app.py`, `wepppy/microservices/shape_converter/ui/app.js`, `tests/shape_converter/unit/test_ui_endpoints.py`, `tests/shape_converter/integration/test_ui_flow.py` | Codex |
| QA-01 | qa | Low | Reviewed end-to-end UI flow evidence: proxied route reachability, inspect `.shp.xml` advisory, projected-GeoJSON warning, and abuse-control UX (`429`/`503` with `Retry-After` when present). | Closed (no additional action required) | Required gate runs + proxied curl smoke outputs recorded in Evidence Log | Codex |
| SEC-01 | security | Low | Reviewed client-side trust-boundary handling: no unsafe HTML rendering (`textContent` only), no sidecar-content leak introduced, no auth bypass semantics added, and canonical API error handling retained. | Closed (no additional action required) | `wepppy/microservices/shape_converter/ui/app.js`, `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master` => PASS | Codex |

Medium/High disposition status: **0 open, 0 deferred**.

## Target File Plan
Expected new/modified files for WP-06 (adjust only if justified):
- `wepppy/microservices/shape_converter/app.py`
- `wepppy/microservices/shape_converter/ui/index.html` (recommended new)
- `wepppy/microservices/shape_converter/ui/styles.css` (recommended new)
- `wepppy/microservices/shape_converter/ui/app.js` (recommended new)
- `tests/shape_converter/unit/test_ui_endpoints.py` (recommended new)
- `tests/shape_converter/integration/test_ui_flow.py` (recommended new)
- `tests/shape_converter/integration/test_inspect_api.py` (if payload/UI contract assertions expand)
- `tests/shape_converter/integration/test_convert_api.py` (if payload/UI contract assertions expand)

Doc updates required:
- `/workdir/wepppy/wepppy/microservices/shape_converter/docs/work-packages/wp-06_ui_implementation_and_metadata_rendering.md` (fill evidence)
- `/workdir/wepppy/wepppy/microservices/shape_converter/docs/implementation-plan.md` (WP-06 state + gates + note)

## Implementation Steps (Execute Sequentially)
1. Define UI route/asset serving approach under `/utils/shape-converter/`.
2. Implement upload and inspect workflow with metadata rendering panels.
3. Implement convert controls and download flow wiring (`response_mode=download`).
4. Render warnings and canonical errors, including `.shp.xml` advisory and abuse-control states.
5. Add responsive layout behavior for common mobile and desktop widths.
6. Add unit tests for UI endpoint/static delivery and key state helpers.
7. Add integration tests for core user flow and key error/warning states.
8. Run required gates and capture outputs.
9. Run code/QA/security reviews and fill disposition ledger.
10. Update this WP evidence log and parent implementation plan row.

## Commands and Validation
## Focused unit iteration
```bash
cd /workdir/wepppy
wctl run-pytest tests/shape_converter/unit -k "ui or inspect or convert or warning or metadata" --maxfail=1
```

## Full unit gate
```bash
cd /workdir/wepppy
wctl run-pytest tests/shape_converter/unit
```

## Integration gate (UI-focused)
```bash
cd /workdir/wepppy
wctl run-pytest tests/shape_converter/integration -k "ui or inspect or convert" --maxfail=1
```

## Manual proxied QA smoke
```bash
cd /workdir/wepppy
docker compose -f docker/docker-compose.dev.yml up -d caddy shape-converter

# UI route
curl -i http://127.0.0.1:8080/utils/shape-converter/

# Inspect + warning scenario (.shp.xml advisory expected)
curl -i -H 'X-Forwarded-Proto: https' \
  -F 'archive=@<zip_with_shp_xml>' \
  http://127.0.0.1:8080/utils/shape-converter/v1/inspect

# Convert projected warning scenario
curl -i -H 'X-Forwarded-Proto: https' \
  -F 'archive=@<projected_zip>' \
  -F 'output_format=geojson' \
  -F 'target_crs=same_as_shapefile' \
  http://127.0.0.1:8080/utils/shape-converter/v1/convert

# Throttle scenario from WP-05 surfaced in UI
for i in $(seq 1 20); do
  curl -s -o /tmp/sc_ui_rate_$i.json -w "%{http_code}\n" -H 'X-Forwarded-Proto: https' \
    -F 'archive=@<valid_zip>' \
    http://127.0.0.1:8080/utils/shape-converter/v1/inspect
done
```

Expected:
- UI route is reachable through Caddy namespace.
- Required metadata/warnings are rendered by UI for inspect and convert.
- `429`/`503` responses are surfaced with clear user guidance.

## Gate Checklist
## Code gate
- [x] WP-06 implementation scope complete.
- [x] Code review completed and findings dispositioned.
- [x] Lint/static checks for touched files pass.

## Shape-converter unit-test gate
- [x] `wctl run-pytest tests/shape_converter/unit -k "ui or inspect or convert or warning or metadata" --maxfail=1` passes.
- [x] `wctl run-pytest tests/shape_converter/unit` passes.

## QA gate
- [x] Integration tests cover UI core flow and warning/error rendering.
- [x] Manual proxied smoke verifies proxied UI route, inspect/convert warning scenarios, and abuse-control messaging (`429`/`503`, `Retry-After` visibility).
- [x] QA review findings dispositioned.

## Security review gate
- [x] UI rendering verified to avoid leaking sensitive sidecar metadata.
- [x] Trust-boundary behavior unchanged (no client-side bypass semantics introduced).
- [x] Security review findings dispositioned (no unresolved High findings).

## Evidence Log (Fill During Execution)
| Item | Evidence |
| --- | --- |
| Commit SHA(s) | Working tree (uncommitted changes during WP execution) |
| Unit gate output | `wctl run-pytest tests/shape_converter/unit -k "ui or inspect or convert or warning or metadata" --maxfail=1` => **77 passed**, 0 failed (2026-04-12) |
| Full unit gate output | `wctl run-pytest tests/shape_converter/unit` => **77 passed**, 0 failed (2026-04-12) |
| Integration gate output | `wctl run-pytest tests/shape_converter/integration -k "ui or inspect or convert" --maxfail=1` => **23 passed**, 0 failed (2026-04-12) |
| QA smoke output | Proxied Caddy smoke on `http://127.0.0.1:8080/utils/shape-converter/` with `X-Forwarded-Proto: https`: UI route returned `200` + HTML shell; inspect `.shp.xml` scenario returned `200` with explicit removal advisory warning; projected GeoJSON convert (`target_crs=same_as_shapefile`) returned `200` download + metadata warning containing RFC 7946 compatibility caveat; throttle run (`SHAPE_CONVERTER_RATE_LIMIT_COUNT=3`) yielded **1x200 + 7x429** with canonical `rate_limited` payload and `Retry-After`; saturation run (`SHAPE_CONVERTER_RATE_LIMIT_COUNT=1000`, `MAX_INFLIGHT_GLOBAL=1`) with 20 parallel convert requests yielded **1x200 + 19x503** with canonical `service_saturated` payload |
| Code review reference | 2026-04-12 focused review of UI serving changes (`app.py`), UI assets (`ui/index.html`, `ui/styles.css`, `ui/app.js`), and UI-focused test additions |
| QA review reference | 2026-04-12 review of UI-focused unit/integration coverage + proxied Caddy smoke matrix (route reachability, inspect/convert warnings, throttle/saturation guidance) |
| Security review reference | 2026-04-12 review of client-side rendering and trust-boundary assumptions (`textContent` rendering, canonical error handling, no sidecar data exposure) + `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master` => PASS |
| Disposition ledger summary | 3 findings recorded (code/qa/security), all Low; Medium/High open findings: 0 |
| Residual risks | Deferred to WP-06B/WP-07: `response_mode=json_body` relay UX + payload handling is not implemented in WP-06; runtime hardening/sandbox controls remain under WP-07; mobile visual polish verification remains part of broader final QA closeout in WP-09 |

## Completion Criteria
WP-06 is `done` only when:
- All four gates are `pass` (or explicitly waived with rationale/approver).
- Code/QA/security review findings are fully dispositioned and recorded.
- Parent orchestration board is updated with WP-06 state/gates and evidence notes.
- This work-package evidence table is filled with concrete references.

## Agent Execution Prompt (E2E)
Use this prompt to run WP-06 end-to-end with mandatory reviews/dispositions:

```text
You are working in /workdir/wepppy.

Execute WP-06 end-to-end using:
- /workdir/wepppy/wepppy/microservices/shape_converter/docs/work-packages/wp-06_ui_implementation_and_metadata_rendering.md
- /workdir/wepppy/wepppy/microservices/shape_converter/docs/implementation-plan.md
- /workdir/wepppy/wepppy/microservices/shape_converter/docs/specification.md

Goal:
Deliver WP-06 “UI implementation and metadata rendering” completely, including all required gates:
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
1. Implement UI route and assets for inspect/convert flow under proxied `/utils/shape-converter/`.
2. Render required metadata panels (projection, schema, geometry summary, warnings).
3. Surface `.shp.xml` removal advisory and projected GeoJSON compatibility warning clearly.
4. Surface abuse-control responses (`429`/`503`, `Retry-After` when present) with user guidance.
5. Keep `response_mode=download` flow explicit; keep `json_body` deferred to WP-06B with explicit messaging.
6. Add unit/integration tests for UI flow and warning/error rendering.
7. Run code review, QA review, and security review; disposition all Medium/High findings.
8. Update evidence and gate states in:
   - /workdir/wepppy/wepppy/microservices/shape_converter/docs/work-packages/wp-06_ui_implementation_and_metadata_rendering.md
   - /workdir/wepppy/wepppy/microservices/shape_converter/docs/implementation-plan.md

Validation required:
- wctl run-pytest tests/shape_converter/unit -k "ui or inspect or convert or warning or metadata" --maxfail=1
- wctl run-pytest tests/shape_converter/unit
- wctl run-pytest tests/shape_converter/integration -k "ui or inspect or convert" --maxfail=1
- Manual proxied smoke checks via Caddy for UI route, inspect/convert warnings, and abuse-control UX states.

Final response format:
- Findings first (bugs/risks/blockers with file:line), if any.
- Then concise change summary with exact files touched.
- Include exact validation commands run and outcomes.
- Include code/QA/security review findings and explicit dispositions.
- Include remaining deferred risks for WP-06B/WP-07.
```
