# Tracker – WBT Least-Cost Unresolved-Depression Fail-Fast Guidance

> Living status, decisions, risks, and handoff record for this work package.

## Quick Status

**Timezone**: UTC
**Started**: 2026-07-30 17:11 UTC
**Current phase**: Validation / rollout handoff
**Last updated**: 2026-07-30 18:10 UTC
**Next milestone**: Deploy WEPPpy and WBT together to Forest for a canary
**Security impact**: `low`
**Dedicated security review**: `no`
**Security artifact**: N/A

## Task Board

### Ready / Backlog

- [x] Capture a minimized, licensed/provenanced incident fixture or a durable
  fixture-generation procedure from
  `/wc1/runs/sr/srivas42-reconciled-turf/dem/dem.tif`.
- [x] Run the forked binary with identical inputs and `--fill=true` /
  `--fill=false`; record output, metadata/stdout, unsolved count, deltas, and
  downstream D8 result.
- [x] Ratify the contract-first decision and add the parameterization ADR.
- [x] Implement the narrow typed unresolved-depression failure at the accepted
  ownership boundary.
- [x] Propagate the controlled failure through RQ without stacktrace-oriented
  user messaging or successful readiness/timestamps.
- [x] Add instructional channel delineation summary copy and controller tests.
- [x] Update user, developer, and operator documentation.
- [x] Validate the exact incident, a solvable least-cost DEM, corrected retry,
  partial-artifact cleanup, and compatibility cases.
- [x] Complete code and QA reviews and disposition all findings.
- [ ] Deploy to Forest, observe a canary, then roll out with a documented
  rollback.

### In Progress

- [ ] Deploy WEPPpy and WBT commit
  `b4d8774e3375ffd86a487c172f84e0d3f8a6cc50` together to Forest, observe a
  canary, then roll out with a documented rollback.

### Blocked

- [ ] None.

### Done

- [x] Verified the production run log records `breach_least_cost`,
  `wbt_blc_dist=1000`, and `blc_fill=True` (2026-07-30 17:11 UTC).
- [x] Verified upstream documentation and fork source semantics: `--fill`
  fills unresolved depressions; omitting it does not by itself create an error
  (2026-07-30 17:11 UTC).
- [x] Located the WEPPpy wrapper, RQ, UI controller, current user guidance, and
  related Topaz/boundary hardening packages (2026-07-30 17:11 UTC).
- [x] Pushed WBT source commit `17ebe99d92210679f120e83033920109eb99a767`
  and runtime commit `b4d8774e3375ffd86a487c172f84e0d3f8a6cc50`
  to `origin/master` (2026-07-30 17:37 UTC).
- [x] Exact runtime reproduction returns
  `WBT_UNRESOLVED_DEPRESSIONS count=377 max_dist_cells=33`, exit code 1, and
  no canonical output (2026-07-30 17:37 UTC).
- [x] Targeted pytest passed (83 tests), full Jest passed (750 tests), ESLint
  passed, and test-stub validation passed (2026-07-30 17:37 UTC).
- [x] Removed duplicate controlled guidance from the preformatted stacktrace
  container; the normal summary is now the sole instructional presentation
  (2026-07-30 18:10 UTC).

## Decisions Log

### 2026-07-30 17:11 UTC: Preserve fail-fast intent; do not assume flag semantics

**Context**: The requested outcome is an informative failure instead of a
roughly 450 m fill. Whitebox documents `--fill` as a remaining-depression fill
flag. The fork increments `num_unsolved`, skips the fill block when the flag is
absent, writes the raster, and returns success.

**Options considered**:

1. Set `fill=false` only — smallest delta, but does not establish the requested
   error and may defer failure or invalid output to downstream tools.
2. Make the fork return a stable error when unresolved depressions remain —
   strongest ownership near the diagnostic, but changes a general tool
   contract and requires wrapper/CLI compatibility review.
3. Keep fork behavior and add a WEPPpy postcondition using stable tool output
   or machine-readable diagnostics — narrower application scope, but only safe
   if the unresolved count is reliably available without parsing brittle prose.

**Decision**: Keep options 2 and 3 open until the reproduction milestone.
Reject option 1 as sufficient acceptance behavior.

**Impact**: Implementation cannot begin by changing one boolean alone.

### 2026-07-30 17:11 UTC: User guidance must offer choices, not automatic fallback

**Decision**: The controlled failure should recommend increasing the least-cost
distance, enlarging/repositioning the DEM extent, inspecting DEM/NoData edges,
or deliberately choosing another conditioning method. It must not silently
change parameters or algorithms.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|---|---|---:|---|---|
| `fill=false` succeeds with unresolved pits | High | Confirmed | Native opt-in pre-write failure implemented | Mitigated |
| Downstream D8 accepts a bad surface | High | Medium | Validate and stop before downstream acceptance | Open |
| General fork behavior breaks other callers | High | Medium | Opt-in flag preserves omitted-flag behavior | Mitigated |
| Partial artifacts look successful | High | Medium | Pre-write failure plus canonical cleanup regression | Mitigated |
| Guidance recommends ineffective retries | Medium | Medium | Test each recommended recovery on incident/fixtures | Open |
| Scientific default changes without provenance | High | Medium | ADR gate before merge | Open |

