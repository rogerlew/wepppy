# Tracker - Disturbed BD Override and Rosetta WC/FC Recompute

> Living document tracking progress, decisions, risks, and communication for this work package.

## Quick Status

**Started**: 2026-04-01  
**Current phase**: Completed / Closed  
**Last updated**: 2026-04-01  
**Next milestone**: None (package complete).

## Task Board

### Ready / Backlog
- [ ] None.

### In Progress
- [ ] None.

### Blocked
- [ ] None.

### Done
- [x] Created package scaffold (`package.md`, `tracker.md`, `prompts/active`, `prompts/completed`, `notes`, `artifacts`) (2026-04-01).
- [x] Authored initial active ExecPlan with implementation, test, and review milestones (2026-04-01).
- [x] Registered package in `PROJECT_TRACKER.md` backlog (2026-04-01).
- [x] Locked guidance: `wc => wp`, top-horizon-only recomputation, empty `bd` valid, malformed numeric `bd` hard-error (2026-04-01).
- [x] Captured bd-bounds precedent from WEPPpy docs and WEPP-Forest source for final policy selection (2026-04-01).
- [x] Confirmed disturbed `bd` bounds policy: `0.6-2.2 g/cm^3` developer-oriented margin (2026-04-01).
- [x] Added canonical disturbed lookup `bd` column after `avke` with blank defaults (2026-04-01).
- [x] Added disturbed mutation forwarding for Soils Rosetta toggle in both single-OFE + MOFE paths (2026-04-01).
- [x] Added Soils persisted property `rosetta_wc_fc_from_disturbed_bd_override` (+ stubs) (2026-04-01).
- [x] Added WEPP advanced-options themable checkbox with exact requested label and default unchecked wiring (2026-04-01).
- [x] Added rq-engine parsing/persistence for new boolean across `run-wepp`, `run-wepp-watershed`, and `prep-wepp-watershed` (2026-04-01).
- [x] Implemented top-horizon disturbed `bd` override + gated Rosetta `wp/fc` recomputation in `to_7778disturbed` and `to_over9000` (2026-04-01).
- [x] Added regression coverage for lookup schema, disturbed mutation forwarding, soils persistence, route persistence, render + controller payload serialization, and soil utility behavior (2026-04-01).
- [x] Completed mandatory `reviewer` + `qa_reviewer` passes with artifacts and resolved medium/high findings (2026-04-01).
- [x] Completed required validation gates and closed package docs (2026-04-01).
- [x] Revalidated closure gates and reran authenticated smoke command with `dev-agent` account label; no new medium/high review findings (2026-04-01).

## Timeline

- **2026-04-01** - Package created and scoped.
- **2026-04-01** - Active ExecPlan drafted with milestone-level validation and review gates.
- **2026-04-01** - Milestones 1-5 implemented (lookup/schema, soils persistence, UI/route wiring, disturbed Rosetta logic, regression tests).
- **2026-04-01** - Mandatory review passes completed; findings resolved and validations rerun.
- **2026-04-01** - Package closed and ExecPlan moved to `prompts/completed/`.
- **2026-04-01** - End-to-end revalidation run completed (required gates + authenticated smoke command + refreshed review artifacts).

## Decisions Log

### 2026-04-01: Use Soils NoDb as the source-of-truth for checkbox persistence
**Context**: The new checkbox must serialize to `soils.nodb` and be available during disturbed soil mutation after soils build.

**Options considered**:
1. Persist in browser-only state and attach ad hoc request flags.
2. Persist in Soils NoDb and parse through existing rq-engine WEPP request payload flow.
3. Persist in Disturbed NoDb even though control lives under WEPP Advanced Options soil settings.

**Decision**: Option 2.

**Impact**: State survives sessions and aligns with existing WEPP options persistence conventions.

---

### 2026-04-01: Keep checkbox rendering inside existing soil options include using shared pure macros
**Context**: Control must be themable and consistent with WEPP advanced options UI contracts.

**Options considered**:
1. Raw HTML checkbox in a new template fragment.
2. `ui.checkbox_field(...)` in existing `clip_soils_depth.htm` include.
3. JavaScript-injected control outside server-rendered templates.

**Decision**: Option 2.

**Impact**: Inherits theming, accessibility, and form serialization behavior with minimal divergence.

---

### 2026-04-01: Treat code review and QA review as mandatory closure gates
**Context**: User requested explicit code + QA review in the work-package.

**Options considered**:
1. Manual self-review only.
2. Dedicated reviewer + qa_reviewer subagent passes with artifact capture and findings closure.

**Decision**: Option 2.

**Impact**: Package closure requires review artifacts and remediation evidence.

---

### 2026-04-01: Lock wc/wp terminology and top-horizon-only recomputation scope
**Context**: User clarified requested semantics for moisture recomputation and wildfire modeling intent.

**Options considered**:
1. Interpret `wc` ambiguously and leave scope open.
2. Map `wc` to WEPP `wp`, recompute `wp`/`fc`, and limit recomputation to top horizon only.

