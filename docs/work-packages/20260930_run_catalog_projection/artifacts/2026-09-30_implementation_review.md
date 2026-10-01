# Implementation review and disposition

Status: bounded predeployment implementation and evidence-method PASS;
all findings closed, 2026-10-01 UTC. No deployment approval. Base/checkpoint:
`db8e6be126fb231f16dd5e76f322d2b03089c10c`.

## Independent reviewers

Dirac (`01a0f460-85ce-7b71-9137-0ceea20a52e8`) reviews correctness and
compatibility. Ohm (`01a0f460-864f-7eb3-87aa-d9e763b175f5`) reviews security and
noninterference. Reviews are read-only; static closure is not execution evidence.

## Findings

| IDs | Severity | Finding | Disposition |
| --- | --- | --- | --- |
| M1-01 | High | Actual Ron `py/state` envelope rejected | Closed by Dirac; actual serializer fixture |
| SEC-06 | High | Generated `..` prefix escaped run root | Closed by Ohm; component validation |
| M1-02 | Medium | Batch named omni misresolved | Closed by Dirac; group precedence |
| M1-03 | Medium | Lexical normalization changed symlink/parent semantics | Closed by Dirac; descriptor component traversal |
| M1-04 / SEC-07 | Medium | READONLY incorrectly required readable contents | Closed by both; O_PATH presence |
| M1-05 / SEC-08 | Medium | Disappearing binding became absence/fallback | Closed by both; resolver/source re-verification |
| SEC-09 | Medium | Ancestor replacement escaped binding check | Closed by Ohm; full directory chain |
| SEC-10 | Medium | Trusted root alias source link rejected | Closed by Ohm; canonical and configured alias |
| SEC-11 | Medium | Omni inherited playback precedence | Closed by Ohm; canonical parent mappings |
| M1-06 | Medium | Backoff measured before slow extraction | Closed by Dirac; completion-based retry |
| SEC-12 | Medium | READONLY link equal to project root rejected | Closed by Ohm; exact boundary accepted |
| M1-07 / SEC-13 | Medium | Parent named profile could not have Omni child | Closed by both reviewers |
| M2-01 / SEC-15 | Medium | Batch named omni notification misrouted | Closed by both; grammar-based parent/child; SQL regressions |
| M2-02 / SEC-17 | Medium | Dedicated fork/archive preset lost timestamp integration | Closed by both for staging configuration only; no wepp3 deployment authorized |
| SEC-14 | Medium | Ordinary run token could cancel shared sweep | Closed by Ohm; Admin/Root before fetch, bounded failures |
| SEC-16 | Medium | Unavailable DB driver passed static startup | Closed by Ohm; construct engine without connecting |
| M3-01 | High | Two row-local failures starved later work | Closed by Dirac after SQL backoff and TTL overflow regressions |
| M3-02 | Medium | Unreadable comparison falsely reported parity | Closed by Dirac; explicit inconclusive state |
| SEC-18 | Medium | Matching URI labels falsely proved same database | Closed by Ohm; connection-bound probes and mandatory operator gate |
| M2-03 | Medium | Archive restore did not invalidate projection | Closed by Dirac; real ZIP/SQL regression |
| M2-04 | Medium | Restore canonicalized a trusted root alias before notification | Closed by Dirac; original mapped path retained and aliased ZIP/SQL regression |
| M3-03 | Medium | First diagnostic masked simultaneous unreadable source | Closed by Dirac; readiness counts source states independently |
| SEC-19 | Medium | Alternate export routes leaked reserved-job fetch failure | Closed by Ohm; shared helper boundary plus both export-route canaries |
| SEC-20 | Low | CLI outages omitted mandatory operator-gate fields | Closed by Ohm; both outage branches tested |
| EVD-01 | Low | READONLY timing coupled operation/order and compared removal to no-op | Closed by Dirac; matched initial states, independent counterbalancing, retained 100 samples/mode and passing rerun |
| EVD-02 | Low | Summary omitted the distinct timestamp-only baseline overrun | Closed by Dirac; both distinct failures retained below |

