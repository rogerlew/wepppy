# S02 after-restart security disposition

**PASS for the changed event-seed capture, promotion and supported authenticated
HTTP dispatch. Canonical `wctl run-test-profile` failed its upload workflow and
must not be reported as passing.** Reviewer: `freshness_security`, 2026-09-17.
No production/test/authentication edits or credential reads were performed by
this reviewer. Overall package closeout remains separate.

## Confirmed canonical limitation

[Canonical CLI log](runtime_profile_canonical_cli.log) now demonstrates the
previously source-traced mismatch: both SBS uploads receive **HTTP401, Missing
Authorization header**, but the CLI exits0 and prints completion success.
The result/stream envelope is not an endpoint acceptance result. Existing
cookie-only CLI/service transport does not satisfy the unchanged RQ bearer
requirement; this behavior predates the S02 change.

The retained diagnostic replaces the cookie payload with an explicit redaction.
No raw credential is needed to assess the response statuses. The separate
[auth disposition](profile_http_auth_security_disposition.md) retains the
unchanged cookie-output hazard and the precise allowed alternative. This review
does not accept that logging hazard as safe, broaden endpoint authentication or
turn a preexisting workflow failure into a successful gate.

Parent closeout must explicitly retain the canonical method as a failed,
justified-unresolved compatibility/transport row if using the package allowance;
otherwise that canonical row remains incomplete. Any later transport or success
classification change needs its own credential-handling/compatibility contract.
The review cannot silently substitute a different client method for that row.

## Actual changed-boundary evidence

The existing authenticated capture/promote routes accepted both real uploads
and promoted the profile. Evidence is retained in
[capture record](runtime_profile_capture.json) and
`runtime_profile_upload_1.json` / `runtime_profile_upload_2.json`.

The parent then executed the existing `PlaybackSession(session=...)` API with
an already authenticated Requests session against the unchanged real RQ upload
route in a unique disposable playback sandbox. The inspected driver delegates
to `requests.Session.request`; it observes the prepared multipart body and
actual server file after each response. It does not fabricate responses or
replace upload authorization. [HTTP acceptance](runtime_profile_http_acceptance.json)
and [wire observations](runtime_profile_http_wire.json) record:

| Event | Actual response | Multipart bytes | Verified seed, wire and server SHA-256 |
| --- | --- | --- | --- |
| `freshness-upload-1` | 200 | 599196 | `7d1ed360d8e639050cf3879293efcdbee216bd9a4faac4e03399442416d97405` |
| `freshness-upload-2` | 200 | 597742 | `a8a42913b4603f4e14b8e4d50556b26ae73b5636ba1ea59c2f72b42e6f46b2c0` |

These are two distinct event payloads despite the same upload role. The original
disposable capture and new playback sandbox are distinct; replayed bytes match
each event rather than the latest canonical seed. Existing JWT/run-access
checks remain the authority. No claim is made that the cookie-only client gained
bearer support.

## Independent external-repository preservation check

Executed as the ordinary restarted service identity:

```text
wctl exec weppcloud python docs/work-packages/20260916_file_dependency_freshness/artifacts/runtime_profile_seed_security.py
```

The [read-only driver](runtime_profile_seed_security.py),
[log](runtime_profile_seed_security_initial.log), and
[complete record](runtime_profile_seed_security.json) retain a first-run PASS
under UID1000/GID993/groups993. It reads only the actual disposable draft and
promoted seed roots, validates both events using production `read_event_seed`,
checks the original response markers are1, and compares byte/mode inventories
before and after. The draft and promoted inventories match exactly.

Both event directories remain0700; receipts/statuses remain0600; payload0644
is protected by the event directory in both trees. The roots are:

```text
/workdir/wepppy-test-engine-data/profiles/_drafts/qa-freshness-profile-7e24c8d1/freshness-http/seed/uploads
/workdir/wepppy-test-engine-data/profiles/qa-freshness-profile-7e24c8d1-sbs-profile/capture/seed/uploads
```

No file in either tree changed during this independent check. These records live
in the profile data repository, not the project tree; project ZIP coverage or
new browser exposure is not implied. Existing profile-owner access policy stays
unchanged. The actual capture contains two successful events, so this runtime
check does not claim a newly failed capture/receipt. Required/missing/failed and
immutable duplicate behavior remains backed by the separately retained direct
implementation probes in [S02 security](profile_sbs_implementation_security_review.md)
and [correctness](profile_sbs_implementation_correctness_review.md).

This accepts the demonstrated changed S02 byte/provenance/authority boundary.
It does not close the failed canonical client row, certify an external profile
archive operation, or replace the other package runtime acceptance results.

Durable operator guidance now lives in
[Profile Test Engine Specification: RQ bearer authentication and outcome verification](../../../../wepppy/profile_recorder/PROFILE_TEST_ENGINE_SPEC.md#rq-bearer-authentication-and-outcome-verification),
with a warning/link in the README's CLI Integration section. It documents the
actual401/false-success limitation, per-request verification, existing
authenticated-session diagnostics on disposable runs and credential-safe log
handling. Documentation only; no auth or CLI behavior changed. Both documents
pass canonical doc lint and have no spelling-normalization diff.
