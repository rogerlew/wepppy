# M5 full regression receipt

## Final acceptance — 2026-11-12 00:28 UTC

Final reviewed implementation: `dfab59bb1f34be6810accf79ee1b905e039743fd`.
M0 checkpoint is an ancestor. No implementation changes occurred during the
final gates. All required commands passed:

| Exact command | Final result |
| --- | --- |
| `wctl run-pytest tests --maxfail=1` | 13687 passed, 437 skipped, 6029 warnings; 3829.62 seconds |
| `wctl run-npm lint` | PASS, exit 0 |
| `wctl run-npm test` | PASS, exit 0; 126 suites, 1076 tests |

The Python process continued across an agent-server restart, emitted the final
passing summary, and exited. Its original tool session handle was lost; no
separate shell exit-code receipt is claimed. Complete output is retained in
`20261112_full_pytest_output.txt`; frontend and container receipts have the same
date prefix. Receipt files normalize trailing whitespace only.

Synthetic container acceptance repeated on the final candidate: PASS with the
recorded image, UID 1000/GID 993, network disabled, read-only 0444 secret mounts
and same-process replacement. Dedicated disposable Redis canary acceptance,
focused artifact/readability tests and independent correctness/security/QA
reviews remain PASS. Default full-run skips do not replace those focused gates.

Docs lint, test-stub completeness and broad-exception enforcement pass.
SEC-05 is locally verified; no production deployment or live exposure closure
is claimed. Unrelated working-tree changes remain excluded.

## Earlier attempts and repairs


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
