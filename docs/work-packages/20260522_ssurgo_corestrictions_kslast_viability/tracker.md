# Tracker - SSURGO Corestrictions `kslast` Viability Assessment

> Living document tracking progress, decisions, risks, and communication for this work package.

## Quick Status

**Timezone**: UTC  
**Started**: 2026-05-22 23:45 UTC  
**Current phase**: Closed  
**Last updated**: 2026-05-23 01:09 UTC  
**Next milestone**: Follow-up implementation-gating package definition  
**Security impact**: `none`  
**Dedicated security review**: `no`  
**Security artifact**: `N/A`

## Task Board

### Ready / Backlog

- [ ] Follow-up package: full WEPP run-fixture M4 validation and production cutover decision gate.

### In Progress

- [ ] None.

### Blocked

- [ ] None.

### Done

- [x] M0: Scope/input freeze completed; legacy baseline and extraction provenance frozen.
- [x] M1: National + ecoregion sampled coverage extracted and documented.
- [x] M2: Reasonableness diagnostics and anomaly catalog completed.
- [x] M3: Candidate A/B rules implemented in analysis harness with bounds/fallback logic.
- [x] M4: Regional legacy-vs-candidate directional comparison completed (input-space + proxy hydrologic direction).
- [x] M5: Recommendation memo published (`retain legacy`) with implementation gating checklist.

## Timeline

- **2026-05-22 23:45 UTC** - Package created and initial scope/spec committed.
- **2026-05-23 00:54-01:08 UTC** - SDA/EPA extraction and artifact generation run completed.
- **2026-05-23 01:09 UTC** - Recommendation and tracker/execplan synchronization completed.

## Decisions Log

### 2026-05-23: Preserve assessment-only scope

**Decision**: No production `ssurgo.py` parameterization change in this package.

**Impact**: Keeps risk bounded to analysis artifacts and recommendation.

### 2026-05-23: Use hybrid regional extraction strategy

**Context**: Full-region polygon-ranked SDA extraction was unstable/slow for several large regions.

**Decision**:
1. Keep polygon-ranked extraction where stable (`Marine West Coast Forest`, `Cascades`, `Sierra Nevada`).
2. Use bounded point-sampled fallback for remaining regions.
3. Explicitly flag restrictive-present sample shortfalls as low-confidence regions due extraction/runtime limits in this run.

**Impact**: Reproducible completion with transparent denominator/coverage limitations.

### 2026-05-23: Recommendation outcome

**Decision**: `retain legacy`.

**Impact**: Candidate formulas are not promoted to production without stronger regional inference confidence and full run-fixture hydrologic validation.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Coverage varies strongly by ecoregion and biases conclusions | High | Medium | Explicit low-confidence labels for execution-limited restrictive-present sample shortfall regions | Mitigated (partially) |
| `corestrictions` semantics are inconsistent across regions/survey vintages | High | Medium | Semantic-direction checks and anomaly catalog included in decision basis | Open |
| Candidate formulas overfit sampled regions | Medium | Medium | Recommendation held at `retain legacy`; follow-up run-fixture gate required | Open |
| Legacy comparison run set underrepresents key terrain/climate regimes | Medium | Medium | M4 marked proxy-only; follow-up package must run full WEPP fixtures | Open |

## Verification Checklist

### Documentation

- [x] Package overview created.
- [x] Assessment spec created.
- [x] Active ExecPlan synchronized with outcomes.
- [x] Final recommendation and closure notes added.

### Analysis and Reproducibility

- [x] Coverage queries and scripts recorded with reproducible commands.
- [x] Reasonableness check outputs captured in `artifacts/`.
- [x] Legacy-vs-candidate comparisons reproducible from documented inputs.
- [x] Recommendation includes residual-risk and gating section.

### Testing / Validation

- [x] Analysis harness executed end-to-end with successful artifact generation.
- [ ] Full WEPP hydrograph validation reruns per ecoregion (deferred to follow-up package).

## Progress Notes

### 2026-05-23 01:09 UTC: ExecPlan run completion

**Agent/Contributor**: Codex

**Evidence class**:
- **Ran**: `python -u docs/work-packages/20260522_ssurgo_corestrictions_kslast_viability/artifacts/run_corestrictions_kslast_viability.py`
- **Static**: artifact synthesis/review and recommendation framing updates

**Work completed**:
- Built reproducible analysis harness with SDA/EPA integration and fallback sampling modes.
- Generated required artifacts:
  - `coverage_report.md`
  - `reasonableness_checks.md`
  - `ecoregion_comparison_matrix.csv`
  - `legacy_vs_candidate_summary.md`
  - `recommendation_memo.md`
  - supporting machine-readable provenance tables.
- Updated active ExecPlan and tracker with milestone outcomes and limitations.

**Blockers encountered**:
- Full-region ranked extraction was unstable/slow for several large regions; mitigated via bounded point-sampled fallback.
- Restrictive-present shortfalls in specific regions are treated as infrastructure-constrained sampling limits, not SSURGO dataset absence signals.

**Next steps**:
- Define follow-up package for full WEPP run-fixture hydrologic validation and production cutover gate.
