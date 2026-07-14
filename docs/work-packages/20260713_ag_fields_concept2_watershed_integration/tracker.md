# Tracker - AgFields Concept 2 Watershed Integration

> Living record for weighted PASS accounting, isolated watershed execution, and
> the scientific-evaluation handoff.

## Quick Status

**Timezone**: UTC

**Started**: 2026-07-13 19:37 UTC

**Current phase**: Engineering complete; Mariana scientific evaluation pending

**Last updated**: 2026-07-14 00:30 UTC

**Next milestone**: Mariana records the scientific-use disposition for the public
evaluation bundle

**Security impact**: `high`

**Dedicated security review**: `yes`

**Security artifact**: `artifacts/2026-07-13_security_review.md`

## Task Board

### Ready / Backlog

- [ ] Mariana reviews the public `sacral-self-discipline` evaluation bundle and
  records the scientific-use disposition.

### In Progress

None.

### Blocked

None. Mariana's evaluation follows engineering delivery and does not block starting
or implementing Concept 2.

### Done

- [x] Selected Concept 2, opened its implementation scope, assigned scientific
  evaluation to Mariana, and deferred Concept 1 (2026-07-13 19:37 UTC).
- [x] Inspected the current AgFields, Roads, RQ/API/UI, PASS parser/combiner, and
  dev-project contracts (2026-07-13 19:37 UTC).
- [x] Created the package, active ExecPlan, compatibility plan, proposed ADR, initial
  security review, and root tracker entry (2026-07-13 19:37 UTC).
- [x] Finalized every PASS field transformation and zero-volume rule, derived the
  serialization closure budgets, and accepted ADR-0018 (2026-07-13 21:02 UTC).
- [x] Implemented, exported, documented, built, and release-tested the weighted
  `wepppyo3` PASS API without changing Roads behavior (2026-07-13 21:17 UTC).
- [x] Implemented the isolated collaborator/facade, raster plan, parent
  materialization, versioned manifests, weighted combination, watershed rerun, and
  interchange pipeline (2026-07-13 21:48 UTC).
- [x] Added the fourth AgFields job and fifth runs-page stage, two authenticated
  routes, additive hydration/staleness/clear state, generated controller asset,
  dependency catalog/graph, and security disposition (2026-07-13 21:48 UTC).
- [x] Completed focused, frontend, native, docs, graph, stub, security, and
  repository-wide validation (2026-07-13 22:46 UTC).
- [x] Executed the authenticated real-project job, validated all closure/interchange
  contracts, proved the four source trees byte-identical, and published the public
  Mariana evaluation bundle (2026-07-14 00:30 UTC).

## Timeline

- **2026-07-13 19:37 UTC** - Package opened. Concept 2 became the sole implementation
  track; Concept 1 was explicitly deferred.
- **2026-07-13 19:37 UTC** - `/wc1/runs/sa/sacral-self-discipline` designated as the
  generated-output dev and scientific-evaluation project.
- **2026-07-13 21:02 UTC** - Milestone 1 completed with Accepted ADR-0018 and
  `artifacts/pass_field_semantics.md` as the normative field contract.
- **2026-07-13 21:17 UTC** - Milestone 2 completed; canonical py312 release exports
  the weighted API and its Rust/Python release tests pass.
- **2026-07-13 21:48 UTC** - Milestones 3-4 completed; real-project preflight and a
  one-parent executable/weighted rehearsal match the accepted contracts.
- **2026-07-13 22:46 UTC** - Milestone 5 completed; 4,833 repository tests, 85
  frontend suites/621 tests, security, docs, RQ graph, stub, and native release
  gates passed.
- **2026-07-14 00:14 UTC** - Final authenticated RQ job completed the isolated
  parent materialization, weighted combination, watershed rerun, and interchange.
- **2026-07-14 00:27 UTC** - Post-run immutable inventory matched the pre-run
  inventory across all 97,734 protected files; Milestone 6 engineering acceptance
  completed.

## Decisions Log

### 2026-07-13 19:37 UTC: Open Concept 2 and defer Concept 1

**Context**: Both concepts were feasible enough to plan, but Concept 2 retains the
independent sub-field simulations and their source accounting without quantizing
the field mosaic into parent-profile OFEs.

**Decision**: Implement Concept 2. Do not implement Concept 1 or require it as a
comparison fixture. Mariana Dobre performs the scientific evaluation after the
engineering result and evidence bundle exist.

