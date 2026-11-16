# Omni SBS map reload and resubmission

**Status**: Complete — implementation and scoped/native/browser acceptance passed
**Closed**: 2026-11-16 (local validation; no production deployment)
**Started**: 2026-11-16 19:05 UTC
**Owner**: WEPPcloud maintainers; implementation agent unassigned

## Overview

Users must be able to reopen saved Omni SBS (soil burn severity) scenarios,
see the current map filename, and submit again without uploading the same map.
This package repairs the UI-to-admission round trip and resolves the consumed
upload lifecycle that can independently prevent resubmission.

The user requested a scaffold and issue/decision walkthrough, then explicitly
required contract-first implementation with scoped validation tests. The operator subsequently authorized execution of the plan. Production deployment
is outside this authorization.

## Scope and complexity budget

Include Omni scenario hydration, saved-map display, serialization, run admission,
and only the persisted input/copy lifecycle changes needed for repeat submissions.
Author an independent user-file staging lifecycle contract, with Omni as its
first consumer. Other upload workflows are not enrolled or migrated here.
Reuse existing controls, upload validation, NoDb locking, freshness receipts,
and workers. No new service, queue, dependency, datastore, or protocol is planned.
Start with preserving the saved reference and canonical filename presentation;
resolve the existing map from `_limbo` or its corresponding Omni scenario project.
No new persistent map store or migration is planned.

Exclude numerical parameterization, contrasts redesign, general upload cleanup,
auth changes, queue topology, production deployment, and automatic repair of
existing runs. Parameterization ADR: not applicable within this scope.

## Identified issues

Source inspection at `65fa0c0bd008b16157a82191a766a0bdb9453173` establishes:

1. `controllers_js/omni.js::serializeScenarios` constructs fresh definitions
   from controls and sends a file only when a new File is selected. It does not
   preserve hydrated `sbs_file_path`. The server rejects that submission with
   `Missing SBS file for scenario {idx}`.
2. `createControlElement` already conditionally renders `Current file:` from
   `sbs_file_path`, but as help text. It does not use the canonical `Current SBS
   map` display. The normal reader returns `Omni.scenarios`, and the parser
   persists `sbs_file_path`; therefore complete absence of the filename on the
   reported page still needs browser reproduction, including loaded bundle and
   response inspection. Do not assume the reader always omits the path.
3. `rq_engine/omni_routes.py::_prevalidate_omni_sbs_inputs` requires a claimed
   path, then finds exactly one raster under `omni/_limbo/{idx:02d}`. Meanwhile
   `omni_sbs_freshness.py` consumes the copied source. Returning a saved path
   alone cannot satisfy admission after the temporary source is gone.
4. Admission associates reused files with request row position rather than
   resolving the claimed saved association. Row deletion/reindexing and multiple
   SBS rows require explicit regression coverage for rejection or wrong-map
   selection. These are identified risks, not reproduced incidents.
5. The existing hydration test in `controllers_js/__tests__/omni.test.js` uses
   thinning inputs; it does not demonstrate an SBS reload/resubmit round trip.

Full source paths and the execution sequence are in the [ExecPlan](prompts/completed/implementation_execplan.md).
The original affected project was not identified. A disposable real-project copy
and authenticated browser were inspected during execution; see the validation artifact.

## Contract decisions and rationale

These requirements capture the user's intended outcome and subsequent direction
to keep existing-map reuse simple. Promote them into the canonical contracts
through the pre-implementation checkpoint.

- **Saved versus selected file:** Keep a server-associated saved reference separate
  from the browser File input. An empty file chooser means retain the current
  map. Do not attempt to repopulate a browser file chooser.
- **Presentation:** Reuse `disturbed_sbs_pure.htm`'s `Current SBS map` text display,
  code-formatted basename, and `No map uploaded.` empty state. Render filename
  as text. A selected replacement must be distinguishable from the accepted map;
  a failed replacement must not falsely relabel the accepted map.
- **Replacement precedence:** A new valid upload supersedes the saved association
  after acceptance. No replacement preserves it. Failed validation must retain
  the prior usable association. Verify the actual mutation boundary.
- **Identity:** A saved map belongs to a scenario, not its current row number or
  basename alone. Prefer resolving existing persisted definitions on the server
  before introducing a new public identifier. Never trust a submitted absolute
  path as authorization to read it.
- **Existing-map resolution (user-directed):** When no replacement is selected,
  use the scenario's saved upload in `_limbo` if present; otherwise use the saved
  SBS map in that corresponding Omni scenario project. Resolve the association
  from server-owned scenario state, and apply existing containment and raster
  validation. Do not search unrelated scenarios or choose by basename alone.
  If a rerun resets the child project, stage the selected map before that reset
  using the existing upload/copy machinery.
- **Existing projects:** Apply the same resolution rule to old and new scenarios.
  Absence of a historical verification receipt alone must not force re-upload.
  Validate the file available now; do not invent historical content proof or
  equate input availability with permission to skip model execution. Preserve
  freshness checks when deciding whether prior outputs can be reused.
- **Missing maps:** If neither location supplies the associated map, or the file
  fails validation, explain the problem and request a replacement. No migration,
  new receipt scheme, or separate legacy recovery workflow is planned.

The rationale is to reuse the two locations the existing workflow already owns,
rather than add storage or make users re-upload an available map. The current
freshness contract's missing-source execution rule must be reconciled explicitly
with staging an existing scenario map before reset.

## Shared staging contract deliverable

Create `docs/schemas/user-file-staging-contract.md` as part of this package's
contract checkpoint. The user explicitly approved an independent contract
because `_limbo` can stage user-provided files beyond Omni scenarios. Keep it a
shared lifecycle convention, not a generic storage implementation.

