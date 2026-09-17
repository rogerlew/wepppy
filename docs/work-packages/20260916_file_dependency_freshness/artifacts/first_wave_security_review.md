# First-wave implementation security review

Status: **PASS for scoped first-wave implementation security review. Runtime
delivery and final package acceptance remain open.**
Reviewer: independent `freshness_security`, 2026-09-17 UTC.
Checkpoint: `43317704fd046faffac39e114634bb155213c547`.
Cache-admission amendment ancestor: `0fe02dc0f`.

## Findings and review state

| ID | Severity | Evidence / consequence | Required action | Status |
| --- | --- | --- | --- | --- |
| SEC-I01 | Medium, availability | Changed `_digest_version` originally read all 3,145,736 bytes after an 8-byte source grew. | Bound reads by captured size plus bounded growth detection; reject short reads and retain explicit failures. | Resolved: same growth probe now reads 9 bytes and raises `changed_source`; final exact byte-count comparison is present. |
| SEC-I02 / FWC-01 | Medium, confirmed integrity defect in initial implementation | Ordinary rapid rewrites produced equal stat keys and stale cached digests. | Uncached one-second observation; fresh admission; observation-generation key after eviction; retained real-clock collision evidence. | Resolved for the demonstrated sequential same-quantum case under the amended filesystem assumptions. Independent admission tests pass; 966 retained equal-key collisions produced no stale digest after the guard. |

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
descriptor admission. These observations do not constitute final approval;
subsequent cache verification is recorded below.

## Retained intermediate validation

The author's `first_wave_focused.log` reports 135 passed with 15 warnings in
143.45 seconds. It is an interim author run; later edits are not covered. No
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

## Verification after admission amendment

The one-second admission guard is implemented after ancestor `0fe02dc0f`.
`_digest_observed_at` tracks bounded first observation; digests during observation
use the uncached function. Mature cache keys include the monotonic observation
generation, so an old digest surviving observation eviction cannot be reused
for the new observation. Project reads now use `local=True` and the existing
component-wise no-follow reader; trusted engine/tool paths remain distinct.
Strong artifact signatures still bypass cache.

Independent commands and retained results:

```text
wctl exec weppcloud python docs/work-packages/20260916_file_dependency_freshness/artifacts/first_wave_security_probe.py
wctl run-pytest tests/nodb/mods/test_postfire_debris_flow_freshness.py -k 'observation_eviction or rapid_rewrites or warm_digest' --maxfail=1
```

`security_growth_after_bound.log`: the cache probe reads **9 bytes** from the
initially 8-byte file before `changed_source`, instead of 3,145,736. The download
continues to return 409 with bounded reads. Code also checks total bytes read
equal captured size before returning a digest.

`security_admission_tests.log`: **3 passed, 15 deselected** in 9.98 seconds.
These directly cover observation eviction while an old digest survives, rapid
real-file rewrites, and mature zero-hash reuse plus read-permission recheck.

Author-retained `ctime_probe_after_admission.json` records **933 overlay** and
**33 repository** identical-version collisions with **zero stale digest hits**.
The NFS sample found zero identical-version collisions and zero stale hits;
that does not prove NFS collisions impossible. This closes the demonstrated
sequential cache defect under the ADR's explicit filesystem assumptions.

## Revision-3 single-block race classification

`first_wave_focused_revision3.log` retains 14 passing tests followed by failure
of `test_cached_digest_detects_change_during_hash`. Its hook receives and hashes
the complete old six-byte contents, then rewrites the file to another six-byte
value inside the same metadata quantum. The returned digest can therefore name
the **complete earlier contents**. It is not evidence of mixed-generation bytes
and is not a stale cache hit: this access does not admit a digest to the cache.

An advisory point-in-time read can legitimately precede a concurrent write.
The next uncached access must see the new complete contents once the writer has
finished. Retain this explicit characterization and verify no cache admission;
do not replace it with sleeps that make the metadata collision disappear.
Use real atomic replacement, growth, or another observable version change for
deterministic tests that promise guard rejection.

This classification does **not** prove arbitrary concurrent-read coherence.
A multi-block mixed read would be a different case and is not established by
this single-block test. A matching metadata key cannot prove that no write
occurred. The canonical statement that concurrent mutation fails explicitly
must be scoped to observable generation/size drift and existing cooperating
producer/immutable-artifact boundaries; it cannot promise detection of every
uncoordinated write within a timestamp quantum.

Downloads and publication have separate obligations. Keeping the same descriptor
pins an inode but does not freeze it against in-place writes; verifying old
bytes and then streaming changed bytes would not be verified delivery. Do not
generalize the advisory-read characterization into authority to stream
unverified content or publish a mixed input set. Review the actual immutable
artifact/producer protocol and retain the existing strict guards.

## Residual risk and next gate

No unresolved medium/high finding remains in the two scoped cache fixes as
verified above. The canonical Cached digest and read coherence section now
explicitly limits rejection to observable generation/byte-count drift, recognizes
complete earlier point-in-time observations, and preserves immutable artifact
and worker publication boundaries. This resolves the overbroad concurrency
wording identified in this review.

`first_wave_focused_revision4.log` reports **144 passed**, 15 warnings, 145.50
seconds. The deterministic mutation regression now makes its version change
observable; the earlier equal-quantum failure remains retained and classified
above, and the rapid real-clock cache-collision proof remains independently
required rather than replaced with sleeps.

Scoped code security disposition is pass, with zero unresolved scoped findings.
NoDb SEC-M1-01 has its separate implementation review. Final correctness/QA,
performance, rebuilt/restarted UI/RQ/WEPP and archive/restore acceptance remain
required before package closeout. This scoped pass is not runtime or package
approval and does not dispose of other inventory findings.
