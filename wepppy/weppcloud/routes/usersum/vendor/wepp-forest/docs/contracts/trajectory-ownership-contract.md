# Trajectory Ownership Contract

Date: 2026-05-04
Repository: `/workdir/wepp-forest`

## Normative Status

- This document is normative for subsystem modernization, `.for` to `.f90`
  migration, process-kernel cutover, release/vendoring, and legacy retirement
  work in WEPP.
- It applies to WB-08A first and to every later subsystem rewrite whose outputs
  or state are consumed by another routine.
- It is additive to:
  - `AGENTS.md`
  - `docs/contracts/f90-modernization-strategy.md`
  - `docs/contracts/f90-migration-header-schema.md`
  - `docs/ablation/protocol.md`

## Purpose

Prevent hybrid binaries and hybrid output rows during modernization.

A modernized subsystem may implement scientifically correct process logic while
legacy code remains available for rollback or historical reproduction. That
does not permit mixing fields from both trajectories in one production row, one
routine invocation, or one binary call chain. A mixed row can combine two
internally defensible calculations into an output that has no valid conservation
or physics interpretation.

## Public Release and Modernization Imperative

WEPP modernization is a public-release strategy, not only an internal cleanup.
The imperative for this program is moral, scientific, and strategic: a public
environmental model should be inspectable, reproducible, and defensible by the
people who depend on it. For source units that are works of the United States
Government, 17 U.S.C. 105 states that copyright protection under Title 17 is not
available, and the revision notes state that section 105 places those works in
the public domain. That legal status is context for qualifying federal source
units and permits non-cleanroom rewrites of those core WEPP source units by
allowing direct inspection, translation, and replacement of the existing
implementation. It is not a personal legal duty imposed on non-federal
contributors.

The public-release strategy responds to the model's public scientific role, to
the need for reproducible scrutiny, and to recurring institutional objections
that legacy source is "not ready" or could diverge if released. Divergence has
already occurred in practice. The durable answer is not to keep defective legacy
implementation paths private; it is to replace them with process-oriented,
specification-driven, test-driven code whose provenance and behavior can be
audited. When authorship or source class varies, the project records that
provenance through `docs/contracts/f90-migration-header-schema.md` rather than
using uncertainty as a reason to keep modernization private or blocked.

The available defect evidence from the water-balance campaign shows a defect
rate higher than acceptable for mature scientific infrastructure. The repair
strategy is to make the model process-oriented, specification-driven, and
test-driven, then retire legacy trajectories as soon as their replacement gates
clear. Keeping legacy code active longer than necessary preserves cruft, keeps
known-defective implementation paths reachable, and increases the chance that
future changes will reintroduce hybrid behavior.

Legacy code may remain available as a tagged rollback binary for historical
reproducibility and operational recovery. It should not remain an active,
runtime-selectable production trajectory after the migration acceptance window
closes.

## Definitions

**Trajectory**: a coherent set of inputs, state updates, fluxes, outputs, and
side effects produced by one implementation path for a model step. Examples:
legacy water-balance trajectory, process water-balance trajectory, legacy
sediment trajectory, modernized sediment trajectory.

**Single-trajectory invariant**: a runtime invariant requiring all terms used to
compute a residual, exported row, or downstream state transition to come from
one trajectory.

**Hybrid row**: an exported output row whose fluxes, storage terms, state delta,
or metadata come from more than one trajectory. Hybrid rows are invalid even
when each contributing trajectory is internally consistent.

**Hybrid binary**: a binary whose production call chain combines subsystems from
different trajectories without an explicit compatibility contract and acceptance
gate. A binary may contain inactive legacy code for rollback during a controlled
window, but the active production path must be coherent.

**Rollback binary**: a separately tagged binary that preserves a prior
trajectory for operational recovery or historical reproducibility.

**Migration acceptance window**: a named package interval during which a legacy
runtime toggle may remain available while process-mode release evidence,
downstream compatibility, and rollback tagging are completed. The package must
name the window, owner, and close condition. A package that introduces a runtime
trajectory toggle must remove that toggle before the same package closes. Toggle
removal is a closure deliverable, not a successor-package follow-up; if the
toggle remains, the package disposition is blocked/no-go.

