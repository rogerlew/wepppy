# SURF-20A dependency-failure contract correction

**Starting implementation revision**: `4197be09d`
**Operator approval**: Explicitly granted 2026-08-23 after observing job
`5af82b08-f1af-4180-8613-9917d53ac3f0`: downstream execution after a required
soils-preparation failure is a regression, core dependency tracking must stop
that work, and the fix must preserve frictionless retry.
**Implementation conformance**: Pending

## Discrepancy

Commit `9022acba6` converted broad RQ dependency wiring to
`Dependency(allow_failure=True)`. In the observed WEPP tree,
`_prep_managements_rq` failed because soils were absent, yet every later stage
was released. Hillslope execution, watershed preparation and execution,
interchange generation, analysis, and export then ran against missing required
artifacts. Several consumed their full file-wait timeout before failing.

That behavior conflated workflow termination with dependency correctness. The
already-ratified deferred retry contract supplies the user recovery mechanism:
an ordinary resubmission cancels and detaches the obsolete deferred graph. It
does not require executable descendants of a failed prerequisite to run.

## Normative Correction

1. Dependency edges are strict by default. A stage that consumes or transforms
   upstream output runs only after every required dependency succeeds.
2. `allow_failure=True` is limited to the named terminal observers/finalizers
   and the three enumerated independent-work/request serialization families in
   `artifacts/dependency_edge_matrix.md`. None consumes failed required output.
3. A failed strict dependency may leave downstream jobs deferred. This is an
   expected never-started state, not permission to execute them.
4. Deferred controller workflows remain immediately retryable. Ordinary
   resubmission reconciles, cancels, and detaches the old deferred graph before
   enqueueing replacement work, with no new user action or confirmation.
5. Aggregate polling must continue to report the workflow failure and expose
   retry even while never-started descendants remain raw deferred.

The exact edge dispositions and mixed-version policy are normative in
`artifacts/dependency_edge_matrix.md`.
The operator's 2026-08-23 approval established the strict required-output and
frictionless retry invariants. AgFields routing schemes and Omni contrast
batches were the two exceptions known at that checkpoint. Focused real-RQ
validation subsequently identified consecutive WBT subcatchment submissions as
an existing independent-request serialization edge; the addendum is subject to
fresh correctness and security review and does not authorize any other
executable tolerant edge.

## Valid-State Matrix

- All prerequisites finished: enqueue/release the dependent normally.
- Any required prerequisite queued, started, scheduled, or deferred: dependent
  remains deferred.
- Any required prerequisite failed, stopped, or canceled: executable dependent
  never starts and naturally remains deferred unless an existing owning contract
  explicitly cancels it, as for WBT controlled policy failures.
- Explicit tolerant finalizer or serialization edge whose direct prerequisites
  are all `finished` or `failed`: it may run and must not consume unavailable
  model outputs.
- A stopped, canceled, missing, expired, or malformed tolerant prerequisite is
  not released by RQ's failure-tolerant flag; recovery uses ordinary submission.
- User resubmits after failure: the established SURF-20A admission transaction
  cancels and detaches all safely associated deferred nodes, then records and
  enqueues the exact replacement receipt.
- Malformed, cross-run, cross-operation, or active graph: existing association,
  authorization, and conflict rules continue unchanged.

## Scope and Compatibility

The correction covers the finite sources and every retained exception in
`artifacts/dependency_edge_matrix.md`, including registered-tree aggregation.
Queue names, task signatures, request/response schemas,
authorization, locks, persisted project data, and deferred resubmission behavior
do not change.

Applicable canonical contracts are `docs/schemas/rq-response-contract.md` and
`docs/schemas/output-scope-contract.md` for AgFields scheme isolation. This
correction does not change the controller-state endpoint surface, token
bootstrap contract, or autonomous operator workflow.

## Regression Evidence

- Direct RQ test: a failed prerequisite never releases an executable dependent.
- WEPP pipeline test: one stage-0 failure leaves every transitive executable
  descendant never-started/deferred, including hillslope and watershed runs.
- Finalizer test: an explicitly tolerant terminal observer still runs after all
  direct prerequisites become `finished` or `failed`.
- Per-family failure-to-deferred-to-authenticated-retry evidence proves ordinary
  replacement and production association; shared direct cleanup evidence covers
  cross-run containment and promotion-race safety in the identical WATCH helper.
- Registered-tree tests cover root-finished plus failed child plus blocked
  deferred descendants, viable deferred-only trees, and active-work precedence.
- Mixed-version smoke proves producers are stopped/drained and restarted at one
  revision before strict-edge acceptance.
- Regenerate and check the dependency catalog/static graph, run focused RQ and
  rq-engine tests, then run the substantive repository gate.

## Rationale and Rejected Alternative

Strict execution plus automatic retry cleanup preserves both required outcomes:
bad inputs do not trigger cascades, and users are never required to understand
or cancel RQ jobs. Globally allowing failure was rejected because it converts
dependency ordering into ordering-only and causes downstream code to operate on
artifacts the graph itself says are required.

## Reviews

Two independent read-only reviews of this correction and the amended canonical
contract are required before the standalone documentation ancestor is committed.
