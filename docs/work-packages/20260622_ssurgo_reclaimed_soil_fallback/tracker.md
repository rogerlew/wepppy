# Tracker - SSURGO Reclaimed Soil Conversion and Fallback Transparency

> Living document tracking progress, decisions, risks, and communication for this work package.

## Quick Status

**Timezone**: UTC  
**Started**: 2026-06-22 18:28 UTC  
**Current phase**: Complete; ADR amended with Tahoe precedent rationale
**Last updated**: 2026-06-22 20:29 UTC
**Next milestone**: Handoff.
**Security impact**: low  
**Dedicated security review**: no  
**Security artifact**: N/A  
**Parameterization ADR**: [ADR-0008](../../adrs/ADR-0008-ssurgo-reclaimed-soil-restrictive-layer-fallback.md)

## Task Board

### Ready / Backlog

- [ ] None.

### In Progress

- [ ] None.

### Blocked

- [ ] None.

### Done

- [x] Created package, tracker, and active ExecPlan from production investigation findings (2026-06-22 18:28 UTC).
- [x] Drafted ADR-0008 with decision provenance for first-horizon restrictive-layer handling and fallback transparency (2026-06-22 18:50 UTC).
- [x] Built deterministic Fairpoint SSURGO fixture data for MUKEYs `3294459`, `3294460`, and `3294461` (2026-06-22 18:50 UTC).
- [x] Added unit tests proving Fairpoint profiles produce valid WEPP soils and at least one WEPP layer (2026-06-22 18:50 UTC).
- [x] Implemented restrictive-layer handling fix in `wepppy/soils/ssurgo/ssurgo.py` (2026-06-22 18:50 UTC).
- [x] Added fallback transparency state/artifact design in `wepppy/nodb/core/soils.py` (2026-06-22 18:50 UTC).
- [x] Added NoDb legacy-load and generated artifact compatibility tests (2026-06-22 18:50 UTC).
- [x] Added integrated generated-output test for `3294459`, `3294460`, and `3294461` (2026-06-22 18:50 UTC).
- [x] Updated `wepppy/soils/ssurgo/ssurgo.md` and `wepppy/soils/README.md` (2026-06-22 18:50 UTC).
- [x] Completed QA review and dispositioned findings (2026-06-22 18:56 UTC).
- [x] Ran validation gates; package gates pass and unrelated full-suite blocker is documented (2026-06-22 18:56 UTC).
- [x] Amended ADR-0008 with Brooks et al. Tahoe restrictive-layer rationale and local comparison-run evidence (2026-06-22 20:27 UTC).

## Timeline

- **2026-06-22 18:28 UTC** - Package created after production investigation showed Fairpoint MUKEYs are present in 2025 gNATSGO but rejected by SSURGO-to-WEPP conversion.

## Decisions Log

### 2026-06-22 18:28 UTC: Treat the issue as conversion plus fallback transparency

**Context**: Production run `hard-line-foothold / disturbed9002` selected raw Fairpoint MUKEYs for Topaz 573 and 581, but WEPPcloud rejected the Fairpoint soils and substituted `2451115`, yielding Shelocta-Latham output.

**Options considered**:
1. Replace or update the gNATSGO raster layer.
2. Clear the project-local SSURGO tabular cache.
3. Fix reclaimed-profile conversion and make invalid-MUKEY fallback observable.

**Decision**: Option 3.

**Impact**: The installed 2025 gNATSGO data appears current for this area. The package focuses on SSURGO-to-WEPP conversion and fallback behavior instead of raster data replacement.

---

### 2026-06-22 18:28 UTC: Require an ADR before merge

**Context**: The package changes how restrictive-layer thresholds affect generated WEPP layers and how invalid dominant soils are substituted or reported.

**Options considered**:
1. Treat this as a narrow bug fix with only tests.
2. Require a parameterization ADR because generated WEPP soil inputs change.

**Decision**: Option 2.

**Impact**: Implementation must add `docs/adrs/ADR-0008-ssurgo-reclaimed-soil-restrictive-layer-fallback.md` or equivalent before merge and link it from this package.

---

### 2026-06-22 20:27 UTC: Interpret the Tahoe precedent as lower-boundary handling

**Context**: The restrictive-layer rule was based on the Brooks et al. Lake Tahoe WEPP workflow, where steep rocky forest soils and consolidated bedrock create a lower-boundary modeling issue. The reclaimed Fairpoint failure is different: the first valid SSURGO horizon is a low-conductivity reclaimed soil horizon.

**Options considered**:
1. Preserve first-horizon low-ksat rejection as the conservative Tahoe-derived behavior.
2. Treat Tahoe-style restrictions as lower-boundary truncation after at least one modeled soil layer exists, while retaining valid first low-ksat horizons for reclaimed profiles.

**Decision**: Option 2.

