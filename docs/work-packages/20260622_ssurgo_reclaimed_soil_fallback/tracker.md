# Tracker - SSURGO Reclaimed Soil Conversion and Fallback Transparency

> Living document tracking progress, decisions, risks, and communication for this work package.

## Quick Status

**Timezone**: UTC  
**Started**: 2026-06-22 18:28 UTC  
**Current phase**: Scoping complete; implementation pending  
**Last updated**: 2026-06-22 18:28 UTC  
**Next milestone**: Draft ADR and implement Fairpoint fixture tests before changing conversion logic.  
**Security impact**: low  
**Dedicated security review**: no  
**Security artifact**: N/A  
**Parameterization ADR**: `docs/adrs/ADR-0008-ssurgo-reclaimed-soil-restrictive-layer-fallback.md` (planned)

## Task Board

### Ready / Backlog

- [ ] Draft ADR-0008 with decision provenance for first-horizon restrictive-layer handling and fallback transparency.
- [ ] Build deterministic Fairpoint SSURGO fixture data for MUKEYs `3294459`, `3294460`, and `3294461`.
- [ ] Add unit tests proving Fairpoint profiles produce valid WEPP soils and at least one WEPP layer.
- [ ] Implement restrictive-layer handling fix in `wepppy/soils/ssurgo/ssurgo.py`.
- [ ] Add fallback transparency state/artifact design in `wepppy/nodb/core/soils.py`.
- [ ] Add NoDb legacy-load and generated artifact compatibility tests.
- [ ] Add integrated generated-output test for `3294459`, `3294460`, and `3294461`.
- [ ] Update `wepppy/soils/ssurgo/ssurgo.md` and `wepppy/soils/README.md`.
- [ ] Complete QA review artifact and disposition every finding.
- [ ] Run targeted and pre-handoff validation gates.

### In Progress

- [ ] None.

### Blocked

- [ ] None.

### Done

- [x] Created package, tracker, and active ExecPlan from production investigation findings (2026-06-22 18:28 UTC).

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

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Fixing zero-layer profiles changes model behavior for more soils than Fairpoint. | High | Medium | Add targeted Fairpoint tests plus broader SSURGO regression tests; document ADR rationale and rollback conditions. | Open |
| Fallback transparency mutates run-scoped artifacts and breaks existing consumers. | High | Low | Add only nullable/backward-compatible fields; add legacy-load and parquet schema tests. | Open |
| Tests depend on live NRCS SDA and become flaky. | Medium | Medium | Use deterministic fixture rows for CI; record optional live validation separately. | Open |
| The first-horizon restrictive rule is scientifically ambiguous. | High | Medium | Resolve in ADR with explicit alternatives and evidence before implementation. | Open |
| Disturbed soil modification consumes final `domsoil_d` and could ignore raw provenance. | Medium | Medium | Validate disturbed generated artifacts and document final-vs-raw semantics. | Open |

## Hardening Signal Log

- **Baseline health signals**: Fairpoint MUKEYs `3294459`, `3294460`, and `3294461` are present in current production 2025 gNATSGO/gSSURGO rasters but are invalidated as "no horizons".
- **Post-change health signals**: Fairpoint MUKEYs produce valid `.sol` files; substitutions are visible when they still occur.
- **Danger signals observed**: None yet; implementation pending.
- **Temporary callus register**: None planned.
- **Softening experiments**: Future package may reduce broad invalid-soil substitution after provenance is available.

## Verification Checklist

### Code Quality

- [ ] `python -m py_compile wepppy/soils/ssurgo/ssurgo.py wepppy/nodb/core/soils.py`
- [ ] `wctl run-pytest tests/soils/<new_fairpoint_test>.py --maxfail=1`
- [ ] `wctl run-pytest tests/nodb/<new_fallback_test>.py --maxfail=1`
- [ ] `wctl run-pytest tests --maxfail=1` or documented unrelated blocker.
- [ ] Broad exception gate run if touched files introduce or modify exception handling.

### Security

- [x] Security impact triage recorded as `low` with rationale.
- [ ] Re-triage if implementation changes route payloads, file/path handling outside expected run artifacts, queue wiring, or external egress behavior.

### Documentation

- [ ] ADR-0008 added and linked from package/tracker.
- [ ] ADR captures decision venue, participants, decision owner, implementer, evidence, risks, and rollback notes.
- [ ] `wepppy/soils/ssurgo/ssurgo.md` updated.
- [ ] `wepppy/soils/README.md` updated.
- [ ] Package and tracker updated with implementation decisions and closure evidence.

### Testing

- [ ] Unit test: `3294459` builds valid WEPP soil from deterministic fixture data.
- [ ] Unit test: `3294460` builds valid WEPP soil from deterministic fixture data.
- [ ] Unit test: `3294461` builds valid WEPP soil from deterministic fixture data.
- [ ] Unit test: first valid horizon below restrictive threshold emits at least one WEPP layer.
- [ ] Integrated generated-output test writes `.sol` files for all three Fairpoint MUKEYs.
- [ ] Fallback test: invalid raw MUKEY substitution preserves original MUKEY and reason.
- [ ] Legacy NoDb load test covers missing new fallback-provenance fields.
- [ ] Disturbed-flow propagation evidence confirms final `domsoil_d` remains usable and raw provenance is retained.

### Review

- [ ] QA review completed and saved to `artifacts/qa_review_findings.md`.
- [ ] Every QA finding is dispositioned.
- [ ] Accepted medium/high findings are fixed and rechecked.

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

## Communication Log

### 2026-06-22 18:28 UTC: User request

**Participants**: User, Codex  
**Question/Topic**: User asked to create a work package for both fixing reclaimed Fairpoint conversion and making fallback behavior non-silent, including unit coverage, QA review, and integrated test MUKEYs `3294459`, `3294460`, `3294461`.  
**Outcome**: Package created with those requirements as closure criteria.
