# Geneva Implementation Plan
Status: Active (execution not started)  
Last Updated: 2026-04-14  
Owner: WEPPpy NoDb hydrology stack  
Primary Spec: `/workdir/wepppy/wepppy/nodb/mods/geneva/specification.md`

## Purpose
This document is the execution board for implementing Geneva end to end across `wepppy` and `wepppyo3`.
It breaks work into bounded work-packages that agents can carry through code, tests, QA review, security review, and manual integration checks.

## Scope Boundary
In scope:
- Geneva NoDb mod implementation in `wepppy`.
- Geneva compute kernel implementation in `wepppyo3`.
- API/task/report integration in WEPPcloud.
- Test and review evidence for each completed package.

Out of scope:
- Changes to Culvert-at-risk.
- Reservoir routing (deferred by specification).
- Non-US taxonomy support in v1.

## State Model
### Work-package state
- `not_started`
- `in_progress`
- `blocked`
- `in_review`
- `done`

### Gate state
- `pending`
- `running`
- `pass`
- `fail`
- `waived` (requires explicit risk acceptance in notes)

## Agent Orchestration Protocol
1. Claim exactly one `not_started` package with all dependencies `done` by updating this board row.
2. Implement scope-complete code for that package only.
3. Add or update tests for the exact changed behavior.
4. Run required gates and record concrete command evidence.
5. Complete QA + security review checklists for the package.
6. Run manual integration checks when listed for that package.
7. Update board row to `in_review`, then `done` after review findings are resolved.

## Review Disposition (2026-04-14)
| Finding ID | Severity | Disposition | Plan Action |
| --- | --- | --- | --- |
| H1 | High | fix_now | Add WP-00 blocking gate: conformance deviation table must be dispositioned before WP-01. |
| H2 | High | fix_now | Keep cell-level HSG mapping/fallback in Rust kernel; Python HSG collaborator is provenance/orchestration only. |
| H3 | High | fix_now | Add collapsed-vs-uncollapsed hydrologic-impact acceptance checks for default collapse path. |
| M1 | Medium | fix_now | Clarify override semantics as watershed-level `default_hsg_code` only in v1. |
| M2 | Medium | fix_now | Keep `neh4_type_b` as only accepted v1 distribution; reserve others. |
| M3 | Medium | fix_now | Add `antecedent_condition_source` to CN schema and downstream artifact expectations. |
| M4 | Medium | fix_now | Add explicit NoDb-only negative tests for WBT/US guardrails. |
| M5 | Medium | fix_now | Add conditional frontend lint/test gates when WP-08 introduces or modifies report UI assets. |
| L1 | Low | fix_now | Section numbering order corrected in specification for stable navigation references. |
| L2 | Low | fix_now | `run_batch` payload example and one-of timing/null semantics were clarified. |

## Global Gates
Use these as defaults unless a package defines a stricter command set.

Core repo gates (`/workdir/wepppy`):
- `wctl run-pytest tests/nodb --maxfail=1`
- `wctl run-pytest tests --maxfail=1`
- `wctl check-rq-graph` (required when queue wiring changes)
- `wctl doc-lint --path wepppy/nodb/mods/geneva`
- `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master`
- when WP-08 touches report/query UI assets:
  - `wctl run-npm lint`
  - `wctl run-npm test`

Kernel repo gates (`/workdir/wepppyo3`):
- `cargo test -p geneva_core` (once crate exists)
- `cargo test -p cli_revision` (for PyO3 export coverage)
- `cargo fmt --check`
- `cargo clippy --all-targets -- -D warnings`

