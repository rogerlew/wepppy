# Tracker - Iterative First-Order Link Prune WP-05 TopAZ Parity Validation

> Living document tracking progress, decisions, risks, and handoff state for WP-05 execution.

## Quick Status

**Timezone**: UTC  
**Started**: 2026-04-13 08:00 UTC  
**Current phase**: Closed (effective parity accepted for WP-05)  
**Last updated**: 2026-04-14 01:25 UTC  
**Next milestone**: Archive active ExecPlan and hand off post-closure follow-ons (H-006+).  
**Security impact**: `none`  
**Dedicated security review**: `no`  
**Security artifact**: `N/A`

## Task Board

### Ready / Backlog
- [ ] H-006 (`oracle.runtime_contract.native_vs_snapshot.v1`) as post-closure governance hardening.
- [ ] Optional H-007 trace assist for long-horizon divergence forensics.

### In Progress
- [ ] None (WP-05 execution closed).

### Blocked
- [ ] None.

### Done
- [x] Captured remediation baseline from `/tmp/ifolp_wp05_remediate/run1` and `run2` (hash `5e818ce796d5f703ec3bcef86de84c0345d554f7198699265c7ad5c5a5286a79`).
- [x] Populated and maintained `hypothesis_log.md` with executable hypotheses and per-experiment evidence.
- [x] Executed bounded hypothesis-driven modifications and immediate post-change parity runs.
- [x] Completed full parity reruns (`run1`/`run2`) and verified canonical hash stability for retained state (`2ef1aff3842e2a7b0ac31a04464d78bdf56efa83cdd8b2794704930c454a0845`).
- [x] Performed post-parity code review/disposition and updated `mismatch_disposition.md`.
- [x] Ran required cargo gates for retained remediation set:
  - `cargo check -p whitebox_tools`
  - `cargo test -p whitebox_tools iterative_first_order_link_prune -- --nocapture`
- [x] Executed H-004 (`phase_b.tie_break_last_within_epsilon.v1`) under anti-retest controls and dispositioned it as rejected/reverted after zero parity movement.
- [x] Completed second clean-room TopAZ investigation focused on F-003/F-004 and F-002 regression check.
- [x] Authored `second_clean_room_analysis.md` with 12-contract coverage, first-divergence localization, topology-context decomposition, sensitivity sweep, and H-005+ recommendations.
- [x] Patched IFOLP specification with explicit oracle/provenance, unit-conversion, numeric-decision, pass-level behavior, ordering, and acceptance-metric contracts.
- [x] Recorded basin-mask stage-alignment discovery from manual map QA: basin-masked diagnostics show candidate is over-pruned relative to oracle for gatecreek/clueless.
- [x] Executed H-009/H-010/H-011 iterative remediation cycle and recorded deterministic retained-state hash (`07e351537eb91525d85cf922f41c89bcc8ee12dc415ad2d078e159f27db93dc1`).
- [x] Executed provenance-aligned H-005 probe (`blackwood 5/60`, `gatecreek 2/30`) with deterministic probe hash (`cd013e16c16f14ac00e4c8b1b2b4cf9c325449bd54a74cd6fd640f37f183beb5`).
- [x] Stakeholder accepted current Rust behavior as effectively parity-equivalent for WP-05 closure.

## Timeline