The contract must define project/input ownership and association, validation
before acceptance, replacement failure preserving the accepted input, copy/move
and consumption responsibilities, documented resolution locations, and cleanup
ownership and eligibility. A staging directory or basename alone is not input
identity. Cleanup must not remove an input still needed for an accepted or
in-progress operation; consumers must specify when deletion becomes safe.

Consumers opt into this convention through their domain contracts. Do not imply
that existing upload workflows already conform. The shared contract requires
explicit locations and resolution rules but does not require every consumer to
have a scenario project, use numeric directories, or use SBS freshness receipts.

Omni's domain contract supplies `omni/_limbo` layout, scenario association,
lookup order (associated staged upload, then corresponding scenario map), and
preservation before child reset. The existing freshness contract continues to
own content identity and output-reuse decisions, amended for this input-resolution
rule. Cross-link shared staging, upload admission, and Omni domain contracts so
ownership is clear without duplicating their normative rules.

Acceptance includes both contracts in the reviewed ancestor checkpoint and
scoped Omni tests demonstrating the lifecycle: staging, failed/successful
replacement, consumption, reload/resubmit, and rerun preservation. No generalized
framework, new service, retention timer, bulk cleanup, or migration of unrelated
consumers is authorized. This keeps the reusable rules independent while limiting
implementation and validation to the confirmed Omni failure.

## Contract-first gate

Before code edits, prepare `artifacts/20261116_contract_decision.md` with the
starting revision, exact request/response and lifecycle changes, state matrix,
compatibility plan, and approval provenance. Create the shared staging contract
and `docs/ui-docs/contracts/omni-sbs-control-contract.md` together; reconcile
these current contracts:

- `docs/ui-docs/controller-contract.md` (presentation and lifecycle).
- `docs/schemas/omni-sbs-freshness-contract.md` (identity, consumption, rerun).
- `docs/schemas/upload-endpoint-contract.md` and
  `docs/schemas/request-payload-contract.md` (admission and transport).
- `docs/schemas/rq-response-contract.md` (actionable error responses).
- `docs/schemas/nodb-persistence-concurrency-contract.md` (saved association).
- `docs/ui-docs/contracts/sbs-control-contract.md` as the canonical-control
  reference; it currently covers Disturbed/BAER, not blanket Omni behavior.

Follow `docs/standards/contract-first-change-standard.md`: accepted exact
semantics, two independent read-only contract reviews with disposition, and a
standalone contract ancestor commit before implementation. User direction for
the shared staging contract, two-location resolution rule, and simple
existing-project behavior is recorded above; do not ask for that decision again. Commit authority
is not inferred. Do not edit unrelated dirty contracts.

## Compatibility and regression plan

Prefer existing `sbs_file_path` and unchanged public scenario names and keys.
Before any persisted/schema mutation, record old/new reader compatibility,
legacy handling, fork/archive/restore behavior, rollback implications, and how
references survive row deletion/reindexing. No bulk migration is planned.
Retain content freshness, run containment, validation limits, and same-name
replacement detection. Confirm non-SBS scenarios and batch consumers of the same
admission/parser paths remain compatible; repair confirmed peers only.

## Validation and success criteria

Validation is **scoped**, per the user's explicit instruction. Do not run the
full repository pytest or frontend suites for this package. Use the targeted
commands and browser acceptance in the ExecPlan; expand only for a demonstrated
affected consumer and record why.

- Reload saved SBS rows, see each current basename, and resubmit without uploads.
- Exercise before execution, after source consumption, and dependency-triggered
  rerun states under the accepted contract. Verify the intended raster is used.
- Exercise replacement success/failure, same-name changed bytes, multiple maps,
  deleted/blank preceding rows, type changes, reload/remount, and true missing
  state. No stale map may attach to another row.
- Exercise hostile filenames/paths and cross-run references; preserve valid states
  while rejecting unauthorized or ambiguous inputs before mutation/enqueue.
- Verify real rendered presentation and current generated controller bundle.
- Complete independent correctness/UX and security reviews with no unresolved
  medium/high findings. Review artifacts are implementation deliverables, not
  implied complete by this scaffold.

## Security and artifact evidence

**Security impact: high**, because saved file/path resolution and upload admission
are in scope. A dedicated security review artifact is required. No new authority
or relaxed raster validation is permitted.

Generated-artifact validation applies. Retain browser request and normal-reader
state; inspect the accepted raster and copied child raster semantically and by
main-file digest; inspect generated landuse/soil and `wepp/runs` inputs; run the
relevant scenario and read fresh output/report content. Prove reuse separately
from a forced execution case. Exercise actual filesystem/copy/admission boundaries
without mocks. Record candidate revision, project, runtime identity, mounts,
and configuration. Use a disposable representative project in the dev Compose
environment; identify an affected project only if needed to reproduce unresolved
behavior. Missing environment evidence limits closure claims.

**Current evidence grade:** implemented and locally validated (116 scoped Python
tests plus 2 real NoDb persistence tests, 26 controller tests, scoped ESLint and independent code reviews). Authenticated browser reload/resubmit passed (HTTP 202). Native restoration,
reset, regenerated inputs, and 217 fresh hillslope outputs passed. The user-authorized
fixture repair regenerated stale prepared inputs from unchanged 2007–2024 climate.
Baseline and scenario watershed execution and 22-row report now pass; unchanged
browser resubmission completed its three-job tree. No production deployment or
affected-project incident resolution claim. See [validation evidence](artifacts/validation.md).

## Related history

`20260728_omni_scenarios_ui_contract`, `20260910_sbs_native_upload`, and
`20260810_fork_omni_empty_state_fix` are historical leads only; their closed
records must not be amended as current authority.
