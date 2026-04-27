# Tracker - Peridot Runtime Contract Hardening

> Living document tracking progress, decisions, risks, validation, and handoffs for Peridot CLI error-contract and sub-field CSV schema hardening.

## Quick Status

**Timezone**: UTC
**Started**: 2026-04-26 22:51 UTC
**Current phase**: Closed
**Last updated**: 2026-04-27 01:26 UTC
**Next milestone**: None; follow-up is optional Peridot binary deployment if requested
**Security impact**: `none`
**Dedicated security review**: `no`
**Security artifact**: `N/A`

## Task Board

### Ready / Backlog
- [ ] None.

### In Progress
- [ ] None.

### Blocked
- [ ] None.

### Done
- [x] Package scaffold created with package brief, tracker, active ExecPlan, compatibility artifact, and root tracker registration (2026-04-26 22:51 UTC).
- [x] Milestone 1: Hardened `abstract_watershed` and `wbt_abstract_watershed` CLI error propagation.
- [x] Milestone 2: Disambiguated Peridot `field_flowpaths.csv` headers.
- [x] Milestone 3: Added WEPPpy compatibility normalization for new and historical field-flowpath CSV schemas.
- [x] Milestone 4: Updated Peridot and WEPPpy documentation for canonical field-flowpath schema and CLI error contract.
- [x] Milestone 5: Ran targeted Peridot and WEPPpy tests and captured validation artifact.
- [x] Milestone 6: Updated package closure notes and root tracker lifecycle.

## Timeline

- **2026-04-26 22:51 UTC** - Package created from two documented Peridot follow-up items.
- **2026-04-26 22:54 UTC** - Package scaffold validated with `wctl doc-lint` and `git diff --check`.
- **2026-04-26 23:07 UTC** - Runtime/schema hardening implemented, targeted validation passed, package moved to Done.

## Decisions Log

### 2026-04-26 22:51 UTC: Track Peridot runtime work in a WEPPpy work package
**Context**: The implementation targets Peridot, but the defects were discovered while aligning Peridot documentation for WEPPpy and one fix requires WEPPpy post-processing compatibility.

**Options considered**:
1. Track only in Peridot.
2. Track under WEPPpy work packages while explicitly listing Peridot as the implementation repo.

**Decision**: Option 2.

**Impact**: WEPPpy agents can discover and coordinate the cross-repo contract work, while Peridot remains the source of runtime changes.

---

### 2026-04-26 22:51 UTC: Preserve parent `topaz_id` and rename the duplicate flowpath column
**Context**: `field_flowpaths.csv` currently emits two `topaz_id` headers. WEPPpy post-processing reads `topaz_id` as the parent hillslope/subcatchment ID.

**Options considered**:
1. Rename the first `topaz_id` to `parent_topaz_id` and the second to `flowpath_topaz_id`.
2. Keep the first `topaz_id` for compatibility and rename only the second duplicate to `flowpath_topaz_id`.
3. Keep duplicate headers and document parser-specific behavior.

**Decision**: Option 2.

**Impact**: New outputs become unambiguous while preserving the main downstream column name. Historical pandas-mangled `topaz_id.1` remains supported through WEPPpy normalization.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| CLI tests assert implementation text rather than observable non-zero behavior | Medium | Medium | Added injected CLI wrapper tests that assert returned `io::Error` propagation | Closed |
| CSV header rename breaks consumers expecting pandas `topaz_id.1` | Medium | Medium | Kept parent `topaz_id`; normalized historical `topaz_id.1` to `flowpath_topaz_id` in WEPPpy | Closed |
| Scope expands into binary deployment or queue wiring | Medium | Low | Kept deployment/rebuild out of scope unless explicitly requested | Closed |
| Peridot dirty release binaries obscure docs/code diffs | Low | Medium | Continue ignoring preexisting `target/release/*` modifications unless deployment is in scope | Open |
| Peridot full `cargo test` has unrelated library-test failures | Low | Medium | Resolved in Peridot commit `e09f54c`; full suite passes locally | Closed |

## Hardening Signal Log

- **Baseline health signals**:
  - Peridot docs now identify CLI error propagation as a runtime gap.
  - Peridot docs now identify duplicate `field_flowpaths.csv` `topaz_id` headers as a schema gap.
- **Post-change health signals**:
  - Peridot CLI wrapper tests propagate injected `io::Error` failures.
  - Peridot `field_flowpaths.csv` schema test verifies unique headers and `flowpath_topaz_id`.
  - WEPPpy sub-field tests verify new schema, historical `topaz_id.1` normalization, and ambiguous mixed-schema rejection.
- **Danger signals observed**: None yet.
- **Temporary callus register**: None.
- **Softening experiments**: Not applicable.

## Verification Checklist

### Code Quality
- [x] Peridot targeted Rust tests pass.
- [x] WEPPpy targeted pytest suite passes.
- [x] `git diff --check` passes in both repos.

### Security
- [x] Security impact triage recorded (`none`) with rationale.
- [x] Dedicated security review artifact not required.
- [x] No implementation changes expand into attack-surface areas.

