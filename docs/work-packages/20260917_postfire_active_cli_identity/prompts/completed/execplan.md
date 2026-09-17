# Repair active post-fire CLI identity

Follow docs/prompt_templates/codex_exec_plans.md. Owner requested the fix.

## Purpose / Big Picture


Normal WEPP hard-link creation during an M3 run must not discard unchanged
scientific inputs. Real changes must still prevent stale publication.

## Progress


- [x] Cause identified: only active CLI ctime differs, content identical.
- [x] Contract/checkpoint independent reviews; ancestor `567eacf7d`.
- [x] Failing baseline and bounded implementation with regression.
- [x] Full applicable tests, independent reviews and restarted-worker acceptance.
- [x] Named run recovery, durable docs, evidence and closeout.

## Surprises & Discoveries


The prior contract intentionally retained strict active-worker metadata equality,
even after accepted-result content comparison was repaired. User's overlapping
WEPP/M3 run exposed this missed valid workflow.

## Decision Log


2026-09-17 UTC: narrow exception only for active_cli ctime drift, with unchanged
path/size/mtime, explicit admission-time digest and fresh coherent uncached hash.
Other source metadata, selections, legacy snapshots and artifact guards retain
strict checks. No acceptance-time hash is fabricated.

## Outcomes & Retrospective


Completed 2026-09-17 UTC. Final code `1003fe9ad`; final normal Run job
`0c3bb451-0e7a-4814-95f5-3f1d2f219d49` completed with a current report,
verified attachments and unchanged scientific inputs. Independent correctness
and security PASS. Main full suite 8,971 passed/99 skipped; later corrections
validated with 107 boundary, 21 preparation and two final native legacy cases.
See artifacts/runtime_acceptance.md for precise coverage and retained evidence.

Retrospective: accepted-result currentness tests alone missed active overlap.
Explicit stage coverage must include admission, preparation, pre-publication and
locked publication. Legacy rebasing also must preserve the absence of admission
hashes. These requirements live in the canonical active CLI amendment.

## Context and Plan of Work


Repository /home/workdir/wepppy. Edit production.py and run_preparation.py under
wepppy/nodb/mods/postfire_debris_flow after contract checkpoint. Add one worker
snapshot comparator used at admission, authority checks and preparation rebasing.
Verify changed active CLI through strong signature's descriptor-bound hash;
require observed signature remains equal to current snapshot. Do not reuse the
permissive accepted-result comparator for other source files. Extend real NoDb/
native M3 tests; add adversarial helper tests as needed. Independent reviewers
verify race handling and absence of a general metadata waiver.

## Concrete Steps and Validation


Run wctl run-pytest tests/nodb/mods/test_postfire_debris_flow_runtime_m3.py during
iteration, affected post-fire suites, then wctl run-pytest tests --maxfail=1.
Inspect Docker instructions and canonical deployment entry before restarting
web/rq-worker. Retain actual source-prepared worker run with deliberate normal
WEPP climate materialization overlapping execution on a disposable clone, plus
real-content invalidation. Use normal UI/RQ to recover thespian-cleanness only
after confirmed fixes, protecting earlier acceptance and other project inputs.

## Idempotence and Recovery


Retain failed artifacts and previous accepted records. No new schema or run-wide
cache clear. No rollback requires deleting scientific data. Stop stale candidates
rather than publishing when hash, path or generation verification fails.

## Artifacts and Interfaces


Records under artifacts; project outputs remain in normal browsable attempt
paths and archives. No public API/schema changes. Final docs describe behavior,
limits and exact runtime evidence. Independent review/checkpoint precedes code.

## Validation observations

The native M3 baseline failed at the reproduced publication guard. First eight
hard-link stage cases passed after the fix. Expanded testing exposed M1 mock
sources ignoring content=False and incorrectly treating climate as an uploaded
dNBR dependency; corrected the fixture without weakening upload guards. A race
test needed an observable timestamp delta because adjacent metadata operations
can share a filesystem clock tick. Intermediate failures remain under artifacts.


Runtime acceptance, 2026-09-17 UTC: disposable UI/RQ M3 job
`fa299be5-45b0-448b-b1d1-718445c1529a` accepted after actual WEPP
link/unlink/rematerialization during predictors. Original admitted nanosecond
metadata and hash match retained intervention evidence; CLI ctime alone changed.
Equal-size restored-mtime byte edit in job `5bff6acb-16ad-4252-aeae-f3668c4e3509`
was superseded, retained previous acceptance and browsable diagnostics. Restored
copy CLI; report current again. Canonical archive/restore regression passes.
Source copy required canonical destination fork-marker reset after inherited
job associations blocked its first enqueue. Named retry encountered a transient
submission lock; it expired naturally and queues were idle before normal retry.
All intermediate evidence is retained. Focused suite: 153 passed. Full suite:
9,069 collected, still running.


Named recovery completed 2026-09-17 18:55:56 UTC through the actual Run button:
job `0fd409ce-8e3c-480a-af2c-8a5fd571c7f8`, accepted attempt
`0c7899f7ac6f464e80e3f873a4c75fe1`. Current report survives reload; all five
attachments and original failure records are accessible. Named CLI bytes and
nanosecond metadata unchanged. Implementation commit `2b00c4165` descends the
contract checkpoint. Full-suite gate remains in progress; code is unchanged
since native runtime acceptance.


Final closeout, 2026-09-17 UTC: review-discovered legacy rebase and malformed
snapshot conformance findings are closed in `1003fe9ad`. Native legacy and
boundary tests pass on the final code. The final named report engine fingerprint
matches the frozen source files, all source hashes match the original failed
attempt, and original diagnostics/prior accepted artifacts remain accessible.
The completed plan supersedes earlier in-progress observations above.