## Work-Package Board
| WP | Title | Depends On | Assignee | Target Date | State | Code Gate | Test Gate | QA Gate | Security Gate | Manual Int Gate | Evidence / Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| WP-00 | Orchestration bootstrap and fixtures | none | codex | 2026-04-14 | in_progress | running | running | pending | pending | pending | Bootstrap scaffold created: `work-packages/` + fixture manifest + starter test. Evidence: `work-packages/wp-00_orchestration_bootstrap_and_fixtures.md`. |
| WP-01 | `wepppyo3` Geneva kernel scaffold | WP-00 | unassigned | tbd | not_started | pending | pending | pending | pending | pending | Add `geneva_core` crate and PyO3 function stubs. |
| WP-02 | Rust HRU + HSG kernel (`prepare_hrus`) | WP-01 | unassigned | tbd | not_started | pending | pending | pending | pending | pending | Raster alignment, keying, fallback, `2 ha` collapse. |
| WP-03 | Rust CN rainfall-excess kernel | WP-01 | unassigned | tbd | not_started | pending | pending | pending | pending | pending | `lambda 0.20/0.05`, cumulative and incremental excess. |
| WP-04 | Frequency panel + NEH4 Type B kernel | WP-01 | unassigned | tbd | not_started | pending | pending | pending | pending | pending | CLIGEN always + NOAA when available, no synthetic fill. |
| WP-05 | SCS UH + hydrograph kernel | WP-03, WP-04 | unassigned | tbd | not_started | pending | pending | pending | pending | pending | `scs_triangular` + `scs_curvilinear`, mass/volume closure. |
| WP-06 | Geneva NoDb facade + collaborators | WP-02, WP-03, WP-04, WP-05 | unassigned | tbd | not_started | pending | pending | pending | pending | pending | Python orchestration and artifact IO. |
| WP-07 | CN table workflow + edit_csv integration | WP-06 | unassigned | tbd | not_started | pending | pending | pending | pending | pending | Run-scoped seed/init/reset/modify/meta/snapshot parity. |
| WP-08 | Routes, tasks, RQ wiring, query/report API | WP-06, WP-07 | unassigned | tbd | not_started | pending | pending | pending | pending | pending | Full endpoint family and payload schema conformance. |
| WP-09 | End-to-end integration and performance validation | WP-08 | unassigned | tbd | not_started | pending | pending | pending | pending | pending | Batch runs, dual-source matrix behavior, warning surfaces. |
| WP-10 | QA/security closeout and release readiness | WP-09 | unassigned | tbd | not_started | pending | pending | pending | pending | pending | Final findings closure and ship decision record. |

## Parallel Execution Lanes
Lane A (kernel foundation):
- WP-00 -> WP-01

Lane B (kernel implementation, parallel after WP-01):
- WP-02, WP-03, WP-04 in parallel
- WP-05 after WP-03 and WP-04

Lane C (NoDb and API integration):
- WP-06 after WP-02/WP-03/WP-04/WP-05
- WP-07 after WP-06
- WP-08 after WP-06 and WP-07

Lane D (validation and closeout):
- WP-09 after WP-08
- WP-10 after WP-09

## Work-Package Details
## WP-00 Orchestration bootstrap and fixtures
Scope:
- Create `work-packages/` evidence folder for Geneva (`wp-xx_*.md` records).
- Add baseline fixtures for small watershed runs (aligned rasters + expected metadata).
- Add golden reference metadata for deterministic comparisons.
- Record conformance-deviation dispositions (`DEV-001..DEV-004`) with rationale and evidence links before WP-01 starts.

Required tests:
- Fixture-load tests in `tests/nodb/mods/geneva/`.
- Schema validation tests for fixture metadata.

QA review checklist:
- Fixture coverage includes no-burn and burn-severity paths.
- Fixture docs explain provenance and expected limits.

Security review checklist:
- Fixtures contain no secrets or sensitive location data beyond approved public datasets.

Manual integration checks:
- Verify fixture set can be loaded by local dev stack without path rewrites.

Exit criteria:
- Fixture suite and evidence template are committed and passing.
- Conformance deviation disposition gate is completed and recorded.

## WP-01 `wepppyo3` Geneva kernel scaffold
Scope:
- Add `geneva_core` crate to workspace.
- Add modules and typed error contracts.
- Add `cli_revision` Geneva adapter entrypoints:
  - `geneva_prepare_hrus(...)`
  - `geneva_build_frequency_panel(...)`
  - `geneva_run_batch(...)`
  - `geneva_validate_uh(...)`

Required tests:
- Rust unit tests for type parsing and error mapping.
- PyO3 export smoke test for each entrypoint.

QA review checklist:
- No monolith growth in `cli_revision/src/lib.rs`; logic resides in module files.

Security review checklist:
- Boundary inputs reject malformed or missing required fields.
- No panic-based error control for user data paths.

Manual integration checks:
- Import module in Python environment and call each function with minimal valid payload.

Exit criteria:
- Crate scaffold merged with passing compile/tests/lint gates.

