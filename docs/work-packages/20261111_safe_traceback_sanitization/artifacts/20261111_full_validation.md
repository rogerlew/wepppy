# M5 full regression receipt

Reviewed implementation: `3fea2f06dd7bdacca6813a2b55679e8e99c7514f`.
M0 ancestor: `d6796407f29b4dd7b05031ed89efa416b13a5665`.
M4 independent correctness, security and QA: PASS.

| Exact command | Result |
| --- | --- |
| `wctl run-pytest tests --maxfail=1` | Attempt 1 failed: 677 passed, 29 skipped; fixture repair in progress |
| `wctl run-npm lint` | PASS, exit 0 |
| `wctl run-npm test` | PASS, exit 0; 126 suites, 1076 tests |

Synthetic Docker mount contract rerun on the committed implementation: PASS,
image `sha256:659eb59a98ce2e69a74cd36538b9e392c8e33d66de3c8ee5303e02bd243d01a0`.
No production deployment. Full acceptance and SEC-05 closure remain pending
until the Python command exits zero. Unrelated working-tree changes were
preserved and excluded from the implementation commit.

Attempt 1 stopped at auth lifecycle expected 401/received 503: middleware and
auth Redis constructors captured during collection bypassed the existing
session-level RecordingRedis fixture. A scoped reproduction also exposed the
second auth alias. The test fixture now replaces/restores both captured aliases
without importing services and keeps integration lock files under tmp_path.
No production Redis behavior or authorization code changed. Exact full rerun
is required after focused regression and independent fixture review.

The auth/microservice sweep subsequently reached 1376 passes and exposed
a repeat-rendering defect: an already-redacted assignment gained an extra
closing bracket. A bounded complete-placeholder value match fixes idempotence;
141 focused renderer/project-route tests and independent security review pass.
Existing message expectations now reflect conservative structural token-label
redaction. A diagnostic run excluding slow tests is checking remaining
regressions before the mandatory exact full command is repeated; it does not
replace that command.

The diagnostic run reached 2365 passes before the explicitly real-Redis stream
marker test failed because unit-test secret isolation removed its configured
password-file path. Its scoped fixture now restores path metadata only; actual
Lua, TTL and revocation assertions pass against the authenticated connection
(26 stream tests), with independent QA PASS. No production code changed.

The diagnostic sweep reached 6854 passes before the Roads publication source
hash guard. Three diagnostic-only source changes were independently reviewed;
`analysis_staleness_current.json` now records their current hashes and review
provenance, preserving historical result hashes and the existing scientific
staleness notice. All three publication checks pass. No scientific artifact was
regenerated or represented as current.

The remaining-test sweep exposed the same credential-source cleanup in the
explicit real-Redis declarative DEM tests. The stream-local repair is now a
shared opt-in `runtime_redis_credentials` fixture, also used by confirmed Compose
Redis consumers in RQ dependency, deferred recovery, controlled failure and fork
failure integration tests. Only the password-file path is captured; unit tests
remain isolated, and actual Redis assertions and scoped cleanup are preserved.

Shared fixture focused validation: 113 passed; independent QA PASS. See
`20261111_real_redis_regression.txt` for the unchanged real Redis checks.

The remaining diagnostic sweep stopped after 4723 passes on static auth prose
redaction. The operator rejected “Bearer [REDACTED] required.” as unhelpful.
Independent correctness/security direction review approved a wording-only
conformance repair: clear access-token prose and validation prefixes, unchanged
credential grammar, auth decisions, statuses and exception chaining. Confirmed
peers in rq-engine and browse use the same repair. Tests now require useful
reasons, including dynamic signature/expiration details, and separately prove
appended real credential-shaped canaries still redact. The raw-grammar tests
remain unchanged; no text whitelist was introduced.

Readable-auth focused gate: 378 passed. Broader WEPPcloud/top-level diagnostic
rerun: 2530 passed, 2 skipped, 6 deselected. These diagnostic selections exposed
and repaired concrete compatibility issues but do not replace the exact full
gates, which are repeated on the follow-up candidate.
