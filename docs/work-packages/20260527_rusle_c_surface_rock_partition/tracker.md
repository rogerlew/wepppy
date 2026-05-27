# Tracker - RUSLE C Surface-Rock Partition Implementation

> Living document tracking progress, decisions, risks, and communication for this work package.

## Quick Status

**Timezone**: UTC  
**Started**: 2026-05-27 21:42 UTC  
**Current phase**: Planning complete / implementation-ready  
**Last updated**: 2026-05-27 22:20 UTC  
**Next milestone**: Begin implementation across UI, rq-engine, and RUSLE runtime with targeted regressions  
**Security impact**: `low`  
**Dedicated security review**: `no`  
**Security artifact**: `N/A`
**Parameterization ADR**: `docs/adrs/ADR-0003-rusle-observed-rap-surface-rock-partition.md`

## Task Board

### Ready / Backlog

- [ ] Implement observed RAP C partition formula and manifest provenance recording.
- [ ] Add UI control (`rock_fraction_of_rap_bare`) and verification guidance messaging.
- [ ] Wire payload contract through controller JS, rq-engine route allowlist, and schema defaults.
- [ ] Add focused regressions and run targeted validation.
- [ ] Close package docs and archive ExecPlan on completion.

### In Progress

- [ ] Implement observed RAP C partition formula and manifest provenance recording.
- [ ] Add UI control (`rock_fraction_of_rap_bare`) and verification guidance messaging.
- [ ] Wire payload contract through controller JS, rq-engine route allowlist, and schema defaults.
- [ ] Add focused regressions and run targeted validation.

### Blocked

- [ ] None.

### Done

- [x] Specification and ADR contracts established for surface-rock partition behavior before implementation package kickoff (2026-05-27 21:42 UTC).
- [x] Prepared work-package scaffold and active ExecPlan for implementation (2026-05-27 21:42 UTC).
- [x] Dispatched independent review agent on package/plan quality and risk coverage (2026-05-27 21:48 UTC).
- [x] Dispositioned review findings and updated package/tracker/ExecPlan contracts (2026-05-27 21:51 UTC).

## Timeline

- **2026-05-27 21:42 UTC** - Package scaffolded and tracker initialized.
- **2026-05-27 21:48 UTC** - Independent review completed (1 High, 2 Medium, 2 Low findings).
- **2026-05-27 21:51 UTC** - Findings disposition documented and package acceptance/validation criteria tightened.
- **2026-05-27 22:20 UTC** - Auto-default contract revised to `cosurffrags` primary with `cfvo` fallback and RAP-bare normalization.

## Decisions Log

### 2026-05-27 21:42 UTC: Scope implementation to `observed_rap` only
**Context**: Surface-rock partition requirement is specific to RAP bare-ground interpretation and should not perturb `scenario_sbs` behavior.

**Options considered**:
1. Apply partitioning to both `observed_rap` and `scenario_sbs`.
2. Implement for `observed_rap` only and keep `scenario_sbs` unchanged.
3. Delay all implementation until a spatialized surface-rock map exists.

**Decision**: Option 2.

**Impact**: Matches the specification and ADR, keeps package size bounded, and avoids unscoped behavior drift in `scenario_sbs`.

### 2026-05-27 22:20 UTC: `auto` source precedence revised to `cosurffrags` first
**Context**: `rock_fraction_of_rap_bare` is a surface-cover control in `C`; SSURGO `cosurffrags` is a closer proxy to surface fragments than profile-volumetric `cfvo`.

**Options considered**:
1. Keep `cfvo` as sole `auto` proxy.
2. Use `cosurffrags` primary, `cfvo` fallback, then `0.0`.
3. Remove `auto` and require explicit user entry.

**Decision**: Option 2.

**Impact**: Improves scientific defensibility of defaulting while preserving deterministic fallback behavior and explicit user override.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Misinterpreting proxy defaults as canonical surface-rock truth | High | Medium | Explicit UI guidance + manifest/source provenance + `auto` labeled proxy only | Open |
| Payload drift across JS/API/controller layers | Medium | Medium | Add route + JS contract tests and schema-default checks | Open |
| Overlooked regressions in existing RAP/SBS mode switching | Medium | Medium | Add focused controller JS tests for mode-specific payload behavior | Open |

## Review Findings Disposition