**Observability-only kernel**: a modernized process kernel that emits diagnostic
provenance under an observability flag but does not drive production outputs,
production state, or downstream side effects. Observability-only kernels do not
claim trajectory ownership. Trajectory ownership begins at the first production
output, production state field, or downstream-readable side effect the kernel
drives.

## Single-Trajectory Invariant

The closure audit, runtime kernel guard, runtime export guard, and downstream
consumers evaluate residuals and model state against a single trajectory's
inputs, outputs, and storage.

A binary may support multiple trajectories during migration only if any single
runtime invocation selects one complete trajectory for the affected call chain.
Observability-only kernels may coexist with a legacy production trajectory
because they do not claim production ownership. Any single `H.wat` row,
`H.pass` row, channel row, sediment row, or other exported accounting surface
must be entirely from one trajectory.

The WB-08 water-balance failure is the canonical anti-pattern: process fluxes
were written into production output slots while storage state remained legacy.
The resulting rows were not "partially cut over"; they were invalid hybrid
rows.

## Ownership Scopes

Trajectory ownership is enforced at three nested scopes.

### 1. Subsystem Scope

Within a subsystem, one trajectory owns every exported term and every mutable
state field that downstream consumers read before the next equivalent subsystem
call.

For water balance, process mode owns:

- all fluxes exported to `H.wat` and `H.pass`;
- all storage terms used by output closure;
- soil moisture state such as `st(:,iplane)`;
- snow state;
- interception state;
- frost/frozen-water state when it participates in storage or downstream
  interpretation;
- every common-block or module field mutated by the water-balance routine and
  read by later routines in the same day, event, or simulation step.

A downstream consumer that rejects the process trajectory's state shape is an
integration defect. It is not grounds for hybrid accounting.

### 2. Binary Call-Chain Scope

Within a binary call chain, every active subsystem must consume state from the
same trajectory or, during active modernization only, from a documented
compatibility boundary with its own acceptance gate.

Examples:

- A process water-balance state consumed by legacy sediment during active
  modernization is a compatibility boundary, not an assumption.
- A modernized sediment routine reading legacy water-balance state is a
  compatibility boundary during active modernization, not a free mix.
- Channel routing consuming sediment outputs inherits the sediment trajectory
  unless an adapter contract proves otherwise.

Modernization order follows the call graph. A downstream subsystem should not be
cut over ahead of the upstream state producer it depends on unless a documented
adapter contract closes the trajectory boundary.

Compatibility boundaries are permitted only while one of the two subsystems is
actively under modernization. A binary that ships two stable trajectories
sharing a compatibility boundary in production violates the single-trajectory
invariant by definition. Compatibility boundaries are migration scaffolding, not
a stable release posture.

### 3. Program Release Scope

Across the program, process and legacy trajectories are released as separate,
tagged binary postures. Runtime flags may exist only inside a documented
migration acceptance window and must not become permanent first-class production
modes.

The preferred retirement model is:

1. produce a process-mode release binary;
2. preserve a tagged legacy rollback binary for recovery and historical
   reproducibility;
3. remove runtime trajectory toggles before the package that introduced them
   closes;
4. retire legacy source code once the subsystem and downstream call-chain gates
   are satisfied.

This mirrors existing historical reproducibility practice: legacy parity is
served by tagged binaries, not by keeping defective source paths active forever.

## Prohibited Patterns

The following patterns are forbidden in production cutover code:

- process fluxes with legacy storage;
- legacy fluxes with process storage;
- process output rows built from legacy common-block state unless an adapter
  rewrites all affected state and passes export closure;
- field-by-field production flipping where some exported fields are process and
  others are legacy;
- runtime toggles kept indefinitely without a retirement gate;
- accepting a package that introduced a runtime trajectory toggle while that
  toggle remains in the production path;
- shipping stable production binaries whose stable subsystems share a
  compatibility boundary between different trajectories;
- deleting rollback before the process trajectory release is accepted.

Field-by-field comparison is useful evidence; field-by-field cutover is how the
WB-08 hybrid came back.

