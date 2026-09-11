# Batch hillslope-to-watershed task boundary

## Status and authority

Intended behavior approved by Roger Lew's request to execute the
20260910_batch_hillslope_watershed_boundary package. Implementation conformance
is pending. This contract specializes the dependency rules in
[rq-response-contract.md](rq-response-contract.md); NoDb persistence and scoped
mutation-cache contracts remain unchanged.

## Tasks and handoff

Each selected leaf has exactly two ordered jobs on the existing `batch` queue:
`run_batch_hillslopes_rq`, then `run_batch_watershed_rq`. Root `jobs:*` metadata
records both IDs and the batch finalizer waits for terminal watershed jobs.
Stage one waits for successful root dispatch, ensuring the complete chain and
finalizer linkage exist before scientific execution or Omni submission starts.
Stage one owns initialization/resume, base resynchronization, all enabled
preparation through hillslope execution and required hillslope interchange.
Stage two freshly resolves the run directory and hydrates its controllers;
it owns watershed execution, postprocessing, WATAR, Omni linkage, terminal
`run_metadata.json`, and the existing leaf completion trigger.

The watershed job is also the terminal observer of its hillslope predecessor.
Its dependency MAY allow failure solely so it can report an upstream failure.
It MUST NOT perform scientific work or submit Omni unless the predecessor is
finished and a successful durable handoff matches the exact batch, leaf,
hillslope job ID and watershed job ID. Neither `(False, elapsed)` nor timestamps
alone authorize watershed work. A missing, malformed, mismatched or unsuccessful
handoff produces explicit terminal leaf failure, never scientific mutation.
This is the enumerated terminal-observer edge permitted by the shared contract;
failed required outputs are never consumed.

Handoff evidence is written atomically to visible
`batch_handoff/<hillslope-job-id>.json` inside the leaf after stage one returns
successfully. It records schema version, run identity, both job IDs, status,
completion time and process/host observations. The upstream RQ metadata mirrors
the receipt; the run artifact is retained across ordinary retry and archive.
Completion is not inferred merely from file existence. Stage two verifies the
receipt and upstream RQ identity/status before any mutable hydration.

## Failure, retry and cancellation

Stage-one exceptions remain failed RQ jobs with logged traceback. After validating its own task/run identity, stage two
records terminal leaf failure when the expected upstream job failed or its handoff is
invalid. Invalid task identity or foreign job lineage fails at the RQ boundary
with job-local diagnostics only, without creating or modifying a run directory
or terminal metadata. A malformed/missing receipt for an independently validated
leaf records failure only inside that authorized leaf. Stage-two model errors retain the existing `(False, elapsed)` leaf
result and terminal metadata schema. The failure-tolerant batch finalizer must
release after failed leaves; Omni dependencies remain terminal dependencies.
A worker loss before receipt publication cannot authorize downstream work.
A loss after publication but before upstream completion also cannot authorize it.

Ordinary retry preserves completed RedisPrep timestamps and valid model outputs;
explicit full rerun retains its existing reset semantics. Each new attempt uses
new IDs and cannot reuse another attempt's receipt. Existing completed leaves
without receipts remain valid and skip normal retry. Existing deferred graph
reconciliation includes both stage functions. Queued/started/scheduled work
remains a submission conflict; cancellation must never start scientific work
from canceled prerequisites. Canceled deferred chains are detached through the
existing conditional reconciliation before replacement. Cancellation is an
explicit stopped workflow, not a success result. Explicit root/tree cancellation
cancels both stage jobs and the batch finalizer through `jobs:*` traversal; it
emits no success completion and leaves no active/deferred members after
cancellation/reconciliation. Direct cancellation of a stage must retain its
terminal downstream linkage so ordinary retry can reconcile the remaining
workflow. Worker failure/stopping without tree cancellation releases the gated
terminal observer and then the batch finalizer; canceled prerequisite proof
never authorizes scientific execution.

## Compatibility, state matrix and artifacts

No formulas, directives, generated scientific schemas, auth, queue services,
lock ownership or resource limits change. Disabled directives and already
completed timestamps retain their existing behavior, including WATAR-only
retry. Optional absent RAP/OpenET/Ash state remains optional. An empty selection
of retryable leaves enqueues only the finalizer; an absent watershed collection
retains its existing validation failure. Malformed identities and foreign job
lineage must fail before filesystem mutation.

Comparable layout: existing leaf `run_metadata.json` and scientific directories.
Inputs, intermediate/failed model outputs and logs retain their current paths.
The added visible `batch_handoff/` directory is an ordinary project record,
browsable/downloadable and included byte-for-byte in normal archive/restore.
It has no hidden storage or archive exclusion. Full-rerun workspace replacement
retains its existing explicit destructive semantics.

The runtime-state matrix is distinct from the directive/input matrix:

| Runtime state | Required outcome |
| --- | --- |
| Leaf absent, never run | Stage one creates it; fresh attempt receipt gates stage two |
| Leaf present, no timestamps/receipt | Resume enabled preparation; never trust absence as success |
| Populated partial leaf before handoff | Resume missing tasks; retain useful intermediate outputs |
| Populated successful handoff | Exact attempt identity and finished upstream authorize stage two |
| Legacy complete leaf without receipt | Normal selection skips it; no migration required |
| Legacy partial leaf without receipt | New stage one creates new proof after resuming work |
| Optional RAP/OpenET/Ash absent | Skip absent optional mod; do not classify as corruption |
| Optional controller present-empty | Preserve controller validation/execution rules; empty content is not automatically absence |
| Failed/malformed/missing handoff for validated leaf | Explicit failed leaf, no watershed or Omni mutation |
| Malformed task identity or foreign RQ lineage | Job-local failure only; no run-tree writes, including failure handler |
| Explicitly canceled tree | Stopped jobs/finalizer, no completion success; normal retry allowed |
| Working/failed/completed/restored receipt artifact | Visible browser/download and byte-preserving archive/restore; restored proof alone cannot authorize a new attempt |

Directive cases independently include hillslopes disabled, watershed disabled,
both disabled, timestamps already complete, WATAR-only, Omni enabled/disabled,
full rerun, zero selected leaves, and mixed leaf outcomes. Contracted execution
or validation failures stay observable; optional absence is an expected no-op.

Regression evidence must cover both stages, disabled/already-complete states,
WATAR/Omni, failure and retry at either stage, cancellation, duplicate submission,
malformed/missing/foreign receipts, zero selected leaves and mixed outcomes.
Use real Redis/RQ registries for transitions, actual receipt filesystem writes,
and browser/download/archive/restore evidence for the added artifact. Forest
proves separate jobs and processes on existing workers; only the later
openwepp.org integration can establish memory acceptance.

## Rationale

A gated terminal observer preserves the two-job topology and failure-tolerant
summary even after an upstream crash. A strict dependency alone strands that
summary; an unconditional failure-tolerant scientific stage would consume
incomplete outputs. Attempt-bound visible receipts preserve observability and
prevent old success from authorizing a new failed attempt.
