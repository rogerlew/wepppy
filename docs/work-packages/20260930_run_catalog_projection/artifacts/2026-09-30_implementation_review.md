# Implementation review and disposition

Status: in progress; no deployment approval. Base/checkpoint:
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
| M3-01 | High | Two row-local failures starved later work | SQL failure fix tested; follow-up TTL UTC overflow found; fixing and re-review pending |
| M3-02 | Medium | Unreadable comparison falsely reported parity | Closed by Dirac; explicit inconclusive state |
| SEC-18 | Medium | Matching URI labels falsely proved same database | Clarification approved; implementation re-review pending |

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

No M1–M4 completion, final implementation PASS, capacity acceptance, or readiness
to deploy is asserted by this interim artifact.