- **2026-04-13 08:00 UTC** - WP-05 package scaffold created.
- **2026-04-13 15:34 UTC** - Initial parity campaign completed; deterministic mismatch baseline recorded.
- **2026-04-13 16:15 UTC** - WP-05 reopened for targeted remediation of F-002/F-003/F-004.
- **2026-04-13 16:34 UTC** - Remediation baseline hash captured for `/tmp/ifolp_wp05_remediate` runs.
- **2026-04-13 17:05 UTC** - H-001 executed and rejected (no parity impact).
- **2026-04-13 17:32 UTC** - H-002 executed (MSCL cell-size scaling in Phase B), with measurable anchor improvement.
- **2026-04-13 17:58 UTC** - Full reruns complete; deterministic final hash confirmed.
- **2026-04-13 18:07 UTC** - Final cargo gates passed.
- **2026-04-13 18:10 UTC** - Post-test disposition completed for remediation cycle 1.
- **2026-04-13 18:25 UTC** - Iterative remediation mode formalized with anti-retest controls and active hypothesis loop.
- **2026-04-13 18:37 UTC** - H-004 immediate parity run completed (`parity-report.h004.json`); canonical hash unchanged (`2ef1aff...`).
- **2026-04-13 18:40 UTC** - Post-parity review rejected H-004 and reverted tie-break code path (no retained behavior change).
- **2026-04-13 18:47 UTC** - Full retained-state reruns (`run1`/`run2`) reconfirmed canonical hash stability (`2ef1aff...`) and final cargo gates passed.
- **2026-04-13 22:40 UTC** - Second clean-room TopAZ source investigation completed with line-level contract evidence (NETFUL/PRUNE/unit conversion/runtime-contract gaps).
- **2026-04-13 23:05 UTC** - Added second-investigation artifact and deficiency classification with no unclassified high/medium ambiguities.
- **2026-04-13 23:20 UTC** - Updated IFOLP specification and WP-05 disposition/tracker with H-005+ follow-on hypotheses.
- **2026-04-13 23:35 UTC** - Manual map QA discovery documented: full-extent candidate/oracle stage mismatch can mislead visual parity interpretation; basin-masked metrics added.
- **2026-04-14 00:15 UTC** - H-009 retained-state reruns stabilized at canonical hash `07e351537eb91525d85cf922f41c89bcc8ee12dc415ad2d078e159f27db93dc1` (anchor exact).
- **2026-04-14 00:55 UTC** - Provenance-aligned H-005 probe produced deterministic low residual FP-only deltas (probe hash `cd013e16...`).
- **2026-04-14 01:20 UTC** - Stakeholder accepted current Rust implementation as effectively parity-equivalent; WP-05 marked closed.

## Decisions Log

### 2026-04-13 17:05 UTC: Reject H-001 cadence expansion
**Context**: H-001 changed repass trigger to fire on any junction inflow drop.

**Decision**: Revert H-001.

**Impact**: Preserved spec-aligned pass cadence; no parity regressions/changes introduced.

### 2026-04-13 17:32 UTC: Keep H-002 Phase B threshold scaling
**Context**: H-002 introduced cell-size-scaled MSCL comparison in Phase B.

**Decision**: Retain H-002 as best bounded remediation from cycle 1.

**Impact**: Anchor mismatch reduced from `803` to `392`; blackwood count delta improved from `+146` to `+121`; gatecreek remained effectively unchanged.

### 2026-04-13 18:10 UTC: Close cycle-1 with low residual hard-blocked findings
**Context**: Full reruns and final gates passed, but F-003/F-004 parity drift remained high and deterministic.

**Decision**: Close remediation cycle-1 with explicit low-severity hard-block dispositions.

**Impact**: No unresolved high/medium findings; residual risk preserved with evidence.

### 2026-04-13 18:25 UTC: Reopen WP-05 as iterative hypothesis loop with anti-retest gate
**Context**: Additional parity remediation is required; prior cycle closure alone does not resolve residual F-003/F-004 drift.

**Decision**: Continue WP-05 under iterative mode and require unique change fingerprints plus retry-gate evidence for any repeated attempt.

**Impact**: Prevents duplicate experiments and keeps subsequent parity work traceable and incremental.

### 2026-04-13 18:40 UTC: Reject H-004 tie-break path
**Context**: H-004 changed receiver-group epsilon tie handling to prefer latest encounter.

**Decision**: Reject and revert H-004.

**Impact**: No parity/report/hash movement was observed; retained code state remains H-002-only.

### 2026-04-13 23:05 UTC: Classify second clean-room deficiencies and patch specification
**Context**: Residual F-003/F-004 drift remained hard-blocked after H-004 rejection; root-cause attribution needed stronger behavioral contracts.

**Decision**: Land a specification-only second clean-room enhancement that formalizes oracle/provenance/runtime/unit/pass/ordering/acceptance contracts and explicitly classifies all high/medium ambiguities.

**Impact**: Root-cause investigation is now governed by explicit contracts; remaining uncertainty is isolated to provenance/runtime evidence gaps and queued as H-005+.