**Impact**: Tahoe-style bedrock/restrictive material below a valid soil mantle still truncates the WEPP profile. Reclaimed mine-land profiles no longer collapse to zero layers merely because the first valid horizon is below the restrictive-layer threshold.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Fixing zero-layer profiles changes model behavior for more soils than Fairpoint. | High | Medium | Added targeted Fairpoint tests plus broader full-suite attempt; documented ADR rationale and rollback conditions. | Mitigated |
| Fallback transparency mutates run-scoped artifacts and breaks existing consumers. | High | Low | Added only nullable/backward-compatible fields; added legacy-load and summary schema tests. | Mitigated |
| Tests depend on live NRCS SDA and become flaky. | Medium | Medium | Used deterministic fixture rows for CI. | Closed |
| The first-horizon restrictive rule is scientifically ambiguous. | High | Medium | Resolved in ADR with explicit alternatives, Brooks et al. Tahoe precedent interpretation, and local comparison-run evidence. | Closed |
| Disturbed soil modification consumes final `domsoil_d` and could ignore raw provenance. | Medium | Medium | Keep final `domsoil_d` semantics unchanged and document raw provenance as additive. | Mitigated |

## Hardening Signal Log

- **Baseline health signals**: Fairpoint MUKEYs `3294459`, `3294460`, and `3294461` are present in current production 2025 gNATSGO/gSSURGO rasters but are invalidated as "no horizons".
- **Post-change health signals**: Fairpoint MUKEYs produce valid `.sol` files; substitutions are visible when they still occur.
- **Danger signals observed**: None yet; implementation pending.
- **Temporary callus register**: None planned.
- **Softening experiments**: Future package may reduce broad invalid-soil substitution after provenance is available.

## Verification Checklist

### Code Quality

- [x] `python -m py_compile wepppy/soils/ssurgo/ssurgo.py wepppy/nodb/core/soils.py`
- [x] `wctl run-pytest tests/soils/test_ssurgo_reclaimed_fairpoint.py -q`
- [x] `wctl run-pytest tests/nodb/test_soils_gridded_root_creation.py -q`
- [x] `wctl run-pytest tests/soils/test_ssurgo_reclaimed_fairpoint.py tests/nodb/test_soils_gridded_root_creation.py --maxfail=1 -q`
- [x] `wctl run-stubtest wepppy.nodb.core.soils`
- [x] `wctl check-test-stubs`
- [x] `wctl run-pytest tests --maxfail=1` attempted; stopped at unrelated `tests/weppcloud/routes/test_wepp_bp.py::test_view_management_effective_returns_texture_specific_preview[clay-1.1-2.1-0.11]` after 4,425 passed and 59 skipped.
- [x] Broad exception gate run: `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master` passed with net delta `+0`.

### Security

- [x] Security impact triage recorded as `low` with rationale.
- [ ] Re-triage if implementation changes route payloads, file/path handling outside expected run artifacts, queue wiring, or external egress behavior.

### Documentation

- [x] ADR-0008 added and linked from package/tracker.
- [x] ADR captures decision venue, participants, decision owner, implementer, evidence, risks, and rollback notes.
- [x] `wepppy/soils/ssurgo/ssurgo.md` updated.
- [x] `wepppy/soils/README.md` updated.
- [x] Package and tracker updated with implementation decisions and closure evidence.
- [x] Tahoe precedent ADR amendment doc lint passed for ADR, package, tracker, active ExecPlan, and QA artifact.

### Testing

- [x] Unit test: `3294459` builds valid WEPP soil from deterministic fixture data.
- [x] Unit test: `3294460` builds valid WEPP soil from deterministic fixture data.
- [x] Unit test: `3294461` builds valid WEPP soil from deterministic fixture data.
- [x] Unit test: first valid horizon below restrictive threshold emits at least one WEPP layer.
- [x] Integrated generated-output test writes `.sol` files for all three Fairpoint MUKEYs.
- [x] Fallback test: invalid raw MUKEY substitution preserves original MUKEY and reason.
- [x] Legacy NoDb load test covers missing new fallback-provenance fields.
- [x] Disturbed-flow propagation evidence confirms final `domsoil_d` remains usable and raw provenance is retained by unit contract.

### Review

- [x] QA review completed and saved to `artifacts/qa_review_findings.md`.
- [x] Every QA finding is dispositioned.
- [x] Accepted medium/high findings are fixed and rechecked.

## Progress Notes

### 2026-06-22 18:28 UTC: Package initialization

**Agent/Contributor**: Codex

**Work completed**:
- Created package scope around two confirmed behaviors: Fairpoint zero-layer rejection and silent fallback substitution.
- Captured production evidence from `hard-line-foothold / disturbed9002`.
- Required unit coverage, integrated generated-output coverage for `3294459`, `3294460`, `3294461`, QA review, docs, and ADR gate.

**Blockers encountered**:
- None.

**Next steps**:
- Draft ADR-0008 and build deterministic SSURGO fixture data for the three Fairpoint MUKEYs.
- Add failing tests before changing conversion logic.

**Test results**: Not run; documentation/package authoring only.

