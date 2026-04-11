# Shape Converter Implementation Plan
Status: Active
Last Updated: 2026-04-11
Owner: Platform / WEPPpy
Primary Spec: `/workdir/wepppy/shape-converter/specification.md`

## Purpose
This document is the orchestration board for implementing the shape-converter service via bounded work-packages.
It tracks work-package completion state and required gates:
- Code gate
- Shape-converter unit-test gate
- QA gate
- Security review gate

## Scope Boundary
- Included in this plan:
  - Shape-converter service implementation.
  - UI/UX implementation.
  - Browser relay support from WEPPcloud clients to shape-converter (`response_mode=json_body`) so clients can forward GeoJSON payloads.
- Explicitly excluded from this plan:
  - WEPPcloud route/controller changes to consume relay payloads (tracked as separate scope/work-package stream).

## State Model
### Work-package state
- `not_started`
- `in_progress`
- `blocked`
- `in_review`
- `done`

### Gate state
- `pending`
- `running`
- `pass`
- `fail`
- `waived` (requires explicit risk acceptance note)

## Gate Definitions (Required)
### Code gate
Required evidence:
- Implementation scope for the work-package is complete.
- Diff reviewed by at least one engineer not authoring the change.
- Lint/static checks for touched code paths pass.

### Shape-converter unit-test gate
Required evidence:
- New/updated unit tests exist for the exact behavior changed.
- Fast gate command passes:
  - `wctl run-pytest tests/shape_converter/unit --maxfail=1`
- Full shape-converter unit gate passes before WP close:
  - `wctl run-pytest tests/shape_converter/unit`

Notes:
- If final path differs after scaffold, update this plan in the same PR.
- Unit gate cannot be waived for behavior changes.

### QA gate
Required evidence:
- Integration tests for affected endpoints pass.
- UI flow validation passes for upload -> inspect -> convert -> cleanup.
- Manual smoke checklist completed for changed UX paths.

### Security review gate
Required evidence:
- Security reviewer sign-off for the work-package scope.
- Abuse-control and sandbox assumptions validated for changed surfaces.
- No unresolved High findings; Medium findings require explicit disposition.

## Work-Package Board
| WP | Title | Depends On | State | Code Gate | Unit Gate | QA Gate | Security Gate | Evidence / Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| WP-00 | Repo scaffold and orchestration setup | none | done | pass | pass | pass | pass | This plan + specification moved under `shape-converter/` |
| WP-01 | Service scaffold and container wiring | WP-00 | not_started | pending | pending | pending | pending | Create `shape-converter` app skeleton, Dockerfile, compose service, Caddy route |
| WP-02 | Inspect endpoint + ZIP/shapefile validation | WP-01 | not_started | pending | pending | pending | pending | Implement `/utils/shape-converter/v1/inspect` and risk controls |
| WP-03 | Convert endpoint + CRS and format pipeline | WP-02 | not_started | pending | pending | pending | pending | Implement `/utils/shape-converter/v1/convert`, GeoJSON/GeoParquet behavior |
| WP-04 | Cleanup lifecycle and failure-path guarantees | WP-02, WP-03 | not_started | pending | pending | pending | pending | Enforce request-scoped delete on success/failure/timeout/disconnect |
| WP-05 | Public abuse controls and edge trust model | WP-01 | not_started | pending | pending | pending | pending | Rate limits, trusted forwarding headers, slowloris and timeout controls |
| WP-06 | UI implementation and metadata rendering | WP-02, WP-03 | not_started | pending | pending | pending | pending | Upload, schema table, projection panel, warnings, download UX |
| WP-06B | Browser relay mode support (`json_body`) | WP-03, WP-06 | not_started | pending | pending | pending | pending | Add relay-friendly convert response mode and browser payload handoff pattern; no WEPPcloud route edits in this plan |
| WP-07 | Runtime hardening and sandbox enforcement | WP-01 | not_started | pending | pending | pending | pending | Rootless, RO filesystem, caps drop, seccomp/AppArmor/SELinux, secondary sandbox |
| WP-08 | Test suite completion and gate automation | WP-02, WP-03, WP-04, WP-05, WP-06, WP-06B, WP-07 | not_started | pending | pending | pending | pending | Add full unit/integration/security/perf gates and CI wiring |
| WP-09 | Final QA + security closeout + release readiness | WP-08 | not_started | pending | pending | pending | pending | Final evidence pack, residual risk log, go/no-go decision |