## Allowed Migration Patterns

The following patterns are allowed when gated:

- legacy trajectory with process observability only;
- process trajectory owning the full subsystem row and downstream-readable
  state;
- staged cutover by coherent ownership boundary, not by arbitrary scalar field;
- adapter-mediated compatibility boundaries during active modernization when
  the adapter declares all inputs, outputs, side effects, invariants, acceptance
  tests, and retirement condition;
- tagged rollback binaries for operational recovery.

## Retirement Gate

Legacy source for a subsystem should be removed from active development after
all of the following are true:

1. process-mode acceptance closes the defect/benchmark corpus at least as broad
   as the corpus that exposed the original defect class;
2. runtime guards are active on every replayed seed in the acceptance corpus;
3. exported rows and downstream state are single-trajectory;
4. every downstream consumer that reads the subsystem's state accepts the
   process trajectory or has a documented adapter contract;
5. rollback is validated as a tagged legacy binary, not as an indefinite runtime
   flag;
6. vendoring/release handoff is complete;
7. migrated `.f90` source and replacement specs satisfy
   `docs/contracts/f90-migration-header-schema.md`;
8. the package final disposition explicitly authorizes retirement.

Deletion or unlinking is part of the closure gate. It must not be deferred to an
unnamed cleanup package unless a human owner records an explicit follow-up
package and blocker.

A package that keeps legacy source after the retirement gate is satisfied must
record an exception with a named owner, expiration condition, and successor
package. A package that introduced a runtime trajectory toggle cannot close
successfully while that toggle remains in the production path.

## Package Requirements

Every modernization or cutover work package must include:

- `trajectory_ownership_statement.md`;
- `upstream_downstream_consumer_manifest.md`;
- `compatibility_boundary_contract.md`, if any;
- `rollback_binary_tag_plan.md`;
- `single_trajectory_validation_matrix.md`;
- runtime guard evidence with command log and pass/fail records;
- release/vendoring disposition;
- legacy retirement disposition.

Any package that introduces a runtime trajectory toggle must remove that toggle
before closeout. If the toggle remains, the package final disposition must be
blocked/no-go and must not assert release readiness.

## WB-08A Instantiation

WB-08A should be scoped as release-readiness recovery from the WB-08 hybrid
cutover failure.

Required WB-08A posture:

- process mode owns the full water-balance row and every downstream-readable
  water-balance state field;
- legacy mode is available only as a tagged rollback binary or runtime rollback
  during execution; any runtime trajectory toggle introduced by WB-08A must be
  removed before accepted closeout;
- no production row may mix process and legacy terms;
- downstream state consumers must be enumerated and either satisfied by process
  state or repaired;
- the full WB-05B known surface must close at the unchanged `1.0 mm` threshold;
- targeted WB-05C and WB-05F regressions must pass;
- WB-06 downstream compatibility and WB-07 observability/performance guardrails
  must be rechecked.

Required WB-08A evidence packet:

- `artifacts/trajectory_ownership_statement.md`;
- `artifacts/upstream_downstream_consumer_manifest.md`;
- `artifacts/compatibility_boundary_contract.md`, if any boundary remains;
- `artifacts/rollback_binary_tag_plan.md`;
- `artifacts/single_trajectory_validation_matrix.md`;
- `artifacts/process_guard_scoreboard.csv`;
- `artifacts/process_guard_scoreboard.log`;
- `artifacts/runtime_export_guard_evidence.md`;
- `artifacts/downstream_compatibility_recheck.md`;
- `artifacts/release_packet.md`;
- `artifacts/legacy_retirement_disposition.md`;
- final disposition note recording pass/fail state for each acceptance gate.

## Review Checklist

Before approving a trajectory cutover, reviewers must answer:

- Which trajectory owns this row?
- Which trajectory owns every downstream-readable state field?
- Which routines consume that state before the next subsystem step?
- Is any compatibility adapter present, documented, and tested?
- Does rollback use a tagged binary or a bounded runtime toggle?
- What package retires the legacy path?
- Did runtime and post-hoc guards evaluate the same trajectory?

If any answer is missing, the cutover is not ready.
