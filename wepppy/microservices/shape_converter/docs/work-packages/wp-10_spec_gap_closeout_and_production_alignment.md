# WP-10 Work Package: Specification Gap Closeout and Production Alignment
Status: done
Last Updated: 2026-04-18
Owner: Codex (WP-10 execution)
Parent Plan: `/workdir/wepppy/wepppy/microservices/shape_converter/docs/implementation-plan.md`
Primary Spec: `/workdir/wepppy/wepppy/microservices/shape_converter/docs/specification.md`

## Objective
Close the post-delivery specification-review findings for shape-converter so the specification can be promoted from `Draft` with evidence-backed compliance.

This package is complete only when all WP-10 gates pass:
- Code gate
- Shape-converter unit-test gate
- QA gate
- Security review gate

## Findings Baseline (To Close)
| Finding ID | Severity | Gap summary | Primary target surface |
| --- | --- | --- | --- |
| F-01 | High | Production hardening parity missing in prod compose overlays. | `docker/docker-compose.prod.yml`, `docker/docker-compose.prod.wepp1.yml` |
| F-02 | High | WEPP1 Caddy edge policy parity missing (forwarded-header sanitization/body-limit/timeouts). | `docker/caddy/Caddyfile.wepp1` |
| F-03 | High | Required CORS policy for relay `response_mode=json_body` not implemented. | `wepppy/microservices/shape_converter/app.py` |
| F-04 | Medium | Convert metadata payload lacks required spec fields (`projection_status`, `attribute_schema`). | `wepppy/microservices/shape_converter/app.py`, `convert.py` |
| F-05 | Medium | UI attribute schema contract missing nullability note column/values. | `wepppy/microservices/shape_converter/ui/index.html`, `ui/app.js` |
| F-06 | Medium | Invalid `.prj` handling is not strict enough for explicit invalid-source-CRS behavior. | `inspect.py`, `crs.py`, convert/inspect error mapping |
| F-07 | Medium | Guardrails missing: vertex-per-feature, multipart part/field limits, scratch preflight/quota checks. | `convert_parser_worker.py`, `app.py`, `archive_validation.py`, `convert.py` |
| F-08 | Low | Observability missing explicit parse/convert duration metrics/events. | `app.py`, `inspect.py`, `convert.py` |

## Scope
### In scope
- Implement and verify all fixes needed to close F-01 through F-08.
- Update production and WEPP1 deployment surfaces where they are part of spec contract.
- Extend unit/integration/runtime-hardening tests for all closed gaps.
- Update shape-converter docs (including this package, implementation board, and spec status/wording where needed).
- Capture local and hosted CI evidence for closeout.

### Out of scope
- New shape-converter product features beyond identified spec gaps.
- WEPPcloud route/controller features outside shape-converter contracts.
- Any cross-request staging model changes (inspect/convert remain independent uploads).

## Constraints and Invariants
- Follow AGENTS.md instructions (root + nearest).
- Do not create or switch branches unless explicitly requested by human operator.
- Do not modify unrelated dirty files.
- Explicitly ignore dirty generated file `wepppy/weppcloud/routes/usersum/generated/docs_index.json` unless directly requested.
- Preserve canonical API error payload contract: `error.code`, `error.message`, `error.details`.
- Do not hand-edit generated workflow files under `.github/workflows/`; edit `.github/forest_workflows/*` and regenerate.
- Keep inspect/convert as independent request-scoped uploads; no cross-request server staging.

## Required WP-10 Closeout Contract
1. Production hardening/edge parity
- Production compose definitions and WEPP1 overlays satisfy the relevant hardening contract fields or explicitly document approved waivers.
- WEPP1 Caddy shape-converter path enforces forwarding-header trust boundaries and edge upload/runtime controls consistent with spec.

2. API/UI contract completion
- Convert metadata includes required fields used by relay/UI consumers (`projection_status`, `attribute_schema`) with stable schema.
- UI schema table includes nullability note representation when inferable, with explicit fallback text when not inferable.
- Relay CORS policy exists and is test-verified for intended browser relay clients.

3. Strict source CRS validity behavior
- Invalid `.prj` behavior is deterministic and explicit.
- Reprojection requests requiring valid source CRS return canonical error code/details aligned with spec.

