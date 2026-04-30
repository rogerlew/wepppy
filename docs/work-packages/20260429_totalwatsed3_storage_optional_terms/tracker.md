# Tracker - totalwatsed3 Storage and Optional Terms Contract Hardening

> Living execution log for additive storage/output-term contract work across WEPP-forest and WEPPpy.

## Quick Status

**Timezone**: UTC  
**Started**: 2026-04-29 22:10 UTC  
**Current phase**: Production rollout gate completed on wepp1; residual closure issue documented  
**Last updated**: 2026-04-30 04:09 UTC  
**Next milestone**: Decide whether the large H2637/H2809 runoff/closure residuals need a follow-up physics/data investigation package  
**Security impact**: `none`  
**Dedicated security review**: `no`  
**Security artifact**: `N/A`

## Task Board

### Ready / Backlog
- [ ] Decide follow-up scope for the large H2637/H2809 runoff/closure residuals and the 1996-02-06 event outlier.

### In Progress
- [ ] None.

### Blocked
- [ ] None.

### Done
- [x] Work-package scaffold created (`package.md`, `tracker.md`, `prompts/active`, `prompts/completed`, `artifacts`) (2026-04-29 22:10 UTC).
- [x] Cross-repo source anchors collected (`watbal.for`, `watbal_hourly.for`, `outfil.for`, interchange parsers, `totalwatsed3`, closure tool) (2026-04-29 22:10 UTC).
- [x] Active ExecPlan authored for phased implementation and validation (2026-04-29 22:10 UTC).
- [x] Root `PROJECT_TRACKER.md` registration completed (2026-04-29 22:10 UTC).
- [x] Optional term contract finalized with stakeholder input: `H.wat` optional columns `SoilWaterTotal`, `ProfileDepth`, `ProfilePorosityCap`, `ProfileFCStore`, `ProfileWPStore` in `mm` (2026-04-30 03:19 UTC).
- [x] WEPPpy WAT parser compatibility implemented with legacy-null optional terms and fail-fast unknown extra-column handling (2026-04-30 03:43 UTC).
- [x] WEPP-forest daily/hourly `H.wat` output writes extended with all five optional storage/capacity terms (2026-04-30 03:43 UTC).
- [x] `totalwatsed3` schema/aggregation/audit/docs/tests updated for optional storage terms (2026-04-30 03:43 UTC).
- [x] Required WEPPpy validation commands passed; WEPP-forest `make wepp wepp_hill` and host smoke checks passed (2026-04-30 03:43 UTC).
- [x] Independent review findings addressed: production-shaped `H.element` date join, `watbalprint.for` `ivers=3` widened rows, and audit command example fixed (2026-04-30 04:00 UTC).
- [x] Missing production-run blocker captured in `artifacts/production_run_missing_probe.md` (2026-04-30 03:43 UTC).
- [x] wepp1 production gate completed without container takedown; regenerated `totalwatsed3.parquet`, captured whole-run closure stats, and captured `H2637`/`H2809` reconciliation artifacts (2026-04-30 04:09 UTC).

## Timeline

- **2026-04-29 22:10 UTC** - Package created and scoped.
- **2026-04-29 22:10 UTC** - Cross-repo references and contract anchors recorded.
- **2026-04-30 03:19 UTC** - Optional-term contract finalized and recorded in spec/work-package docs.
- **2026-04-30 03:43 UTC** - Parser, producer, aggregation, audit, and docs/tests implemented and validated.
- **2026-04-30 03:43 UTC** - Closure audit rerun blocked because `uncapped-spectacular` is not mounted in this workspace.
- **2026-04-30 04:00 UTC** - Independent review findings fixed and required validation commands rerun successfully.
- **2026-04-30 04:09 UTC** - wepp1 production artifact regenerated and closure/reconciliation artifacts copied into the package.

## Decisions Log

### 2026-04-29 22:10 UTC: Keep this effort as a new package separate from runoff-basis hotfix
**Context**: Runoff-depth basis correction package is already closed and narrowly targeted.

**Options considered**:
1. Reopen and expand the closed runoff package.
2. Create a new package dedicated to storage-term and optional-column contract hardening.

**Decision**: Option 2.

**Impact**: Clear boundary between completed runoff bugfix and broader cross-repo contract work.