**Impact**: Engineering acceptance uses area, water, sediment, parser, integration,
and generated-output gates. Concept 1 can be reopened only by a separate decision.

### 2026-07-13 19:37 UTC: Preserve all existing run artifacts

**Context**: The dev project has independent sub-field PASS files but its parent
PASS files were deleted after interchange because the parent setting is
`delete_after_interchange=true`.

**Decision**: Materialize current parent legacy PASS files by rerunning prepared
parent hillslope inputs inside `wepp/ag_fields/watershed/`. Never toggle the parent
setting or rewrite baseline and independent AgFields trees.

**Impact**: The feature works on the designated project and historical projects
with cleaned baseline PASS files. The manifest records that parent sources were
materialized, not silently recovered.

### 2026-07-13 19:37 UTC: Separate engineering and scientific acceptance

**Context**: Conservation and executable routing are engineering claims; buffer
effects and suitable scientific use require domain evaluation.

**Decision**: Close engineering milestones only on conservation, integration,
compatibility, security, and generated-output evidence. Label scientific
qualification pending until Mariana records her disposition.

**Impact**: No unreviewed delivery-ratio or buffer correction enters the build.

### 2026-07-13 23:07 UTC: Preserve signed deposition and native particle vectors

**Context**: The first two full RQ attempts exposed valid WEPP producer values that
synthetic fixtures had not represented: signed `tdep` from `sedseg.for`, and finite
nonnegative `frcflw` component vectors whose serialized sum is not exactly one.

**Decision**: Preserve signed `tdep` as an extensive quantity. Preserve each
particle-flow component through sediment-mass weighting without rejecting or
renormalizing a vector solely because its sum differs from one.

**Impact**: ADR-0018 and the semantic table match the producer/consumer contract.
The final native release SHA-256 is
`5d8e1251d84aed97af358d4473413b089a001de000523fbcd41bf9ffba864db3`.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
| --- | --- | --- | --- | --- |
| A PASS field is scaled with the wrong dimensional semantics | High | Medium | Required field-semantics table, WEPP source evidence, identities, reparse closure | Validated |
| Parent/sub-field calendars or climate files differ | High | Low | Resolve and compare climate sources, headers, row counts, and day keys; fail explicitly | Validated |
| Baseline cleanup leaves no parent PASS | High | Confirmed | Regenerate legacy PASS from current prepared inputs in the isolated workspace | Resolved |
| Large dev run causes excessive time/disk use | Medium | Medium | Hard-link/copy inputs, bounded worker count, retain only needed parent PASS, progress logs | Validated at 59m25s/6.88 GB peak |
| Partial runs are mistaken for current results | High | Low | Versioned source signature, terminal state, required-artifact checks, explicit clear/retry | Resolved |
| Outlet injection is interpreted as buffer routing | High | Medium | UI/docs/manifest warning and Mariana-owned scientific-use disposition | Scientific review pending |
| Queue or clear operations overlap | High | Low | Existing AgFields single-flight guard extended to the new job and route tests | Validated |

## Verification Checklist

### Native Kernel

- [x] Touched Rust sources pass targeted `rustfmt --check`; all-crate
  `cargo fmt --check` still reports unrelated preexisting formatting drift outside
  the touched files. `cargo test -p wepp_interchange_rust` passes 41 tests.
- [x] Existing Roads `combine_hillslope_pass_files` behavior and tests remain unchanged.
- [x] Canonical py312 release import and focused Python API tests pass.

### WEPPpy

- [x] Focused NoDb/AgFields collaborator tests pass through `wctl run-pytest`.
- [x] RQ and rq-engine AgFields route tests pass.
- [x] Frontend lint/Jest tests and regenerated controller bundle pass.
- [x] `wctl check-rq-graph`, stub checks, broad-exception gate, and docs lint pass.
- [x] Repository-wide `wctl run-pytest tests --maxfail=1` passes: 4,833 passed,
  60 skipped.

### Generated Output

- [x] Dev project input inventory and existing-artifact hashes are captured before
  execution.
- [x] Exactly one integrated PASS is staged per parent hillslope.
- [x] Area/source/event/run closure is within the accepted tolerance.
- [x] Watershed run and interchange resources complete under the isolated tree.
- [x] Existing baseline and independent AgFields artifacts remain byte-identical.
- [x] Evaluation bundle and limitations README are published in the public run for
  Mariana; her scientific disposition remains pending.

### Security and Documentation

