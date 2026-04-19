# Shape Converter Implementation Plan
Status: Done
Last Updated: 2026-04-18
Owner: Platform / WEPPpy
Primary Spec: `/workdir/wepppy/wepppy/microservices/shape_converter/docs/specification.md`

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
- Parser dependency review includes GDAL/OGR vulnerability disposition for the release cut.
- Metadata-privacy review confirms `.shp.xml`/XML sidecar PII is blocked or sanitized from API/log outputs.

## Work-Package Board
| WP | Title | Depends On | State | Code Gate | Unit Gate | QA Gate | Security Gate | Evidence / Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| WP-00 | Repo scaffold and orchestration setup | none | done | pass | pass | pass | pass | This plan + specification moved under `wepppy/microservices/shape_converter/docs/` |
| WP-01 | Service scaffold and container wiring | WP-00 | done | pass | pass | pass | pass | Completed 2026-04-11. Evidence: `/workdir/wepppy/wepppy/microservices/shape_converter/docs/work-packages/wp-01_service_scaffold_container_wiring.md` (unit gate: 6/6 pass, Caddy smoke pass, negative namespace probe not proxied). |
| WP-02 | Inspect endpoint + ZIP/shapefile validation | WP-01 | done | pass | pass | pass | pass | Completed 2026-04-11. Evidence: `/workdir/wepppy/wepppy/microservices/shape_converter/docs/work-packages/wp-02_inspect_endpoint_zip_shapefile_validation.md` (unit gate pass, integration gate pass, proxied inspect smoke pass, traversal/symlink/encrypted/nested/quota controls verified). |
| WP-03 | Convert endpoint + CRS and format pipeline | WP-02 | done | pass | pass | pass | pass | Completed 2026-04-11. Evidence: `/workdir/wepppy/wepppy/microservices/shape_converter/docs/work-packages/wp-03_convert_endpoint_crs_format_pipeline.md` (convert endpoint implemented, CRS modes + GeoJSON/GeoParquet outputs covered, unit/integration gates pass, proxied convert smoke pass for success/canonical errors, security checks recorded). |
| WP-04 | Cleanup lifecycle and failure-path guarantees | WP-02, WP-03 | done | pass | pass | pass | pass | Completed 2026-04-12. Evidence: `/workdir/wepppy/wepppy/microservices/shape_converter/docs/work-packages/wp-04_cleanup_lifecycle_and_failure_path_guarantees.md` (request-scoped cleanup enforced on success/failure/timeout/cancel paths; stale-dir janitor constrained to owned directories; focused/full unit + integration gates pass; proxied Caddy cleanup smoke pass; code/QA/security review dispositions closed). |
| WP-05 | Public abuse controls and edge trust model | WP-01 | done | pass | pass | pass | pass | Completed 2026-04-12. Evidence: `/workdir/wepppy/wepppy/microservices/shape_converter/docs/work-packages/wp-05_public_abuse_controls_and_edge_trust_model.md` (trusted-hop client identity with IPv6 `/64` keying, per-IP rate + per-IP/global in-flight controls, read-timeout fast-fail, edge forwarding-header sanitation + body/transport timeouts, parser deny-egress Fiona/GDAL options, focused/full unit + integration gates pass, proxied Caddy smoke verifies baseline/throttle/spoof/saturation, code/QA/security dispositions closed). |
| WP-06 | UI implementation and metadata rendering | WP-02, WP-03 | done | pass | pass | pass | pass | Completed 2026-04-12. Evidence: `/workdir/wepppy/wepppy/microservices/shape_converter/docs/work-packages/wp-06_ui_implementation_and_metadata_rendering.md` (UI route + static assets under `/utils/shape-converter/`, metadata panels + warning callouts implemented, explicit `response_mode=download`/WP-06B defer messaging, focused/full unit + integration gates pass, proxied Caddy smoke verifies inspect/convert warning UX and abuse-control `429`/`503` guidance, code/QA/security dispositions closed). |
| WP-06B | Browser relay mode support (`json_body`) | WP-03, WP-06 | done | pass | pass | pass | pass | Completed 2026-04-12. Evidence: `/workdir/wepppy/wepppy/microservices/shape_converter/docs/work-packages/wp-06b_browser_relay_mode_json_body.md` (`response_mode=json_body` implemented for `output_format=geojson` with relay payload `{request_id, geojson, metadata}`; unsupported relay combinations return canonical `400 invalid_request`; `response_mode=download` compatibility preserved; focused/full unit + integration gates pass; proxied Caddy smoke verifies relay success + invalid-combination + download compatibility; code/QA/security dispositions closed). |
| WP-07 | Runtime hardening and sandbox enforcement | WP-01 | done | pass | pass | pass | pass | Completed 2026-04-12. Evidence: `/workdir/wepppy/wepppy/microservices/shape_converter/docs/work-packages/wp-07_runtime_hardening_and_sandbox_enforcement.md` (compose hardening enforced: rootless `10001`, `read_only`, `no-new-privileges`, `cap_drop=ALL`, pids/mem/cpu limits, hardened `tmpfs`; readiness now enforces required sandbox mode signaling + toolchain presence; dedicated internal `shape-converter-sandbox` network blocks outbound egress and limits east-west reachability; focused/full unit + hardening integration gates pass; proxied ready/inspect/convert smoke pass under hardened container; code/QA/security review dispositions closed). |
| WP-08 | Test suite completion and gate automation | WP-02, WP-03, WP-04, WP-05, WP-06, WP-06B, WP-07 | done | pass | pass | pass | pass | Completed 2026-04-12. Evidence: `/workdir/wepppy/wepppy/microservices/shape_converter/docs/work-packages/wp-08_test_suite_completion_and_gate_automation.md` (added parser-abuse regressions for XML entity-expansion classes and parser-stall timeout/cancellation, added `.shp.xml`/`.qmd` metadata-privacy non-leak assertions, added dedicated blocking shape-converter CI gate workflow, and passed focused/full unit+integration gates plus proxied Caddy smoke). |
| WP-09 | Final QA + security closeout + release readiness | WP-08 | done | pass | pass | pass | pass | Completed 2026-04-12 with **GO** decision and residual-risk tracking. Evidence: `/workdir/wepppy/wepppy/microservices/shape_converter/docs/work-packages/wp-09_final_qa_security_closeout_release_readiness.md`. Local focused/full unit + integration gates, workflow build/check, and proxied Caddy smoke all pass. Hosted shape-converter gate evidence captured: `Shape-Converter Gates` run `24298655324` success on `master` (`88b07b47ccda96c5ee836ca4af82db26ae727148`). Deferred WP-09 residual risks are now closed by WP-09B. |
| WP-09B | Parser containment + GDAL CVE remediation | WP-09 | done | pass | pass | pass | pass | Completed 2026-04-12. Evidence: `/workdir/wepppy/wepppy/microservices/shape_converter/docs/work-packages/wp-09b_parser_containment_and_gdal_cve_remediation.md`. Parser subprocess process-group timeout/kill semantics are implemented in convert runtime path and validated by new unit/integration tests. Runtime CVE disposition evidence captured: Fiona parser path now links system GDAL (`fiona.__gdal_version__=3.10.3`), proxied smoke and focused/full gates pass, and hosted `Shape-Converter Gates` run `24299367284` succeeded on remediation SHA `caa8edd8f92126c7570ea51cf1ab978f47c789d8`. |
| WP-10 | Specification gap closeout and production alignment | WP-09B | done | pass | pass | pass | pass | Completed 2026-04-18. Evidence: `/workdir/wepppy/wepppy/microservices/shape_converter/docs/work-packages/wp-10_spec_gap_closeout_and_production_alignment.md` (prod/WEPP1 hardening + edge-policy parity enforced; scoped relay CORS policy implemented and tested; convert metadata parity (`projection_status`, `attribute_schema`) and UI nullability-note rendering implemented; strict malformed `.prj` behavior now returns canonical `invalid_source_crs`; multipart/vertex/scratch guardrails + parse/convert duration observability added; focused/full unit + integration + hardening gates pass; proxied Caddy smoke pass for UI/inspect/convert + missing/invalid CRS paths). Hosted `Shape-Converter Gates` evidence captured in closeout package (`gh run list` snapshot includes recent success run `24300124393` and latest remote failure `24614228244` pending operator rerun on closeout SHA). |

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
- Enforce deny-all parser egress posture so conversion requests cannot perform remote fetches.

