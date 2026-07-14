# Tracker - AgFields Routing Scheme Suite

> Living record for Concept 1, Concept 2, hybrid routing, and the selectable
> scheme workflow.

## Quick Status

**Timezone**: UTC

**Started**: 2026-07-14 15:37 UTC

**Current phase**: Blocked at the native WEPP management feasibility gate

**Last updated**: 2026-07-14 19:08 UTC

**Next milestone**: Decide whether to open a WEPP `nmscen > 20` binary-limit work
package or revise ADR-0019's faithful all-parent routing contract

**Security impact**: `high`

**Dedicated security review**: `yes`

**Security artifact**:
`docs/work-packages/20260714_ag_fields_routing_scheme_suite/artifacts/2026-07-14_security_review.md`

## Task Board

### Ready / Backlog

- [ ] Implement Concept 1 input synthesis, hillslope execution, watershed rerun,
  manifests, and generated fixture coverage.
- [ ] Refactor Concept 2 behind the common scheme-root interface while preserving
  the completed weighted accounting kernel.
- [ ] Implement hybrid pure/mixed parent planning, source composition, failures,
  and closure diagnostics.
- [ ] Add per-scheme NoDb state and safe, backward-compatible legacy hydration.
- [ ] Add scheme-aware RQ/API orchestration, stable `all` expansion, job-id mapping,
  serial dependency edges, and route/graph tests.
- [ ] Implement the four description-first UI choices and per-scheme status,
  staleness, clear, and browse behavior.
- [ ] Complete focused/broad validation and generated-output comparison on
  `sacral-self-discipline`.
- [ ] Complete QA, security, compatibility, and Mariana handoff artifacts.

### In Progress

None. The package is stopped at its explicit feasibility gate.

### Blocked

- [ ] Production Concept 1 and hybrid execution: 141 of 1,869 Concept 1 parents
  and 59 of 1,644 hybrid residual parents require 21-24 referenced yearly
  management scenarios after exact structural deduplication; the supported native
  WEPP maximum is 20.
- [ ] ADR-0019 acceptance and Milestones 3-7 user-facing wiring: continuing would
  require an explicitly validated WEPP binary-limit expansion or an owner-approved
  revision to the no-fallback/all-parent fidelity contract.

### Done

- [x] Opened a separate implementation package and active ExecPlan (2026-07-14
  15:37 UTC).
- [x] Recorded the description-first UI labels, machine identifiers, filesystem
  slugs, Concept 2 compatibility default, and `all` expansion (2026-07-14 15:37
  UTC).
- [x] Recorded the hybrid double-counting prohibition and explicit feasibility
  gate for residual Concept 1 geometry (2026-07-14 15:37 UTC).
- [x] Drafted the compatibility plan, security gate, and ADR-0019 (2026-07-14
  15:37 UTC).
- [x] Passed Markdown lint/link checks, heading extraction, spelling preview,
  whitespace validation, and the root AGENTS size gate for the scaffold
  (2026-07-14 16:08 UTC).
- [x] Extended Peridot with deterministic per-sub-field connectivity detail and
  preserved its aggregate output contract (recorded 2026-07-14 19:08 UTC).
- [x] Added and release-tested explicit-breakpoint slope segmentation in
  wepppyo3, including the WEPPpy wrapper (recorded 2026-07-14 19:08 UTC).
- [x] Completed corrected Concept 1 and hybrid planner censuses with every source
  represented, positive field overlap, and exact raster-area closure (2026-07-14
  19:08 UTC).
- [x] Proved real mixed parent 102 with a runnable 3,600 m2 residual source,
  1,800 m2 connected source, 5,400 m2 combined PASS, and zero water/sediment
  closure residual across 6,210 events (recorded 2026-07-14 19:08 UTC).
- [x] Completed exact management feasibility preflight and recorded the native
  20-scenario blocker in the package evidence and proposed ADR-0019 (2026-07-14
  19:08 UTC).

## Timeline

- **2026-07-14 15:37 UTC** - Package opened after the connectivity inventory found
  3,269 of 6,626 retained sub-fields (49.3%) directly connected to a channel.