- [x] ADR-0018 Accepted before merge.
- [x] Compatibility plan reflected in code/tests/docs.
- [x] Dedicated security review passes with no unresolved medium/high findings.
- [x] AgFields README, UI contract, usersum design, output docs, package, tracker,
  and ExecPlan describe as-built behavior.

## Progress Notes

### 2026-07-14 00:30 UTC: Real-project acceptance and public evaluation bundle

**Agent/Contributor**: Codex

**Work completed**:

- Executed three actual authenticated RQ attempts. Job
  `1c6a2bfd-2629-4a66-a273-a94fac7d9aa0` exposed valid signed `tdep`; job
  `f9045f70-2f59-44e9-964d-a728da6755d6` exposed valid non-unit-sum particle
  vectors. Both failures were corrected first in ADR-0018/semantics, then in the
  native kernel with regression tests.
- Exhaustively replayed the final native kernel over all 1,869 affected parents;
  every parent passed, with maximum event budget ratio `0.9999999999305551`.
- Final job `2fc269a6-12f8-4d74-a876-0619b2ea3cf7` ran from 23:15:08 to 00:14:33
  UTC (59 minutes 25 seconds) and finished. Peak observed unique allocation was
  6,884,441,600 bytes.
- Fixed the completed-state API path after acceptance exposed missing
  `RedisPrep`/`TaskEnum` imports, added the exact regression, restarted rq-engine,
  and verified through the public HTTPS API: job `finished`; state `completed`,
  `stale=false`.
- After the run was made public, a WEPPcloud recreation exposed missing CAP
  environment propagation in `docker-compose.dev.yml`. Aligned the dev settings
  with production, added a compose regression, and verified the public run URL
  returns HTTP 200 with the CAPTCHA gate.

**Generated-output evidence**:

- 3,543 parent PASS files and 3,543 preserved materialized parent PASS files.
- 10,169 source rows (6,626 sub-field plus 3,543 background), 11,606,490 event
  closure rows, and 1,869 run closure rows. There are zero budget violations; the
  maximum run ratio is `0.9990592207895048` and maximum event ratio is
  `0.9999999999305551`.
- All nine required interchange resources exist. Parent area closes exactly for
  all 3,543 parents; retained field area is 113,774,400 m2 across 176,981,400 m2 of
  affected parents, including 482 full-coverage parents.
- Pre/post protected inventories are identical: 97,734 files, 18,498,460,698
  bytes, zero missing/added/changed, SHA-256
  `198212dd58c9301b9d0b6bcd70c980e45b1c09b64374cc7db22dac8d28477426`.
  Both inventories are in
  `wepp/ag_fields/watershed/manifest/evaluation_evidence/`.

**Validation results**:

- WEPPpy full suite: 4,833 passed, 60 skipped. Frontend: 85 suites/621 tests and
  lint passed. Final native: 41 Rust tests and two release-tree Python tests passed.
- Final post-fix focused suites passed 121 tests; the CAP compose regression suite
  passed six tests.
- RQ graph/contract, stubs, broad exceptions, vulture, docs, pycompile, generated
  controller, and diff checks passed. Security review remains `pass` with no
  unresolved findings.

**Next steps**:

- Mariana records the scientific-use disposition; no further engineering work is
  required by this package.

### 2026-07-13 21:48 UTC: Isolated orchestration and fifth workflow stage

**Agent/Contributor**: Codex

**Work completed**:

- Added the `AgFieldsWatershedIntegrator` collaborator and thin NoDb facade with
  historical defaults, fixed isolated paths, short lock scopes, source/upstream
  signatures, terminal state, safe clear, and failure provenance.
- Implemented common-grid ownership/area planning, complete single-OFE parent
  materialization, climate-content proof, streaming versioned Parquet diagnostics,
  legacy watershed rerun, isolated interchange, `totalwatsed3`, and manifest docs.
- Added `agfields_run_watershed`, structured phases, two authenticated rq-engine
  routes, single-flight admission, state hydration, Stage 5 UI/browse/limitation,
  source stub updates, and the regenerated queue graph.
- Resolved all security-review findings; the gate is pass with no unresolved
  medium/high findings. Stage 5 deliberately does not alter `TaskEnum.run_ag_fields`.

**Test and rehearsal results**:

- Focused NoDb/RQ/route suites: 44 passed; AgFields pure-template selection: 3
  passed; focused Jest: 11 passed; frontend lint passed.
- `wctl check-rq-graph`: up to date; changed-file broad-exception gate passed.
- Read-only real plan reproduced 3,543/1,869/6,626 parent/affected/source counts,
  113,774,400 m2 field area, 176,981,400 m2 affected-parent area, 482 full
  coverage, and zero overcoverage.