---

### 2026-04-29 22:10 UTC: Use additive optional columns only (no destructive rename/removal)
**Context**: Existing runs and consumers depend on legacy hillslope/totalwatsed schemas.

**Options considered**:
1. Replace or rename existing columns to force semantic clarity.
2. Add explicit optional columns while preserving legacy columns and null-safe behavior.

**Decision**: Option 2.

**Impact**: Backward compatibility is preserved while enabling improved storage observability.

---

### 2026-04-30 03:19 UTC: Adopt WEPP-aligned optional `H.wat` storage/capacity terms in mm
**Context**: Stakeholder requested terms that match WEPP variable naming semantics and should be authoritative from WEPP output.

**Options considered**:
1. Derive storage/capacity in WEPPpy from existing columns only.
2. Emit producer-authoritative optional terms from WEPP and parse them when available.

**Decision**: Option 2, using this additive term set and formulas:
`SoilWaterTotal (mm) = watcon + frozwt`, `ProfileDepth (mm) = solthk(nsl)`,
`ProfilePorosityCap (mm) = sum(por * dg)`, `ProfileFCStore (mm) = sum(thetfc * dg)`,
`ProfileWPStore (mm) = sum(thetdr * dg)`.

**Impact**: Storage diagnostics become explicit and reproducible with minimal consumer inference.

---

### 2026-04-30 03:19 UTC: Production gate anchored on `uncapped-spectacular` closure re-audit
**Context**: Stakeholders suspect possible water-balance issues and requested concrete production validation.

**Options considered**:
1. Limit validation to unit tests and synthetic fixtures.
2. Require production run re-audit for `uncapped-spectacular` as release gate.

**Decision**: Option 2.

**Impact**: Implementation is not complete until regenerated `totalwatsed3.parquet` and closure artifacts are captured for `/geodata/wc1/runs/un/uncapped-spectacular/...`.

---

### 2026-04-30 03:19 UTC: `totalwatsed3` must expose all five optional storage/capacity terms
**Context**: Need explicit downstream visibility for all producer-authoritative storage/capacity terms, not a subset.

**Options considered**:
1. Expose only a subset in `totalwatsed3` and keep others in hillslope-only artifacts.
2. Expose all five directly in `totalwatsed3` when available.

**Decision**: Option 2.

**Impact**: `totalwatsed3` schema/aggregation updates must include:
`SoilWaterTotal`, `ProfileDepth`, `ProfilePorosityCap`, `ProfileFCStore`, `ProfileWPStore`.

---

### 2026-04-30 03:19 UTC: Closure gate evaluation uses run-level stats plus hillslope deep dives (`H2637`, `H2809`)
**Context**: Stakeholders suspect potential water-balance issues and want physically reasoned verification, not only a single numeric threshold.

**Options considered**:
1. Apply one global pass/fail threshold only.
2. Combine whole-run closure statistics with event/day and hillslope-level reconciliation.

**Decision**: Option 2.

**Impact**: Gate evidence must include:
- whole-run closure summaries,
- day-level outlier inspection,
- independent hillslope checks for `H2637` and `H2809`.

---

### 2026-04-30 03:30 UTC: Parser must tolerate legacy producers with missing optional columns
**Context**: Users can still run legacy WEPP executables (for example `wepp_dcc52a6`) that do not emit new optional `H.wat` columns.

**Options considered**:
1. Require optional columns and fail parsing when absent.
2. Treat optional columns as truly optional: parse legacy rows successfully and emit nulls downstream.

**Decision**: Option 2.

**Impact**: Parser logic and tests must explicitly validate legacy omission paths; missing optional terms are expected and non-fatal.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Header-layout drift breaks legacy parsing | High | Medium | Add parser compatibility tests across legacy + enriched fixtures; keep additive suffix semantics | Mitigated in tests |
| Storage terms remain semantically ambiguous after rollout | Medium | Medium | Publish explicit contract in spec/README with derivation formulas and source mapping | Mitigated in docs |
| Whole-run closure still shows large residuals after regeneration | Medium | Medium | Use repeatable audit with whole-run + event-level breakdown and document remaining process limits | Confirmed residual: `-13,813.464759 mm` |
| Cross-repo release sequencing delays validation | Medium | Medium | Stage implementation with fallback-safe parser first, then producer rollout, then audit regeneration | Mitigated for code; production gate completed on wepp1 |
| `uncapped-spectacular` run data unavailable in local workspace | High | High | Use wepp1 host path `/geodata/wc1/runs/un/uncapped-spectacular` for production gate | Resolved |