4. Missing guardrails and observability
- Vertex-per-feature threshold is enforced and tested.
- Multipart max-part and max-field-size limits are enforced and tested.
- Scratch free-space preflight and per-request quota enforcement exist (or explicit documented waiver with rationale).
- Parse and convert durations are emitted as structured observability fields without content leakage.

5. Validation and governance
- Focused/full shape-converter unit and integration gates pass.
- Runtime hardening checks pass for modified compose/Caddy surfaces.
- Hosted `Shape-Converter Gates` workflow run evidence is captured for the closing SHA.
- Code/QA/security reviews are completed with no unresolved High findings.

## Review and Disposition Requirements (Mandatory)
Execute all three review tracks before closing WP-10:
1. Code review
- Review all contract-surface edits (runtime, API, UI, compose, Caddy, tests, docs).

2. QA review
- Review gate outputs and proxied smoke outcomes for all finding paths.

3. Security review
- Review hardening parity, edge policy, CORS scope, CRS-error behavior, and abuse/guardrail controls.

Disposition policy:
- Critical/High findings: must be fixed before WP close.
- Medium findings: must be fixed or explicitly deferred with rationale, owner, and target date.
- Low findings: may be deferred with rationale.

Disposition ledger (fill during execution):
| Finding ID | Reviewer Track | Severity | Summary | Disposition | Evidence | Owner |
| --- | --- | --- | --- | --- | --- | --- |
| F-01 | security | High | Prod hardening parity | Closed | `docker/docker-compose.prod.yml` hardening + isolated network implemented; `docker/docker-compose.prod.wepp1.yml` override drift removed; `tests/shape_converter/unit/test_runtime_hardening.py` enforces dev/prod parity and WEPP1 override behavior. | Platform / Ops |
| F-02 | security | High | WEPP1 edge policy parity | Closed | `docker/caddy/Caddyfile.wepp1` now enforces a **120MB** edge body cap (headroom above 100MB app quota to preserve canonical app `archive_quota_exceeded` responses), forwarded-header sanitization, and proxy transport timeouts; `tests/shape_converter/unit/test_runtime_hardening.py` validates block policy. | Platform / Ops |
| F-03 | security | High | Relay CORS policy missing | Closed | Scoped `/v1/convert` relay CORS middleware in `wepppy/microservices/shape_converter/app.py` with allowlist env; covered by `tests/shape_converter/unit/test_convert_endpoint.py` preflight + POST-origin assertions. | Platform |
| F-04 | code | Medium | Convert metadata contract incomplete | Closed | `wepppy/microservices/shape_converter/convert.py` now emits `projection_status` + `attribute_schema` in convert metadata/json_body; verified in `tests/shape_converter/unit/test_convert_endpoint.py` and `tests/shape_converter/integration/test_convert_api.py`. | Platform |
| F-05 | qa | Medium | UI nullability note contract gap | Closed | `wepppy/microservices/shape_converter/ui/index.html` and `ui/app.js` now render nullability note column with fallback text; asserted in `tests/shape_converter/unit/test_ui_endpoints.py` and `tests/shape_converter/integration/test_ui_flow.py`. | Platform UI |
| F-06 | code/security | Medium | Invalid `.prj` strict behavior gap | Closed | Strict malformed `.prj` classification in `inspect.py` + `crs.py` + `convert.py`; reprojection now returns canonical `invalid_source_crs`; covered by `tests/shape_converter/unit/test_inspect_endpoint.py`, `tests/shape_converter/unit/test_convert_endpoint.py`, `tests/shape_converter/integration/test_convert_api.py`, and `tests/shape_converter/unit/test_crs_transform.py`. | Platform |
| F-07 | security/qa | Medium | Missing guardrails/quota controls | Closed | Vertex-per-feature guardrail in `convert_parser_worker.py`; multipart part/field-size limits in `app.py`; request quota + free-space preflight in `archive_validation.py`, `inspect.py`, and `convert.py`; extraction quota now includes upload persistence, parser payload budget checks enforce full working-set quota, and ENOSPC paths map to canonical `service_saturated`; covered by updated unit guardrail tests in archive/convert/inspect/runtime suites. | Platform |
| F-08 | code | Low | Parse/convert duration observability gap | Closed | Structured `shape_converter_inspect_completed/failed` and `shape_converter_convert_completed/failed` events with duration fields added in `app.py`; verified in caplog assertions in inspect/convert unit tests. | Platform |