## Hardening Signal Log

- **Baseline health signals**: Incident path completes and publishes channel
  artifacts despite the extreme fill.
- **Post-change health signals**: Controlled failure on the incident fixture;
  no completed timestamp; successful corrected retry; stable unaffected runs.
- **Danger signals observed**: The prior fill fallback raised terrain by up to
  379.16178369142 m and left 377 pits unresolved before filling.
- **Temporary callus register**: None.

## Verification Checklist

### Contract and parameterization

- [x] Contract-first authority and ancestor checkpoint identified.
- [x] ADR records exact old/new behavior and decision provenance.
- [x] Compatibility and rollback behavior approved.

### WBT and Python

- [x] `cargo check -p whitebox-tools-app`
- [x] Targeted `BreachDepressionsLeastCost` tests pass.
- [x] `cargo test -p whitebox-tools-app`
- [x] Both Python wrappers remain synchronized and compile.
- [x] Incident generated-output comparison captured.

### WEPPpy / WEPPcloud

- [x] Targeted NoDb/topo/RQ tests pass with `wctl run-pytest`.
- [ ] `wctl check-rq-graph` passes if queue wiring changes; catalog updated if
  any enqueue/dependency edge changes.
- [x] Controller unit tests pass with `wctl run-npm test`.
- [x] Frontend lint passes with `wctl run-npm lint`.
- [x] Controller bundles are rebuilt when source changes.
- [x] Full `wctl run-pytest tests --maxfail=1` passes or blocker is recorded.

### Documentation and review

- [x] Affected docs pass scoped `wctl doc-lint`.
- [x] User guidance describes the no-silent-fallback contract.
- [x] Code review and QA review artifacts are complete.
- [ ] Forest canary, rollback, and 30-day observation owner are recorded.

## Progress Notes

### 2026-07-30 17:11 UTC: Discovery and scaffold

**Agent/Contributor**: Codex

**Work completed**:

- Read current Whitebox documentation and fork source.
- Inspected the production run log and WEPPpy call path.
- Identified the hypothesis mismatch: `fill=false` does not itself make the
  Whitebox tool fail.
- Scoped the package, tracker, active ExecPlan, ADR gate, compatibility plan,
  recovery guidance, and related packages.

**Blockers encountered**:

- No implementation blocker. ADR provenance remains required before merge.

**Next steps**:

1. Execute Milestone 1 in the active ExecPlan.
2. Ratify fork-level versus WEPPpy-level ownership.
3. Amend canonical contracts and draft the ADR before production code edits.

**Test results**: Documentation-only discovery; validation pending.

### 2026-07-30 17:37 UTC: Implementation and local validation

**Agent/Contributor**: Codex

**Work completed**:

- Added and pushed the native opt-in pre-write failure plus runtime binary.
- Wired typed WEPPpy translation, stale product cleanup, controlled RQ
  metadata, and summary guidance with diagnostic values and error ID.
- Reproduced the exact incident against the installed runtime.
- Rebuilt generated status-stream output and completed local gates.

**Validation finding**:

- The first broad pytest run found a string-based monkeypatch that failed
  after the import-hygiene suite removed `wepppy.topo` from the parent package
  namespace. The test now patches its already-imported module object; the
  import-hygiene-plus-targeted sequence passes.

**Next steps**:

1. Deploy the coupled WEPPpy/WBT versions to Forest.
2. Record canary and observation evidence.

**Final local gate**:

- Repeated broad pytest passed: 5,745 passed, 58 skipped, 1,024 warnings in
  639.07 seconds.

### 2026-07-30 18:10 UTC: Single instructional summary follow-up

The live controlled message exposed that guidance appeared both in the normal
summary and in the preformatted stacktrace body, where heading styles forced
uppercase presentation. Controlled failures now publish `FAILED` rather than
`EXCEPTION`, render once in the normal summary, and leave the details panel
empty and collapsed. Unexpected failures retain their existing traceback
presentation.

## Watch List

- **Current `disturbed9002_wbt` default**: This configuration now defaults to
  Topaz conditioning, while persisted/explicit least-cost selections remain
  supported. Scope acceptance around the actual least-cost path, not only the
  current config default.
- **Boundary-policy overlap**: Reuse the controlled WBT failure and retry
  semantics from `20260729_user_preferences_wbt_boundary`; do not create a
  second incompatible error presentation.
