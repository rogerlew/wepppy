# S02 profile SBS implementation correctness review

**PASS for scoped correctness after the dispatch and discovery corrections.**
Review covers `sbs_seed.py`, `assembler.py` and `playback.py` after checkpoint
`eb2c33b2b`. No production or test files were edited by this reviewer. Security,
representative performance and real disposable HTTP playback remain separate
acceptance gates; this is not a package/runtime completion claim.

## Findings and disposition

**P-C01, medium, corrected: actual UI upload URLs bypassed event capture.**
`disturbed.js:955` and `baer.js:525` submit `tasks/upload-sbs/`. The new append-time
marker recognized that trailing slash, while `_capture_file_upload` originally
matched only slashless endpoints. Thus a normal UI response was marked as
requiring a seed whose capture was never invoked. The original dispatcher also
missed these URLs before this wave; the new marker made the missing capture an
explicit replay failure. The parent corrected SBS-only dispatch using
`endpoint.rstrip('/')`. Review identified the mismatch statically before the
correction; no pre-correction execution is claimed. The actual paired after-probe
now uses the controller's trailing-slash URL throughout.

**P-I03, medium, independently confirmed in review and corrected by the parent:
lower-priority optional discovery must not invalidate an already selected SBS.**
The intermediate strict exception handling also rejected a Baer lookup failure
after a valid Disturbed candidate was selected. The current conditional fails
only when no higher-priority candidate exists, preserving denied-selected-source
failure without requiring unused lower-priority metadata. The independent
after-probe now sends the valid Disturbed bytes despite an injected optional
Baer PermissionError. Security owns the original failing evidence and its
separate P-I01/P-I02 directory-confinement/denied-selection findings.

No unresolved medium/high correctness finding remains in this bounded review.

## Actual independent evidence

`profile_sbs_implementation_correctness_probe.py` and
`profile_sbs_implementation_correctness_probe_initial.log` retain **11 passed in
9.05s**. The log is the first execution of this probe; both corrections above
were already present. Per-case results remain in `profile_sbs_correctness_*.json`.

The probe executes real assembler append/capture, filesystem receipt handling,
promotion, event loading/indexing, `PlaybackSession.run`, sandbox URL remapping,
form construction and Requests multipart preparation. Controller pointer lookup,
unrelated config setup, playback lock setup and the network transport are
isolated. Payloads are opaque byte fixtures; this establishes upload identity,
not raster decoding, native model results or an HTTP server acceptance result.

- Two same-name source generations produce two marked response records and
  replay their own bytes through the actual paired event IDs. A differing
  `requestMeta.request_id` cannot choose another seed. The accepted suffix,
  `input_upload_sbs` field and existing MIME remain intact.
- Failure during config setup after append leaves a marked response with no
  entry. Promotion preserves its history; replay records an explicit error and
  makes no second request using the prior canonical bytes.
- An unmarked historical event without an event entry keeps canonical-first
  legacy behavior. Boolean, zero, string and null expectation versions fail
  through the existing RequestException/result boundary before dispatch.
- Replacing the seed pathname after verified preparation but before Requests
  encoding changes the file on disk, but the outgoing multipart still contains
  the verified prior bytes. The implementation passes the retained byte value,
  not a pathname that Requests reopens later.
- Repeated delivery cannot overwrite an accepted receipt/payload, including its
  original inode. A source replacement during capture produces visible failed
  status and retains the partial payload; promotion and repeated delivery do
  not bless it, and both paired responses fail without dispatch.
- A valid higher-priority Disturbed selection remains usable when optional
  Baer discovery fails.

## Code assessment and remaining acceptance

New response markers are included in the original draft append before pointer,
config and source work. Event paths derive from the event ID. Capture writes
payload/status/receipt through held directory descriptors, verifies the source
descriptor/path and copied bytes, then publishes receipt and complete status.
An existing entry is validated and compared, never overwritten by a conflicting
delivery. Receipt reading checks schema/version/event ID, fixed payload name,
length and digest, plus the observed record/directory generation. Replay retains
the verified bytes through actual multipart encoding. Strong seed failures
escape the legacy broad form-builder catch as request failures.

This is response-time observation of the existing controller-selected main file,
not proof of the original wire bytes for arbitrarily overlapping uploads. Other
upload families, legacy identity and missing event IDs retain their documented
scope. A failed entry requires a new event identity rather than silently
replacing its failed work. The existing assembler boundary still preserves the
event and reports capture problems through the marker/receipt replay path.

Final performance must include complete primary config handling and the current
directory-descriptor/verification work. The canonical disposable
`wctl run-test-profile` flow, original/sandbox lock cleanup, actual archive
roundtrip and supported service identity remain required. Independent security
must close its own authority findings on these exact files.

Reviewed SHA-256 values:

```text
sbs_seed.py a67475c34382fbd647dfd13b7b4be0f5f3da3be6dd987997af89e0ad5a218b86
assembler.py 881d3963013726e401f5d9cf99c3479d6add3714ddb3ab10ed8743a8bfc94aeb
playback.py 1339b90b9a9de633dc2447b1ac217f1659187cb9682d670c2b2e858c0e4e9c53
```