### Documentation
- [x] Peridot output contract updated.
- [x] Peridot migration/operations docs updated if affected.
- [x] WEPPpy AgFields/data-table docs updated if affected.
- [x] Work-package tracker and validation artifacts updated.
- [x] `wctl doc-lint --path PROJECT_TRACKER.md --path docs/work-packages/20260426_peridot_runtime_contract_hardening` passes.

### Testing
- [x] Peridot regression test covers CLI propagated-error behavior.
- [x] Peridot regression test covers unique `field_flowpaths.csv` headers.
- [x] WEPPpy regression test covers new `flowpath_topaz_id` CSV input.
- [x] WEPPpy regression test covers historical pandas-mangled `topaz_id.1` CSV input.
- [x] Backward compatibility behavior is recorded in artifact.

### Deployment
- [x] Binary rebuild/deployment decision recorded.
- [x] Binary rebuild was out of scope; no target paths or deployment validation commands were required.

## Progress Notes

### 2026-04-26 22:51 UTC: Package scoping
**Agent/Contributor**: Codex

**Work completed**:
- Created package scaffold under `docs/work-packages/20260426_peridot_runtime_contract_hardening/`.
- Authored package brief, tracker, active ExecPlan, and compatibility/regression plan artifact.
- Registered package in `PROJECT_TRACKER.md` backlog.
- Confirmed Peridot has preexisting dirty release binaries under `target/release/`; package plan excludes them unless deployment is requested.

**Blockers encountered**:
- None.

**Next steps**:
1. Start Milestone 1 in `/home/workdir/peridot`.
2. Design observable CLI error-propagation regression test before changing code.
3. Implement CSV header cleanup and WEPPpy normalization tests.

**Test results**:
- `wctl doc-lint --path PROJECT_TRACKER.md --path docs/work-packages/20260426_peridot_runtime_contract_hardening` passed (`5 files validated, 0 errors, 0 warnings`).
- `git diff --check` passed.

### 2026-04-26 23:07 UTC: Implementation and closeout
**Agent/Contributor**: Codex

**Work completed**:
- Updated Peridot CLI wrappers to propagate abstraction `io::Result<()>` errors.
- Renamed the duplicate field-flowpath CSV header to `flowpath_topaz_id`.
- Added WEPPpy normalization for canonical `flowpath_topaz_id` and historical pandas-mangled `topaz_id.1`.
- Updated Peridot and WEPPpy docs for the final schema and CLI error contract.
- Moved package lifecycle to Done in `PROJECT_TRACKER.md`.

**Blockers encountered**:
- None.

**Next steps**:
1. Rebuild and deploy Peridot binaries only if an operator requests deployment scope.
2. Keep the preexisting dirty `target/release/*` binaries out of source commits unless deployment is explicitly included.

**Test results**:
- Peridot targeted tests passed: `cargo test --test watershed_parquet_manifest --test field_flowpaths_schema --bin abstract_watershed --bin wbt_abstract_watershed`.
- Peridot full `cargo test` failed in unrelated library tests (`support::support::tests::{test_invalid_start_distance,test_invalid_end_distance}` and `rasters::raster::tests::{test_indices_of,test_unique_values,test_mask}`).
- WEPPpy targeted tests passed: `wctl run-pytest tests/topo/test_peridot_runner_wait.py tests/topo/test_peridot_sub_fields_schema.py`.
- Peridot `git diff --check` passed.

### 2026-04-27 01:26 UTC: Full-suite follow-up closed
**Agent/Contributor**: Codex

**Work completed**:
- Re-ran Peridot full `cargo test` after follow-up Peridot commit `e09f54c` (`Fix Peridot full-suite regressions`).
- Confirmed the earlier support interpolation panic-expectation failures and raster fixture/GDAL open failures are closed.
- Updated the validation artifact and risk table so benchmark planning no longer treats these failures as open blockers.

**Blockers encountered**:
- None.

**Next steps**:
1. Leave `/home/workdir/peridot/target/release/*` binaries unstaged unless an operator explicitly includes rebuild/deployment scope.
2. Use the clean Peridot source/test baseline as a prerequisite for the Peridot-vs-Python benchmark work package.

**Test results**:
- Peridot full suite passed: `cargo test` reported `23` library tests, `2` CLI-wrapper unit tests, `14` integration tests, and `1` doctest passing.
- Warning-only unused imports remain in unrelated test modules.

## Watch List

- **Peridot target binaries**: `/home/workdir/peridot/target/release/abstract_watershed` and `wbt_abstract_watershed` are dirty before this package. Do not stage or overwrite them unless deployment enters scope.
- **CSV schema compatibility**: Preserve parent `topaz_id`; normalize historical `topaz_id.1`; fail on ambiguous mixed schemas.
- **CLI test quality**: Prefer behavioral exit-code tests over source-text checks.

## Communication Log

### 2026-04-26 22:51 UTC: User follow-up package request
**Participants**: User, Codex
**Question/Topic**: Prepare a work package for Peridot CLI hardening and sub-field CSV schema cleanup.
**Outcome**: Package scaffolded and registered for future execution.