## WP-02 Rust HRU + HSG kernel (`prepare_hrus`)
Scope:
- Implement grid alignment checks on canonical `bound.tif` geometry metadata.
- Compute HRU keys from landuse + HSG + burn severity + hydrophobic class.
- Implement HSG fallback chain with provenance counters.
- Enforce deterministic minimum HRU area collapse (`2 ha` floor).

Required tests:
- Deterministic HRU keying tests.
- Fallback precedence tests (`coded_lookup` -> dominant/default -> unresolved policy).
- Collapse determinism and area-conservation tests.
- Default-collapse sensitivity tests (`allow_cross_hsg_merge=false`) for runoff depth, runoff volume, and peak discharge versus no-collapse references.
- Water HRU protection tests.

QA review checklist:
- Numeric outputs stable across repeated runs.
- Warnings/diagnostics match spec for unresolved and fallback cases.

Security review checklist:
- Raster dimensions and nodata handling are bounds-checked.
- Unexpected code values handled as explicit errors/warnings, not silent coercion.

Manual integration checks:
- Run `prepare_hrus` against one known noisy `hydgrpdcd` watershed and verify no sub-`2 ha` HRUs remain.

Exit criteria:
- HRU artifacts and diagnostics are produced per spec and test-validated.
- Default-collapse sensitivity thresholds are met for reference cases.

## WP-03 Rust CN rainfall-excess kernel
Scope:
- Implement CN transforms (`S`, `Ia`, `Q`) for `lambda=0.20` and `lambda=0.05`.
- Implement cumulative-to-incremental excess generation per HRU.
- Implement area-weighted composite excess hyetograph generation.

Required tests:
- Equation parity tests with fixed vectors and RMRS examples.
- `CN_0.05` cap behavior tests (`CN_0.20 > 98.5`).
- Composite excess closure tests.

QA review checklist:
- Unit consistency checks for SI/English conversions where applicable.

Security review checklist:
- Inputs validated for non-physical values (negative depth, zero duration where invalid).

Manual integration checks:
- Run a single-storm case and verify excess traces against expected golden series.

Exit criteria:
- CN kernel passes tolerance targets defined in specification.

## WP-04 Frequency panel + NEH4 Type B kernel
Scope:
- Build requested-vs-available matrix from:
  - `climate/wepp_cli_pds_mean_metric.csv` (required),
  - `climate/atlas14_intensity_pds_mean_metric.csv` (optional).
- Materialize available events with explicit unavailable reason codes.
- Implement NEH4 Type B ordinate scaling and interpolation.

Required tests:
- Matrix materialization tests for CLIGEN-only and dual-source modes.
- Reason-code correctness tests for unavailable cells.
- Hyetograph depth closure and monotonicity tests.

QA review checklist:
- No synthetic duration interpolation when unavailable.
- Datasource IDs and field naming match canonical enum set.

Security review checklist:
- CSV parsing failures return explicit typed errors.
- No path injection via source artifact references.

Manual integration checks:
- Build panel on a run with NOAA available and verify dual-source event count/reporting.

Exit criteria:
- Frequency panel artifact is reproducible and schema-conformant.

## WP-05 SCS UH + hydrograph kernel
Scope:
- Implement `scs_triangular` and `scs_curvilinear` UH generation.
- Implement excess-to-hydrograph convolution and summary metrics.
- Persist unit/equation provenance (`hf_constant`, unit system, method IDs).

Required tests:
- UH mass closure tests.
- Hydrograph volume closure tests.
- Peak and time-to-peak regression tests.

QA review checklist:
- Method selection behavior and defaults match specification.

Security review checklist:
- Prevent divide-by-zero and invalid timing parameter runtime failures via explicit validation.

Manual integration checks:
- Compare hydrograph summary metrics for one golden storm against expected tolerances.

Exit criteria:
- Hydrograph outputs meet acceptance tolerances and provenance requirements.

## WP-06 Geneva NoDb facade + collaborators
Scope:
- Implement `wepppy/nodb/mods/geneva/geneva.py` facade and collaborator modules.
- Wire Rust kernel calls for HRU prep, frequency panel, and batch run.
- Persist required Geneva artifacts and status lifecycle fields.

Required tests:
- Unit tests for collaborator responsibilities and facade contract behavior.
- Integration tests for state transitions (`idle -> prepared -> running -> completed*`).
- NoDb-only guardrail negative tests:
  - non-WBT run rejection with canonical error envelope,
  - non-US/non-NLCD-HSG-compatible rejection with `unsupported_domain`.

