# Predeployment validation — forest candidate

Scope: implementation and isolated validation only. No application schema
migration, restart/recreation, deployment, scheduled sweep activation or read
cutover occurred. Existing development services hosted temporary-schema/owned-
queue tests. This is not forest M5 acceptance or authorization to deploy.

## Test evidence

| Gate | Result and qualification |
| --- | --- |
| `wctl run-pytest tests --maxfail=1 -q` | 10,034 passed, 99 skipped, 12 subtests; 2,394.60 s. Started before final review fixes; not represented as a final-tree broad run |
| Final targeted functional regression | 487 passed, three timing cases deselected; 94.61 s. Catalog, observer, real SQL/HTTP/browser/RQ, polling/export disclosure, scheduler, NoDb, TTL, restore/fork/sync and migration suites |
| Final real PostgreSQL suite including timing cases and legacy characterization | 24 passed; 36.68 s. Separate from the functional run, with overlapping tests; do not sum as unique coverage |
| Portable event module | 11 passed, including forbidden web/SQL imports and actual standalone save with deployment app/database adapter unavailable |
| Frontend | `wctl run-npm lint` passed; 112 Jest suites / 919 tests passed |
| Stubs | `wctl check-test-stubs` and `wctl run-stubtest wepppy.nodb.persistence_events` passed |
| Queue graph | Generated artifacts refreshed; `wctl check-rq-graph` passed; real isolated queued sweep completed and its safe terminal job tree was inspected |
| Compose | Installed development preset `wctl docker compose config --quiet` passed; no service action |
| Broad exceptions | Changed-file enforcement against `origin/master` passed after refreshing moved, preexisting allowlist line references; new broad catches are documented disclosure/post-commit boundaries |
| Quality observability | Observe-only tool ran; local `radon` unavailable and uncommitted changes were not included in its changed-commit analysis. No complexity/parity claim is inferred; generated root reports restored rather than committing unrelated snapshots |
| Docs / whitespace | Scoped lint passed; final lint/whitespace/spelling pass retained at handoff |

Final narrow follow-ups: corrected READONLY timing test passed; reader suite
passed eight tests after restoring the legacy anonymous-owner fallback for
non-integer labels. The added SQL reader regression covers superscript-digit
text, which passes `isdigit()` but cannot be converted with `int()`.
Both independent reviewers returned bounded predeployment implementation PASS;
correctness evidence-method findings are also closed. See the
[implementation disposition](2026-09-30_implementation_review.md).

The actual registration mapper hook is tested through commit and rollback.
Restoration uses a real ZIP and SQL, both direct and trusted-root-alias paths.
Other real boundaries cover concurrent invalidation/deletion, UUID replacement,
per-run lock contention, partial TTL failure, source containment/drift, READONLY
presence without content access, standalone saves and database refusal.

Authenticated PostgreSQL HTTP tests exercise all three JSON surfaces, alias
rejection for ordinary users, authorized admin selection and shared access.
The Chromium test renders the real table template after actual file → observer
→ SQL publication; its isolated app does not replace the separate live-login
acceptance requirement. Map JSON is tested; production map rendering remains
part of M5. No project-I/O helpers may run on tested PostgreSQL reader paths.

## Isolated reader timing

An 805-row authorized-query fixture exercised 100 sequential calls per surface
plus 20 calls on four concurrent threads; real PostgreSQL and Flask response
serialization, warm process, local temporary schema, not authenticated network
TTFB or a production NFS account.

| Surface | p95 | p99 | Payload | Concurrent maximum |
| --- | --- | --- | --- | --- |
| Catalog | 45.15 ms | 245.12 ms | 213,448 bytes | 523.41 ms |
| Map data | 45.51 ms | 259.19 ms | 153,743 bytes | 670.59 ms |

These establish request-path isolation and plausible SQL performance, not the
required real-host browser/network/805-run acceptance.

## Notification timing and retained adverse evidence

Initial sequential comparisons against disabled integration measured absolute
observer p95 around 63–78 ms. A later unpaired timestamp-only versus catalog
comparison also exceeded the incremental 50 ms budget (21.21 versus 84.33 ms).
These outcomes are retained, not erased by later passes. Profiling 100 callbacks
found 2.298/3.186 seconds in PostgreSQL commit, 0.211 seconds in cursor execution.
No durability or threshold change was made.

The correct producer-specific baseline matters: NoDb already commits a timestamp
mirror; TTL/READONLY do not. Counterbalanced/interleaved sampling avoids assigning
time-separated storage phases entirely to one mode. Both complete mutations and
observer durations were measured. Raw samples are retained in
[first counterbalanced run](2026-09-30_notification_timings.json) and
[repeat plus legacy characterization](2026-09-30_notification_timings_repeat.json).

| Repeat measurement, 100 samples/mode | Baseline p95 | Catalog/replacement p95 | Difference |
| --- | --- | --- | --- |
| NoDb complete save; timestamp-only baseline | 36.35 ms | 32.51 ms | -3.85 ms |
| READONLY mutation; corrected matched no-SQL baseline | 0.34 ms | 17.72 ms | +17.38 ms |
| TTL publication; no-SQL baseline | 1.37 ms | 48.46 ms | +47.09 ms |
| Actual legacy timestamp helper versus replacement | 54.65 ms | 31.08 ms | -23.57 ms |

NoDb paired-delta p95 was 14.78 ms; this is distinct from the difference of mode
p95s. The first counterbalanced run also passed: NoDb paired-delta p95 13.67 ms
and TTL +28.45 ms. Earlier READONLY samples coupled deletion/order and included
no-op removal; they remain diagnostic only. The final
[corrected READONLY sample](2026-09-30_readonly_timings_corrected.json) resets
identical initial marker state outside each timed arm and independently
counterbalances operation and mode order (one focused test passed).
TTL's repeat has little margin: retain it
as a host acceptance risk, not a reason to raise the limit. Actual connection-
refusal saves retained committed bytes (repeat 7.83 ms); this is not a blackholed
network worst-case measurement. M5 must measure that case separately.

## Remaining staged gates

Use the [operations guide](../../../dev-notes/run-catalog-operations.md) and
canonical contract section 11.1. Before sweep admission, prove every eligible
consumer's actual database-origin connection and source mounts; matching URI
labels are not proof. Retain mutation witnesses for every producer. Before read
cutover, require technical preflight, full coverage, classified omissions,
semantic comparison and authorized browser parity. Before host promotion,
require actual queue/model-job capacity, notification and authenticated request
latency, full reconciliation, rollback and >=48 healthy hours.

Forest1 application is not the forest companion worker. Additional-host rollout
is not implicitly authorized. Keep public job redaction through rollback for
the full lifetime of retained catalog records. Package closure and legacy-reader
retirement remain pending after this predeployment handoff.