**Decision**: Option 2.

**Impact**: Implementation and tests will model pre-vs-post wildfire effects using top-horizon-only disturbed `bd` override + Rosetta recomputation.

---

### 2026-04-01: Accept empty bd cells and fail hard on malformed numeric content
**Context**: User provided explicit behavior for lookup `bd` parsing.

**Options considered**:
1. Treat malformed `bd` as warning/no-op.
2. Treat empty as valid no-op and malformed numeric content as hard error.

**Decision**: Option 2.

**Impact**: CSV rows with blank `bd` remain valid and backward compatible; malformed numeric text (for example `10.0.0`) fails closed.

---

### 2026-04-01: Record bd bounds precedent from WEPPpy and WEPP-Forest
**Context**: User requested codebase + `wepp-forest` precedent for bounds.

**Options considered**:
1. Use only WEPPpy docs precedent (`0.8-2.0 g/cm^3` realistic range).
2. Use only WEPP-Forest computed clamp precedent (`1.0-1.8 g/cm^3`).
3. Keep both as references and require explicit policy choice for disturbed override validation.

**Decision**: Option 3.

**Impact**: Implementation can proceed with parse/format behavior now; exact enforced numeric bound remains the only unresolved guidance item.

---

### 2026-04-01: Adopt developer-oriented disturbed bd bounds `0.6-2.2 g/cm^3`
**Context**: User requested margin on both ends for development-oriented override workflows.

**Options considered**:
1. Strict realistic docs range `0.8-2.0 g/cm^3`.
2. WEPP-Forest computed clamp range `1.0-1.8 g/cm^3`.
3. Wider developer-oriented range `0.6-2.2 g/cm^3`.

**Decision**: Option 3.

**Impact**: Validation is intentionally permissive for developer experimentation while still enforcing finite numeric bounds.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Ambiguity in `wc/fc` vs `wc/fs` wording leads to wrong parameter recomputation | High | Medium | Freeze terminology before implementation and codify in tests/plan | Closed |
| Rosetta recomputation can fail for invalid override values | Medium | Medium | Enforce hard error for malformed numeric text and bounds `0.6-2.2 g/cm^3`; add tests | Closed |
| Cross-layer persistence drift (template -> JS -> rq-engine -> Soils NoDb) | Medium | Medium | Add focused tests for each layer and end-to-end payload persistence assertions | Closed |
| Lookup schema update could break existing edited lookup CSVs | Medium | Low | Keep additive schema-upgrade path and assert header order/compatibility in tests | Closed |

## Verification Checklist

### Code Quality
- [x] `wctl run-pytest tests/nodb/mods/disturbed/test_lookup_contract.py --maxfail=1`
- [x] `wctl run-pytest tests/nodb/mods/disturbed/test_modify_soils_single_ofe.py tests/nodb/mods/disturbed/test_modify_soils_mofe.py --maxfail=1`
- [x] `wctl run-pytest tests/wepp/soils/utils/test_wepp_soil_util.py --maxfail=1`
- [x] `wctl run-pytest tests/microservices/test_rq_engine_wepp_routes.py tests/microservices/test_rq_engine_soils_routes.py --maxfail=1`
- [x] `wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py --maxfail=1`
- [x] `wctl run-npm lint`
- [x] `wctl run-npm test -- wepp`
- [x] `wctl run-stubtest wepppy.wepp.soils.utils.wepp_soil_util`
- [x] `wctl run-stubtest wepppy.nodb.core.soils`
- [x] `wctl check-test-stubs`
- [x] `wctl run-pytest tests --maxfail=1`
- [x] `SMOKE_BASE_URL=https://wc.bearhive.duckdns.org SMOKE_SITE_PREFIX=/weppcloud SMOKE_AGENT_ACCOUNT_LABEL=dev-agent SMOKE_AGENT_REQUIRED=true wctl run-playwright --suite full --grep "weppcloud profile|runs0 dashboard|axe accessibility" --workers 1` (`4 passed`, `2 skipped`)

### Documentation
- [x] ExecPlan `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` updated through implementation.
- [x] Package docs (`package.md`, `tracker.md`, completed ExecPlan) doc-lint clean.
- [x] `PROJECT_TRACKER.md` status transitions updated at start/in-progress/closure milestones.

### Testing
- [x] Lookup schema upgrade tests cover additive `bd` column migration and no-data defaults.
- [x] Disturbed soil tests cover numeric `bd` override application and non-numeric/no-op behavior.
- [x] Rosetta recomputation tests cover enabled/disabled toggle and bd-override dependency.
- [x] Route/controller/template tests cover checkbox render, payload serialization, and persistence.

### Review Gates
- [x] Code review artifact authored at `artifacts/code_review_findings.md`.
- [x] QA review artifact authored at `artifacts/qa_review_findings.md`.
- [x] Medium/high findings resolved and documented with validation reruns.

## Progress Notes

### 2026-04-01: Package scoping and execution-plan authoring
**Agent/Contributor**: Codex