- **2026-07-14 17:01 UTC** - End-to-end execution began from the active ExecPlan;
  unrelated dirty files in WEPPpy and generated Peridot release binaries were
  explicitly excluded from package scope.
- **2026-07-14 19:08 UTC** - Milestones 1 and 2 evidence completed. The package
  stopped before UI/API/RQ wiring because the current WEPP binary cannot parse all
  faithful Concept 1/hybrid managements.

## Decisions Log

### 2026-07-14 15:37 UTC: Reopen Concept 1 and add a per-sub-field hybrid

**Context**: Concept 2 preserves independent sub-field balances but bypasses
downslope buffer routing. Only about half of the dev project's sub-fields satisfy
the direct-channel condition that makes outlet injection most credible.

**Options considered**:

1. Keep Concept 2 as the only scheme - simplest, but leaves 3,357 non-connected
   sub-fields with the known outlet-injection limitation.
2. Replace Concept 2 with Concept 1 - improves represented buffer interaction for
   eligible layouts but loses the stronger independent-source fidelity where
   direct channel injection is defensible.
3. Implement Concept 1, retain Concept 2, and add a hybrid - supports direct
   comparison and applies each approximation by sub-field connectivity.

**Decision**: Implement all three selectable schemes. The hybrid uses Concept 2
for channel-connected sub-fields and Concept 1 for the others.

**Impact**: Concept 1 is no longer deferred. The completed Concept 2 package
remains historical evidence; this package owns the new multi-scheme interface and
artifact layout.

### 2026-07-14 15:37 UTC: Use description-first labels and fixed scheme slugs

**Context**: Internal concept numbers do not tell users what a scheme does or what
scientific limitation it carries.

**Decision**: Use the exact labels in `package.md`. Persist machine identifiers
`concept_1`, `concept_2`, and `hybrid`; write filesystem slugs `concept-1`,
`concept-2`, and `hybrid`. The UI-only value `all` expands to all three and does
not create an `all/` tree.

**Impact**: UI, API, NoDb, RQ, manifests, and directories have one explicit mapping.
Concept 2 remains the omitted-value/default behavior for old clients and projects.

### 2026-07-14 15:37 UTC: Serialize Run All as three independent jobs

**Context**: The completed Concept 2 dev run peaked at about 6.88 GB. Running all
schemes concurrently would unnecessarily multiply memory pressure, while a single
aggregate job would obscure independent failures and retries.

**Decision**: Enqueue one job per scheme. For `all`, use the stable order Concept
1, Concept 2, hybrid and RQ dependency edges with `allow_failure=True` so later
schemes still execute after an earlier failure without overlapping their peak
memory. Return an additive scheme-to-job-id mapping.

**Impact**: Each scheme has independent terminal state, retry, browse, and clear
behavior. RQ dependency catalog/graph changes and regression coverage are required.

### 2026-07-14 15:37 UTC: Reject double-counted hybrid composition

**Context**: Adding connected sub-field PASS sources to an unchanged full-area
Concept 1 parent would represent the connected area twice. Uniformly scaling a
whole-parent Concept 1 result down to residual area would also distort the
non-connected/background geometry and process response.

**Decision**: A mixed parent must generate a Concept 1 source that represents only
the residual parent geometry, then merge it with connected sub-field PASS sources
using the existing weighted combiner. If that residual geometry is not defensible,
hybrid preflight fails explicitly. No silent fallback or uniform full-parent scale
is allowed.

**Impact**: Residual-geometry feasibility is the first implementation gate. It may
constrain hybrid eligibility, but cannot silently change scheme semantics.

### 2026-07-14 15:37 UTC: Preserve legacy Concept 2 artifacts in place

**Context**: The completed implementation writes the unscoped
`wepp/ag_fields/watershed/{runs,output,manifest}` layout.

**Decision**: New runs write scheme subdirectories. Existing unscoped artifacts
remain immutable and readable as legacy Concept 2 evidence; no automatic move or
delete is part of this package.