## Hardening Signal Log (Required for incident/remediation packages)

- **Baseline health signals**:
  - Runoff basis is now internally consistent (`Runoff == runvol/Area*1000`), but closure interpretation remains sensitive to storage-term semantics.
- **Post-change health signals**:
  - Optional enriched terms present where binaries support them.
  - Closure reports distinguish legacy-storage vs enriched-storage interpretations without parser failures.
- **Danger signals observed**:
  - Production rollout-gate run was absent locally but present on wepp1.
  - H2637/H2809 have very large runoff/closure residuals centered on the 1996-02-06 outlier.
- **Temporary callus register**:
  - Legacy null-fallback for optional columns, owner: package implementer, introduced: 2026-04-30, sunset: after full producer rollout validation.
- **Softening experiments**:
  - Hypothesis: once enriched terms are ubiquitously emitted, fallback-only code paths can be narrowed.
  - Gate results: Legacy producer data leaves the new WAT storage/capacity fields null for all production rows, while `TSMF` and runoff partition fields are available.
  - Decision: Keep fallback paths; do not soften until enriched WEPP producer outputs are deployed and observed.

## Verification Checklist

### Code Quality
- [x] `wctl run-pytest tests/wepp/interchange/test_hill_wat_interchange.py` (4 passed; 2026-04-30 03:43 UTC)
- [x] `wctl run-pytest tests/wepp/interchange/test_hill_soil_interchange.py` (1 passed; 2026-04-30 03:43 UTC)
- [x] `wctl run-pytest tests/wepp/interchange/test_hill_element_interchange.py` (2 passed; 2026-04-30 03:43 UTC)
- [x] `wctl run-pytest tests/wepp/interchange/test_totalwatsed3.py` (4 passed; 2026-04-30 03:43 UTC)
- [x] `wctl run-pytest tests/tools/test_totalwatsed3_daily_closure_audit.py` (2 passed; 2026-04-30 03:43 UTC)
- [x] Required validation commands rerun after review fixes (all passed; 2026-04-30 04:00 UTC)

### Security
- [x] Security impact triage recorded (`none`) with rationale.
- [x] Dedicated security artifact not required for this package scope.

### Documentation
- [x] Work-package scaffold and active ExecPlan created.
- [x] `docs/dev-notes/totalwatsed-interchange.spec.md` updated with final optional-term contract.
- [x] `wepppy/wepp/interchange/README.totalwatsed3.md` updated with new term semantics.
- [x] Package closure notes completed after production audit gate.

### Testing
- [x] Legacy fixture parsing passes unchanged.
- [x] Enriched fixture parsing passes with new columns populated.
- [x] `totalwatsed3` exposes all five optional storage/capacity columns and remains null-safe when inputs are absent.
- [x] Legacy-executable fixture path verifies missing optional columns parse non-fatally with null outputs.
- [x] Closure audit reports whole-run stats for both legacy and enriched interpretations and supports day/outlier drill-down.

### Deployment / Operations
- [x] Regenerate target production artifact without container takedown.
- [x] Capture pre/post checksum and closure summary artifacts.
- [x] Capture independent hillslope reconciliation artifacts for `H2637` and `H2809`.
- [ ] Confirm downstream report consumers remain functional.

## Progress Notes

### 2026-04-29 22:10 UTC: Work-package preparation
**Agent/Contributor**: Codex

**Work completed**:
- Created package scaffold and documented cross-repo scope.
- Recorded source-code anchors for storage/partition terms in WEPP-forest and WEPPpy.
- Authored active ExecPlan with phased implementation, compatibility, and audit validation steps.
- Registered package in root `PROJECT_TRACKER.md`.

**Blockers encountered**:
- None.

**Next steps**:
1. Implement `H.wat` producer output for the finalized optional term set.
2. Implement parser-first compatibility updates in WEPPpy.
3. Land `totalwatsed3`/audit updates (all five terms) and rerun `uncapped-spectacular` closure evidence capture including `H2637`/`H2809` drill-down.