### Exit criteria
- Flood/slowloris tests pass with expected `429`/timeout behavior.
- Healthy traffic remains available under adversarial load.

## WP-06 UI implementation and metadata rendering
### Scope
- Implement UI for inspect and convert flows.
- Display attribute schema, projection details, warnings, geometry summary.
- Surface `.shp.xml` removal warnings with explicit advisory text that packing `.shp.xml` in shapefile ZIPs is generally not advisable.

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
- Pin and track parser dependency updates (GDAL/OGR stack) with explicit CVE triage evidence.
- Maintain parser vulnerability watchlist seeded with known GDAL cases (`CVE-2021-45943`, `CVE-2025-29480`).
- Enforce parser timeout/kill guarantees for malformed-input non-termination classes.

### Exit criteria
- Hardening verification tests pass.
- Service readiness fails when required sandbox mode is absent.

## WP-08 Test suite completion and gate automation
### Scope
- Complete shape-converter unit and integration test suites.
- Add security and performance gate commands to CI.
- Add parser abuse regression fixtures (XML entity expansion and parser-loop timeout classes).
- Add metadata-privacy regression fixtures proving `.shp.xml` PII is never surfaced.

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
- Residual-risk register explicitly records parser-CVE watchlist status and metadata-privacy posture.

## WP-09B Parser containment and GDAL CVE remediation
### Scope
- Implement explicit parser subprocess process-group timeout/cancel kill semantics in shape-converter runtime path.
- Remediate `CVE-2026-4738` risk for shape-converter GDAL runtime via upgrade or equivalent patch backport with verifiable evidence.
- Re-run full code/unit/QA/security gates and capture hosted CI evidence after remediation.

