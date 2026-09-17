# S02 HTTP playback authentication: bounded security disposition

**The proposed additional HTTP verification method is acceptable; canonical
CLI acceptance remains separate and unproven until actually exercised.** This
read-only review confirms the static limitation. It performs no requests,
changes no authentication code and reads no credential/token/cookie files.

## Confirmed code path

- `tools/wctl2/commands/playback.py:151` exposes Cookie/cookie-file inputs and
  sends the optional cookie in the service payload. It has no bearer input.
- `services/profile_playback/app.py:821` creates a fresh Requests session, then
  supplies the cookie or performs the existing WEPPcloud login. The login
  acquires session cookies; it does not mint an RQ bearer. The service passes
  that session to `PlaybackSession`.
- `PlaybackSession._execute_request` uses `self.session.request` without adding
  Authorization. This preserves headers on an explicitly preconfigured session;
  it does not derive bearer credentials from the recorded event.
- The actual `/rq-engine/api/runs/<run>/<config>/tasks/upload-sbs/` route calls
  `require_jwt` and run-access checks. `auth._extract_bearer_token` requires the
  Authorization header and ignores Cookie. RQ mutation middleware likewise does
  not convert cookies; the checked Caddy RQ proxy adds no bearer bridge.

The service, wctl command and RQ auth files have no changes relative to S02
checkpoint `eb2c33b2b`. This is a pre-existing authentication-transport mismatch,
not a consequence of the new event receipt or multipart byte verification.
The expected missing-Authorization response follows directly from this code;
the restarted canonical request/result must still be retained before calling
the runtime failure demonstrated.

## Acceptance disposition

Use the existing `PlaybackSession(session=...)` API with an already authorized
Requests session on the same intended HTTPS origin and disposable target run.
The bearer must pass the unchanged JWT audience/revocation/scope/run-access
checks. Keep expiry/denial responses as failures; do not patch `require_jwt`,
inject claims, replay a recorded token, broaden actor permissions or change the
target route. Supplying valid credentials to the documented session parameter
is ordinary authenticated use, not an auth bypass or a new production pathway.

That real HTTP run can establish the changed S02 claim: two distinct retained
event payloads are verified, encoded and accepted as their respective SBS bytes
by the actual endpoint. Retain request IDs, statuses, disposable target identity,
source/receipt hashes and resulting native pixels/controller state. Verify a
failed/corrupt marked event does not upload a canonical fallback. Do not claim
end-to-end success from Requests preparation or final file bytes alone if the
HTTP response failed.

Retain canonical `wctl run-test-profile` outcome independently. A401 remains a
failed CLI workflow even if the additional bearer-session run passes. The
explicit canonical-method gate in the S02 checkpoint/AGENTS cannot silently be
replaced. Parent closeout must name this pre-existing limitation and explicitly
qualify that acceptance row if using the package's justified-unresolved allowance;
otherwise the row remains incomplete. This does not waive other runtime gates
or authorize expanding S02 into a production authentication redesign. A later
CLI/service bearer workflow needs its own authority/credential-handling contract.

## Evidence hazards in the unchanged runner

`tools/wctl2/commands/playback.py:202` prints the serialized payload, including
the resolved cookie even when `--cookie-file` is used. Do not stream or retain
that raw stderr in ordinary tool output, project artifacts or review logs.
If explicit cookies are necessary for the canonical attempt, capture raw output
only into private0600 temporary storage and redact the cookie field before any
artifact/output copy. Keep credentials out of argv, event records, receipts and
reports. This review flags the concrete existing logger behavior; it does not
claim any secret was exposed in this session or approve that behavior generally.

Also, ordinary HTTP401 is not among wctl's stream error patterns.
`PlaybackSession.run` records such response statuses, while wctl can return0 and
print success merely because a result token/file exists. Therefore inspect the
per-request report and actual target effects, not just shell exit status or the
service's200 streaming response. Preserve the exact contradictory evidence if
it occurs; do not edit the failed record into a successful acceptance result.

Reviewed SHA-256 values:

```text
services/profile_playback/app.py 76149ef3a3e6d2039a11581ced3337ae184b8cb19555a7b5e4d3e516ac94f37f
tools/wctl2/commands/playback.py 08aca178b3071c65d7afcda199a37f9806b358015da2b40fea34ddcb0e960a15
wepppy/microservices/rq_engine/auth.py 89dc09003026bc01f960fb47250849f6009ee2f9ce93a96cb6a9add7891c6b6d
```

## Actual runtime follow-up

The restarted canonical attempt now confirms the predicted failure: two401
uploads for missing Authorization despite CLI exit0/completion text. The
diagnostic cookie payload was redacted. Separately, the existing authenticated
session API delivered both events with200 and exact seed/wire/server byte parity.
Independent actual draft/promoted receipt and permission checks pass. See
[runtime S02 review](runtime_profile_security_review.md) for retained evidence
and the explicit failed-canonical versus passing-changed-boundary disposition.
This follow-up does not change authentication or mark the canonical method passed.
