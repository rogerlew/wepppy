# Tracker - AgFields Routing Scheme Suite

> Living record for Concept 1, Concept 2, hybrid routing, and the selectable
> scheme workflow.

## Quick Status

**Timezone**: UTC

**Started**: 2026-07-14 15:37 UTC

**Current phase**: Discovery and feasibility gating

**Last updated**: 2026-07-14 16:08 UTC

**Next milestone**: Prove Concept 1 plan fit and hybrid residual-area composition
on representative parents before accepting ADR-0019

**Security impact**: `high`

**Dedicated security review**: `yes`

**Security artifact**:
`docs/work-packages/20260714_ag_fields_routing_scheme_suite/artifacts/2026-07-14_security_review.md`

## Task Board

### Ready / Backlog

- [ ] Extend the Peridot connectivity CLI additively with deterministic
  per-sub-field detail output and version/provenance coverage.
- [ ] Build `ofe_plan.parquet` for the dev project and compare candidate Concept 1
  fits, including rejection rates and area/buffer/order error.
- [ ] Prove a residual-area Concept 1 source for mixed hybrid parents without
  uniform whole-parent scaling or area overlap.
- [ ] Complete and accept ADR-0019 with explicit numeric parameters and decision
  provenance.
- [ ] Add explicit-breakpoint slope segmentation and focused wepppyo3 tests.
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

- [ ] Milestone 1 feasibility spike: freeze input/output schemas, generate the
  first Concept 1 planning census, and validate mixed-parent residual geometry.

### Blocked

None. UI production wiring is gated by feasibility evidence and ADR-0019
acceptance, but the feasibility work can begin immediately.

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

## Timeline

- **2026-07-14 15:37 UTC** - Package opened after the connectivity inventory found
  3,269 of 6,626 retained sub-fields (49.3%) directly connected to a channel.

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
| Arbitrary field mosaics do not fit a defensible one-dimensional OFE plan | High | Medium | Measure fit/rejection census first; reject ineligible parents with reason codes; accept thresholds through ADR-0019 | Open |
| Hybrid residual geometry double-counts or omits source area | High | Medium | Parent-level ownership plan, exact area identities, source manifest, and generated closure tests | Open |
| Connectivity classifier is reimplemented inconsistently | High | Low | Extend and invoke the owned Peridot classifier; do not duplicate its D8/channel logic in Python | Open |
| Run All overwhelms worker memory | High | Medium | Independent jobs chained serially with `allow_failure=True`; retain measured RSS evidence | Open |
| Scheme clear escapes its fixed directory | High | Low | Enum-to-slug allowlist, resolved-path/symlink checks, and cross-scheme deletion tests | Open |
| Legacy clients or projects lose Concept 2 behavior/state | High | Low | Omitted scheme maps to Concept 2; additive state migration; immutable legacy tree | Open |
| Users treat engineering schemes as scientifically equivalent | Medium | Medium | Description-first labels, limitations/manifests, side-by-side evidence, and Mariana-owned disposition | Open |
| MOFE management scenario limits reject valid-looking plans | Medium | Medium | Preflight the actual slope and management limits; expose reason codes and counts | Open |

## Verification Checklist

### Code Quality

- [ ] Focused Python tests pass through `wctl run-pytest`.
- [ ] Peridot and wepppyo3 Rust tests and formatting checks pass.
- [ ] Frontend Jest tests and lint pass.
- [ ] Stubs and changed-file broad-exception checks pass.
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
- [ ] AgFields README, UI contract, API docs, output docs, package, tracker, and
  ExecPlan reflect as-built behavior.

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
