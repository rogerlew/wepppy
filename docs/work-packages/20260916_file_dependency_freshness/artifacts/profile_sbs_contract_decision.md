# S02 per-event SBS seed checkpoint

Status: draft; implementation pending independent correctness/security review
and representative cost observation. Bounded fix for confirmed successive SBS
upload capture/playback identity, not a redesign of profile manifests.

## Behavior and compatibility

New successful SBS upload response events retain an event-specific immutable
main-file seed under`seed/uploads/sbs/events/<sha256(event-id)>/`. The hash is a
path-safe key, not a secret or content identity. Preserve the original append-only
event first, with additive`_sbs_seed_version: 1` on new eligible SBS response
records in that same original append; do not move JSONL append after fallible
pointer/config/source or seed work. Playback requires evidence for marked events
even if no event directory was created. Before copying, create visible status. A complete receipt version1 binds event
ID, fixed local payload basename, byte length and SHA-256. Copy from the current
controller-selected SBS (existing discovery priority), verify source descriptor/
path generation and captured bytes, and publish complete receipt only after
success. Partial payloads and failed status remain browsable/promotable. Repeated
same-event delivery cannot overwrite a completed different payload silently.
Legacy canonical and named seed snapshots retain their existing compatibility
role; they do not identify new event-specific playback bytes.

Playback threads the paired request/response event ID through multipart assembly.
When an event-specific directory exists, require its valid complete receipt and
matching main bytes. Missing, failed, malformed or mismatched new evidence fails
that request explicitly through the existing RequestException/result boundary;
never fall back to another event or the canonical seed. Only unmarked historical events with no entry keep the old canonical-first reader and its explicitly unverified
historical identity. Do not rewrite old event history or fabricate receipts on
read. Other upload families retain current behavior and separate audit findings.

Receipt paths cannot choose arbitrary filesystem locations: derive directory
from the event ID and constrain the fixed payload basename to that directory
under the existing seed root. Do not place request headers, tokens, cookies,
email or request bodies in receipts. Missing event identity remains a visible
capture limitation, not an invented association.

Prepare the actual event-bound multipart bytes from the verified retained seed
so a later pathname replacement cannot swap what is transmitted. The existing
requests multipart encoder already buffers upload content; preserve MIME/form
fields, endpoint mapping and upload authority. This is not proof that an
arbitrary concurrent upload whose response was delayed is captured from its
original wire stream: the recorder observes the controller-selected file at the
existing response-time capture boundary. Retain that concurrency limitation.

## Acceptance and regression plan

Use actual assembler append/copy/promotion and actual multipart bytes for two
same-name class1→class3 responses. Cover legacy profiles, failed/missing event
snapshot, duplicate event ID, malformed receipt, byte corruption, path escape,
source replacement during copy, receipt/seed replacement before dispatch,
failed capture preserving event history, and promotion/archive preservation.
Run existing profile suites. Retain a real disposable profile and execute its
HTTP playback with canonical`wctl run-test-profile`, using a disposable original
as well as sandbox because the existing playback lock cleanup includes both.
Measure representative capture/dispatch overhead before ratifying a budget;
no new size limit or runtime credential flow is part of this correction.

## Review corrections

Actual config-seed failure after the event append but before directory creation
replayed an older canonical seed after promotion. New append-time expectation
marker closes that distinction without rewriting historical events or creating
a second datastore. Strong receipt errors must escape the existing broad form
builder catch and use the explicit request failure boundary. Retained payload
basename preserves the accepted upload suffix so Requests multipart does not
submit an extensionless/JSON filename. Existing MIME and form fields remain.

## Measured performance decision

Root and independent QA accept the "SBS event performance acceptance" gates in
`PROFILE_TEST_ENGINE_SPEC.md`, pending correctness/security ratification of this
checkpoint. Retained evidence is `sbs_receipts_profile_performance_qa.md` and
`sbs_receipts_profile_performance_baseline.json/.log`; all inputs, controller
hydration and outputs are disposable, with named input hashes/versions unchanged.

Actual established assembler capture measured 14.15–14.51 ms on the two real
0.60/0.75 MB uploads and 67.94 ms on the labeled 16.78 MB stress fixture. Adding
a prototype event receipt/copy/verification measured 32.55–32.91/283.02 ms.
Actual first event/config handling measured 39.27–42.81/154.16 ms, and separate
first-controller lookup 19.12–38.73/22.39 ms. Ratify complete established capture
means of 100/450 ms and initial capture means of 125/550 ms (real/stress). The
first composed capture was not timed and must pass on actual final code, with
complete primary config seed handling. The baseline fixtures exercised actual
active-config/default writes but omitted Grizzly's 34,830-byte primary config;
they do not establish a full first-capture pass.

Existing form/Requests preparation measured 1.39–2.36/41.63 ms; verified receipt/
opened bytes plus actual Requests encoding measured 5.02–6.31/95.79 ms. Ratify
20/150 ms complete preparation means. Both paths read one payload and preserve
exact wire bytes, form field and MIME; Python allocation peaks were about
2.13 payloads. No streaming transport or size cap is justified. Final code must
remeasure actual capture/preparation with complete security guards, record seed
growth and allocation peaks, and retain separate disposable HTTP playback and
promotion/archive acceptance. The prototype does not fulfill those gates.