## Release-gate clarification before implementation

The operator's execute-and-hold request remains the authority: no live migration,
restart, activation, or deployment. No acceptance threshold is waived.
Both reviewers accepted the narrower machine/operator split: `technical_ready`
reports automated observations, while the mandatory retained run sheet completes
stage-specific release gates. No new evidence JSON protocol, datastore, daemon,
privilege, or service is added. Canonical sections 6.2, 8 and 11.1 now distinguish
the intact-coordination reader bound and per-run publication fences, and require
connection-bound consumer evidence instead of trusting URI hashes.

Ohm explicitly approved the nonce protocol: actual consumer adapter connection,
fresh held/control exclusive transaction locks, false/true results with origin
lock demonstrably held, explicit cleanup, fail closed on errors, and witness
invalidation after process/configuration/mount/candidate/membership changes.
Dirac approved the technical/operator split and ordering of activation, cutover,
then host-promotion evidence. The new CLI naming/probe helper will follow this
recorded clarification; neither a successful exit nor this artifact authorizes
deployment. This is packaging of existing readiness duties, not a new operator
workflow or a claim that live witnesses have been collected.
Both reviewers independently inspected the canonical clarification text and
returned contract-only PASS before the follow-on CLI behavior was implemented.
Checkpoint: `bf6b0584f7d9a4831576559e9354ff4bb53fa8b6`.
Ohm subsequently returned bounded predeployment security PASS after SEC-19/20
closure; no runtime or deployment approval is inferred.
Dirac returned bounded static functional correctness PASS after M2-04 closure.
Performance evidence and M5 host acceptance remain separate from these verdicts.

## Validation so far

- Focused extractor, real temporary-schema PostgreSQL, SQL reader/browser,
  portable observer, real Redis admission, and RQ route suite: 92 passed.
- Additional real registration commit/rollback and NoDb commit-boundary suite:
  20 passed before subsequent additions.
- Browser: real committed NoDb file → observer → PostgreSQL → HTTP → Chromium
  rendered name and stale/unavailable status. Test app bypasses live login;
  production-equivalent authentication/mount/process proof remains M5.
- Existing frontend lint passed; 112 Jest suites / 919 tests passed.
- Existing broad suite is running. No live application schema was migrated;
  SQL tests create/drop isolated schemas, and Redis tests clean their own queue.
- Broad-exception inventory flags shifted line-based grandfathered boundaries;
  inspect actual diffs before treating these as new catches. New observer and
  reserved-job disclosure catches are deliberate, logged boundaries.

Repeated actual-save timing measured absolute observer p95 around 63 ms when
compared against disabled integration. Profiling 100 callbacks found 2.298 of
3.186 seconds in PostgreSQL commit and 0.211 seconds in cursor execution.
A separate unpaired timestamp-only versus catalog run also failed the added
budget: 21.21 ms versus 84.33 ms (+63.12 ms). This is distinct from the disabled-
baseline issue and remains retained as phase-sensitive variability evidence.
The disabled baseline was inappropriate for the incremental deployment budget:
existing `db_api.update_last_modified` already commits once per NoDb save.
Using the preserved timestamp-only adapter as a conservative baseline measured
22.35 ms save p95 versus 27.19 ms with catalog writes (+4.85 ms), 100 samples
per mode. No runtime durability setting or acceptance threshold changed.
Absolute timings and the failed initial comparisons are retained here rather
than relabeled as production acceptance. Host load/NFS/queue budgets remain M5.

Final targeted functional run passed 487 tests with three performance cases
excluded for separate measurement. The complete SQL suite including repeated
counterbalanced timing and actual legacy-helper characterization passed 24 tests.
Both reviewers accept implementation completion within predeployment scope.
Dirac independently verified the corrected READONLY sample calculation
(+17.376 ms p95) and returned final evidence-method PASS with no remaining findings.
The final reader correction also passed static review and eight executable tests.
Neither static PASS nor isolated timings constitute M5 capacity acceptance or
deployment authorization. The operator's requested pre-forest hold is now reached.
