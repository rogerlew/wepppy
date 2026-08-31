# Table Overflow Discoverability Contract Governance Review

**Decision ID**: `A11Y-TABLE-20260829-1`
**Review time**: 2026-08-29 01:40 UTC
**Starting revision**: `75eb240c8dbffea6beb639c9707821d3d877ac2d`
**Branch**: `feature/project-owned-config`
**Review mode**: independent, read-only governance and scope review
**Verdict**: **READY**

## Scope reviewed

- the complete package under
  `docs/work-packages/20260828_table_overflow_discoverability/`;
- the new canonical
  `docs/ui-docs/contracts/table-overflow-discoverability-contract.md`;
- the proposed deltas to `docs/ui-docs/ui-style-guide.md` and
  `docs/ui-docs/accessiblity.md`;
- the package entry and overlapping unrelated delta in `PROJECT_TRACKER.md`;
- `docs/standards/contract-first-change-standard.md` and the work-package
  security/correctness gates; and
- current branch, revision, staging state, changed-file inventory, and proposed
  implementation/test boundary.

The worktree remains at the recorded starting revision. No table-overflow or
slope-display production/test implementation exists or is staged. The worktree
contains 25 modified tracked paths plus the untracked canonical contract and
work package. The decision now inventories every unrelated dirty path and the
two overlapping documentation hunks.

## Authority disposition

The operator's direction to scaffold and execute this work package, together
with the explicit statement that the instruction is authority and no further
ratification is required, is sufficient authority for the exact bounded
behavior recorded in the decision. It permits preparation and local commit of a
compliant standalone contract checkpoint and subsequent implementation within
the accepted finite boundary. It does not authorize push, merge, deployment, or
production action. The current package preserves those exclusions.

At 2026-08-29 01:38 UTC the operator additionally authorized fixed three-decimal
HTML display of the exact `Slope` column in the Hillslope Summary and Channel
Summary tables. The checkpoint records this as presentation-only: raw numeric
sort keys, report/model/stored values, other columns, outlet output, and CSV
remain unchanged. This is not a parameterization change and does not require an
ADR. No further ratification is required unless behavior or scope expands.

## Findings

### A11Y-GOV-01 - Closed - Canonical ownership and pending conformance

The new contract under `docs/ui-docs/contracts/` is within the finite canonical
set and owns both exact presentation behaviors. It contains eligibility,
attribute precedence/ownership, input, state, compatibility, slope formatting,
evidence, and rationale rules. The decision and ExecPlan identify it as
normative. The style and accessibility guides now identify themselves as
synchronized guidance and explicitly mark implementation/evidence conformance
pending. The original High finding is closed.

### A11Y-GOV-02 - Closed - Exact scope and dirty-worktree containment

The decision now lists every implementation/test path, both pre-implementation
review artifacts, the final correctness artifact, checkpoint document scope,
all 22 unrelated dirty tracked paths, and the two unrelated same-file hunks. It
requires hunk-aware staging, staged path/diff comparison, and a stop/amend/review
gate for a newly discovered consumer. Current status confirms every listed
implementation/test path is untouched. The original Medium finding is closed.

### A11Y-GOV-03 - Closed - Executable checkpoint ancestry and evidence gates

The ExecPlan now requires the two READY reviews, a documentation-only checkpoint,
recording its full SHA, and `git merge-base --is-ancestor` verification before
the first implementation/test edit. It names focused and full Jest/Python gates,
the exact Playwright spec through supported `--playwright-args`, focused Axe and
AA-theme checks, documentation/diff gates, and a final independent correctness
artifact with no unresolved High/Medium finding. Infrastructure-limited full
Python evidence must be reported accurately with a durable proportional
rationale. The original Medium finding is closed.

### A11Y-GOV-04 - Closed - Bounded slope-display amendment

The operator's added authority is exact and durably recorded. Canonical and
package rules limit the change to numeric `Slope` cells in the two named HTML
tables, preserve missing-value display, and require raw sorting keys, report
objects, model/stored data, unrelated ratio fields, outlet output, and CSV to
remain unchanged. Direct rendered-template evidence is required for numeric,
zero, missing, non-slope-ratio, sort-key, and CSV-wiring states. This is a
presentation-format rule, not scientific parameterization or data migration.
No ADR or additional owner authority is required.

### A11Y-GOV-05 - Low - Documentation command list is narrower than the checkpoint

The ExecPlan's documentation commands name the package, style guide, and
accessibility guide, but omit the new canonical contract and
`PROJECT_TRACKER.md`. Both omitted files were linted directly in this post-fix
review with zero errors or warnings, so checkpoint content is not blocked. Add
those two scoped commands to the recorded closure evidence when the living plan
is next updated.

## Controls accepted

- The operator authority is explicit for both requested presentation behaviors;
  no further ratification is required within the current exact scope.
- Overflow eligibility is one deterministic predicate:
  `clientWidth > 0`, a descendant table, and
  `scrollWidth > clientWidth + 1`.
- Accessible naming, authored-value precedence, description-token ownership,
  generated cleanup, and empty/broken authored-name behavior are deterministic.
- Security impact `none` is proportionate. The proposed module reads local DOM
  geometry and manages local presentation/focus attributes without adding
  input, network, authentication, storage, execution, or authorization
  boundaries. No dedicated security artifact is required.
- Required evidence covers absent, fitting, overflowing, boundary, hidden,
  dynamically inserted, authored/malformed ARIA, cleanup, idempotence, slope,
  sorting, CSV, browser input, zoom/reflow, Axe, and validated-theme focus states.
- The package and plan explicitly exclude push, merge, deployment, and
  production. This review grants none of those actions.

## Checkpoint disposition

**READY.** A11Y-GOV-01 through A11Y-GOV-04 are closed with no remaining High or
Medium governance finding; A11Y-GOV-05 is a nonblocking Low documentation-command
note. The companion post-fix correctness review is READY with no finding. The
documentation-only checkpoint may now be hunk-staged from the exact allowlist
and committed as a standalone descendant of
`75eb240c8dbffea6beb639c9707821d3d877ac2d`. Record and verify its full SHA as an
ancestor before any implementation/test edit. This verdict authorizes no push,
merge, deployment, production action, unrelated dirty hunk, or unlisted path.
