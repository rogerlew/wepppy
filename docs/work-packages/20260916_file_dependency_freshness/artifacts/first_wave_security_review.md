# First-wave implementation security review

Status: **HOLD; review incomplete, no implementation approval**.
Reviewer: independent `freshness_security`, 2026-09-17 UTC.
Checkpoint: `43317704fd046faffac39e114634bb155213c547`.

## Findings and review state

| ID | Severity | Evidence / consequence | Required action | Status |
| --- | --- | --- | --- | --- |
| SEC-I01 | Medium, availability | Changed `_digest_version` knows the initial file size but reads to EOF before checking identity. A disposable 8-byte source grew by 3 MiB after admission; the implementation read all 3,145,736 bytes before rejecting it. Repeated growth can prolong a status request hashing mutable project inputs. | Bound reads by the captured size plus bounded growth detection; retain explicit failure, previous acceptance and no-cache-on-failure behavior. | Open against initial reviewed implementation. |
| SEC-I02 | Pending evidence review | The parent reported an ordinary rapid rewrite producing equal stat keys and a stale cached digest. That contradicts the checkpoint assumption that the current metadata key always changes for relevant supported rewrites. | Review concrete reproduction, proposed admission policy, stated filesystem limits, and its warm/cold performance and compatibility effects. | Awaiting contract amendment; no finding closure or approval claimed. |

The RQ download's initially inspected unbounded `hashlib.file_digest` was replaced
during this review with a bounded manual read loop and explicit size comparison.
A disposable growth probe against the revised loop read 1,048,576 bytes, returned
409, and did not consume the remainder. This resolves that inspected download
resource concern; its initial unbounded implementation was not independently
reproduced before the author changed it.

## Scope and interim observations

Reviewed `production.py` digest cache, source snapshot comparison, strong artifact
signatures, `artifacts_current` callers, strict M1/M3 finalizers; RQ accepted-file
download; changed real-filesystem regressions; current contract and author test
log. No production code or tests were edited by this reviewer.

The inspected implementation explicitly passes `strict=True` at existing M1/M3
locked artifact finalizers and keeps strong signature hashing uncached. Source
metadata records remain alongside additive content hashes. Currentness compares
path/size/hash and selections, while legacy snapshots keep exact metadata
behavior. The RQ download retains scopes/run/config/attempt/name authority,
requires recorded SHA-256, and uses the existing all-component no-follow local
descriptor admission. These observations do not settle the newly reported
metadata-key collision or constitute final approval.

## Retained intermediate validation

The author's `first_wave_focused.log` reports 135 passed with 15 warnings in
143.45 seconds. It is an interim author run; edits continued afterward. No
restarted-stack/UI/RQ/WEPP or archive/restore acceptance has been reviewed.

The reviewer ran the retained
[first_wave_security_probe.py](first_wave_security_probe.py) through
`wctl exec weppcloud python`. It uses real disposable files, actual production
functions and hooks scheduling file growth immediately after descriptor
admission; route authentication/state are isolated test doubles. No external
target, named project or credential is accessed.

Observed outputs before the cache-admission amendment:

```json
{
  "download": {
    "initial_bytes": 8,
    "limit_bytes": 1048576,
    "read_bytes": 1048576,
    "response_status": 409,
    "read_exceeded_limit": false
  },
  "cached_digest_growth": {
    "initial_bytes": 8,
    "read_bytes": 3145736,
    "grew": true,
    "error_code": "changed_source"
  }
}
```

The first download-probe run reported zero counted bytes because its read-count
hook wrapped `hashlib.file_digest` after the implementation had already changed
to explicit reads. That run was inadequate measurement, not evidence of zero
I/O. The hook was corrected to count the actual descriptor's reads; the corrected
result above was observed twice.

The parent reported an automated tool failure in the previous review attempt and
requested that it be retained. No exact rejection text or reason was delivered
to this reviewer; none is inferred. No implementation approval was issued.

## Residual risk and next gate

Await the concrete cache-admission contract amendment and independent review of
its valid-workflow guarantee. A delay policy must not silently turn an observed
metadata collision into an unsupported claim of universal filesystem detection.
NoDb SEC-M1-01 remains a separate open package wave. Final correctness/QA,
security finding closure, current test evidence and real workflow acceptance
remain required before package closeout.
