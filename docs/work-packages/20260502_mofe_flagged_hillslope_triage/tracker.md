# Tracker - MOFE Flagged Hillslope Triage for Ablation Campaigns

> Living execution log for v1 triage, v2 refinement, and v3 D2b split closeout.

## Quick Status

**Timezone**: UTC  
**Started**: 2026-05-02 15:54 UTC  
**Current phase**: v3 complete; ready for ablation package spawn  
**Last updated**: 2026-05-02 19:19 UTC  
**Next milestone**: open downstream ablation execution package(s) from `campaign_matrix_v3.csv`  
**Security impact**: `low`  
**Dedicated security review**: `no`  
**Security artifact**: `N/A`

## Task Board

### Ready / Backlog
- [ ] Open ablation execution package(s) from `campaign_matrix_v3.csv`.

### In Progress
- [ ] None.

### Blocked
- [ ] None.

### Done
- [x] v1 ExecPlan (`mofe_flagged_hillslope_triage_execplan.md`) completed with M1-M6 artifacts (2026-05-02 16:30 UTC).
- [x] v2 refinement ExecPlan (`mofe_flagged_hillslope_taxonomy_refinement_execplan.md`) completed with M1-M7 artifacts and closeout (2026-05-02 17:25 UTC).
- [x] v3 split ExecPlan (`mofe_flagged_hillslope_d2b_split_execplan.md`) executed end-to-end with M1-M5 closeout (2026-05-02 19:19 UTC).
- [x] `package.md` follow-up section updated to reference v3 outputs (2026-05-02 19:19 UTC).

## Timeline

- **2026-05-02 15:54 UTC** - Work-package scaffold created and active v1 ExecPlan migrated.
- **2026-05-02 16:01 UTC** - Preconditions validated (`PRECONDITIONS_OK`) for v1 execution.
- **2026-05-02 16:06 UTC** - v1 M1 complete (`triage_table_*` outputs validated).
- **2026-05-02 16:20 UTC** - v1 M2-M6 artifacts generated via `tools/triage_pipeline.py`.
- **2026-05-02 16:30 UTC** - v1 ExecPlan closeout complete.
- **2026-05-02 17:06 UTC** - v2 preconditions validated (`hdbscan_available=True`, `sklearn_extra_available=True`).
- **2026-05-02 17:10 UTC** - v2 M1-M3 pass complete via `tools/refine_mofe_taxonomy.py --no-cluster --no-sensitivity` (`D_UNCLASSIFIED=0`).
- **2026-05-02 17:15 UTC** - v2 full pass complete via `tools/refine_mofe_taxonomy.py` (cluster + sensitivity outputs emitted).
- **2026-05-02 17:25 UTC** - v2 ExecPlan, tracker, and package closeout updates complete.
- **2026-05-02 19:08 UTC** - v3 ExecPlan execution-readiness pass completed.
- **2026-05-02 19:12 UTC** - v3 preconditions validated and `tools/split_d2b_taxonomy.py` executed.
- **2026-05-02 19:17 UTC** - v3 full artifact set emitted (`taxonomy_assignments_v3.csv`, `taxonomy_disagreements_v3.csv`, `representative_seeds_v3.csv`, `campaign_matrix_v3.csv`, `defect_families_v3.md`, `taxonomy_evolution_v3.md`, `threshold_sensitivity_v3.csv`).
- **2026-05-02 19:19 UTC** - v3 ExecPlan, tracker, and package closeout updates completed.

## Decisions Log

### 2026-05-02 16:20 UTC: v1 used deterministic pipeline implementation
**Decision**: Implement v1 M2-M6 in `tools/triage_pipeline.py`.  
**Impact**: Reproducible v1 outputs and baseline lineage for refinement.

### 2026-05-02 17:10 UTC: v2 kept baseline D2b and D3 thresholds
**Decision**: Keep `D2b` threshold at `1.0` and `D3` threshold at `0.99`.  
**Impact**: D2b coverage remained high (`99/132`) without violating v2 guardrails; D3 remained a focused minority family (`7/132`).

### 2026-05-02 17:10 UTC: v2 sparse-family merge applied
**Decision**: Merge sparse `D6a` (2 rows) into `D6b`.  
**Impact**: Satisfied v2 family-size gate (`>=3`, D4 exempt) while preserving mechanistic continuity.

### 2026-05-02 19:17 UTC: v3 split accepted without threshold retune
**Decision**: Keep v3 D2b split thresholds unchanged after M2 disagreement review.  
**Impact**: Retired `D2b`, produced balanced split (`41/5/13/17/23`), and kept deterministic severity×persistence boundaries stable for downstream operations.

### 2026-05-02 19:17 UTC: v3 D2b2 recommendation linked to H2637 precedent
**Decision**: Set D2b2 recommendation to `extend_20260430_uncapped-spectacular_h2637_hillslope_closure-spike`.  
**Impact**: Preserves precedent continuity for the D4-adjacent single-day moderate band while keeping other split families as `new_incident`.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Threshold brittleness near split boundaries (`severity_split_300`, `severity_split_500`, `persistence_split_3`) | Medium | Medium | Use `threshold_sensitivity_v3.csv` unstable rows to prioritize robust first ablation lanes; revisit split thresholds only if lane evidence contradicts taxonomy | Open |
| Cluster disagreement concentration in dominant run/config may hide alternate mechanisms | Medium | Medium | Treat `taxonomy_disagreements_v3.csv` cohorts as secondary prioritization signal when selecting initial incident scope | Open |

## Verification Checklist

### Documentation
- [x] `package.md` includes v3 follow-up outputs and matrix status.
- [x] v1, v2, and v3 active ExecPlans updated through retrospective closeout.
- [x] tracker updated with full v1-v3 timeline.

### Execution
- [x] v1 artifact set complete.
- [x] v2 artifact set complete.
- [x] v3 artifact set complete:
  - `taxonomy_assignments_v3.csv`
  - `taxonomy_disagreements_v3.csv`
  - `representative_seeds_v3.csv`
  - `campaign_matrix_v3.csv`
  - `defect_families_v3.md`
  - `taxonomy_evolution_v3.md`
  - `threshold_sensitivity_v3.csv`
  - `split_d2b_taxonomy_metadata.json`
- [x] v3 acceptance gate met: `D2b=0`, `D_UNRESOLVED_D2B_SPLIT=0`, `D_UNCLASSIFIED=0`, largest family `41 <= 53`.
- [x] v3 representative-seed gate met: split-family worst/median rows have `missing_shared_context == ""`.

## Progress Notes

### 2026-05-02 19:19 UTC: v3 end-to-end closeout
**Agent/Contributor**: Codex

**Work completed**:
- Authored `tools/split_d2b_taxonomy.py`.
- Executed v3 M1-M4 outputs and M5 documentation updates.
- Validated strict v3 gates, disagreement export, seed manifests, matrix row count, and six-threshold sensitivity coverage.

**Blockers encountered**:
- None.

**Next steps**:
1. Open ablation execution package(s) from `campaign_matrix_v3.csv`.
2. Prioritize D2b2 extension lane against H2637 precedent, then stage new incidents for D2b1/D2b3/D2b4/D2b5.