### 2026-04-14 01:20 UTC: Close WP-05 on effective parity acceptance
**Context**: Retained-state IFOLP reached anchor exact parity and deterministic behavior; provenance-aligned non-anchor probes reduced residuals to low FP-only deltas and stakeholder accepted equivalence.

**Decision**: Close WP-05 with effective parity disposition and defer runtime-identity/provenance-governance hardening to H-006+ follow-on work.

**Impact**: No unresolved high/medium issues remain for WP-05; package exits iterative remediation mode.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Residual parity drift persists without threshold provenance backfill | Low | Medium | Captured as accepted low residual for WP-05; defer governance hardening to H-006+ | Accepted (WP-05 closed) |
| Duplicate experiment churn without new signal | Medium | Medium | Enforce change fingerprints + retry-gate criteria in `hypothesis_log.md` | Mitigated (policy active) |
| Overfitting behavior to narrow fixture set | Medium | Low | Keep bounded changes and require full deterministic reruns before retaining | Mitigated |
| Review before evidence could hide regressions | Medium | Low | Preserve strict order: modification -> parity -> review | Mitigated |
| Oracle runtime identity remains ambiguous under snapshot-only capture | Medium | Medium | Add native-runtime oracle manifest capture path (H-006) | Open |
| Full-extent parity interpretation can conflate basin behavior with background encoding stage differences | Medium | Medium | Add basin-masked diagnostic metrics (alongside canonical full-extent metrics) to WP-00/05 reporting | Mitigated (protocol updated 2026-04-13) |

## Verification Checklist

### Package Governance
- [x] Package scaffold follows `docs/work-packages/README.md` layout.
- [x] ExecPlan structure follows `docs/prompt_templates/codex_exec_plans.md`.
- [x] Tracker/hypothesis artifacts include anti-retest controls.

### Iterative Remediation Gates
- [x] Each new hypothesis has a unique fingerprint before edits begin.
- [x] Any repeated fingerprint includes explicit retry-gate evidence.
- [x] Parity evidence is captured immediately after each hypothesis modification.
- [x] Post-test code review/disposition is recorded for each executed hypothesis.
- [x] Full run1/run2 determinism hash is captured for retained change sets.
- [x] `cargo check -p whitebox_tools` and targeted IFOLP tests pass for retained change sets.

## Progress Notes

### 2026-04-13 18:10 UTC: Cycle-1 remediation closeout
**Agent/Contributor**: Codex

**Work completed**:
- Executed remediation sequence end-to-end under active ExecPlan.
- Maintained hypothesis + mismatch disposition artifacts with experiment-level evidence.
- Applied one retained bounded code change (H-002) in Phase B plus targeted test coverage.
- Re-ran full parity campaign (`run1`/`run2`) and confirmed canonical determinism.
- Ran required final cargo gates.

**Cycle-1 parity snapshot (run1/run2 identical)**:
- `blackwood_60_5`: `differing_cell_count=4467`, `stream_delta=+121`
- `clueless_aftertaste_anchor_10_100`: `differing_cell_count=392`, `stream_delta=-42`
- `gatecreek_10m_30_2`: `differing_cell_count=65949`, `stream_delta=-5575`

### 2026-04-13 18:25 UTC: Iterative mode activation
**Agent/Contributor**: Codex

**Work completed**:
- Reopened WP-05 for additional parity convergence on residual mismatches.
- Added anti-retest governance (fingerprints, supersession, retry gates).
- Added active iteration ExecPlan and updated package/tracker references.

**Next expected output**:
- H-004+ experiment entry with parity report evidence and explicit disposition.

### 2026-04-13 18:40 UTC: H-004 cycle complete (rejected)
**Agent/Contributor**: Codex

**Work completed**:
- Activated H-004 in `hypothesis_log.md` with unique fingerprint.
- Implemented bounded tie-break change and added/updated focused topology tests.
- Ran immediate parity compare (`parity-report.h004.json` + canonical).
- Performed post-parity review/disposition and reverted H-004 due zero impact.

**H-004 parity snapshot (run1)**:
- `blackwood_60_5`: unchanged (`differing_cell_count=4467`, `stream_delta=+121`)
- `clueless_aftertaste_anchor_10_100`: unchanged (`differing_cell_count=392`, `stream_delta=-42`)
- `gatecreek_10m_30_2`: unchanged (`differing_cell_count=65949`, `stream_delta=-5575`)