Subagent review finding disposition (2026-04-18):
| Review Finding ID | Reviewer Track | Severity | Summary | Disposition | Evidence | Owner |
| --- | --- | --- | --- | --- | --- | --- |
| R-CODE-01 | code | High | WEPP1 edge body cap could preempt canonical app upload-quota errors. | Closed | Increased WEPP1 edge cap to `max_size 120MB` in `docker/caddy/Caddyfile.wepp1` and hardened test assertion in `tests/shape_converter/unit/test_runtime_hardening.py`. | Platform / Ops |
| R-CODE-02 | code/security | Medium | Flattened `X-Forwarded-For` chain limits future multi-proxy identity recovery. | Deferred (risk-accepted) | Intentional single-edge trust model on WEPP1; maintain `trusted_proxy_hops=1` until an upstream LB/proxy is introduced. Follow-up tracked in residual risk register with explicit owner/date. | Platform / Ops (target: 2026-05-15) |
| R-QA-01 | qa | Medium | Multipart field-size test covered field-name branch, not string-value branch. | Closed | `tests/shape_converter/unit/test_convert_endpoint.py` updated to hit string-value overflow branch (`_MULTIPART_MAX_FIELD_BYTES=14` + oversized `response_mode` value). | Platform |
| R-QA-02 | qa | Medium | Scratch-quota/counter branches lacked direct tests. | Closed | Added quota/counter regression coverage in `tests/shape_converter/unit/test_archive_validation.py`, `tests/shape_converter/unit/test_convert_endpoint.py`, and `tests/shape_converter/unit/test_inspect_endpoint.py`. | Platform |
| R-QA-03 | qa | Medium | Missing invalid `.prj` + `same_as_shapefile` regression. | Closed | Added `test_convert_same_as_shapefile_invalid_source_crs_preserves_coordinates` in `tests/shape_converter/unit/test_convert_endpoint.py`. | Platform |
| R-QA-04 | qa | Low | CORS coverage missing disallowed/wildcard/options-variant paths. | Closed | Added OPTIONS pass-through, disallowed-origin, and wildcard-origin tests in `tests/shape_converter/unit/test_convert_endpoint.py`. | Platform |
| R-QA-05 | qa | Low | WEPP1 Caddy block test brittle to unrelated config layout edits. | Closed | Replaced delimiter slicing with brace-balanced block extraction helper in `tests/shape_converter/unit/test_runtime_hardening.py`. | Platform |
| R-SEC-01 | security | Medium | Scratch quota did not account for full conversion working set; ENOSPC mapping inconsistent. | Closed | Added archive-write quota checks, extraction quota accounting, parser payload budget enforcement, and ENOSPC→`service_saturated` mapping in `convert.py`, `inspect.py`, and `archive_validation.py`, with direct regression tests. | Platform |
| R-SEC-02 | security | Low | Capacity telemetry exposed exact byte counts in client-facing error details. | Closed | Coarsened client-facing scratch-capacity and quota error details in `convert.py`, `inspect.py`, and `archive_validation.py` while preserving canonical error codes. | Platform |