**Test results**:
- Scoping/documentation session only; no test suite executed in this session.

### 2026-04-30 03:19 UTC: Optional-term contract finalized
**Agent/Contributor**: Codex

**Work completed**:
- Recorded stakeholder-approved optional term contract and units in package docs, tracker decisions, and active ExecPlan.
- Updated normative `totalwatsed` interchange spec with `H.wat` optional terms and totalwatsed3 aggregation semantics.

**Blockers encountered**:
- None.

**Next steps**:
1. Implement WEPP-forest `H.wat` output additions for the finalized terms.
2. Update WEPPpy interchange parsers and tests for optional trailing columns.
3. Extend `totalwatsed3` and rerun `uncapped-spectacular` closure audit as rollout gate.

**Test results**:
- Documentation-only update; no code tests run in this session.

### 2026-04-30 03:43 UTC: Parser, producer, aggregation, and audit implementation
**Agent/Contributor**: Codex

**Work completed**:
- Added optional WAT storage/capacity schema fields and parser handling for `SoilWaterTotal`, `ProfileDepth`, `ProfilePorosityCap`, `ProfileFCStore`, and `ProfileWPStore`.
- Preserved legacy WAT parsing by emitting null optional values when the additive fields are absent.
- Kept unknown/unmapped extra WAT columns fail-fast with a clear `Unexpected WAT column layout` error.
- Extended WEPP-forest `watbal.for`, `watbal_hourly.for`, and `outfil.for` to append all five optional storage/capacity terms after legacy `Area`.
- Extended `totalwatsed3` to area-weight optional WAT terms and emit nulls for legacy inputs.
- Extended daily closure audit with whole-run enriched-storage statistics when `SoilWaterTotal` is present.
- Updated docs and schema snapshot for the new WAT/`totalwatsed3` contract.

**Blockers encountered**:
- `/geodata/wc1/runs/un/uncapped-spectacular` and `/wc1/runs/un/uncapped-spectacular` are absent, so production regeneration, closure stats, and `H2637`/`H2809` reconciliation could not be completed. Evidence captured in `artifacts/production_run_missing_probe.md`.

**Next steps**:
1. Mount or restore `uncapped-spectacular`.
2. Regenerate `H.wat.parquet` and `totalwatsed3.parquet` using the enriched WEPP output.
3. Run `tools/totalwatsed3_daily_closure_audit.py` and capture whole-run stats plus H2637/H2809 reconciliation artifacts.

**Test results**:
- `wctl run-pytest tests/wepp/interchange/test_hill_wat_interchange.py` - 4 passed.
- `wctl run-pytest tests/wepp/interchange/test_hill_soil_interchange.py` - 1 passed.
- `wctl run-pytest tests/wepp/interchange/test_hill_element_interchange.py` - 2 passed.
- `wctl run-pytest tests/wepp/interchange/test_totalwatsed3.py` - 4 passed.
- `wctl run-pytest tests/tools/test_totalwatsed3_daily_closure_audit.py` - 2 passed.
- `/workdir/wepp-forest/src make wepp wepp_hill` - passed.
- `tools/smoke_wepp_binary_host.sh /workdir/wepp-forest/src/wepp` - p962 and p1 passed.
- `tools/smoke_wepp_binary_host.sh /workdir/wepp-forest/src/wepp_hill` - p962 and p1 passed.

### 2026-04-30 04:00 UTC: Independent review fixes
**Agent/Contributor**: Codex

**Work completed**:
- Updated `totalwatsed3` element optional partition aggregation to join real `H.element.parquet` rows to WAT on `wepp_id`, OFE, and calendar fields, taking `sim_day_index` from WAT.
- Adjusted the `totalwatsed3` regression fixture so `H.element.parquet` omits `sim_day_index`, matching the production interchange schema.
- Extended `/workdir/wepp-forest/src/watbalprint.for` so watershed `ivers=3` WAT output rows append `SoilWaterTotal`, `ProfileDepth`, `ProfilePorosityCap`, `ProfileFCStore`, and `ProfileWPStore` after legacy `Area`.
- Corrected the ExecPlan audit command example to use the closure-audit tool's positional parquet argument.