**Retained-state verification after revert**:
- `run1`/`run2` canonical hashes reconfirmed equal (`2ef1aff3842e2a7b0ac31a04464d78bdf56efa83cdd8b2794704930c454a0845`).
- Final gates rerun and passed:
  - `cargo check -p whitebox_tools`
  - `cargo test -p whitebox_tools iterative_first_order_link_prune -- --nocapture`

### 2026-04-13 23:20 UTC: Second clean-room spec enhancement complete
**Agent/Contributor**: Codex

**Work completed**:
- Performed a second clean-room investigation against `/workdir/topaz` and WP-00/WP-05 parity harness artifacts.
- Produced `second_clean_room_analysis.md` covering all required contracts (provenance, runtime, units, numeric decisions, Phase A/B behavior, ordering, divergence localization, topology decomposition, sensitivity, acceptance metrics).
- Patched `/workdir/weppcloud-wbt/docs/iterative-first-order-link-prune/specification.md` with neutral behavior contracts derived from source-level evidence.
- Updated `mismatch_disposition.md` with second-investigation closure state and root-cause confidence per F-002/F-003/F-004.

**Key outcomes**:
- No F-002 regression signal under CSA/MSCL/epsilon perturbation checks.
- Residual F-003/F-004 remain hard-blocked primarily by non-anchor provenance/runtime uncertainty.
- All high/medium ambiguities are now explicitly classified and tied to H-005+ follow-on hypotheses.

### 2026-04-13 23:35 UTC: Basin-mask interpretation update from manual map QA
**Agent/Contributor**: Codex

**Work completed**:
- Validated that oracle rasters are channel-only (`1` + `NoData`) while candidate rasters are full-extent binary (`0/1`), which can mislead visual comparison when unmasked.
- Computed basin-masked diagnostics (`bound.tif > 0`) and documented in `mismatch_disposition.md`.

**Basin-masked run1 snapshot**:
- `gatecreek_10m_30_2`: candidate `12048` vs oracle `47810` (`delta=-35762`, `FP=0`, `FN=35762`)
- `clueless_aftertaste_anchor_10_100`: candidate `124` vs oracle `341` (`delta=-217`, `FP=0`, `FN=217`)

**Interpretation**:
- Candidate is over-pruned relative to oracle within basin for these fixtures.

### 2026-04-13 23:50 UTC: WP-00 apples-to-apples protocol update landed
**Agent/Contributor**: Codex

**Work completed**:
- Updated WP-00 fixture/compare tooling to stage `bound.tif` as basin mask and default parity comparison to basin domain.
- Updated WP-00 protocol docs (`fixture-catalog`, `parity-metrics-spec`, `topaz-oracle-manifest`, `determinism-report`) and refreshed deterministic canonical hash evidence.
- Updated WBT implementation-plan WP-00 row with basin-mask comparison contract and v2 canonical hash.

**Validation**:
- `/tmp/ifolp_wp00/run1` + `/tmp/ifolp_wp00/run2` canonical hash stable at `f5dd0c560bb766278526f15100efe33faade5a4fc7485510058246bc10276f9d`.

### 2026-04-14 01:20 UTC: Effective parity closure accepted
**Agent/Contributor**: Codex

**Work completed**:
- Executed additional hypotheses H-009/H-010/H-011 with immediate parity evidence and disposition updates.
- Re-ran full run1/run2 retained-state parity with deterministic canonical stability:
  - `07e351537eb91525d85cf922f41c89bcc8ee12dc415ad2d078e159f27db93dc1`
- Executed provenance-aligned non-anchor threshold probe (H-005) and confirmed deterministic cross-run probe hash:
  - `cd013e16c16f14ac00e4c8b1b2b4cf9c325449bd54a74cd6fd640f37f183beb5`
- Recorded stakeholder acceptance that current Rust behavior is effectively parity-equivalent for WP-05.

**Closure snapshot**:
- Retained-state manifest contract: anchor exact parity; non-anchor deterministic residuals documented.
- Provenance-aligned probe contract: low FP-only residuals (`blackwood=8`, gatecreek best neighborhood floor `13`).