### Exit criteria
- Parser non-termination containment is implemented in production path and test-validated.
- Shape-converter runtime includes documented `CVE-2026-4738` mitigation evidence.
- Code/QA/security review findings are dispositioned (no unresolved High findings).
- WP-09B board row and evidence references are complete.

## WP-10 Specification gap closeout and production alignment
### Scope
- Close post-delivery specification-review findings that prevent promoting `specification.md` from `Draft`.
- Bring production deployment/runtime policy (`docker-compose.prod.yml`, `docker-compose.prod.wepp1.yml`, `docker/caddy/Caddyfile.wepp1`) to parity with required hardening/edge contracts where applicable.
- Implement missing API/UI contract fields and guardrails identified in review (convert metadata parity, UI schema nullability note, strict invalid-source-CRS handling, multipart/scratch/vertex guardrails, parse/convert duration observability).
- Add/extend tests and CI evidence so each closed finding is enforced by gates.

### Exit criteria
- All WP-10 findings are closed or formally waived with documented risk acceptance.
- WP-10 code/unit/QA/security gates are `pass`.
- `wepppy/microservices/shape_converter/docs/specification.md` status is updated from `Draft` only if all required gaps are closed.
- Implementation-plan board and WP-10 evidence are complete and auditable.

## Cadence and Update Rules
- Update this file at least once per work-package transition.
- Any gate failure must update gate state to `fail` with evidence link.
- If a gate is waived, add waiver rationale and approver in `Evidence / Notes`.
- Do not mark a work-package `done` unless all required gates are `pass` or formally waived.

## Rollup Checklist
- [x] WP-01 through WP-09B complete (including WP-06B)
- [x] WP-10 complete
- [x] WP-10 code gate passes
- [x] WP-10 shape-converter unit-test gate passes
- [x] WP-10 QA gate passes
- [x] WP-10 security review gate passes
- [x] Specification status updated from `Draft` after WP-10 closeout