**Blockers encountered**:
- Production regeneration remains blocked by missing `uncapped-spectacular` run paths.

**Next steps**:
1. Mount or restore `uncapped-spectacular`.
2. Regenerate the target interchange artifact without container takedown.
3. Capture whole-run closure stats and independent `H2637`/`H2809` reconciliation artifacts.

**Test results**:
- `wctl run-pytest tests/wepp/interchange/test_hill_wat_interchange.py` - 4 passed.
- `wctl run-pytest tests/wepp/interchange/test_hill_soil_interchange.py` - 1 passed.
- `wctl run-pytest tests/wepp/interchange/test_hill_element_interchange.py` - 2 passed.
- `wctl run-pytest tests/wepp/interchange/test_totalwatsed3.py` - 4 passed.
- `wctl run-pytest tests/tools/test_totalwatsed3_daily_closure_audit.py` - 2 passed.
- `/workdir/wepp-forest/src make wepp wepp_hill` - passed.
- `tools/smoke_wepp_binary_host.sh /workdir/wepp-forest/src/wepp` - p962 and p1 passed.
- `tools/smoke_wepp_binary_host.sh /workdir/wepp-forest/src/wepp_hill` - p962 and p1 passed.

### 2026-04-30 04:09 UTC: wepp1 production rollout gate
**Agent/Contributor**: Codex

**Work completed**:
- Verified `uncapped-spectacular` exists on wepp1 at `/geodata/wc1/runs/un/uncapped-spectacular`.
- Patched the `weppcloud` container source surgically without container takedown and retained timestamped backups.
- Regenerated `/wc1/runs/un/uncapped-spectacular/wepp/output/interchange/totalwatsed3.parquet` from existing interchange parquet inputs.
- Ran the closure audit and independent `H2637`/`H2809` reconciliation.
- Copied production artifacts into `artifacts/wepp1_uncapped_spectacular_20260430/`.

**Blockers encountered**:
- None for the rollout gate. The production `H.wat.parquet` is legacy and does not contain the five new WAT storage/capacity terms, so those fields are null in the regenerated `totalwatsed3.parquet`.

**Next steps**:
1. Decide whether to open a follow-up root-cause investigation for the large H2637/H2809 residuals and the 1996-02-06 outlier.
2. Confirm downstream report consumers render the additive columns safely.

**Production results**:
- New `totalwatsed3.parquet` hash: `20f39d30280c9ccaf20754778e57c9e5595711ea334c8ffab82def2d89f68ca2`.
- Backup hash: `d649088f1948c3f98de4f4c5868824aba920b8552bacc07da4cfaf40f37c8e73`.
- Whole-run reconstructed closure with legacy storage: `-13,813.464759 mm` (`-16.855844%` of rain + melt).
- Runoff consistency max absolute difference: `0.0 mm`.
- `H2637` closure with storage: `-119,246.654467 mm` (`-114.007900%` of rain + melt).
- `H2809` closure with storage: `-297,116.718881 mm` (`-278.295506%` of rain + melt).

## Communication Log

### 2026-04-29 22:10 UTC: User requested implementation work-package with optional terms
**Participants**: User, Codex  
**Question/Topic**: Prepare a work-package to implement robust optional terms for storage and runoff partition interpretation.  
**Outcome**: New package created with scope, tracker, and active ExecPlan ready for implementation.

### 2026-04-30 03:19 UTC: User finalized optional-term contract preferences
**Participants**: User, Codex  
**Question/Topic**: Confirm decision points for naming/units/source-of-truth and rollout gate.  
**Outcome**: Agreed contract recorded:
- Terms should closely match WEPP variable semantics.
- Preferred optional terms are in `H.wat` as `mm`.
- WEPP values are authoritative when available; WEPPpy parses/pass-throughs.
- `uncapped-spectacular` closure re-audit is the production rollout gate.

### 2026-04-30 03:30 UTC: User required legacy executable tolerance
**Participants**: User, Codex  
**Question/Topic**: Ensure parser compatibility when users run legacy WEPP executables such as `wepp_dcc52a6`.  
**Outcome**: Added explicit contract: missing optional columns are expected on legacy producers and must parse as non-fatal omissions with null downstream terms.