- Parent 747 materialized in 0.93 seconds. Its nine-source, 6,210-row weighted PASS
  had zero area residual and maximum runoff event budget ratio 0.993884.

**Next steps**:

- Complete broad code/docs/frontend/stub gates, capture authoritative-tree hashes,
  and run the real job through the authenticated RQ/API surface.

### 2026-07-13 21:17 UTC: Weighted native kernel and release refresh

**Agent/Contributor**: Codex

**Work completed**:

- Added the stable `combine_weighted_hillslope_pass_files` PyO3 API and kept the
  Roads function signature and output path unchanged.
- Added typed source/header validation, exact source-area closure, header/calendar
  compatibility, semantic reconstruction, legacy formatting, atomic output,
  reparsed event/run closure, and bounded diagnostics.
- Corrected PASS Arrow metadata for particle fractions and groundwater volumes.
- Refreshed the canonical py312 extension and documented its provenance and
  SHA-256 `8c94041776a66968aab302ee20fa1b85d6e53c0b0ca3ffec234ffb84247b5d6f`.
- Published `wepppyo3` source commit `2779b41` and py312 release commit `96c028f`
  to `origin/main`.

**Test results**:

- `cargo test -p wepp_interchange_rust`: `39 passed; 0 failed`.
- Release-tree weighted API import: `ok`.
- `python3.12 -m pytest -q tests/wepp_interchange/test_weighted_hillslope_pass.py`:
  `1 passed`.
- Touched Rust files pass targeted `rustfmt --check`; full workspace formatting has
  preexisting drift in unrelated crate/test files and was not rewritten.

**Next steps**:

- Implement isolated AgFields orchestration and additive facade state.

### 2026-07-13 21:02 UTC: PASS semantics and ADR acceptance

**Agent/Contributor**: Codex

**Work completed**:

- Grounded header and row semantics against `wshpas.f90`, `wshred.for`,
  `sloss.for`, the HBP contract, and the owned Rust parser.
- Classified `gwbfv` and `gwdsv` as extensive m3 volumes and `clot` through `sdot`
  as unitless sediment particle fractions.
- Defined direct water/sediment closure and product-of-rounded-operands budgets
  from legacy five-significant-digit `E11.5`/`E10.5` serialization.
- Accepted ADR-0018 only after every header and row numeric had an explicit rule.

**Test results**:

- `wctl doc-lint` passed for the semantic table and ADR when invoked with the repo
  virtual environment on `PATH`.
- The default `/usr/local/bin/wctl` invocation lacked `typer`; the repository venv
  resolved the environment mismatch without changing dependencies.

**Next steps**:

- Implement and release-test the additive weighted native API.

### 2026-07-13 19:37 UTC: Package opening and fixture discovery

**Agent/Contributor**: Codex

**Work completed**:

- Converted the concept comparison into a selected implementation decision.
- Recorded Mariana as scientific evaluator and removed Concept 1 from active
  implementation and validation dependencies.
- Inspected the real project, current controller/RQ/UI surface, Roads precedent,
  and native PASS combiner.
- Authored the required planning/governance artifacts.

**Dev-project evidence**:

- 6,626 sub-field records and independent legacy PASS files.
- 1,869 affected parent hillslopes out of 3,543 total parent hillslopes.
- 113,774,400 m2 retained field area within 176,981,400 m2 affected parent area.
- No overcovered parent; 482 affected parents have full field coverage.
- `length * width` differs from raster area by at most `5.9e-11` m2.
- Parent `wepp/output` has no `H*.pass.dat`; interchange cleanup removed them.

**Next steps**:

- Confirm PASS writer semantics and accept ADR-0018.
- Implement the weighted native API before WEPPpy orchestration.

**Test results**: Documentation validation is recorded after package scaffolding.

## Watch List

- PASS header line 3 appears to be modeled area and must be parsed/validated rather
  than inferred only from Peridot `length * width`.
- `gwbfv` and `gwdsv` lack unit metadata in the current interchange schema.
- The parent project uses legacy ASCII PASS but deletes it after interchange; the
  isolated path must not depend on baseline retention settings.

## Communication Log

### 2026-07-13 19:37 UTC: Delivery ownership

**Participants**: Roger Lew, Codex

**Outcome**: Concept 2 implementation opened; Concept 1 deferred; Mariana Dobre
will perform the science evaluation; `sacral-self-discipline` is the dev project.
