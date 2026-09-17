# S02 profile SBS checkpoint: independent correctness review

**Current disposition: PASS for the revised bounded checkpoint; implementation
and runtime gates remain pending.** No production/test changes or HTTP playback were performed.

## Findings

| ID | Severity / disposition | Required treatment |
| --- | --- | --- |
| PS-C01 | Medium, design blocker | `no event entry => legacy fallback` cannot distinguish a historical capture from a new capture that failed before creating its directory/status. Actual `ProfileAssembler.handle_event` appends the event before pointer/config/seed work; any earlier capture failure can therefore leave a new event with no entry and an older canonical seed. Mark new eligible response records with an additive receipt expectation in their original draft append. A marked record must require its valid event receipt even when the event directory is absent. Old unmarked records retain legacy fallback. |
| PS-C02 | Low, compatibility precision | A fixed local payload basename must not silently change the uploaded filename extension accepted by `upload_disturbed_routes.py`. Preserve a compatible transmitted filename/extension for `.tif`, `.tiff` and `.img` inputs while keeping receipt-derived paths fixed and contained. The MIME value alone does not satisfy the route's extension validation. |
| PS-C03 | Gate pending | Neither representative capture/dispatch cost nor its accepted budget exists yet. Design approval cannot stand in for the required performance checkpoint. |

PS-C01 requires no second datastore or history rewrite. The additive marker can
be attached to the new draft response before its first JSONL append; all subsequent
fallible snapshot work then has a durable missing-receipt interpretation. Preserve
the event's original ID and fields. Do not mark only after successful copy or rely
on creating another sidecar when the first directory creation failed. Unknown or
malformed expectation versions must fail explicitly, not revert to legacy.

The disposable `profile_sbs_missing_entry_probe.py` uses the real assembler,
promotion, form reconstruction and requests multipart encoder, with an injected
unrelated config-capture failure after append and before SBS capture. It is a
bounded baseline probe; its opaque file bytes test selection rather than raster
numerics. Its retained log records **1 passed in 9.05s**: both response events
survive promotion, the new source remains present, no second-event entry exists,
and the encoded multipart contains only the prior seed bytes. It ran after QA
released the isolated raster timing window. The earlier actual raster baseline remains in
`remaining_semantic_baseline_probe.py` and `remaining_semantic_inventory.md`.

## Correct state and error boundaries

Per-event immutable bytes solve the confirmed successive-upload defect; replacing
only the canonical seed would merely select the last upload for every event.
Keep the existing canonical/named snapshots for legacy readers and initial seeds.
Do not reinterpret unrelated config snapshots as current-source caches.

Thread the actual paired `event['id']` from `PlaybackSession.run` through request
assembly. The frontend emits that key; `request_id` in a form summary is not its
canonical association. Validate exact receipt version, event identity, fixed
payload name, integer length and digest before preparing multipart bytes. Repeated
delivery must preserve completed evidence and surface a conflicting duplicate.
Missing event identity cannot be fabricated from loop position or another event.

`_build_form_request` currently catches all exceptions from helpers. A new receipt
failure must still reach the existing per-request `RequestException`/results
boundary without retaining partially selected fallback files. No malformed,
missing, denied or corrupt new receipt may silently send the canonical seed.
Read the actual retained bytes under coherent descriptor/path checks, then pass
those bytes to the encoder; verifying a pathname and reopening later leaves a
different generation available for transmission.

Preserve response-time controller selection and its explicit concurrent-upload
limitation. An event receipt proves the bytes observed at that boundary, not the
original wire payload of an arbitrarily delayed overlapping response. Retain
event-first append and failed/partial snapshot artifacts through promotion.
Receipt content must remain free of request credentials and PII.

## Required evidence before acceptance

Cover real two-event multipart bytes, marked missing entry, permission/config
failure before capture status, failed and malformed receipt, unknown marker,
duplicate event ID, source/captured-path replacement, filename-extension parity,
legacy unmarked profile, and promotion of partial attempts. A real disposable
profile must execute with `wctl run-test-profile`; both its original and playback
run must be disposable because existing lock cleanup touches both. The active
design remains separate from that future HTTP/runtime acceptance.

Reviewed initial draft identities:

```text
PROFILE_TEST_ENGINE_SPEC.md e360ad25731e26081c7592b0014ed780d0d7a6c2a4f9453470e27e1a3feffb2b
profile_sbs_contract_decision.md 162503dfb644c0e195e4f30f69cfa0fe45d809e7bbb167f03f800705e6010f1d
```

## Revised design disposition

The revised canonical draft resolves PS-C01 with `_sbs_seed_version: 1` in the
original append of each new eligible SBS response, before fallible pointer,
configuration, source or seed work. Marked missing entries fail explicitly;
only unmarked historical records without an entry retain legacy fallback.
The decision also requires receipt failures to escape the form-builder catch.
PS-C02 is resolved by preserving the accepted upload suffix in the fixed payload
basename. **The bounded correctness design passes; PS-C03 remains pending, so
this is not implementation-checkpoint or runtime acceptance.**

```text
PROFILE_TEST_ENGINE_SPEC.md f0605a8557d8aeb8e4fe6f79d9028a9707c1823aacc3276f78b6d67ec3b54db8
profile_sbs_contract_decision.md 810d646c1c1dafc1c77d60dea05e016d34dc84c3c5246e00058735041d6c8c23
```

## Measured-budget ratification

PS-C03 is resolved **at checkpoint level** by the retained independent
`sbs_receipts_profile_performance_qa.md` evidence. Established real assembler
work plus composed verified event capture measured 32.55–32.91 ms on the
599/747 KB uploads and 283.02 ms on the labeled 16.78 MB stress raster. The
100/450-ms established-capture gates include existing append/config/legacy work
and new receipt work. Event-bound verification plus actual Requests preparation
measured 5.02–6.31/95.79 ms, supporting the 20/150-ms real/stress gates. Both
paths read one payload and encode the same bytes, field and MIME; Python peak
allocation is about 2.13 payloads, not a process-RSS claim.

The 125/550-ms initial-capture gate is an acceptance target, not an observed
pass: the first composed capture was not timed, and the first baseline omitted
the Grizzly fixture's 34,830-byte primary config seed. The final canonical text
requires the complete configured first-capture workflow to be measured. That
explicit limitation is acceptable before implementation; preserve the missing
measurement rather than subtracting initialization work from final acceptance.
The current evidence does not justify another datastore, streaming protocol,
new size cap or dropping per-event bytes. Archive/promotion, aggregate seed
growth, service permissions and disposable `wctl run-test-profile` remain
required separate gates.

**Final scoped checkpoint: PASS**, with security ratification separately owned.

```text
PROFILE_TEST_ENGINE_SPEC.md 1cab08ddf127a030f12b37343b6ad3a1feb92637d014081d3c35e45e71527358
profile_sbs_contract_decision.md 3c6fe38157925c1631047f283f92c71e690432ac596321d9cc9df44820a988d0
```
