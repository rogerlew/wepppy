# S02 profile SBS implementation security review

**PASS for the scoped implementation: P-I01/P-I02/P-I03 verified closed.** Review covers uncommitted
`sbs_seed.py`, assembler and playback changes after checkpoint `eb2c33b2b`.
Reviewer: `freshness_security`. Only disposable probes/artifacts were written;
no production/test edits, external endpoints or named project mutations.

## Findings

**P-I01, medium, closed below: validation after payload copying does not confine the
write.** `capture_event_seed` resolves `_member(entry, name)`, then opens that
pathname with `Path.open('xb')`. A replacement of the event directory between
those operations redirects the write outside the seed root. The later `_entry`
check raises ValueError, but the outside payload already exists. This violates
the accepted new event-folder authority. It is a demonstrated local filesystem
boundary failure, not a claim of remote privilege escalation.

Required remediation: bind event payload, status and receipt creation/publication
to a validated held directory and fixed member names, with appropriate no-follow
and descriptor/path identity checks. Preserve existing resolved seed-root and
selected-source authority; do not add a blanket project-root/source symlink
ban. Rejection must not create a file in an unrelated replaced target directory.
Retain partial work in the opened intended event directory and do not silently
change which event or accepted completed receipt it belongs to.

**P-I02, medium, closed below: an access failure can select different SBS bytes and
publish a successful event receipt.** The new event capture reuses the old
best-effort candidate collector in `_snapshot_sbs_upload`. A real PermissionError
while checking the Disturbed-selected file is caught by its broad exception
handler. A readable Baer candidate then becomes first and gets a complete
receipt, although it is not the selected source whose access failed.

Required remediation: event-specific selection must distinguish a genuinely
absent optional controller/source from denial or failed required observation.
Preserve existing selection priority and supported absence fallback, but do not
turn a denied selected path into a successful association with different bytes.
The legacy multi-file snapshots may retain their separate compatibility behavior;
they cannot confer new event-specific provenance. The appended marker must make
the new failed capture explicit at replay, without old canonical fallback.

**P-I03, medium, closed below: the initial denial correction also rejects a valid
selected source because an unused fallback is denied.** The revised collector
still examines Baer after finding a readable Disturbed selection, and now
rethrows its error for the new event. A real inaccessible Baer parent prevents
capture of the valid preferred Disturbed bytes. Strict verification should cover
the applicable selection path, not require unrelated fallback access after the
event source is established. Capture the chosen source separately from later
best-effort legacy multi-file snapshots, preserving both selection priority and
denial of an actually needed source. No broad fallback or permission bypass is
required to fix this valid-state regression.

## Actual evidence

```text
wctl run-pytest docs/work-packages/20260916_file_dependency_freshness/artifacts/profile_sbs_implementation_security_probe.py -v -s
```

`profile_sbs_implementation_security_probe.log`: **2 failed, 4 passed in 8.97 s**.
All fixtures are disposable ordinary files. These security checks exercise actual
filesystem access/copy and receipt readers; they do not claim native raster
validation or whole HTTP playback acceptance.

`profile_sbs_security_capture_directory_swap.json` records an actual directory
rename/symlink replacement at the pathname-open boundary: capture raises, the
original working status remains retained, but `outside/input_upload_sbs.tif` is
written. The source and outside directory are temporary probe fixtures.

`profile_sbs_security_denied_selection.json` records actual mode0000 denial on
the selected source parent under ordinary UID 1000. Controller acquisition alone
is supplied by fixture objects; selection, stat, copying and receipt validation
are real. No error is raised and the complete event contains `different fallback
bytes` from Baer. This is not a simulated permission exception.

Passing controls establish that an initially outside-root event alias is
rejected without writes; receipt payload traversal is rejected; different-byte
redelivery cannot overwrite a completed seed; marked missing evidence fails
while unmarked historical absence remains the legacy path. These passes do not
close the races or fallback finding.

## Other reviewed boundaries and remaining gates

The assembler now marks eligible response records in their original draft append
before pointer/config/source work. Playback carries paired event IDs, propagates
RequestException through the generic form-builder boundary, and hands the same
verified `SbsSeed` bytes to Requests rather than reopening the payload path.
The fixed basename retains the upload extension and octet-stream MIME. Receipt
fields add no headers, credentials or request bodies. These are consistent with
the checkpoint; actual assembler failure/promotion/multipart and HTTP runtime
evidence remains necessary.

Before scoped approval, verify P-I01/P-I02 fixes and recheck immutable duplicate
and failed capture behavior, receipt/seed replacement before dispatch, supported
source/root aliases and legacy paths. Final performance must include the actual
confinement operations; prototype timings do not certify them. Observe complete
first-capture config handling, seed growth, memory and promotion/archive. The
separate A-S01 project archive directory-mode finding remains a cross-wave gate;
this review does not waive it or authorize hidden/excluded profile artifacts.

## Descriptor correction after-probes

The helper now walks no-follow components from the selected resolved seed root,
holds directory descriptors through copy and record publication, uses fixed
no-follow members, and rechecks current directory identity before acceptance.
Source and seed-root aliases retain their existing authority. It verifies
copied bytes and rechecks selected source SHA through the shared recent-file
admission policy. P-I01's adapted probe replaces the event directory at the
actual `os.open(..., dir_fd=...)` boundary: copying stays in the original held
directory, failed status is retained there, the outside directory receives no
payload and capture rejects the changed selection. P-I01 is closed.

`profile_sbs_implementation_security_probe_revision2.py/.log`: **7 passed,
1 failed in 9.38 s**. The denied primary now fails without creating a successful
fallback receipt, closing P-I02. Existing root/source aliases, outside initial
alias rejection, malformed receipt confinement, duplicate immutability and
legacy/required absence controls pass. The one failure is P-I03; its actual
permission result is retained in
`profile_sbs_security_unused_baer_denial_revision2.json`. Original failing
scripts/logs/results remain separate. No final scoped approval yet.

## Final selection correction and scoped disposition

`profile_sbs_implementation_security_probe_revision3.py/.log`: **8 passed in
8.94 s**. The strict collector now propagates nonmissing failures only while no
preferred candidate has been selected. Actual denial of the needed primary
still fails, while denied unused Baer access does not invalidate an established
Disturbed selection. P-I03 is closed. The held-directory replacement, immutable
duplicate, required/legacy absence, receipt confinement and supported source/root
alias controls all pass again. Earlier failures remain unmodified.

The separate independent correctness review retains 11 actual append, promotion,
paired `PlaybackSession.run` and Requests probes, including replacement after
verification without changing dispatched bytes. Together with the reviewed
bytes-valued multipart path, that supplies the requested final-dispatch evidence;
this security review does not claim a live HTTP request or native raster decode.

No unresolved medium/high finding remains in this bounded S02 implementation.
Actual complete first-capture performance, service identity/HTTP workflow,
promotion/archive and cross-wave A-S01 acceptance remain separate gates.

Reviewed SHA-256 values:

```text
sbs_seed.py a67475c34382fbd647dfd13b7b4be0f5f3da3be6dd987997af89e0ad5a218b86
assembler.py 881d3963013726e401f5d9cf99c3479d6add3714ddb3ab10ed8743a8bfc94aeb
playback.py 1339b90b9a9de633dc2447b1ac217f1659187cb9682d670c2b2e858c0e4e9c53
```
