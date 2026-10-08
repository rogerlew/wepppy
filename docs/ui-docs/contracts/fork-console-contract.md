# Fork Console Contract

Status: Accepted and independently reviewed, 2026-10-07.
Implementation locally validated, including full repository tests. Read-only
readiness replay passes on the three affected wepp1 destinations. This document
does not claim deployment.

## Scope and authority

This contract governs fork-console option availability and destination readiness.
The [controller contract](../controller-contract.md),
[RQ response contract](../../schemas/rq-response-contract.md),
[NoDb persistence contract](../../schemas/nodb-persistence-concurrency-contract.md),
and [ADR-0031](../../adrs/ADR-0031-fork-destination-readiness-retry-budget.md)
continue to govern shared behavior. Authorization, CSRF, job arguments, queue
topology, copy/reset execution, and the readiness retry budget remain unchanged.

## Option availability

The server resolves current source state when rendering the console. It must
not create a missing optional controller or materialize scenarios, contrasts,
or SBS artifacts merely to decide whether an option is available.

| Option | Enabled when | Disabled explanation |
| --- | --- | --- |
| Skip Omni Scenarios/Contrasts and reset controllers | Source has configured Omni scenarios or contrasts, or retained scenario/contrast child runs | No Omni scenarios or contrasts to skip. |
| Undisturbify output (optional) | Source has an SBS map usable by the existing disturbed undisturbify workflow | No SBS map to remove. |
| Skip wepp/runs and wepp/output | Always | N/A |

For Omni, configured scenarios, named contrasts, and configured contrast pairs
count even before execution. Retained child runs count independently of
configuration, including supported legacy projects. A real named directory in
either child collection counts even if that named directory is empty; an empty
collection root does not. An enabled mod alone or an empty controller does not
count. Capability discovery
must not load every contrast sidecar or recursively scan model output trees.

For undisturbify, persisted disturbed metadata must identify an SBS map and
either its referenced map or the existing supported `disturbed/sbs_4class.tif`
derived map must be present. Uploaded and generated uniform-severity maps both
count. Preserve supported relative and absolute map references and existing
artifact symlinks. Merely enabling the disturbed mod is insufficient. This change
does not add undisturbify support for BAER-only projects or change model logic.

Capability reads must not hydrate/migrate controllers, write `nodb.version`, or
change source files. Bounded plain-JSON metadata reads of current `py/state` and
legacy flat envelopes are sufficient; do not decode executable object graphs.
Absent optional metadata is normal. Existing nonregular metadata entries,
malformed envelopes/field types, and unreadable state must fail explicitly;
do not follow metadata symlinks or block opening FIFOs. SBS artifact links retain
their existing supported read semantics. Regression evidence must include a
legacy source without `nodb.version` and prove its bytes/paths stay unchanged.

Unavailable checkboxes remain visible, natively disabled, and unchecked, with
their explanation associated through the shared checkbox help mechanism.
True query parameters must not select an unavailable option. Client bootstrap
must preserve this state, and explicit payload assembly must serialize a disabled
option as false even if its checked property was changed programmatically.
Available options retain false defaults and existing query hydration.

Availability is guidance for a newly submitted fork, not an admission rule or
an authorization boundary. Existing API clients and queued jobs retain their
boolean contract. Restoring a tracked job must keep tracking its original job
and destination independently of current source capabilities.

Rationale: disabling an inapplicable action explains the available workflow;
hiding it gives no explanation. Backend compatibility is necessary because
existing tabs, clients, and already-submitted jobs can still request a no-op.

## Destination readiness

Readiness remains read-only. It must authorize the source and destination,
bind the exact fork job to them, require that job to be finished, and verify
the existing core destination files before applying the following Omni rule.
Legacy four-argument jobs and false fifth-argument jobs retain current checks.

For an exact five-argument job with a true skip-Omni flag:

| Destination state | Readiness result after core checks |
| --- | --- |
| No Omni controller and all optional Omni directories absent or real and empty | Ready; the worker's no-op is valid |
| Regular Omni controller and all three required Omni directories real and empty | Ready; existing reset result |
| Regular Omni controller but missing or populated reset directories | Not ready |
| No Omni controller but populated Omni directories | Not ready; inconsistent no-op state |
| Symlink/special controller, directory, or ancestor; unreadable state | Not ready, without following an unsafe entry |

The three directories are `omni`, `_pups/omni/scenarios`, and
`_pups/omni/contrasts`. Missing optional ancestors are allowed only in the
no-controller branch. A dangling symlink is an existing unsafe entry, not
absence. Other `_pups` siblings are irrelevant and must not be inspected or
changed. Directory checks retain descriptor-relative no-follow handling.

Rationale: the worker deliberately skips an Omni reset when `omni.nodb` is
absent. Requiring reset artifacts in that state makes a completed non-Omni
fork permanently fail readiness. Longer retries cannot correct that mismatch.

The response remains `{ready: boolean}`. Success exposes the existing destination
link; false follows ADR-0031's 30-attempt budget and manual retry. Missing
optional state alone must not produce an exception. Existing authorization,
unrelated/missing-job, malformed-run-ID, and transport errors retain their
current explicit response/UI paths. This amendment adds no silent recovery
from corrupt controller data or permission errors.

## Regression obligations

Cover absent, empty, configured-only, populated, legacy, malformed, and hostile
states separately from the eight combinations of fork flags. Render actual
Jinja for disabled/help/checked state, exercise query hydration and client
serialization, and retain existing restored-job and readiness-retry tests.

Exercise readiness against real temporary directory trees, including missing
ancestors, unrelated siblings, symlinks, and special entries. Preserve source
and destination authorization and exact-job binding tests. Recheck the deployed
incident destinations under the web runtime identity using a read-only candidate
check before claiming environment validation. An RQ success or filesystem
existence check alone does not certify model outputs.