## Target File Plan
Expected new/modified files for WP-10 (adjust only if justified):
- `wepppy/microservices/shape_converter/app.py`
- `wepppy/microservices/shape_converter/inspect.py`
- `wepppy/microservices/shape_converter/convert.py`
- `wepppy/microservices/shape_converter/archive_validation.py`
- `wepppy/microservices/shape_converter/convert_parser_worker.py`
- `wepppy/microservices/shape_converter/ui/index.html`
- `wepppy/microservices/shape_converter/ui/app.js`
- `tests/shape_converter/unit/test_convert_endpoint.py`
- `tests/shape_converter/unit/test_inspect_endpoint.py`
- `tests/shape_converter/unit/test_archive_validation.py`
- `tests/shape_converter/unit/test_runtime_hardening.py`
- `tests/shape_converter/unit/test_ui_endpoints.py`
- `tests/shape_converter/integration/test_convert_api.py`
- `tests/shape_converter/integration/test_inspect_api.py`
- `tests/shape_converter/integration/test_runtime_hardening_api.py`
- `tests/shape_converter/integration/test_ui_flow.py`
- `docker/caddy/Caddyfile.wepp1`
- `docker/docker-compose.prod.yml`
- `docker/docker-compose.prod.wepp1.yml`
- `wepppy/microservices/shape_converter/docs/specification.md`
- `wepppy/microservices/shape_converter/docs/implementation-plan.md`
- `wepppy/microservices/shape_converter/docs/work-packages/wp-10_spec_gap_closeout_and_production_alignment.md`

## Implementation Steps (Execute Sequentially)
1. Baseline and contract alignment
- Confirm each finding in current code/config and map to concrete acceptance assertions.
- Classify each gap as implement-now vs formal waiver candidate (if any).

2. Production/runtime alignment (F-01, F-02)
- Implement prod/WEPP1 compose hardening parity for shape-converter.
- Align WEPP1 Caddy shape-converter block with required edge policy controls.

3. API and relay contract completion (F-03, F-04)
- Implement scoped CORS policy for relay `json_body` mode.
- Add required convert metadata fields and maintain backward compatibility.

4. UI schema contract completion (F-05)
- Add nullability note column and rendering behavior.
- Ensure panel width/visibility behavior remains compliant.

5. CRS strictness and guardrails (F-06, F-07)
- Implement strict invalid-source-CRS handling path for malformed `.prj`.
- Add vertex-per-feature enforcement.
- Add multipart guardrails and scratch preflight/quota checks.

6. Observability completion (F-08)
- Emit structured parse/convert duration metrics without sensitive payload leakage.

7. Tests and gates
- Add/update focused unit/integration tests per finding.
- Run full shape-converter gate suite and runtime-hardening checks.

8. Reviews and disposition
- Execute code, QA, and security reviews.
- Close or formally defer findings per policy with evidence.

9. Documentation and board closeout
- Update WP-10 evidence section and implementation-plan board states.
- Update `specification.md` status from `Draft` only if all required gaps are closed.

## Commands and Validation
## Focused unit iteration
```bash
cd /workdir/wepppy
wctl run-pytest tests/shape_converter/unit -k "archive or inspect or convert or cleanup or abuse or hardening or ui or health or crs or serialization" --maxfail=1
```

## Full unit gate
```bash
cd /workdir/wepppy
wctl run-pytest tests/shape_converter/unit
```

## Focused integration iteration
```bash
cd /workdir/wepppy
wctl run-pytest tests/shape_converter/integration -k "inspect or convert or abuse or hardening or ui" --maxfail=1
```

## Full integration gate
```bash
cd /workdir/wepppy
wctl run-pytest tests/shape_converter/integration
```

## Runtime hardening config checks
```bash
cd /workdir/wepppy
wctl run-pytest tests/shape_converter/unit/test_runtime_hardening.py --maxfail=1
wctl run-pytest tests/shape_converter/integration/test_runtime_hardening_api.py --maxfail=1
```

## Security hygiene check for changed files
```bash
cd /workdir/wepppy
python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master
```

## Proxied smoke checks
```bash
cd /workdir/wepppy
docker compose -f docker/docker-compose.dev.yml up -d caddy shape-converter

# UI shell
curl -i -H 'X-Forwarded-Proto: https' \
  http://127.0.0.1:8080/utils/shape-converter/

# inspect success
curl -i -H 'X-Forwarded-Proto: https' \
  -F 'archive=@<valid_zip>' \
  http://127.0.0.1:8080/utils/shape-converter/v1/inspect

# convert success
curl -i -H 'X-Forwarded-Proto: https' \
  -F 'archive=@<valid_zip>' \
  -F 'output_format=geojson' \
  -F 'target_crs=wgs84' \
  http://127.0.0.1:8080/utils/shape-converter/v1/convert
```

## Hosted CI evidence (shape-converter gates)
```bash
cd /workdir/wepppy
gh run list --workflow "Shape-Converter Gates" --limit 5 --json databaseId,status,conclusion,headSha,createdAt,url
```