### 2026-06-22 18:50 UTC: Implementation and focused validation

**Agent/Contributor**: Codex

**Work completed**:
- Added ADR-0008 and documented the first-horizon restrictive-layer rule.
- Added deterministic Fairpoint fixture tests for `3294459`, `3294460`, and `3294461`.
- Updated restrictive-layer analysis so the first valid low-ksat horizon is retained.
- Added `raw_ssurgo_domsoil_d` and `ssurgo_substitution_d` with legacy-load defaults.
- Added nullable summary fields `raw_mukey`, `substituted_mukey`, and `substitution_reason`.
- Updated soil conversion and subsystem documentation.

**Blockers encountered**:
- None.

**Next steps**:
- Complete QA review artifact and final validation gates.

**Test results**:
- `wctl run-pytest tests/soils/test_ssurgo_reclaimed_fairpoint.py -q` - passed, 3 tests.
- `wctl run-pytest tests/nodb/test_soils_gridded_root_creation.py -q` - passed, 15 tests.

### 2026-06-22 18:56 UTC: QA and final validation

**Agent/Contributor**: Codex

**Work completed**:
- QA review found one package issue: invalid low-ksat horizons could still
  influence restrictive-layer detection. Fixed by skipping invalid horizons and
  adding a focused regression assertion.
- Stub hygiene was corrected for existing runtime cache properties in
  `wepppy/nodb/core/soils.pyi`.
- Full-suite validation was attempted and the unrelated blocker was confirmed
  with a standalone rerun.

**Blockers encountered**:
- `wctl run-pytest tests --maxfail=1` stops at
  `tests/weppcloud/routes/test_wepp_bp.py::test_view_management_effective_returns_texture_specific_preview[clay-1.1-2.1-0.11]`.
  The test also fails standalone, and neither `tests/weppcloud/routes/test_wepp_bp.py`
  nor `wepppy/weppcloud/routes/nodb_api/wepp_bp.py` has a local diff.

**Test results**:
- `python -m py_compile wepppy/soils/ssurgo/ssurgo.py wepppy/nodb/core/soils.py` - passed.
- `wctl run-pytest tests/soils/test_ssurgo_reclaimed_fairpoint.py -q` - passed, 3 tests.
- `wctl run-pytest tests/nodb/test_soils_gridded_root_creation.py -q` - passed, 15 tests.
- `wctl run-pytest tests/soils/test_ssurgo_reclaimed_fairpoint.py tests/nodb/test_soils_gridded_root_creation.py --maxfail=1 -q` - passed, 18 tests.
- `wctl run-stubtest wepppy.nodb.core.soils` - passed.
- `wctl check-test-stubs` - passed.
- `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master` - passed.
- `wctl doc-lint` on package, tracker, active ExecPlan, QA artifact, `wepppy/soils/ssurgo/ssurgo.md`, and `wepppy/soils/README.md` - passed.

### 2026-06-22 20:27 UTC: ADR provenance amendment

**Agent/Contributor**: Codex

**Work completed**:
- Amended ADR-0008 to document the Brooks et al. Lake Tahoe restrictive-layer precedent.
- Recorded the physical distinction between Tahoe-style restrictive material below a modeled soil mantle and reclaimed first-horizon low-conductivity profiles.
- Added local comparison evidence: Blackwood/Lake Tahoe has 231 restrictive-profile hillslopes but zero prior-rule zero-layer reassignment cases, while hard-line-foothold has 73 restrictive-profile hillslopes and 71 prior-rule zero-layer reassignment cases.

**Blockers encountered**:
- None.

**Next steps**:
- Handoff.

**Test results**:
- `wctl doc-lint --path docs/adrs/ADR-0008-ssurgo-reclaimed-soil-restrictive-layer-fallback.md` - passed.
- `wctl doc-lint --path docs/work-packages/20260622_ssurgo_reclaimed_soil_fallback/tracker.md` - passed.
- `wctl doc-lint --path docs/work-packages/20260622_ssurgo_reclaimed_soil_fallback/prompts/active/ssurgo_reclaimed_soil_fallback_execplan.md` - passed.
- `wctl doc-lint --path docs/work-packages/20260622_ssurgo_reclaimed_soil_fallback/package.md` - passed.
- `wctl doc-lint --path docs/work-packages/20260622_ssurgo_reclaimed_soil_fallback/artifacts/qa_review_findings.md` - passed.
- `git diff --check -- docs/adrs/ADR-0008-ssurgo-reclaimed-soil-restrictive-layer-fallback.md docs/work-packages/20260622_ssurgo_reclaimed_soil_fallback` - passed.

## Communication Log

### 2026-06-22 18:28 UTC: User request

**Participants**: User, Codex  
**Question/Topic**: User asked to create a work package for both fixing reclaimed Fairpoint conversion and making fallback behavior non-silent, including unit coverage, QA review, and integrated test MUKEYs `3294459`, `3294460`, `3294461`.  
**Outcome**: Package created with those requirements as closure criteria.