Review artifact: `artifacts/20260527_independent_review.md`  
Disposition artifact: `artifacts/20260527_findings_disposition.md`

| Finding | Severity | Disposition | Status |
|------|----------|-------------|--------|
| Missing explicit boundary/error contract tests for `rock_fraction_of_rap_bare` | High | Accepted; added acceptance and planned regression matrix for `<0`, `>1`, non-numeric, and `auto` with `cosurffrags`/`cfvo`/fallback paths, plus canonical error-path handling | Closed (planning) |
| `schema_defaults_routes` scope not explicit in validation plan | Medium | Accepted; added explicit scope + validation command target for `test_rq_engine_schema_defaults_routes.py` | Closed (planning) |
| `auto` fallback semantics not pinned in acceptance language | Medium | Accepted; pinned fallback contract to `0.0` with explicit manifest fallback annotation when proxy sources are unavailable | Closed (planning) |
| PROJECT tracker WIP counters inconsistent | Low | Accepted; reconciled tracker counters to current active package count | Closed |
| Package tracker next-steps stale / ADR linkage not visible | Low | Accepted; updated task board, next milestone, and explicit ADR link in quick status | Closed |

## Verification Checklist

### Code Quality
- [ ] Targeted Python and JS tests pass for touched modules.
- [ ] No broad regression in touched RUSLE routes/controllers.

### Security
- [x] Security impact triage recorded (`low`) with rationale.
- [ ] Attack-surface contract reviewed for new user input field handling.

### Documentation
- [x] Package docs and active ExecPlan created.
- [x] Tracker updated with review and disposition outcomes.
- [x] Parameterization ADR linkage recorded.

### Testing
- [ ] Unit/regression tests added for new partition logic.
- [ ] Route payload tests include new field acceptance and filtering.
- [ ] Controller JS tests assert payload and guidance behavior.

## Progress Notes

### 2026-05-27 21:42 UTC: Package Initialization
**Agent/Contributor**: Codex

**Work completed**:
- Created package scaffold (`package.md`, `tracker.md`, `prompts/active/`, `artifacts/`).
- Drafted package scope, objectives, risks, and validation targets.
- Prepared active ExecPlan path for implementation.

**Blockers encountered**:
- None.

**Next steps**:
- Begin implementation milestones in active ExecPlan.
- Add regression tests for boundary/error paths and schema defaults contract.
- Run targeted validation gates after code edits.

**Test results**: Not run yet (docs scaffolding stage).

### 2026-05-27 21:51 UTC: Independent Review + Disposition
**Agent/Contributor**: Codex (+ delegated reviewer agent)

**Work completed**:
- Dispatched independent review and captured findings (1 High, 2 Medium, 2 Low).
- Updated package acceptance criteria to include explicit input validation/error contract coverage.
- Pinned `auto` fallback semantics to `0.0` when proxy data are unavailable, with manifest reason requirement.
- Added explicit schema-default test coverage target.
- Reconciled `PROJECT_TRACKER.md` WIP counters.

**Blockers encountered**:
- None.

**Next steps**:
- Implement code changes per active ExecPlan.
- Add and run targeted regressions.

**Test results**:
- `wctl doc-lint --path docs/work-packages/20260527_rusle_c_surface_rock_partition`
- `wctl doc-lint --path PROJECT_TRACKER.md`

### 2026-05-27 22:20 UTC: Proxy Source Contract Revision
**Agent/Contributor**: Codex

**Work completed**:
- Updated spec + ADR + package docs to use SSURGO `cosurffrags` as primary `auto` proxy source.
- Preserved deterministic fallback chain: `cosurffrags -> cfvo -> 0.0`.
- Clarified control-domain conversion rule: normalize proxy total-surface cover into fraction-of-RAP-bare space by division (with zero-bare guard), not multiplication.

**Blockers encountered**:
- None.

**Next steps**:
- Implement code-path support for `cosurffrags` retrieval and aggregation.
- Add regression coverage for `auto` source precedence and RAP-bare normalization behavior.

**Test results**:
- `wctl doc-lint --path docs/work-packages/20260527_rusle_c_surface_rock_partition --path docs/adrs/ADR-0003-rusle-observed-rap-surface-rock-partition.md --path wepppy/nodb/mods/rusle/specification.md`