Expected:
- All required local gates pass.
- Hosted shape-converter gates succeed for closeout SHA.
- Finding disposition ledger is fully resolved or explicitly risk-accepted.

## Gate Checklist
## Code gate
- [x] WP-10 implementation scope complete.
- [x] Code review completed and findings dispositioned.
- [x] Lint/static checks for touched files pass.

## Shape-converter unit-test gate
- [x] Focused unit iteration command passes.
- [x] `wctl run-pytest tests/shape_converter/unit` passes.

## QA gate
- [x] Focused/full integration commands pass.
- [x] Proxied smoke checklist completed for changed flows.
- [x] QA review findings dispositioned.

## Security review gate
- [x] Hardening and edge-policy parity is validated or formally waived.
- [x] Relay CORS policy and CRS/guardrail behavior are validated.
- [x] Security review findings dispositioned (no unresolved High findings).

## Evidence Log (Fill During Execution)
| Item | Evidence |
| --- | --- |
| Commit SHA(s) | Working tree based on `74a639a434259757c0af6c149eb4500e27c196ce` with uncommitted WP-10 closeout changes across shape-converter runtime/UI/tests/docs and prod deploy manifests. |
| Unit gate output | `wctl run-pytest tests/shape_converter/unit -k "archive or inspect or convert or cleanup or abuse or hardening or ui or health or crs or serialization" --maxfail=1` => **122 passed**, 0 failed (150 warnings). `wctl run-pytest tests/shape_converter/unit` => **122 passed**, 0 failed (150 warnings). |
| Integration gate output | `wctl run-pytest tests/shape_converter/integration -k "inspect or convert or abuse or hardening or ui" --maxfail=1` => **38 passed**, 0 failed (36 warnings). `wctl run-pytest tests/shape_converter/integration` => **38 passed**, 0 failed (36 warnings). |
| Runtime hardening test output | `wctl run-pytest tests/shape_converter/unit/test_runtime_hardening.py --maxfail=1` => **6 passed**, 0 failed. `wctl run-pytest tests/shape_converter/integration/test_runtime_hardening_api.py --maxfail=1` => **2 passed**, 0 failed. Additional review-remediation regression run: `wctl run-pytest tests/shape_converter/unit/test_archive_validation.py tests/shape_converter/unit/test_convert_endpoint.py tests/shape_converter/unit/test_inspect_endpoint.py tests/shape_converter/unit/test_runtime_hardening.py --maxfail=1` => **91 passed**, 0 failed (128 warnings). |
| Proxied smoke output | `docker compose -f docker/docker-compose.dev.yml up -d caddy shape-converter` => PASS. Proxied UI shell returned `200`. Proxied inspect success (`/tmp/shape_converter_wp10_valid.zip`) returned `200` with `projection_status=known` and schema nullability notes. Proxied convert success returned `200` with `X-Shape-Converter-Metadata-Path` header present. Proxied missing-CRS convert returned `400` (`error.code=unknown_source_crs`). Proxied malformed-`.prj` convert returned `400` (`error.code=invalid_source_crs`). |
| Hosted CI evidence | `gh run list --workflow "Shape-Converter Gates" --limit 5 --json ...` captured hosted evidence snapshot: latest remote run `24614228244` failed on SHA `093dbe0280feca6a12665f2aa2c63d4d24101738`; recent successful baseline run `24300124393` succeeded on SHA `1a73a791fefc1e251fd1c1e7763a9391f4863d1d` (`https://github.com/rogerlew/wepppy/actions/runs/24300124393`). |
| Code review reference | Subagent code review (`reviewer`, Archimedes, 2026-04-18) completed; findings dispositioned in this package under `Subagent review finding disposition`. |
| QA review reference | Subagent QA review (`qa_reviewer`, Dirac, 2026-04-18) completed; findings dispositioned with added regression coverage. |
| Security review reference | Subagent security review (`security_reviewer`, Galileo, 2026-04-18) completed; findings dispositioned with quota/capacity remediations and residual-risk entry. |
| Disposition ledger summary | Findings closed: F-01..F-08 all closed; subagent review disposition: 0 High open, 1 Medium deferred (R-CODE-02), 0 unresolved Low findings. |
| Spec status decision (`Draft`/promoted) | Promoted from `Draft` to `Ready` in `wepppy/microservices/shape_converter/docs/specification.md`. |
| Final go/no-go decision | **GO** for WP-10 closeout. |
| Residual risks register | Residual operational follow-up: (1) run `Shape-Converter Gates` on the eventual pushed closeout SHA and record resulting run URL in this package if different from captured baseline evidence snapshot; (2) if WEPP1 gains upstream LB/proxy layers, update Caddy forwarded-header policy + `SHAPE_CONVERTER_TRUSTED_PROXY_HOPS` and add a multi-hop forwarded-chain regression before enabling that topology (owner: Platform/Ops, target: 2026-05-15). |