**Impact**: State hydration and browse behavior must distinguish historical
Concept 2 evidence from a current `concept-2` scheme run.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
| --- | --- | --- | --- | --- |
| Arbitrary field mosaics do not fit a defensible one-dimensional OFE plan | High | Medium | Preserve agreement/error distributions for Mariana; the engineering planner represents every source but does not invent a science cutoff | Measured |
| Hybrid residual geometry double-counts or omits source area | High | Medium | Parent-level ownership plan, exact area identities, source manifest, and generated closure tests | Fixture passed |
| Connectivity classifier is reimplemented inconsistently | High | Low | Extend and invoke the owned Peridot classifier; do not duplicate its D8/channel logic in Python | Mitigated |
| Run All overwhelms worker memory | High | Medium | Independent jobs chained serially with `allow_failure=True`; retain measured RSS evidence | Open |
| Scheme clear escapes its fixed directory | High | Low | Enum-to-slug allowlist, resolved-path/symlink checks, and cross-scheme deletion tests | Open |
| Legacy clients or projects lose Concept 2 behavior/state | High | Low | Omitted scheme maps to Concept 2; additive state migration; immutable legacy tree | Open |
| Users treat engineering schemes as scientifically equivalent | Medium | Medium | Description-first labels, limitations/manifests, side-by-side evidence, and Mariana-owned disposition | Open |
| MOFE management scenario limits reject valid-looking plans | High | Confirmed | Open a binary-limit augmentation package or revise the fidelity contract; do not drop sources or fall back silently | Blocking |

## Verification Checklist

### Code Quality

- [x] Focused Python tests pass through `wctl run-pytest`.
- [x] Peridot and focused wepppyo3 Rust tests pass; Peridot retains two
  unrelated unused-import warnings.
- [ ] Peridot formatting passes. The wepppyo3 package formatting gate reports
  preexisting drift in `catalog.rs` and `parquet.rs`; neither changed
  `mofe.rs` nor `lib.rs` appears in its diff.
- [ ] Frontend Jest tests and lint pass.
- [x] Updated stub and changed-file broad-exception checks pass.
- [ ] Full `wctl run-pytest tests --maxfail=1` gate passes.

### Security

- [x] Security impact triage and dedicated artifact created.
- [ ] Auth, CSRF/JWT scope, enum input validation, run-tree boundaries, queue
  dependencies, subprocess arguments, locking, and partial-failure recovery are
  reviewed.
- [ ] No unresolved medium/high findings remain.

### Documentation and Governance

- [x] Authoritative usersum decision contract updated.
- [x] Artifact compatibility plan written before schema changes.
- [x] ADR-0019 drafted with current decision provenance.
- [ ] ADR-0019 accepted with exact fit parameters before wired behavior.
- [x] The authoritative design, package, tracker, root board, proposed ADR, and
  ExecPlan reflect the measured feasibility stop; deferred UI/API docs remain
  unchanged because those paths were not wired.

### Testing

- [ ] Synthetic Concept 1 layout and failure-mode fixtures pass.
- [ ] Pure and mixed hybrid parent fixtures close area, water, and sediment.
- [ ] API omission, one-scheme, all-scheme, invalid-scheme, job dependency, clear,
  stale, and partial-failure cases pass.
- [ ] Legacy Concept 2 state/artifact compatibility passes.
- [ ] Generated all-scheme run completes on `sacral-self-discipline` with protected
  artifacts byte-identical.

### Deployment and Evaluation

- [ ] Current native binaries are built, provenance-stamped, and exercised by the
  wired path.
- [ ] Dev compose RQ/API/UI smoke passes through authenticated routes.
- [ ] Mariana receives the three-scheme comparison bundle and records scientific
  disposition separately from engineering acceptance.

## Progress Notes

### 2026-07-14 19:08 UTC: Feasibility evidence complete; production suite blocked

**Agent/Contributor**: Codex

**Work completed**:

- Peridot now emits one deterministic topology-classification row for each of the
  6,626 retained sub-fields; its prior summary contract is unchanged.
- The corrected dev-project planner census represented every field with 1-20
  OFEs and exact raster-area closure. Fit/error distributions are recorded as
  science diagnostics rather than hidden rejection thresholds.
- The native explicit-breakpoint slope kernel, WEPPpy wrapper, input synthesis
  spike, and opt-in management graph deduplication have focused coverage.
- A real mixed parent produced runnable native WEPP output and exact area,
  event-water, and event-sediment closure.