## Work-Package Details
## WP-01 Service scaffold and container wiring
### Scope
- Create service codebase structure and app entrypoint.
- Add container build/run wiring and Caddy integration for `/utils/shape-converter`.

### Exit criteria
- Service starts and responds on health endpoints.
- Caddy routing works for exact and subtree matchers.
- Base tests run in CI without regressions.

## WP-02 Inspect endpoint + ZIP/shapefile validation
### Scope
- Implement inspect API and metadata extraction.
- Implement ZIP and shapefile validation rules from specification.

### Exit criteria
- Inspect returns schema, projection, geometry summary, warnings.
- Invalid archives fail with canonical error payload.
- Unit and security tests cover traversal, bombs, malformed inputs.

## WP-03 Convert endpoint + CRS and format pipeline
### Scope
- Implement convert API with independent upload model.
- Implement `same_as_shapefile`, `wgs84`, `utm_wepppy_upper_left` behavior.
- Implement GeoJSON/GeoParquet output rules.

### Exit criteria
- Conversion works across point/line/polygon fixtures.
- Projected GeoJSON behavior and warnings are explicit.
- UTM out-of-domain behavior returns documented error.

## WP-04 Cleanup lifecycle and failure-path guarantees
### Scope
- Enforce request-scoped temp directories and artifact cleanup.
- Ensure cleanup on failures, timeouts, and client disconnect.

### Exit criteria
- No residual per-request artifacts after terminal response.
- Janitor handles abnormal-termination residue only.

## WP-05 Public abuse controls and edge trust model
### Scope
- Implement public no-auth rate limiting and concurrency controls.
- Enforce trusted forwarding header model and IP identity policy.
- Implement upload/read/write timeout protections.

### Exit criteria
- Flood/slowloris tests pass with expected `429`/timeout behavior.
- Healthy traffic remains available under adversarial load.

## WP-06 UI implementation and metadata rendering
### Scope
- Implement UI for inspect and convert flows.
- Display attribute schema, projection details, warnings, geometry summary.

### Exit criteria
- UX supports inspect and convert with clear error/warning states.
- UI reports projection and schema before conversion.

## WP-06B Browser relay mode support (`json_body`)
### Scope
- Implement relay-friendly convert response mode for GeoJSON payload returns.
- Provide browser integration pattern for immediate forwarding of GeoJSON payloads to WEPPcloud endpoints.
- Keep relay implementation stateless in shape-converter request scope.

### Exit criteria
- `response_mode=json_body` implemented for GeoJSON conversions.
- Browser relay flow validated against a downstream contract test endpoint.
- No ZIP/shapefile artifacts persist beyond request completion.
- No WEPPcloud route/controller code changes included in this work-package.

## WP-07 Runtime hardening and sandbox enforcement
### Scope
- Apply and verify runtime hardening controls.
- Enforce secondary parser sandbox in production readiness checks.

### Exit criteria
- Hardening verification tests pass.
- Service readiness fails when required sandbox mode is absent.

## WP-08 Test suite completion and gate automation
### Scope
- Complete shape-converter unit and integration test suites.
- Add security and performance gate commands to CI.

### Exit criteria
- All gates automated and blocking where required.
- Gate evidence links recorded in this plan.

## WP-09 Final QA + security closeout + release readiness
### Scope
- Execute full QA and security closeout.
- Produce final release evidence and residual-risk register.

### Exit criteria
- All WP states are `done`.
- All gates are `pass` or explicitly waived with risk acceptance.
- Release readiness signed by engineering + security.

## Cadence and Update Rules
- Update this file at least once per work-package transition.
- Any gate failure must update gate state to `fail` with evidence link.
- If a gate is waived, add waiver rationale and approver in `Evidence / Notes`.
- Do not mark a work-package `done` unless all required gates are `pass` or formally waived.

## Rollup Checklist
- [ ] WP-01 through WP-09 complete (including WP-06B)
- [ ] Code gates all pass
- [ ] Shape-converter unit-test gates all pass
- [ ] QA gates all pass
- [ ] Security review gates all pass
- [ ] Release readiness approved