**Work completed**:
- Created package scaffold and authored brief/tracker/active ExecPlan.
- Mapped affected files and test suites across disturbed, soils, rq-engine, WEPP controls, and controller JS.
- Captured explicit guidance questions needed before execution hardens behavior contracts.

**Blockers encountered**:
- None for planning/scoping.

**Next steps**:
- Freeze guidance decisions with user.
- Execute Milestone 1 and update tracker + ExecPlan live sections as implementation proceeds.

**Test results**: Not run (planning-only session).

### 2026-04-01: Guidance refinement for bd parsing and bounds precedent
**Agent/Contributor**: Codex

**Work completed**:
- Updated package, tracker, active ExecPlan, and guidance notes with confirmed parsing behavior:
  - blank `bd` accepted as no override
  - malformed numeric `bd` content hard-fails
- Searched `/home/workdir/wepppy` and `/home/workdir/wepp-forest` for bounds precedent and documented both:
  - WEPPpy docs realistic Rosetta input range `0.8-2.0 g/cm^3`
  - WEPP-Forest consolidated BD clamp `1.0-1.8 g/cm^3`

**Blockers encountered**:
- No blockers for guidance updates.

**Next steps**:
- Begin Milestone 1 implementation.

**Test results**: `wctl doc-lint --path docs/work-packages/20260401_disturbed_bd_rosetta_wc_fc` (pass).

### 2026-04-01: Implementation + validation + closure
**Agent/Contributor**: Codex

**Work completed**:
- Implemented disturbed lookup schema/data changes (`bd` added after `avke`) and additive upgrade coverage.
- Implemented soils/rq-engine/ui wiring for `rosetta_wc_fc_from_disturbed_bd_override` persistence.
- Implemented strict disturbed `bd` parse/bounds behavior and top-horizon-only override + Rosetta `wp/fc` recomputation in soil utilities.
- Added/updated tests across disturbed, soils, rq-engine, WEPP template rendering, controller payload serialization, and soils.nodb persistence.
- Ran mandatory independent `reviewer` and `qa_reviewer` passes and resolved all medium/high findings.
- Updated package docs, authored review artifacts, and moved ExecPlan to completed.

**Review findings resolved**:
- Stub/type-contract drift resolved by updating `wepp_soil_util.pyi` and `soils.pyi`; stubtests now pass.
- `to_over9000` positional compatibility preserved by keeping `version` before new optional toggle parameter.
- Strict non-empty non-numeric `bd` validation enforced (for example `10.0.0`, `none` now hard-fail).
- Added missing 7778 forwarding and Soils serialization persistence tests.

**Validation results**:
- Targeted pytest pass: `138 passed`.
- Post-finding targeted pytest pass: `154 passed`.
- Full suite pass: `wctl run-pytest tests --maxfail=1` -> `2952 passed, 36 skipped`.
- Frontend gates: `wctl run-npm lint` (pass), `wctl run-npm test -- wepp` (pass).
- Stub gates: `wctl check-test-stubs` (pass), `wctl run-stubtest wepppy.wepp.soils.utils.wepp_soil_util` (pass), `wctl run-stubtest wepppy.nodb.core.soils` (pass).
- Docs gate: `wctl doc-lint --path docs/work-packages/20260401_disturbed_bd_rosetta_wc_fc` (pass).

**Blockers encountered**:
- None.

**Next steps**:
- None. Package complete.

### 2026-04-01: End-to-end revalidation + authenticated smoke rerun
**Agent/Contributor**: Codex

**Work completed**:
- Verified current implementation still satisfies package success criteria without code drift.
- Re-ran all required targeted test/lint/stub gates from the closure checklist.
- Ran required Playwright smoke command using `SMOKE_AGENT_ACCOUNT_LABEL=dev-agent` and `SMOKE_AGENT_REQUIRED=true`.
- Performed independent code-review and QA-review revalidation passes and refreshed both findings artifacts.

**Validation results**:
- Targeted backend/frontend/stub gates all pass (same command set listed in Verification Checklist).
- Smoke command result: `4 passed`, `2 skipped` (`weppcloud profile`, `runs0 dashboard`).

**Blockers encountered**:
- The target host (`https://wc.bearhive.duckdns.org/weppcloud`) did not render a local email/password login form for the smoke harness and auth probe returned `401`, so two auth-required scans were skipped.

**Next steps**:
- None for package scope; treat remote auth-form availability as an environment risk for future fully-authenticated smoke coverage.

## Watch List

- Disturbed lookup schema remains additive and preserves edited run-scoped tables.
- Rosetta branch does not alter non-disturbed or non-override paths.
- Checkbox default stays `false` for backward-compatible behavior.

## Communication Log

### 2026-04-01: Work-package request for disturbed bd override + Rosetta wc/fc option
**Participants**: User, Codex  
**Question/Topic**: Author a work-package to implement disturbed `bd` override, WEPP advanced checkbox persistence, Rosetta recomputation behavior, and mandatory test/review execution.  
**Outcome**: New package created with active ExecPlan, tracker, validation gates, and guidance questions for end-to-end execution.