- Exact full-project management preflight found 141 Concept 1 and 59 hybrid
  residual parents above native `nmscen = 20`.

**Blockers encountered**: The supported WEPP hillslope binary cannot parse the
required 21-24 referenced yearly scenarios. The prior MOFE NSCEN work explicitly
deferred widening the relevant fixed-array/common-block contracts.

**Next steps**: Obtain a decision to execute a separate binary-limit augmentation
package or revise ADR-0019's routing coverage/fidelity contract. Do not wire the
scheme choices while the ADR remains Proposed.

**Evidence**:
`artifacts/2026-07-14_concept1_feasibility.md` contains input hashes, distributions,
coverage, runtime/RSS, mixed-parent proof, release provenance, and the stop
rationale.

**Test results**: 33 focused WEPPpy tests, 46 Peridot tests, 43 focused
wepppyo3 Rust tests, and 9 wepppyo3 release Python tests passed. Stubtest,
changed-file broad-exception enforcement, code-quality observability,
`git diff --check`, Peridot formatting, and Markdown lint/heading extraction also
passed. wepppyo3 package formatting reports unrelated preexisting drift in
`catalog.rs` and `parquet.rs`; the touched source files are not in that diff. A
broad wepppyo3 workspace `cargo test -q` was additionally attempted and hit the
known host PyO3/libpython linker environment; the crate-local command required by
the repository guide passed all 43 tests.

### 2026-07-14 17:01 UTC: End-to-end execution started

**Agent/Contributor**: Codex

**Work completed**:

- Re-read the active ExecPlan, compatibility plan, security gate, ADR, and nearest
  repository instructions.
- Inspected WEPPpy, Peridot, and wepppyo3 worktrees before implementation.
- Confirmed that the existing Peridot connectivity CLI is committed and its only
  dirty files are unrelated generated release binaries.

**Blockers encountered**: None.

**Next steps**:

- Extend the canonical Peridot analysis with deterministic detail rows.
- Freeze the planner schemas and implement the Concept 1 feasibility census.
- Prove the mixed-parent residual source and update ADR-0019 with evidence-backed
  parameters before user-facing wiring.

**Test results**: Not yet run for implementation; this note records the clean
execution boundary.

### 2026-07-14 15:37 UTC: Package scaffolding and contract freeze

**Agent/Contributor**: Codex

**Work completed**:

- Created the package, active self-contained ExecPlan, compatibility plan,
  security-review gate, and proposed ADR-0019.
- Updated the authoritative AgFields design decision and root package trackers.
- Locked the scheme IDs/slugs, exact UI labels, compatibility default, output-tree
  layout, hybrid classifier, and no-double-counting rule.

**Blockers encountered**: None. Concept 1 fit and residual hybrid geometry are
known feasibility questions and are the first milestone, not external blockers.

**Next steps**:

- Extend Peridot detail output and generate the dev-project routing census.
- Implement the Concept 1 plan spike and mixed-parent residual composition proof.
- Update ADR-0019 with measured parameters and seek decision-owner acceptance.

**Test results**: `wctl doc-lint` passed with zero errors/warnings for all 12
changed Markdown files. `markdown-extract --all '.*'` parsed all headings,
`git diff --check` passed, spelling preview was applied only to the two new-file
normalizations it identified, and `tools/check_agents_size.sh AGENTS.md` passed.

## Watch List

- **Concept 1 eligible-area fraction**: A working implementation may still be too
  restrictive for a general UI option if many parents fail the fit gate.
- **Mixed-parent residual background**: Parents with connected, non-connected, and
  uncovered cells are the most important hybrid fixture.
- **OFE/scenario caps**: The management scenario ceiling may bind before the
  current slope segmentation cap.
- **Legacy result presentation**: Historical Concept 2 evidence must remain visible
  without being mistaken for a current scheme result.

## Communication Log

### 2026-07-14 15:37 UTC: Scheme suite requested

**Participants**: Roger Lew, Codex

**Question/Topic**: The 49.3% channel-connectivity result was lower than hoped, so
the user requested Concept 1, a per-sub-field Concept 1/2 hybrid, selectable
one-or-all UI behavior, composable directories, and descriptive option labels.

**Outcome**: The package is open with those requirements as normative contracts.