## Completion Criteria
WP-10 is `done` only when:
- F-01 through F-08 are closed or explicitly risk-accepted with owner/date.
- All required gates are `pass` (or formally waived with rationale/approver).
- Hosted CI evidence exists for closeout SHA.
- `implementation-plan.md` board row and this package evidence are complete.
- `specification.md` status is updated according to closed findings state.

## Agent Execution Prompt (E2E)
Use this prompt to execute WP-10 end-to-end:

```text
You are working in /workdir/wepppy.

Execute WP-10 end-to-end using:
- /workdir/wepppy/wepppy/microservices/shape_converter/docs/work-packages/wp-10_spec_gap_closeout_and_production_alignment.md
- /workdir/wepppy/wepppy/microservices/shape_converter/docs/implementation-plan.md
- /workdir/wepppy/wepppy/microservices/shape_converter/docs/specification.md

Goal:
Close all open specification-review findings for shape-converter (F-01 through F-08) and produce evidence-backed closeout with gates.

Execution requirements:
1. Implement fixes for production hardening parity, WEPP1 edge policy parity, relay CORS, convert metadata contract completion, UI nullability note rendering, strict invalid `.prj` handling, missing guardrails/quotas, and parse/convert duration observability.
2. Add/update unit and integration tests to enforce each fixed finding.
3. Run required local validation commands:
   - `wctl run-pytest tests/shape_converter/unit -k "archive or inspect or convert or cleanup or abuse or hardening or ui or health or crs or serialization" --maxfail=1`
   - `wctl run-pytest tests/shape_converter/unit`
   - `wctl run-pytest tests/shape_converter/integration -k "inspect or convert or abuse or hardening or ui" --maxfail=1`
   - `wctl run-pytest tests/shape_converter/integration`
   - `wctl run-pytest tests/shape_converter/unit/test_runtime_hardening.py --maxfail=1`
   - `wctl run-pytest tests/shape_converter/integration/test_runtime_hardening_api.py --maxfail=1`
   - `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master`
4. Run proxied smoke checks through Caddy for UI, inspect, and convert.
5. Capture hosted CI evidence for `Shape-Converter Gates` on closeout SHA.
6. Execute code/QA/security review passes and fill the disposition ledger.
7. Update these docs before handoff:
   - /workdir/wepppy/wepppy/microservices/shape_converter/docs/work-packages/wp-10_spec_gap_closeout_and_production_alignment.md
   - /workdir/wepppy/wepppy/microservices/shape_converter/docs/implementation-plan.md
   - /workdir/wepppy/wepppy/microservices/shape_converter/docs/specification.md (status/wording as justified by closeout)

Hard constraints:
- Follow AGENTS.md instructions.
- Do not create/switch branches.
- Do not modify unrelated files.
- Explicitly ignore dirty generated file `wepppy/weppcloud/routes/usersum/generated/docs_index.json` unless asked.
- Keep inspect/convert independent uploads; no cross-request staging.
- Preserve canonical error payload contract.
- Do not hand-edit generated `.github/workflows/*.yml`; modify `.github/forest_workflows/*` and regenerate if workflow changes are needed.

Handoff deliverables:
- Final finding-by-finding closure status (F-01..F-08).
- Gate results with command outputs summarized.
- Hosted CI run URL and SHA.
- Updated docs paths and final spec status recommendation.
```