QA review checklist:
- Collaborator boundaries follow NoDb facade/collaborator standard.
- Error envelope and status payloads conform to canonical contracts.

Security review checklist:
- Locking and state serialization preserve NoDb safety assumptions.
- No broad exception swallowing on production paths.

Manual integration checks:
- Prepare + run batch from UI/API against a small watershed and inspect generated artifacts.

Exit criteria:
- NoDb controller path is functional and test-covered without monolithic controller growth.

## WP-07 CN table workflow + edit_csv integration
Scope:
- Implement run-scoped `cn_table.csv` initialize/recreate/reset behavior.
- Implement modify/meta/snapshot endpoints with optimistic concurrency token.
- Integrate `controls/edit_csv.htm` workflow with disturbed parity semantics.

Required tests:
- Concurrency token success/conflict tests.
- Seed recreation and reset behavior tests.
- CN key resolution missing-row failure tests.

QA review checklist:
- User edit experience surfaces conflicts with actionable messaging.

Security review checklist:
- CSV mutation endpoints validate schema and reject malformed rows.

Manual integration checks:
- Edit CN table via UI, run a storm, and verify modified row effects in outputs.

Exit criteria:
- CN edit lifecycle is reliable, auditable, and exercised by tests.

## WP-08 Routes, tasks, RQ wiring, query/report API
Scope:
- Implement Geneva route family and task endpoints per specification.
- Implement report/query payload endpoints for interactive chart/table usage.
- Wire RQ jobs and dependency graph updates.

Required tests:
- Route contract tests for payload schemas and error envelopes.
- RQ job submission/status/result contract tests.
- Query/report payload shape tests.
- Route-level tests for WBT/US guards validate NoDb error propagation only (no duplicate route-layer domain logic).

QA review checklist:
- API docs and endpoint behavior are consistent.
- Partial-availability (`completed_with_gaps`) status is correctly surfaced.

Security review checklist:
- CSRF/session expectations preserved for browser routes.
- Task endpoints enforce run-scope authorization boundaries.

Manual integration checks:
- Full UI flow: enable mod -> prepare HRUs -> build panel -> run batch -> inspect report filters.

Exit criteria:
- Endpoint family is implemented and passes contract/integration tests.

## WP-09 End-to-end integration and performance validation
Scope:
- Run end-to-end scenarios for:
  - no-burn vs burn-severity inputs,
  - CLIGEN-only vs dual-source,
  - mixed available/unavailable matrix cells.
- Profile runtime for representative panel sizes and watershed sizes.
- Validate warning behavior for watershed size thresholds.

Required tests:
- End-to-end regression suites under `tests/nodb/mods/geneva/`.
- Performance regression harness with explicit runtime baselines.
- Collapsed-vs-uncollapsed end-to-end sensitivity checks for default collapse path (`allow_cross_hsg_merge=false`).

QA review checklist:
- Results are digestible and consistent with report/query design.
- Known limitations are documented in output/report assumptions.

Security review checklist:
- Performance safeguards cannot be bypassed to create resource exhaustion.

Manual integration checks:
- Manual run on at least two real run directories, including one with noisy `hydgrpdcd`.

Exit criteria:
- End-to-end behavior is validated with evidence and acceptable runtime profile.

## WP-10 QA/security closeout and release readiness
Scope:
- Consolidate package evidence and unresolved risks.
- Run final full gates in both repos.
- Record go/no-go recommendation with explicit rationale.

Required tests:
- Full repository test gates for touched areas.
- Re-run Geneva-focused suites after final merges.

QA review checklist:
- All package findings dispositioned.
- Documentation and runbook notes complete for operators and developers.

Security review checklist:
- No unresolved High findings.
- Medium findings documented with mitigation plan and owner.

Manual integration checks:
- Final release-candidate smoke run through Geneva report path.

Exit criteria:
- All WPs `done`, required gates `pass` (or formal waiver recorded), and release readiness note committed.

## Cadence and Board Hygiene
- Update this board for every state transition.
- Never mark a package `done` without evidence links in the row notes.
- If a package is `blocked`, record blocker owner and unblock target date.
- Keep package scope bounded; create a follow-on WP instead of expanding scope mid-flight.
